from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db import transaction
from django.utils import timezone
from .models import Flower, Category

# Import Developer 2's models
from orders.models import OrderRequest, OrderItem

def is_florist_staff(user):
    return user.is_authenticated and user.is_staff

# ----------------- 1. FLORIST DASHBOARD -----------------
@user_passes_test(is_florist_staff, login_url='/accounts/login/')
def florist_dashboard(request):
    """
    Overview of pending, quick, scheduled, active and completed orders with filters.
    """
    order_type_filter = request.GET.get('order_type', '')
    status_filter = request.GET.get('status', '')

    orders = OrderRequest.objects.select_related('customer').prefetch_related('items__flower').order_by('-created_at')

    # Apply filters
    if order_type_filter:
        orders = orders.filter(order_type=order_type_filter)
    if status_filter:
        orders = orders.filter(status=status_filter)

    # Status counts for metrics bar
    metrics = {
        'pending': OrderRequest.objects.filter(status='pending').count(),
        'quick': OrderRequest.objects.filter(order_type='quick', status__in=['pending', 'in_process']).count(),
        'scheduled': OrderRequest.objects.filter(order_type='scheduled', status__in=['pending', 'in_process']).count(),
        'in_process': OrderRequest.objects.filter(status='in_process').count(),
        'ready': OrderRequest.objects.filter(status='ready_for_pickup').count(),
        'completed': OrderRequest.objects.filter(status='completed').count(),
    }

    return render(request, 'catalog/florist_dashboard.html', {
        'orders': orders,
        'metrics': metrics,
        'selected_type': order_type_filter,
        'selected_status': status_filter,
    })


# ----------------- 2. FLORIST REVIEW DECISIONS -----------------
@user_passes_test(is_florist_staff, login_url='/accounts/login/')
def florist_order_decision(request, order_id):
    """
    POST handler for Florist review:
    - Accept -> in_process
    - Request Changes -> changes_required (requires revision_reason)
    - Reject -> rejected (requires rejection_reason)
    """
    order = get_object_or_404(OrderRequest, pk=order_id)

    if request.method == 'POST':
        action = request.POST.get('action')
        reason = request.POST.get('reason', '').strip()

        if action == 'accept':
            order.status = 'in_process'
            order.save()
            messages.success(request, f"Order #{order.id} accepted and is now In Process.")

        elif action == 'request_changes':
            if not reason:
                messages.error(request, "A reason explaining what items need changing is required.")
                return redirect('catalog:florist_dashboard')
            order.status = 'changes_required'
            order.revision_reason = reason
            order.save()
            messages.warning(request, f"Order #{order.id} marked as Changes Required.")

        elif action == 'reject':
            if not reason:
                messages.error(request, "A rejection reason is required.")
                return redirect('catalog:florist_dashboard')
            order.status = 'rejected'
            order.rejection_reason = reason
            order.save()
            messages.error(request, f"Order #{order.id} rejected.")

    return redirect('catalog:florist_dashboard')


# ----------------- 3. PREPARATION, PICKUP & COUNTER PAYMENT -----------------
@user_passes_test(is_florist_staff, login_url='/accounts/login/')
def florist_status_transition(request, order_id):
    """
    Florist advances status:
    - in_process -> ready_for_pickup (arrangements finished)
    - ready_for_pickup -> completed (payment recorded at counter)
    """
    order = get_object_or_404(OrderRequest, pk=order_id)

    if request.method == 'POST':
        next_step = request.POST.get('next_step')

        if next_step == 'mark_ready' and order.status == 'in_process':
            order.status = 'ready_for_pickup'
            order.save()
            messages.success(request, f"Order #{order.id} is now Ready for Pickup.")

        elif next_step == 'complete_order' and order.status == 'ready_for_pickup':
            # Record counter payment and mark completed
            order.payment_status = 'paid'
            order.status = 'completed'
            order.save()
            messages.success(request, f"Order #{order.id} payment recorded as Paid and order marked Completed.")

    return redirect('catalog:florist_dashboard')


# ----------------- 4. CUSTOMER REVISION WORKFLOW -----------------
@login_required(login_url='/accounts/login/')
def revise_order_request(request, order_id):
    """
    Customer-facing view:
    Order owner modifies quantities or removes unavailable flowers
    when an order is in 'changes_required', then resubmits to 'pending'.
    """
    order = get_object_or_404(OrderRequest, pk=order_id, customer=request.user)

    if order.status != 'changes_required':
        messages.error(request, "This order cannot be revised unless changes were requested by the florist.")
        return redirect('orders:order_detail', pk=order.id)

    if request.method == 'POST':
        with transaction.atomic():
            new_total = Decimal('0.00')
            items_to_keep = 0

            for item in order.items.all():
                qty_key = f'quantity_{item.id}'
                delete_key = f'delete_{item.id}'

                if delete_key in request.POST:
                    item.delete()
                else:
                    new_qty = int(request.POST.get(qty_key, item.quantity))
                    if new_qty > 0:
                        item.quantity = new_qty
                        item.save()
                        new_total += (item.unit_price_at_request * new_qty)
                        items_to_keep += 1
                    else:
                        item.delete()

            if items_to_keep == 0:
                messages.error(request, "Your order cannot be empty. Please keep at least one flower.")
                return redirect('catalog:revise_order_request', order_id=order.id)

            # Update order details and return to pending for re-review
            order.estimated_total = new_total
            order.status = 'pending'
            order.save()

            messages.success(request, "Order revised and resubmitted! It is now pending florist review.")
            return redirect('orders:order_detail', pk=order.id)

    return render(request, 'catalog/revise_order.html', {'order': order})