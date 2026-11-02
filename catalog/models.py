from django.db import models

class Category(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)

    class Meta:
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name

class Flower(models.Model):
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='flowers')
    name = models.CharField(max_length=150)
    color = models.CharField(max_length=50)
    description = models.TextField(blank=True)
    image = models.ImageField(upload_to='flowers/', blank=True, null=True)
    unit_price = models.DecimalField(max_digits=10, decimal_places=2)
    stock_quantity = models.PositiveIntegerField(default=0)
    is_available = models.BooleanField(default=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name
