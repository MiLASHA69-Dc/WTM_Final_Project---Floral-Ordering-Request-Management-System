from django.urls import path

from . import cart_views

urlpatterns = [
    path('', cart_views.cart_detail, name='cart'),
    path('add/<int:pk>/', cart_views.cart_add, name='cart_add'),
    path('update/<int:pk>/', cart_views.cart_update, name='cart_update'),
    path('proceed/', cart_views.cart_proceed, name='cart_proceed'),
]