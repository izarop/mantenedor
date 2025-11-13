from math import isfinite
import pandas as pd
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
from .forms import CalificacionEncabezadoForm, CalificacionFactoresForm, RegistroForm, CargaFactoresForm 
from .models import Perfil, ROL_ADMIN, ROL_ANALISTA, ROL_CORREDOR, ROL_SUPERVISOR
from decimal import Decimal, InvalidOperation
from django.utils import timezone
import io
from django.views.decorators.http import require_http_methods
import json


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

# ... (código anterior)

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
        # return render(request, 'calificacion-editar.html', {'form': form})
        
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


# ===========================
# CARGA MASIVA: ENCABEZADO + FACTORES
# ===========================

# Columnas de factores (modelo usa f19a)
FACTOR_COLS = [f"f{i:02}" for i in range(8, 19)] + ["f19a"] + [f"f{i:02}" for i in range(20, 38)]

# Columnas mínimas para crear/actualizar el encabezado
HEADER_COLS = [
    "mercado", "origen", "instrumento", "evento_capital",
    "valor_historico", "fecha_pago", "secuencia_evento",
    "anio", "factor_actualizacion", "sfut", "descripcion"
]

# Si viene, se usa para actualizar; si está vacío, se crea el encabezado
REQ_COLS = ["encabezado_id"] + HEADER_COLS + FACTOR_COLS

def _df_from_uploaded(file):
    content = file.read()
    for enc in ("utf-8-sig", "latin-1"):
        try:
            return pd.read_csv(io.BytesIO(content), encoding=enc)
        except Exception:
            continue
    raise ValueError("No se pudo leer el CSV. Verifique codificación o separador.")

def _to_bool(x):
    s = str(x).strip().lower()
    return s in ("1","true","t","si","sí","y","yes")



def _validate_df(df):
    errors = []

    # normaliza encabezados (evita espacios accidentales)
    df.columns = [str(c).strip() for c in df.columns]

    # 1) Columnas obligatorias
    faltantes = [c for c in REQ_COLS if c not in df.columns]
    if faltantes:
        errors.append(f"Columnas faltantes: {', '.join(faltantes)}")
        return errors  # no seguimos si faltan columnas

    # 2) Tipos numéricos, rango 0..1 y máx 8 decimales
    for col in FACTOR_COLS:
        # fuerza numérico; valores inválidos -> NaN
        df[col] = pd.to_numeric(df[col], errors='coerce')

        # rango 0..1 (NaN se ignoran aquí, se validan en decimales)
        fuera_rango = df[(df[col] < 0) | (df[col] > 1)]
        if not fuera_rango.empty:
            idxs = ", ".join(map(str, (fuera_rango.index[:5] + 1).tolist()))
            errors.append(f"{col}: hay valores fuera de 0..1 (filas: {idxs}...)")

        # máximo 8 decimales
        def _dec_ok(v):
            try:
                # rechaza None/NaN/inf
                if v is None:
                    return False
                fv = float(v)
                if not isfinite(fv):
                    return False

                d = Decimal(str(fv))
                # por si acaso: NaN/Inf en Decimal
                if not d.is_finite():
                    return False

                exp = d.as_tuple().exponent
                # en Decimals “normales” exponent es int; si no lo es, inválido
                if not isinstance(exp, int):
                    return False

                decs = -exp if exp < 0 else 0
                return decs <= 8
            except Exception:
                return False

        malos_dec = df[~df[col].apply(_dec_ok)]
        if not malos_dec.empty:
            idxs = ", ".join(map(str, (malos_dec.index[:5] + 1).tolist()))
            errors.append(f"{col}: más de 8 decimales o valor inválido (filas: {idxs}...)")

    # 3) Suma global f08..f37 entre 0 y 1 (ignora NaN como 0 para la suma)
    df["_suma_factores"] = df[FACTOR_COLS].fillna(0).sum(axis=1)
    bad_sum = df[(df["_suma_factores"] < 0) | (df["_suma_factores"] > 1)]
    if not bad_sum.empty:
        idxs = ", ".join(map(str, (bad_sum.index[:5] + 1).tolist()))
        errors.append(f"Suma de factores fuera de [0..1] (filas: {idxs}...)")

    return errors




@require_http_methods(["GET", "POST"])
@login_required(login_url='login')
def carga_factores(request):
    """
    Sube CSV -> muestra tabla editable con encabezado_id y f08..f37.
    Permite corregir en la misma vista antes de confirmar.
    """
    form = CargaFactoresForm()
    columns, rows = None, None  # para renderizar tabla editable

    if request.method == "POST" and request.FILES:
        form = CargaFactoresForm(request.POST, request.FILES)
        if form.is_valid():
            try:
                df = _df_from_uploaded(form.cleaned_data['archivo'])
            except Exception as e:
                messages.error(request, f"No se pudo leer el archivo: {e}")
                return render(request, "carga-factores.html", {"form": form})

            # validación (muestra mensajes, pero igual seguimos para permitir edición)
            errs = _validate_df(df.copy())
            for e in errs:
                messages.error(request, e)

            # ordenar/filtrar columnas a las requeridas
            faltantes = [c for c in REQ_COLS if c not in df.columns]
            if faltantes:
                messages.error(request, f"Columnas faltantes: {', '.join(faltantes)}")
                return render(request, "carga-factores.html", {"form": form})

            df = df[REQ_COLS].copy()

            # convertir NaN -> '' para inputs; no redondeamos aún para que el usuario lo corrija
            df = df.astype(object).where(pd.notna(df), "")

            columns = REQ_COLS[:]  # encabezado_id + f08..f37
            rows = df.to_dict(orient='records')

            # guardamos en sesión por si el usuario cierra sin confirmar
            request.session['factores_csv'] = df.to_json(orient='records')

            messages.info(
                request,
                "Vista previa generada. Puedes corregir valores aquí y luego confirmar."
            )

    return render(
        request,
        "carga-factores.html",
        {"form": form, "columns": columns, "rows": rows}
    )


# =======================
# CONFIRMACIÓN Y GUARDADO
# =======================
@require_http_methods(["POST", "GET"])
@login_required(login_url='login')
def confirmar_carga_factores(request):
    """
    Recibe JSON (desde la tabla editable) o, en fallback, lo que quedó en sesión.
    Vuelve a validar en servidor, normaliza a 8 decimales y guarda.
    """
    # 1) Origen de datos
    if request.method == "POST" and request.POST.get("data_json"):
        data_json = request.POST["data_json"]
    else:
        data_json = request.session.get("factores_csv")

    if not data_json:
        messages.error(request, "No hay datos para confirmar. Sube un CSV primero.")
        return redirect("carga_factores")

    try:
        # data_json puede venir como lista JSON o como DF.to_json
        data = json.loads(data_json)
        df = pd.DataFrame(data)
    except Exception:
        try:
            df = pd.read_json(io.StringIO(data_json))
        except Exception as e:
            messages.error(request, f"No se pudo interpretar los datos: {e}")
            return redirect("carga_factores")

    # 2) Validación servidor (tipos/rangos/decimales/suma)
    #    - Forzamos numéricos y redondeamos a 8; rechazamos vacíos o no numéricos
    hard_errors = []

    # encabezado_id
    try:
        df["encabezado_id"] = pd.to_numeric(df["encabezado_id"], errors="coerce").astype("Int64")
    except Exception:
        hard_errors.append("encabezado_id inválido (no numérico).")

    # factores
    for col in FACTOR_COLS:
        df[col] = pd.to_numeric(df[col], errors="coerce")
        if df[col].isna().any():
            bad = df[df[col].isna()].index[:5] + 1
            hard_errors.append(f"{col}: celdas vacías o no numéricas (filas: {', '.join(map(str, bad))}...)")
        # rango
        fuera = df[(df[col] < 0) | (df[col] > 1)]
        if not fuera.empty:
            bad = fuera.index[:5] + 1
            hard_errors.append(f"{col}: valores fuera de 0..1 (filas: {', '.join(map(str, bad))}...)")
        # normalizamos a 8 decimales
        df[col] = df[col].round(8)

    # suma por fila 0..1
    df["_suma"] = df[FACTOR_COLS].sum(axis=1)
    fuera_suma = df[(df["_suma"] < 0) | (df["_suma"] > 1)]
    if not fuera_suma.empty:
        bad = fuera_suma.index[:5] + 1
        hard_errors.append(f"Suma f08..f37 fuera de 0..1 (filas: {', '.join(map(str, bad))}...)")

    if hard_errors:
        for e in hard_errors:
            messages.error(request, e)
        # devolvemos al editor con lo que el usuario ya tenía
        columns = REQ_COLS[:]
        rows = df[REQ_COLS].astype(object).where(pd.notna(df[REQ_COLS]), "").to_dict(orient="records")
        return render(request, "carga-factores.html", {
            "form": CargaFactoresForm(),
            "columns": columns,
            "rows": rows
        })

    # 3) Guardado
    ok, err, no_enc = 0, 0, []
    for _, row in df.iterrows():
        try:
            enc_id = int(row["encabezado_id"])
            try:
                enc = CalificacionEncabezado.objects.get(id=enc_id)
            except CalificacionEncabezado.DoesNotExist:
                no_enc.append(enc_id)
                continue

            fac, _ = CalificacionFactores.objects.get_or_create(encabezado=enc)

            # set f08..f37 con Decimal cuantizado
            for i in range(8, 38):
                v = Decimal(str(row[f"f{i:02}"])).quantize(Decimal("0.00000000"))
                setattr(fac, f"f{i:02}", v)
            fac.save()

            enc.pendiente = False
            enc.actualizado = timezone.now()
            enc.save(update_fields=["pendiente", "actualizado"])
            ok += 1

        except Exception as ex:
            err += 1
            messages.warning(request, f"encabezado_id={row.get('encabezado_id')}: {ex}")

    if no_enc:
        ids_txt = ", ".join(map(str, sorted(set(no_enc))))
        messages.warning(request, f"IDs de encabezado inexistentes: {ids_txt}")
    messages.success(request, f"Carga completada. Guardados: {ok}, con error: {err}.")

    # limpiar sesión
    request.session.pop("factores_csv", None)
    return redirect("calificacion_list")
