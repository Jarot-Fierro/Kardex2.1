from django.urls import path

from users.views.roles import *
from users.views.usuarios import *

# app_name = 'users'
urlpatterns = [
    # path('login/', LoginViewCustom.as_view(), name='login'),
    # path('logout/', LogoutViewCustom.as_view(), name='logout'),
    # path('perfil/', PerfilUsuarioView.as_view(), name='perfil'),
    # path('cambiar-password/', CambiarPasswordView.as_view(), name='cambiar_password'),
    # path('crear/', CreacionUsuarioView.as_view(), name='creacion_usuario'),

    # USUARIOS
    path('login/', login_view, name='login'),
    path('logout/', logout_view, name='logout'),
    path('lista-usuarios/', UserListView.as_view(), name='usuarios_list'),
    path('crear-usuario', UserCreateView.as_view(), name='usuarios_create'),
    path('actualizar-usuario/<int:pk>/', UserUpdateView.as_view(), name='usuarios_update'),
    path('usuarios/<int:pk>/', UserDetailView.as_view(), name='usuarios_detail'),
    path('usuarios/<int:pk>/reset-password/', UserResetPasswordView.as_view(), name='usuarios_reset_password'),
    path('usuarios/cambiar-password/', UserChangePasswordView.as_view(), name='usuarios_change_password'),
    path('perfil/', UserProfileUpdateView.as_view(), name='perfil'),

    # ROLES

    path('roles/', RoleListView.as_view(), name='roles_list'),
    path('roles/crear/', RoleCreateView.as_view(), name='roles_create'),
    path('roles/<int:pk>/editar/', RoleUpdateView.as_view(), name='roles_update'),
    path('roles/<int:pk>/', RoleDetailView.as_view(), name='roles_detail'),
]
