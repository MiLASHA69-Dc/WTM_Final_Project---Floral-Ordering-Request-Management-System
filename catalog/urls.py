from django.urls import path
from . import views

app_name = 'catalog'

urlpatterns = [
    # Staff Inventory Management
    path('management/', views.flower_management_list, name='management_list'),
    
    # Flower Actions
    path('flowers/add/', views.flower_create, name='flower_create'),
    path('flowers/<int:pk>/edit/', views.flower_update, name='flower_update'),
    path('flowers/<int:pk>/delete/', views.flower_delete, name='flower_delete'),
    
    # Category Actions
    path('categories/add/', views.category_create, name='category_create'),
    path('categories/<int:pk>/edit/', views.category_update, name='category_update'),
    path('categories/<int:pk>/delete/', views.category_delete, name='category_delete'),
]