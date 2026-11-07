from django.db import transaction
from django.core.exceptions import ValidationError
from .models import OrderRequest

def update_order_status_by_florist(order_id, new_status, reason=""):
    """
    Service helper function designed for Developer 3's Florist Dashboard.
    Validates allowable status transitions and updates reasons accordingly.
    """
    valid_statuses = [choice[0] for choice in OrderRequest.OrderStatus.choices]
    if new_status not in valid_statuses:
        raise ValidationError(f"Invalid status '{new_status}'.")

    with transaction.atomic():
        order = OrderRequest.objects.select_for_update().get(id=order_id)

        if new_status == OrderRequest.OrderStatus.CHANGES_REQUIRED:
            if not reason:
                raise ValidationError("A revision reason must be provided when requesting changes.")
            order.revision_reason = reason

        elif new_status == OrderRequest.OrderStatus.REJECTED:
            if not reason:
                raise ValidationError("A rejection reason must be provided when rejecting an order.")
            order.rejection_reason = reason

        order.status = new_status
        order.save()

    return order