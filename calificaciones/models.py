from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver
from decimal import Decimal
from django.db import models

# Helper para no repetir
DEC18_8_DEFAULT = Decimal('0.00000000')

class CalificacionEncabezado(models.Model):
    MERCADO_CHOICES = [
        ('ACCIONES', 'ACCIONES'),
        ('BONOS', 'BONOS'),
        ('FONDOS', 'FONDOS'),
        ('AC', 'AC'),
        ('BC', 'BC'),
    ]
    ORIGEN_CHOICES = [
        ('CORREDOR', 'CORREDOR'),
        ('DEPOSITARIO', 'DEPOSITARIO'),
        ('EMISOR', 'EMISOR'),
    ]

    mercado = models.CharField(max_length=20, choices=MERCADO_CHOICES)
    origen = models.CharField(max_length=20, choices=ORIGEN_CHOICES, blank=True)
    instrumento = models.CharField(max_length=100)
    evento_capital = models.CharField(max_length=100)
    valor_historico = models.DecimalField(max_digits=18, decimal_places=8, default=DEC18_8_DEFAULT)
    fecha_pago = models.DateField()
    secuencia_evento = models.PositiveIntegerField()
    anio = models.PositiveIntegerField()
    factor_actualizacion = models.DecimalField(max_digits=18, decimal_places=8, default=DEC18_8_DEFAULT)
    sfut = models.BooleanField(default=False)
    descripcion = models.CharField(max_length=255, blank=True)
    ingreso_por_montos = models.BooleanField(default=False)
    pendiente = models.BooleanField(default=False)

    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            models.Index(fields=['anio', 'mercado', 'origen']),
            models.Index(fields=['instrumento']),
        ]
        ordering = ['-actualizado']

    def __str__(self):
        return f'{self.anio} · {self.instrumento} · {self.fecha_pago}'


class CalificacionFactores(models.Model):
    encabezado = models.OneToOneField(
        CalificacionEncabezado,
        on_delete=models.CASCADE,
        related_name='factores'
    )

    # 08..37 con default Decimal('0.00000000')
    f08  = models.DecimalField(max_digits=18, decimal_places=8, default=DEC18_8_DEFAULT)
    f09  = models.DecimalField(max_digits=18, decimal_places=8, default=DEC18_8_DEFAULT)
    f10  = models.DecimalField(max_digits=18, decimal_places=8, default=DEC18_8_DEFAULT)
    f11  = models.DecimalField(max_digits=18, decimal_places=8, default=DEC18_8_DEFAULT)
    f12  = models.DecimalField(max_digits=18, decimal_places=8, default=DEC18_8_DEFAULT)
    f13  = models.DecimalField(max_digits=18, decimal_places=8, default=DEC18_8_DEFAULT)
    f14  = models.DecimalField(max_digits=18, decimal_places=8, default=DEC18_8_DEFAULT)
    f15  = models.DecimalField(max_digits=18, decimal_places=8, default=DEC18_8_DEFAULT)
    f16  = models.DecimalField(max_digits=18, decimal_places=8, default=DEC18_8_DEFAULT)
    f17  = models.DecimalField(max_digits=18, decimal_places=8, default=DEC18_8_DEFAULT)
    f18  = models.DecimalField(max_digits=18, decimal_places=8, default=DEC18_8_DEFAULT)
    f19a = models.DecimalField(max_digits=18, decimal_places=8, default=DEC18_8_DEFAULT)
    f20  = models.DecimalField(max_digits=18, decimal_places=8, default=DEC18_8_DEFAULT)
    f21  = models.DecimalField(max_digits=18, decimal_places=8, default=DEC18_8_DEFAULT)
    f22  = models.DecimalField(max_digits=18, decimal_places=8, default=DEC18_8_DEFAULT)
    f23  = models.DecimalField(max_digits=18, decimal_places=8, default=DEC18_8_DEFAULT)
    f24  = models.DecimalField(max_digits=18, decimal_places=8, default=DEC18_8_DEFAULT)
    f25  = models.DecimalField(max_digits=18, decimal_places=8, default=DEC18_8_DEFAULT)
    f26  = models.DecimalField(max_digits=18, decimal_places=8, default=DEC18_8_DEFAULT)
    f27  = models.DecimalField(max_digits=18, decimal_places=8, default=DEC18_8_DEFAULT)
    f28  = models.DecimalField(max_digits=18, decimal_places=8, default=DEC18_8_DEFAULT)
    f29  = models.DecimalField(max_digits=18, decimal_places=8, default=DEC18_8_DEFAULT)
    f30  = models.DecimalField(max_digits=18, decimal_places=8, default=DEC18_8_DEFAULT)
    f31  = models.DecimalField(max_digits=18, decimal_places=8, default=DEC18_8_DEFAULT)
    f32  = models.DecimalField(max_digits=18, decimal_places=8, default=DEC18_8_DEFAULT)
    f33  = models.DecimalField(max_digits=18, decimal_places=8, default=DEC18_8_DEFAULT)
    f34  = models.DecimalField(max_digits=18, decimal_places=8, default=DEC18_8_DEFAULT)
    f35  = models.DecimalField(max_digits=18, decimal_places=8, default=DEC18_8_DEFAULT)
    f36  = models.DecimalField(max_digits=18, decimal_places=8, default=DEC18_8_DEFAULT)
    f37  = models.DecimalField(max_digits=18, decimal_places=8, default=DEC18_8_DEFAULT)

    f38_desc = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f'Factores de {self.encabezado}'
    
    # Helper para no repetir (de tus snippets)
DEC18_8_DEFAULT = Decimal('0.00000000')

# Definición de Roles (usando constantes para consistencia en Vistas y Decoradores)
ROL_ADMIN = 1
ROL_ANALISTA = 2
ROL_CORREDOR = 3
ROL_SUPERVISOR = 4

ROLES_CHOICES = (
    (ROL_ADMIN, 'Administrador del sistema'),
    (ROL_ANALISTA, 'Analista tributario'),
    (ROL_CORREDOR, 'Corredor de Bolsa'),
    (ROL_SUPERVISOR, 'Supervisor'),
)

class Perfil(models.Model):
    # Enlace uno a uno con el usuario de Django
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    # Campo para almacenar el rol
    rol = models.PositiveSmallIntegerField(choices=ROLES_CHOICES, default=ROL_CORREDOR)
    # Campo adicional para el Corredor de Bolsa (para filtros de datos)
    institucion = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f'{self.user.username} - {self.get_rol_display()}'

# Este decorador asegura que, al crearse un User, automáticamente se cree su Perfil asociado.
# Lo necesitaremos para que el Admin pueda crear usuarios sin usar nuestro formulario de registro.
@receiver(post_save, sender=User)
def crear_o_actualizar_perfil_usuario(sender, instance, created, **kwargs):
    if created:
        Perfil.objects.create(user=instance)
    instance.perfil.save()
