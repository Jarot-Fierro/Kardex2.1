from django.urls import path

from core import views

urlpatterns = [
    path('dashboard/', views.dashboard_view, name='dashboard')
]
