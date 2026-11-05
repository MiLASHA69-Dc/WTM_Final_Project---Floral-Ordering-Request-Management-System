
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

    # User->OrderRequest (1:M)
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

    @property
    def can_be_revised(self):
        """Returns True if the order status allows customer revision."""
        return self.status == self.OrderStatus.CHANGES_REQUIRED

    @property
    def is_terminal(self):
        """Returns True if the order is in a final state (Completed, Rejected, Cancelled)."""
        return self.status in [
            self.OrderStatus.COMPLETED,
            self.OrderStatus.REJECTED,
            self.OrderStatus.CANCELLED,
        ]

    @property
    def status_badge_class(self):
        """Returns semantic CSS badge colors for frontend status display."""
        mapping = {
            self.OrderStatus.PENDING: "bg-amber-100 text-amber-800 border-amber-300",
            self.OrderStatus.CHANGES_REQUIRED: "bg-orange-100 text-orange-800 border-orange-300",
            self.OrderStatus.IN_PROCESS: "bg-blue-100 text-blue-800 border-blue-300",
            self.OrderStatus.READY_FOR_PICKUP: "bg-emerald-100 text-emerald-800 border-emerald-300",
            self.OrderStatus.COMPLETED: "bg-gray-100 text-gray-800 border-gray-300",
            self.OrderStatus.REJECTED: "bg-rose-100 text-rose-800 border-rose-300",
            self.OrderStatus.CANCELLED: "bg-slate-100 text-slate-800 border-slate-300",
        }
        return mapping.get(self.status, "bg-slate-100 text-slate-800")

    def request_changes(self, reason):
        """Florist helper: Request revisions from customer."""
        self.status = self.OrderStatus.CHANGES_REQUIRED
        self.revision_reason = reason
        self.save()

    def mark_in_process(self):
        """Florist helper: Move order to in-process."""
        self.status = self.OrderStatus.IN_PROCESS
        self.save()

    def mark_ready_for_pickup(self):
        """Florist helper: Mark order ready for pickup."""
        self.status = self.OrderStatus.READY_FOR_PICKUP
        self.save()

    def mark_completed(self):
        """Florist helper: Complete order and mark paid upon counter collection."""
        self.status = self.OrderStatus.COMPLETED
        self.payment_status = self.PaymentStatus.PAID
        self.save()

    def reject(self, reason):
        """Florist helper: Reject order request."""
        self.status = self.OrderStatus.REJECTED
        self.rejection_reason = reason
        self.save()

    def cancel(self):
        """Cancel order request."""
        self.status = self.OrderStatus.CANCELLED
        self.save()



class OrderItem(models.Model):

    # OrderRequest->OrderItem (1:M)
    order_request = models.ForeignKey(
        OrderRequest,
        on_delete=models.CASCADE,
        related_name="items"
    )

    # Flower->OrderItem (1:M)
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
