from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password, identify_hasher
from django.db.models.signals import pre_save
from django.dispatch import receiver

User = get_user_model()


@receiver(pre_save, sender=User)
def hash_user_password(sender, instance, **kwargs):
    password = instance.password
    if password:
        try:
            identify_hasher(password)  # Verifica si ya está hasheada
        except ValueError:
            # No está hasheada → la convertimos en hash seguro
            instance.password = make_password(password)
