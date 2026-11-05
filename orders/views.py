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
        return redirect("shop:catalog_list")  # Adjust if catalog name differs
    return render(request, "orders/select_type.html")


@login_required
def create_quick_order(request):
    cart = request.session.get("cart", {})
    if not cart:
        return redirect("shop:catalog_list")

    if request.method == "POST":
        form = QuickOrderForm(request.POST)
        if form.is_valid():
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
                for flower_id, qty in cart.items():
                    flower = Flower.objects.get(
                        id=flower_id, is_available=True, is_active=True
                    )
                    item_total = flower.unit_price * qty
                    total += item_total
                    OrderItem.objects.create(
                        order_request=order,
                        flower=flower,
                        quantity=qty,
                        unit_price_at_request=flower.unit_price,
                    )

                order.estimated_total = total
                order.save()

                # Clear cart on successful commit
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
        return redirect("shop:catalog_list")

    if request.method == "POST":
        form = ScheduledOrderForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                order = form.save(commit=False)
                order.customer = request.user
                order.order_type = OrderRequest.OrderType.SCHEDULED
                order.status = OrderRequest.OrderStatus.PENDING
                order.estimated_total = 0
                order.save()

                total = 0
                for flower_id, qty in cart.items():
                    flower = Flower.objects.get(
                        id=flower_id, is_available=True, is_active=True
                    )
                    item_total = flower.unit_price * qty
                    total += item_total
                    OrderItem.objects.create(
                        order_request=order,
                        flower=flower,
                        quantity=qty,
                        unit_price_at_request=flower.unit_price,
                    )

                order.estimated_total = total
                order.save()

                del request.session["cart"]
                request.session.modified = True

            messages.success(request, f"Order #{order.id} submitted!")
            return redirect("orders:order_confirmation", order_id=order.id)
    else:
        form = ScheduledOrderForm()

    return render(request, "orders/scheduled_order.html", {"form": form})


@login_required
def order_confirmation(request, order_id):
    order = get_object_or_404(OrderRequest, id=order_id, customer=request.user)
    return render(request, "orders/order_confirmation.html", {"order": order})


@login_required
def my_orders_view(request):
    """
    Retrieves all order requests placed by the logged-in customer.
    Orders are sorted newest first and paginated (10 per page).
    """
    orders_list = OrderRequest.objects.filter(customer=request.user).order_by("-created_at")
    paginator = Paginator(orders_list, 10)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(request, "orders/my_orders.html", {"page_obj": page_obj})


@login_required
def order_detail_view(request, order_id):
    """
    Retrieves details of a specific order request.
    Uses get_object_or_404 with customer=request.user to restrict unauthorized access.
    Optimizes queries using prefetch_related for order items and flowers.
    """
    order = get_object_or_404(
        OrderRequest.objects.prefetch_related("items__flower"),
        id=order_id,
        customer=request.user
    )
    return render(request, "orders/order_detail.html", {"order": order})


# Convenience aliases
my_orders = my_orders_view
order_detail = order_detail_view

