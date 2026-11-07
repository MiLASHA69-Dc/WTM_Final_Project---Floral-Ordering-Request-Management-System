from zoneinfo import ZoneInfo
from catalog.models import Flower  # Import Developer 3's Flower model
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from .forms import QuickOrderForm, ScheduledOrderForm
from .models import OrderItem, OrderRequest


@login_required
def select_order_type(request):
    cart = request.session.get("cart", {})
    if not cart:
        messages.warning(
            request, "Your cart is empty. Please select flowers first."
        )
        return redirect("catalog")
    return render(request, "orders/select_type.html")

# Validate cart items before saving an order request
def validate_cart(cart):
    validated_items=[]
    for flower_id, qty in cart.items():
        flower=Flower.objects.get(
            id=int(flower_id), is_available=True, is_active=True
        )
        qty=int(qty)
        if qty < 1:
            raise ValueError("Invalid flower quantity. You have to pick at least 1 flower.")
        # Florist check whether the requested quantity is availbale in stock.
        if qty > flower.stock_quantity:
            raise ValueError(f"Not enough stock for {flower.name}. Available: {flower.stock_quantity}, Requested: {qty}.")
        validated_items.append((flower, qty))
    return validated_items


@login_required
def create_quick_order(request):
    cart = request.session.get("cart", {})
    if not cart:
        messages.warning(
            request, "Your cart is empty. Please select flowers first."
        )
        return redirect("catalog")

    if request.method == "POST":
        form = QuickOrderForm(request.POST)
        if form.is_valid():
            try:
                validated_items = validate_cart(cart)
            except(ValueError, TypeError,Flower.DoesNotExist):
                messages.error(request, "Your cart contains invalid or unavailable items. Please review your cart.")
                return redirect("cart")
            
            with transaction.atomic():
                order = form.save(commit=False)
                order.customer = request.user
                order.order_type = OrderRequest.OrderType.QUICK
                order.pickup_date = timezone.localtime(
                    timezone.now(), ZoneInfo("Asia/Colombo")
                ).date()
                order.status = OrderRequest.OrderStatus.PENDING
                order.estimated_total = 0
                order.save()

                total = 0
                for flower, qty in validated_items:
                    item_total = flower.unit_price * qty
                    total = total + item_total
                    OrderItem.objects.create(
                        order_request=order,
                        flower=flower,
                        quantity=qty,
                        unit_price_at_request=flower.unit_price,
                    )

                order.estimated_total = total
                order.save()

            # Clear session cart after successfully saving the order to DB..
            del request.session["cart"]
            request.session.modified = True

            messages.success(request, f"Order #{order.id} submitted!")
            return redirect("orders:order_confirmation", order_id=order.id)
        else:
            form = QuickOrderForm()

    return render(request, "orders/quick_order.html", {"form": form})


@login_required
def create_scheduled_order(request):
    cart = request.session.get("cart", {})
    if not cart:
        return redirect("catalog")

    if request.method == "POST":
        form = ScheduledOrderForm(request.POST)
        if form.is_valid():
            try:
                validated_items = validate_cart(cart)
            except (ValueError, TypeError, Flower.DoesNotExist):
                messages.error(request, "Your cart contains invalid or unavailable items. Please review your cart.")
                return redirect("cart")
            
            with transaction.atomic():
                order = form.save(commit=False)
                order.customer = request.user
                order.order_type = OrderRequest.OrderType.SCHEDULED
                order.status = OrderRequest.OrderStatus.PENDING
                order.estimated_total = 0
                order.save()

                total = 0
                for flower, qty in validated_items:
                    item_total = flower.unit_price * qty
                    total = total + item_total
                    OrderItem.objects.create(
                        order_request=order,
                        flower=flower,
                        quantity=qty,
                        unit_price_at_request=flower.unit_price,
                    )

                order.estimated_total = total
                order.save()

            # Clear cart only after successful database saving
            del request.session["cart"]
            request.session.modified = True

            messages.success(request, f"Order #{order.id} submitted!")
            return redirect("orders:order_confirmation", order_id=order.id)
    else:
        form = ScheduledOrderForm()

    return render(request, "orders/scheduled_order.html", {"form": form})


@login_required
def order_confirmation(request, order_id):
    order = get_object_or_404(
        OrderRequest, id=order_id, customer=request.user
        )
    return render(request, "orders/order_confirmation.html", {"order": order})


@login_required
def my_orders_view(request):
    #Displays a list of all orders placed by the logged-in customer. Orders are sorted newest first and paginated (10 per page).
    orders_list = OrderRequest.objects.filter(customer=request.user).order_by("-created_at")
    paginator = Paginator(orders_list, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(request, "orders/my_orders.html", {"page_obj": page_obj})


@login_required
def order_detail_view(request, order_id):
    #Retrieves detailed information about a specific order for the logged-in customer. Uses get_object_or_404 with customer=request.user to restrict unauthorized access. Optimizes queries using prefetch_related for order items and flowers.
    order = get_object_or_404(
        OrderRequest.objects.prefetch_related("items__flower"),
        id=order_id,
        customer=request.user
    )
    return render(request, "orders/order_detail.html", {"order": order})


@login_required
def revise_order_view(request, order_id):
    """Customer View: Allows customer to revise an order when status is 'changes_required'.
    Customer can adjust quantities or remove unavailable items, recalculate totaland resubmit (changing status back to 'pending')."""
    order = get_object_or_404(
        OrderRequest.objects.prefetch_related("items__flower"),
        id=order_id,
        customer=request.user
    )

    # Security check: Customer can ONLY revise if florist marked it as 'changes_required'
    if not order.can_be_revised:
        messages.error(request, "This order cannot be edited at its current stage.")
        return redirect("orders:order_detail", order_id=order.id)

    if request.method == "POST":
        with transaction.atomic():
            new_total = 0
            items_to_keep = False

            # Loop through existing order items to update quantities or remove items
            for item in order.items.all():
                qty_field = f"quantity_{item.id}"
                remove_field = f"remove_{item.id}"

                if remove_field in request.POST:
                    item.delete()
                else:
                    new_qty = int(request.POST.get(qty_field, item.quantity))
                    if new_qty > 0:
                        item.quantity = new_qty
                        # Update snapshot price from current flower catalog price
                        item.unit_price_at_request = item.flower.unit_price
                        item.save()
                        new_total += item.quantity * item.unit_price_at_request
                        items_to_keep = True
                    else:
                        item.delete()

            if not items_to_keep:
                messages.error(request, "An order request must contain at least one flower.")
                return redirect("orders:revise_order", order_id=order.id)

            # Recalculate total, reset status back to PENDING for florist review
            order.estimated_total = new_total
            order.status = OrderRequest.OrderStatus.PENDING
            order.save()

        messages.success(request, f"Order #{order.id} has been revised and resubmitted to the florist!")
        return redirect("orders:order_detail", order_id=order.id)

    return render(request, "orders/revise_order.html", {"order": order})


# Convenience aliases
my_orders = my_orders_view
order_detail = order_detail_view
revise_order = revise_order_view


def update_order_status(order, new_status, reason=""):
    """
    Utility helper for Florist Operations (Developer 3):
    Safely transitions an order to a new status with corresponding reasons.
    """
    if new_status == OrderRequest.OrderStatus.CHANGES_REQUIRED:
        order.request_changes(reason)
    elif new_status == OrderRequest.OrderStatus.REJECTED:
        order.reject(reason)
    elif new_status == OrderRequest.OrderStatus.IN_PROCESS:
        order.mark_in_process()
    elif new_status == OrderRequest.OrderStatus.READY_FOR_PICKUP:
        order.mark_ready_for_pickup()
    elif new_status == OrderRequest.OrderStatus.COMPLETED:
        order.mark_completed()
    elif new_status == OrderRequest.OrderStatus.CANCELLED:
        order.cancel()
    else:
        order.status = new_status
        order.save()
    return order



