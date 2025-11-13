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
from .models import Perfil, ROL_ADMIN, ROL_ANALISTA
from decimal import Decimal, InvalidOperation
from django.utils import timezone
import io
from django.views.decorators.http import require_http_methods
import json
import logging
from django.db import transaction
import datetime
from django.http import HttpResponse

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

#registro pero no concuerda mucho con la logica
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

#LOGIN
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

#LISTADO DE CALIFICACIONES   
@login_required(login_url='login')
def calificacion_list(request):
    qs = CalificacionEncabezado.objects.select_related('factores')

    try:
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

@rol_requerido([ROL_ADMIN, ROL_ANALISTA])
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

#EDICION DE CALIFICACIONES
@rol_requerido([ROL_ADMIN, ROL_ANALISTA])
def calificacion_edit(request, pk):
    enc = get_object_or_404(CalificacionEncabezado, pk=pk)
    if request.method == 'POST':
        form = CalificacionEncabezadoForm(request.POST, instance=enc)
        if form.is_valid():
            form.save()
            messages.success(request, "Encabezado modificado. Ahora puedes editar los factores.")
            return redirect('calificacion_factores', pk=enc.pk)
            
    else:
        form = CalificacionEncabezadoForm(instance=enc)
        
    context = {
        'form': form,
        'enc': enc,
        'mercado_choices': CalificacionEncabezado.MERCADO_CHOICES, 
        'origen_choices': CalificacionEncabezado.ORIGEN_CHOICES,   
    }
    return render(request, 'calificacion-editar.html', context)

#INGRESO DE FACTORES
@rol_requerido([ROL_ADMIN, ROL_ANALISTA,]) 
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


@rol_requerido([ROL_ADMIN, ROL_ANALISTA])
def carga_montos(request):
    return render(request, 'carga-montos.html')

def index(request):
    return redirect('calificacion_list')


# ELIMINACION CALIFICACIONES
@rol_requerido([ROL_ADMIN, ROL_ANALISTA])
def calificacion_delete(request, pk):
    if request.method == 'POST':
        enc = get_object_or_404(CalificacionEncabezado, pk=pk)
        enc.delete()
        
        messages.success(request, f"La Calificación ID {pk} ha sido eliminada permanentemente.")
        return redirect('calificacion_list')

    messages.error(request, "Método no permitido para la eliminación.")
    return redirect('calificacion_list')

FACTOR_COLS = [f"f{i:02}" for i in range(8, 19)] + ["f19a"] + [f"f{i:02}" for i in range(20, 38)]

HEADER_COLS = [
    "mercado", "origen", "instrumento", "evento_capital",
    "valor_historico", "fecha_pago", "secuencia_evento",
    "anio", "factor_actualizacion", "sfut", "descripcion"
]

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

    df.columns = [str(c).strip() for c in df.columns]

    
    faltantes = [c for c in REQ_COLS if c not in df.columns]
    if faltantes:
        errors.append(f"Columnas faltantes: {', '.join(faltantes)}")
        return errors  

    for col in FACTOR_COLS:
        df[col] = pd.to_numeric(df[col], errors='coerce')

        fuera_rango = df[(df[col] < 0) | (df[col] > 1)]
        if not fuera_rango.empty:
            idxs = ", ".join(map(str, (fuera_rango.index[:5] + 1).tolist()))
            errors.append(f"{col}: hay valores fuera de 0..1 (filas: {idxs}...)")

        def _dec_ok(v):
            try:
                if v is None:
                    return False
                fv = float(v)
                if not isfinite(fv):
                    return False

                d = Decimal(str(fv))
                if not d.is_finite():
                    return False

                exp = d.as_tuple().exponent
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

    df["_suma_factores"] = df[FACTOR_COLS].fillna(0).sum(axis=1)
    bad_sum = df[(df["_suma_factores"] < 0) | (df["_suma_factores"] > 1)]
    if not bad_sum.empty:
        idxs = ", ".join(map(str, (bad_sum.index[:5] + 1).tolist()))
        errors.append(f"Suma de factores fuera de [0..1] (filas: {idxs}...)")

    return errors

logger = logging.getLogger(__name__)

FACTOR_FIELDS_TO_SUM = [f'f{i:02d}' for i in range(8, 38)] 
SUMA_MAXIMA = Decimal('1.0')
DECIMAL_PRECISION = Decimal('0.00000001') # Para asegurar la precisión en la suma



def to_json_safe(value):
    """
    Convierte Decimals dentro de listas/dicts a string
    para que se puedan guardar en sesión (JSON).
    """
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, dict):
        return {k: to_json_safe(v) for k, v in value.items()}
    if isinstance(value, list):
        return [to_json_safe(v) for v in value]
    return value


FACTOR_FIELDS_TO_SUM = [f"f{str(i).zfill(2)}" for i in range(8, 38)]  
DECIMAL_PRECISION = Decimal("0.00000001")
SUMA_MAXIMA = Decimal("1.0")

#CARGA DE FACTORES
@login_required
@rol_requerido([ROL_ADMIN, ROL_ANALISTA])
def carga_factores(request):
    """
    1. Carga el CSV.
    2. Valida FACTORES (rango y suma > 0 y <= 1).
    3. Muestra previsualización de TODOS los campos del CSV.
    """
    form = CargaFactoresForm()
    context = {'form': form, 'preview_html': None, 'invalid_records': []}

    if request.method == 'POST':
        form = CargaFactoresForm(request.POST, request.FILES)
        context['form'] = form

        if form.is_valid():
            archivo = request.FILES['archivo']

            try:
                data_set = archivo.read().decode('utf-8')
                data_io = io.StringIO(data_set)
                df = pd.read_csv(data_io)
                df.columns = [col.lower().strip() for col in df.columns]
            except Exception as e:
                messages.error(request, f"Error al leer/decodificar el archivo CSV: {e}")
                return render(request, 'carga-factores.html', context)

            HEADER_FIELDS = [
                'mercado', 'origen', 'instrumento',
                'evento_capital', 'valor_historico', 'fecha_pago',
                'secuencia_evento', 'anio', 'factor_actualizacion',
                'sfut', 'descripcion',
            ]

            # Validar que existan todas las columnas requeridas
            required_cols = HEADER_FIELDS + FACTOR_FIELDS_TO_SUM
            missing = [c for c in required_cols if c not in df.columns]
            if missing:
                messages.error(
                    request,
                    "Columnas faltantes en el CSV: " + ", ".join(missing)
                )
                return render(request, 'carga-factores.html', context)

            valid_rows = []
            invalid_records_log = []

            for index, row in df.iterrows():
                linea_numero = index + 2  
                row_is_valid = True
                sum_factors = Decimal('0.0')
                error_message = ""

                temp_data = {}

                for col in HEADER_FIELDS:
                    temp_data[col] = row.get(col)

                for factor_field in FACTOR_FIELDS_TO_SUM:
                    raw_value = row.get(factor_field)

                    if pd.isna(raw_value):
                        value_to_process = '0.0'
                    else:
                        value_to_process = str(raw_value).strip()

                    try:
                        dec_value = Decimal(value_to_process or '0.0').quantize(DECIMAL_PRECISION)

                        if dec_value < Decimal('0.0') or dec_value > Decimal('1.0'):
                            raise ValueError(
                                f"Factor '{factor_field}' ({dec_value}) fuera del rango [0, 1]."
                            )

                        sum_factors += dec_value
                        temp_data[factor_field] = dec_value

                    except (InvalidOperation, ValueError) as e:
                        error_message = f"Factor '{factor_field}' inválido o fuera de rango: {e}"
                        row_is_valid = False
                        break

                if row_is_valid:
                    sum_q = sum_factors.quantize(DECIMAL_PRECISION)
                    if sum_q <= Decimal('0.0') or sum_q > SUMA_MAXIMA:
                        error_message = (
                            f"La suma de factores ({sum_q}) debe ser mayor a 0 "
                            f"y menor o igual a {SUMA_MAXIMA}."
                        )
                        row_is_valid = False

                if not row_is_valid:
                    logger.warning(
                        f"Carga Factores Rechazada - Línea {linea_numero}: Error: {error_message}"
                    )
                    invalid_records_log.append({
                        'linea': linea_numero,
                        'error': error_message
                    })
                else:
                    valid_rows.append(temp_data)

            if valid_rows:
                request.session['carga_factores_validos'] = to_json_safe(valid_rows)

                preview_df = pd.DataFrame(valid_rows)
                context['preview_html'] = preview_df.to_html(
                    classes=['preview'],
                    index=False,
                    float_format='%.8f'
                )
                messages.success(
                    request,
                    f"Validación completa. {len(valid_rows)} registros listos para guardar. "
                    "Revise la previsualización."
                )

            if invalid_records_log:
                messages.error(
                    request,
                    f"¡Atención! {len(invalid_records_log)} registros fueron rechazados por errores en factores."
                )
                context['invalid_records'] = invalid_records_log

    return render(request, 'carga-factores.html', context)


FACTOR_FIELDS_TO_SUM = [f"f{str(i).zfill(2)}" for i in range(8, 38)]
FACTOR_FIELDS_TO_SUM[11] = 'f19a'  

def _to_bool(value):
    """
    Convierte valores tipo 1/0, 'SI'/'NO', 'TRUE'/'FALSE' en boolean.
    """
    if value is None:
        return False
    s = str(value).strip().upper()
    return s in ('1', 'TRUE', 'SI', 'S')

#RESULTADOS DE LOS FACTORES
@login_required
def carga_resultados_factores(request):
    """
    Muestra los errores de la fase de confirmación de la DB.
    """
    db_errors = request.session.pop('carga_db_errors', [])

    if not db_errors:
        return redirect('calificacion_list')

    context = {
        'invalid_records_db': db_errors,
        'title': 'Resultados de Carga de Factores',
    }
    return render(request, 'carga_resultados.html', context)

##MODIFICADOOOOOOOOOOOOOOOOOOOOO CONFIRMACION DE FACTORES
@login_required
@rol_requerido([ROL_ADMIN, ROL_ANALISTA])
@require_http_methods(["POST"])
def confirmar_carga_factores(request):
    """
    Crea CalificacionEncabezado + CalificacionFactores a partir de los datos
    previamente validados y almacenados en sesión.
    """
    valid_data = request.session.pop('carga_factores_validos', None)

    if not valid_data:
        messages.error(request, "No hay datos válidos para confirmar. Vuelva al paso de carga.")
        return redirect('carga_factores')

    ok, err = 0, 0
    errors_log = []

    try:
        with transaction.atomic():
            for idx, row in enumerate(valid_data, start=1):
                try:
                    mercado = row.get('mercado')
                    origen = row.get('origen') or ''
                    instrumento = row.get('instrumento')
                    evento_capital = int(row.get('evento_capital') or 0)

                    valor_historico = Decimal(str(row.get('valor_historico') or '0')).quantize(Decimal("0.00000000"))
                    fecha_pago_str = str(row.get('fecha_pago'))
                    fecha_pago = datetime.date.fromisoformat(fecha_pago_str)  

                    secuencia_evento = int(row.get('secuencia_evento') or 0)
                    anio = int(row.get('anio') or 0)
                    factor_actualizacion = Decimal(str(row.get('factor_actualizacion') or '0')).quantize(Decimal("0.00000000"))

                    sfut = _to_bool(row.get('sfut'))
                    descripcion = row.get('descripcion') or ''

                    enc = CalificacionEncabezado.objects.create(
                        mercado=mercado,
                        origen=origen,
                        instrumento=instrumento,
                        evento_capital=evento_capital,
                        valor_historico=valor_historico,
                        fecha_pago=fecha_pago,
                        secuencia_evento=secuencia_evento,
                        anio=anio,
                        factor_actualizacion=factor_actualizacion,
                        sfut=sfut,
                        descripcion=descripcion,
                    )

                    factores_data = {}
                    for field in FACTOR_FIELDS_TO_SUM:
                        v = row.get(field, '0')
                        factores_data[field] = Decimal(str(v)).quantize(Decimal("0.00000000"))

                    CalificacionFactores.objects.create(
                        encabezado=enc,
                        **factores_data
                    )

                    ok += 1

                except Exception as e:
                    err += 1
                    errors_log.append(f"Fila {idx}: Error al guardar en BD: {e}")
                    logger.error(f"Error al guardar fila {idx}: {e}")

    except Exception as e:
        messages.error(request, f"Error CRÍTICO de base de datos: La transacción ha fallado. {e}")
        logger.critical(f"Error de transacción en carga masiva: {e}")
        return redirect('carga_factores')

    if ok > 0:
        messages.success(
            request,
            f"¡Carga Masiva Exitosa! Se guardaron {ok} registros de calificaciones con sus factores."
        )

    if errors_log:
        request.session['carga_db_errors'] = errors_log
        messages.warning(
            request,
            f"Atención: {len(errors_log)} registros no pudieron ser guardados en la BD."
        )
        return redirect('carga_resultados_factores')

    listado_url = reverse('calificacion_list')

    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="utf-8">
      <title>Carga completa</title>
    </head>
    <body>
    <script>
      if (window.parent && window.parent.closeCarga) {{
          // Estamos dentro del iframe de la modal
          window.parent.closeCarga();           // Cierra la modal
          window.parent.location.href = "{listado_url}";  // Vuelve al listado
      }} else {{
          // Por si se abrió fuera de la modal
          window.location.href = "{listado_url}";
      }}
    </script>
    </body>
    </html>
    """
    return HttpResponse(html)

    

