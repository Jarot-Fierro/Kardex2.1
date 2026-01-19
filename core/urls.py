from django.urls import path

from core import views
from core.views import ContactoView

urlpatterns = [
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('no-posee-establecimiento/', views.no_establecimiento, name='no_establecimiento'),
    path('contacto/', ContactoView.as_view(), name='contacto'),
]
