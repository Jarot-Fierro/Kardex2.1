from django.contrib import admin
from django.urls import path, include

from core.views import *

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('users.urls')),
    path('', dashboard_view, name='home'),
    path('inicio/', include('core.urls')),
    path('geografia/', include('geografia.urls')),
    path('establecimientos/', include('establecimientos.urls')),
    path('personas/', include('personas.urls')),
    path('clinica/', include('clinica.urls')),
]
