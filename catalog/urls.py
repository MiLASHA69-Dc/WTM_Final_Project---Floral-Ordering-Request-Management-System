from django.urls import path
from . import views

app_name = 'catalog'

urlpatterns = [
    # Staff Flower & Category Management List
    #path('', views.flower_management_list, name='catalog'),
    path('management/', views.flower_management_list, name='management_list'),
    
    # Flower CRUD
    path('flowers/add/', views.flower_create, name='flower_create'),
    path('flowers/<int:pk>/edit/', views.flower_update, name='flower_update'),
    path('flowers/<int:pk>/delete/', views.flower_delete, name='flower_delete'),
    
    # Category CRUD
    path('categories/add/', views.category_create, name='category_create'),
    path('categories/<int:pk>/edit/', views.category_update, name='category_update'),
    path('categories/<int:pk>/delete/', views.category_delete, name='category_delete'),

    # Florist Operations & Dashboard
    path('florist/dashboard/', views.florist_dashboard, name='florist_dashboard'),
    path('florist/orders/<int:order_id>/decision/', views.florist_order_decision, name='florist_decision'),
    path('florist/orders/<int:order_id>/transition/', views.florist_status_transition, name='florist_transition'),

    # Customer Revision
    path('orders/<int:order_id>/revise/', views.revise_order_request, name='revise_order_request'),
]