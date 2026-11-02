from django.contrib import admin


from .models import Category, Flower

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name', 'description')

@admin.register(Flower)
class FlowerAdmin(admin.ModelAdmin):
    list_display = ('name', 'category', 'unit_price', 'stock_quantity', 'is_available', 'is_active')
    list_filter = ('category', 'is_available', 'is_active')
    search_fields = ('name', 'color')
