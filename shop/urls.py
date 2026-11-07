from django.urls import path

from . import views

urlpatterns = [
    path('', views.catalog_list, name='catalog'),
    path('<int:pk>/', views.flower_detail, name='flower_detail'),
]