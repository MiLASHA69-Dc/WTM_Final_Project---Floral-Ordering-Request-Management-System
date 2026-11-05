from django.urls import path
from . import views

app_name = "orders"

urlpatterns = [
    path("select_type/", views.select_order_type, name="select_order_type"),
    path("quick/", views.create_quick_order, name="create_quick_order"),
    path("quick/", views.create_quick_order, name="quick_order"),
    path("scheduled/", views.create_scheduled_order, name="create_scheduled_order"),
    path("scheduled/", views.create_scheduled_order, name="scheduled_order"),
    path("confirmation/<int:order_id>/", views.order_confirmation, name="order_confirmation"),
    path("my-orders/", views.my_orders_view, name="my_orders"),
    path("my-orders/", views.my_orders_view, name="my_orders_view"),
    path("<int:order_id>/", views.order_detail_view, name="order_detail"),
    path("<int:order_id>/", views.order_detail_view, name="order_detail_view"),
    path("detail/<int:order_id>/", views.order_detail_view, name="order_detail_alt"),
]
