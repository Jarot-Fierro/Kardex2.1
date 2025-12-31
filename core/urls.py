from django.urls import path

from core import views

urlpatterns = [
    path('dashboard/', views.dashboard_view, name='dashboard'),
    path('no-posee-establecimiento/', views.no_establecimiento, name='no_establecimiento')
]
