from django.db.models.signals import post_save
from django.dispatch import receiver
from django.contrib.auth.models import User
from .models import Perfil

@receiver(post_save, sender=User)
def crear_o_actualizar_perfil(sender, instance, created, **kwargs):
    """
    Crea un perfil automáticamente cada vez que se crea un nuevo usuario.
    Si el usuario ya existe, asegura que tenga su perfil asociado.
    """
    if created:
        Perfil.objects.get_or_create(user=instance)
    else:
        Perfil.objects.get_or_create(user=instance)
