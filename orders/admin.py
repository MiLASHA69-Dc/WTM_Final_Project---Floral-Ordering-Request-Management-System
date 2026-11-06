from django.contrib import admin
from .models import OrderRequest,OrderItem

# Register your models here.

class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ["subtotal"]

class OrderRequestAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "customer",
        "order_type",
        "occasion",
        "pickup_date",
        "pickup_time",
        "contact_phone",
        "estimated_total",
        "status",
        "payment_status",
        "created_at",
    ]

    list_filter = [
        "order_type",
        "status",
        "payment_status",
        "pickup_date",
    ]

    search_fields = [
        "customer__username",
        "contact_phone",
    ]

    inlines = [OrderItemInline]


class OrderItemAdmin(admin.ModelAdmin):
    list_display = [
        "id",
        "order_request",
        "flower",
        "quantity",
        "unit_price_at_request",
        "subtotal",
    ]

admin.site.register(OrderRequest,OrderRequestAdmin)
admin.site.register(OrderItem,OrderItemAdmin)
