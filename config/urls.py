from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('users.urls')),
    path('inicio/', include('core.urls')),
    path('comunas/', include('geografia.urls')),
    path('establecimientos/', include('establecimientos.urls')),
]
