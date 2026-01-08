from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password, identify_hasher
from django.db.models.signals import post_save, post_delete
from django.db.models.signals import pre_save
from django.dispatch import receiver

from .models import UserRole
from .permissions import sync_user_permissions

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


@receiver(post_save, sender=UserRole)
@receiver(post_delete, sender=UserRole)
def update_permissions_on_role_change(sender, instance, **kwargs):
    sync_user_permissions(instance.user_id)
