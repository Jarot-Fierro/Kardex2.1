from django.urls import path

from users import views

# app_name = 'users'
urlpatterns = [
    # path('login/', LoginViewCustom.as_view(), name='login'),
    # path('logout/', LogoutViewCustom.as_view(), name='logout'),
    # path('perfil/', PerfilUsuarioView.as_view(), name='perfil'),
    # path('cambiar-password/', CambiarPasswordView.as_view(), name='cambiar_password'),
    # path('crear/', CreacionUsuarioView.as_view(), name='creacion_usuario'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('lista-usuarios/', views.UserListView.as_view(), name='usuarios_list'),
    path('crear-usuario', views.UserCreateView.as_view(), name='usuarios_create'),
]
