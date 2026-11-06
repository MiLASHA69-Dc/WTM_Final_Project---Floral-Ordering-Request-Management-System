from django.urls import path
from . import views

app_name = "orders"

urlpatterns = [
    # 1. Order Creation & Type Selection
    path("select-type/", views.select_order_type, name="select_order_type"),
    path("select-type/", views.select_order_type, name="select_type"),  # alias for Developer 1 compatibility
    path("quick/", views.create_quick_order, name="create_quick_order"),
    path("scheduled/", views.create_scheduled_order, name="create_scheduled_order"),
    path("confirmation/<int:order_id>/", views.order_confirmation, name="order_confirmation"),
    
    # 2. Customer Order History & Receipt Details
    path("my-orders/", views.my_orders_view, name="my_orders"),
    path("detail/<int:order_id>/", views.order_detail_view, name="order_detail"),
    
    # 3. Customer Order Revision (When Florist requests changes)
    path("revise/<int:order_id>/", views.revise_order_view, name="revise_order"),
]