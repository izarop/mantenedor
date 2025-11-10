from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.contrib import messages
from functools import wraps
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import AuthenticationForm
# Importaciones de tus modelos/formularios (Asegúrate de tener ROL_* en models.py)
from .models import CalificacionEncabezado, CalificacionFactores
from .forms import CalificacionEncabezadoForm, CalificacionFactoresForm, RegistroForm 
from .models import ROL_ADMIN, ROL_ANALISTA, ROL_CORREDOR, ROL_SUPERVISOR

# =================================================================
# DECORADOR DE AUTORIZACIÓN (RBAC)
# =================================================================

def rol_requerido(roles):
    """
    Decorador que comprueba si el usuario tiene al menos uno de los roles dados.
    """
    def decorator(view_func):
        @wraps(view_func)
        def _wrapped_view(request, *args, **kwargs):
            if not request.user.is_authenticated:
                messages.warning(request, "Debe iniciar sesión para acceder.")
                return redirect('login') 
            
            try:
                user_rol = request.user.perfil.rol
            except Exception:
                messages.error(request, "Error de perfil de usuario. Contacte a soporte.")
                logout(request)
                return redirect('login')

            if user_rol in roles:
                return view_func(request, *args, **kwargs)
            else:
                messages.error(request, "No tiene permisos para acceder a esta función.")
                return redirect('calificacion_list') 

        return _wrapped_view
    return decorator

# =================================================================
# VISTAS DE AUTENTICACIÓN
# =================================================================

def register_view(request):
    if request.user.is_authenticated:
        return redirect('calificacion_list')
        
    if request.method == 'POST':
        form = RegistroForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user) 
            messages.success(request, f"¡Bienvenido/a {user.first_name}! Cuenta creada y has iniciado sesión.")
            return redirect('calificacion_list') 
        else:
            messages.error(request, "Error en el registro. Revise los campos.")
    else:
        form = RegistroForm()
    return render(request, 'register.html', {'form': form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect('calificacion_list')
        
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            messages.success(request, f"¡Bienvenido/a! Has iniciado sesión correctamente.")
            return redirect('calificacion_list')
        else:
            messages.error(request, "Nombre de usuario o contraseña inválidos.")
    else:
        form = AuthenticationForm()
    return render(request, 'login.html', {'form': form})


def logout_view(request):
    logout(request)
    messages.info(request, "Has cerrado sesión correctamente.")
    return redirect('login') 


# =================================================================
# VISTAS DE CONTENIDO CON RBAC APLICADO
# =================================================================

@login_required(login_url='login')
def calificacion_list(request):
    qs = CalificacionEncabezado.objects.select_related('factores')

    try:
        # COMENTADO: Mantiene el acceso global por ahora, para confirmar que los datos se muestren.
        pass
    except Exception:
        pass 

    mercado = request.GET.get('mercado', '').strip()
    origen = request.GET.get('origen', '').strip()
    periodo = request.GET.get('periodo', '').strip()
    pendiente = request.GET.get('pendiente', '').strip() 

    if mercado:
        qs = qs.filter(mercado__iexact=mercado)
    if origen:
        qs = qs.filter(origen__iexact=origen)
    if periodo:
        qs = qs.filter(anio=periodo)
    if pendiente == '1':
        qs = qs.filter(pendiente=True)

    return render(request, 'index.html', {'items': qs})

@rol_requerido([ROL_ADMIN, ROL_ANALISTA, ROL_CORREDOR])
def calificacion_create(request):
    if request.method == 'POST':
        form = CalificacionEncabezadoForm(request.POST)
        if form.is_valid():
            enc = form.save()
            CalificacionFactores.objects.get_or_create(encabezado=enc)
            messages.success(request, "Calificación ingresada con éxito. Continúe con Factores.")
            return redirect('calificacion_factores', pk=enc.pk)
    else:
        form = CalificacionEncabezadoForm()
        
    return render(request, 'calificacion-ingresar.html', {'form': form})

@rol_requerido([ROL_ADMIN, ROL_ANALISTA])
def calificacion_edit(request, pk):
    enc = get_object_or_404(CalificacionEncabezado, pk=pk)
    if request.method == 'POST':
        form = CalificacionEncabezadoForm(request.POST, instance=enc)
        if form.is_valid():
            form.save()
            messages.success(request, "Encabezado modificado. Ahora puedes editar los factores.")
            
            # --- MODIFICACIÓN CLAVE: REDIRIGIR A FACTORES ---
            return redirect('calificacion_factores', pk=enc.pk)
            # -----------------------------------------------
            
    else:
        form = CalificacionEncabezadoForm(instance=enc)
        
    # NOTA: Debes asegurarte de pasar el contexto corregido (mercado_choices, origen_choices)
    context = {
        'form': form,
        'enc': enc,
        'mercado_choices': CalificacionEncabezado.MERCADO_CHOICES, 
        'origen_choices': CalificacionEncabezado.ORIGEN_CHOICES,   
    }
    return render(request, 'calificacion-editar.html', context)

# Factores / Calcular (Admin, Analista pueden editar; Supervisor solo ver/consultar)
@rol_requerido([ROL_ADMIN, ROL_ANALISTA, ROL_SUPERVISOR]) 
def calificacion_factores(request, pk):
    enc = get_object_or_404(CalificacionEncabezado, pk=pk)
    factores, _ = CalificacionFactores.objects.get_or_create(encabezado=enc)

    can_edit = request.user.perfil.rol in [ROL_ADMIN, ROL_ANALISTA]

    if request.method == 'POST' and can_edit:
        enc.ingreso_por_montos = bool(request.POST.get('ingreso_por_montos'))
        enc.save(update_fields=['ingreso_por_montos'])

        form = CalificacionFactoresForm(request.POST, instance=factores)
        if form.is_valid():
            f = form.save()
            
            try:
                # Esto requiere que implementes f.todos_en_cero() en CalificacionFactores
                enc.pendiente = f.todos_en_cero() 
            except AttributeError:
                enc.pendiente = False 
                messages.warning(request, "Advertencia: Falta la función 'todos_en_cero' en el modelo.")

            enc.save(update_fields=['pendiente'])
            messages.success(request, "Factores grabados con éxito.")
            return redirect('calificacion_list')
    else:
        form = CalificacionFactoresForm(instance=factores)

    return render(request, 'calificacion-factores.html', {
        'form': form,
        'enc': enc,
        'can_edit': can_edit 
    })

# Vistas de carga (Solo Admin y Analista)
@rol_requerido([ROL_ADMIN, ROL_ANALISTA])
def carga_factores(request):
    return render(request, 'carga-factores.html')

@rol_requerido([ROL_ADMIN, ROL_ANALISTA])
def carga_montos(request):
    return render(request, 'carga-montos.html')

# Vista extra por conveniencia (Mapea la URL raíz a la lista principal)
def index(request):
    return redirect('calificacion_list')


# NOTA: Usaremos ROL_ADMIN y ROL_ANALISTA (1 y 2) para permitir la eliminación operativa
@rol_requerido([ROL_ADMIN, ROL_ANALISTA])
def calificacion_delete(request, pk):
    # La eliminación debe realizarse mediante POST por seguridad (CSRF)
    if request.method == 'POST':
        enc = get_object_or_404(CalificacionEncabezado, pk=pk)
        
        # Eliminar el registro (Django se encarga de eliminar también los factores por CASCADE)
        enc.delete()
        
        messages.success(request, f"La Calificación ID {pk} ha sido eliminada permanentemente.")
        return redirect('calificacion_list')
    
    # Si alguien intenta acceder por GET, lo redirigimos o mostramos un error
    messages.error(request, "Método no permitido para la eliminación.")
    return redirect('calificacion_list')