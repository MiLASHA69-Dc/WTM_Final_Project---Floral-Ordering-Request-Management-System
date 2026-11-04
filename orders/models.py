
from django.conf import settings
from django.db import models
from django.db.models import Q


class OrderRequest(models.Model):

    # Allowing customer to select Order Type
    class OrderType(models.TextChoices):
        QUICK = "quick", "Quick Order"
        SCHEDULED = "scheduled", "Scheduled Order"

    # Order Status Choices
    class OrderStatus(models.TextChoices):
        PENDING = "pending", "Pending"
        CHANGES_REQUIRED = "changes_required", "Changes Required"
        IN_PROCESS = "in_process", "In Process"
        READY_FOR_PICKUP = "ready_for_pickup", "Ready for Pickup"
        COMPLETED = "completed", "Completed"
        REJECTED = "rejected", "Rejected"
        CANCELLED = "cancelled", "Cancelled"

    # Payment Status
    class PaymentStatus(models.TextChoices):
        UNPAID = "unpaid", "Unpaid"
        PAID = "paid", "Paid"

    # User (1) -> OrderRequest (Many)
    customer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.PROTECT,
        related_name="order_requests"
    )

    order_type = models.CharField(
        max_length=10,
        choices=OrderType.choices
    )

    occasion = models.CharField(
        max_length=50,
        blank=True
    )

    pickup_date = models.DateField()
    pickup_time = models.TimeField()

    contact_phone = models.CharField(max_length=20)
    instructions = models.TextField(blank=True)

    estimated_total = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    status = models.CharField(
        max_length=20,
        choices=OrderStatus.choices,
        default=OrderStatus.PENDING
    )

    revision_reason = models.TextField(blank=True)
    rejection_reason = models.TextField(blank=True)

    payment_status = models.CharField(
        max_length=10,
        choices=PaymentStatus.choices,
        default=PaymentStatus.UNPAID
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

        constraints = [
            models.CheckConstraint(
                condition=Q(estimated_total__gte=0),
                name="order_total_nonnegative"
            )
        ]

    def __str__(self):
        return f"Order #{self.pk} - {self.get_status_display()}"


class OrderItem(models.Model):

    # OrderRequest (1) -> OrderItem (Many)
    order_request = models.ForeignKey(
        OrderRequest,
        on_delete=models.CASCADE,
        related_name="items"
    )

    # Flower (1) -> OrderItem (Many)
    flower = models.ForeignKey(
        "catalog.Flower",
        on_delete=models.PROTECT,
        related_name="order_items"
    )

    quantity = models.PositiveIntegerField()

    unit_price_at_request = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    class Meta:
        constraints = [
            models.CheckConstraint(
                condition=Q(quantity__gte=1),
                name="order_item_quantity_positive"
            ),
            models.CheckConstraint(
                condition=Q(unit_price_at_request__gte=0),
                name="order_item_price_nonnegative"
            ),
            models.UniqueConstraint(
                fields=["order_request", "flower"],
                name="unique_flower_per_order"
            )
        ]

    @property
    def subtotal(self):
        return self.quantity * self.unit_price_at_request

    def __str__(self):
        return f"{self.flower.name} x {self.quantity}"
