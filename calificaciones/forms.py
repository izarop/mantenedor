from decimal import Decimal
from django import forms
from .models import CalificacionEncabezado, CalificacionFactores
from django.contrib.auth.forms import UserCreationForm
# Asegúrate de que ROL_ADMIN esté disponible en models.py
from .models import Perfil, ROL_CORREDOR, ROLES_CHOICES, ROL_ADMIN 


class Decimal8Input(forms.NumberInput):
    def format_value(self, value):
        if value is None or value == '':
            return ''
        try:
            d = Decimal(str(value)).quantize(Decimal('0.00000000'))
            return f"{d:.8f}"  # fuerza 8 decimales, sin notación científica
        except Exception:
            return super().format_value(value)


class CalificacionEncabezadoForm(forms.ModelForm):
    class Meta:
        model = CalificacionEncabezado
        fields = [
            'mercado', 'origen', 'instrumento', 'evento_capital', 'valor_historico',
            'fecha_pago', 'secuencia_evento', 'anio', 'factor_actualizacion', 'sfut',
            'descripcion'
        ]
        widgets = {
            'fecha_pago': forms.DateInput(attrs={'type': 'date'}),
            'valor_historico': Decimal8Input(attrs={'step': '0.00000001'}),
            'factor_actualizacion': Decimal8Input(attrs={'step': '0.00000001'}),
            'sfut': forms.Select(choices=[(False, 'No'), (True, 'Sí')]),
        }


class CalificacionFactoresForm(forms.ModelForm):
    class Meta:
        model = CalificacionFactores
        exclude = ['encabezado']
        widgets = {
            **{f'f{n}': Decimal8Input(attrs={'step': '0.00000001'}) for n in
               ['08','09','10','11','12','13','14','15','16','17',
                '18','19a','20','21','22','23','24','25','26','27',
                '28','29','30','31','32','33','34','35','36','37']},
        }

class RegistroForm(UserCreationForm):
    nombre_completo = forms.CharField(max_length=150, required=True, label='Nombre Completo')

    rol = forms.ChoiceField(
        choices=ROLES_CHOICES,
        required=True,
        initial=ROL_CORREDOR,
        label='Rol de Usuario'
    )

    institucion = forms.CharField(max_length=100, required=False, label='Institución/Corredora')
    
    class Meta(UserCreationForm.Meta):
        fields = UserCreationForm.Meta.fields + ('email', 'nombre_completo', 'rol', 'institucion')

    def save(self, commit=True):
        # 1. Guardar el objeto User. commit=True dispara la señal post_save que crea el Perfil.
        user = super().save(commit=True) 
        user.email = self.cleaned_data.get('email') 
        
        # Intentar dividir el nombre completo en first_name y last_name
        try:
            first_name, last_name = self.cleaned_data['nombre_completo'].split(' ', 1)
        except ValueError:
            first_name = self.cleaned_data['nombre_completo']
            last_name = ''
            
        user.first_name = first_name
        user.last_name = last_name

        # --- LÓGICA DE ACTIVACIÓN DE PERMISOS DE ADMIN AUTOMÁTICAMENTE ---
        rol_seleccionado = int(self.cleaned_data['rol'])
        
        if rol_seleccionado == ROL_ADMIN:
            user.is_staff = True      # Permite el acceso al sitio /admin/
            user.is_superuser = True  # Otorga todos los permisos (recomendado para el Administrador del sistema)
        # -----------------------------------------------------------------


        # 2. ACCEDER y ACTUALIZAR el objeto Perfil que la señal ya creó.
        # Esto evita el IntegrityError.
        user.perfil.rol = rol_seleccionado # Usamos el valor casteado a int
        user.perfil.institucion = self.cleaned_data.get('institucion')

        if commit:
            # user.save() guardará los cambios de first/last name y las banderas is_staff/is_superuser
            user.save()       
            user.perfil.save() # Guarda los campos rol/institucion en el Perfil

        return user