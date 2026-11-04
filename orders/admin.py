from django.contrib import admin
from .models import OrderRequest,OrderItem

# Register your models here.

admin.site.register(OrderRequest)
admin.site.register(OrderItem)