from decimal import Decimal
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from django.db import transaction

from .models import Category, Flower
from .forms import CategoryForm, FlowerForm
from orders.models import OrderRequest, OrderItem

def is_florist_staff(user):
    return user.is_authenticated and user.is_staff

# ----------------- 1. FLOWER & CATEGORY MANAGEMENT -----------------
@user_passes_test(is_florist_staff, login_url='/accounts/login/')
def flower_management_list(request):
    flowers = Flower.objects.select_related('category').all().order_by('name')
    categories = Category.objects.all().order_by('name')
    return render(request, 'catalog/management_list.html', {
        'flowers': flowers,
        'categories': categories,
    })

@user_passes_test(is_florist_staff, login_url='/accounts/login/')
def flower_create(request):
    if request.method == 'POST':
        form = FlowerForm(request.POST, request.FILES)
        if form.is_valid():
            flower = form.save()
            messages.success(request, f"Flower '{flower.name}' created successfully.")
            return redirect('catalog:management_list')
    else:
        form = FlowerForm()
    return render(request, 'catalog/flower_form.html', {'form': form, 'title': 'Add New Flower'})

@user_passes_test(is_florist_staff, login_url='/accounts/login/')
def flower_update(request, pk):
    flower = get_object_or_404(Flower, pk=pk)
    if request.method == 'POST':
        form = FlowerForm(request.POST, request.FILES, instance=flower)
        if form.is_valid():
            form.save()
            messages.success(request, f"Flower '{flower.name}' updated successfully.")
            return redirect('catalog:management_list')
    else:
        form = FlowerForm(instance=flower)
    return render(request, 'catalog/flower_form.html', {'form': form, 'flower': flower, 'title': f"Edit {flower.name}"})

@user_passes_test(is_florist_staff, login_url='/accounts/login/')
def flower_delete(request, pk):
    flower = get_object_or_404(Flower, pk=pk)
    if request.method == 'POST':
        name = flower.name
        flower.delete()
        messages.success(request, f"Flower '{name}' has been deleted.")
        return redirect('catalog:management_list')
    return render(request, 'catalog/confirm_delete.html', {'item': flower, 'type': 'Flower'})

@user_passes_test(is_florist_staff, login_url='/accounts/login/')
def category_create(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            category = form.save()
            messages.success(request, f"Category '{category.name}' created successfully.")
            return redirect('catalog:management_list')
    else:
        form = CategoryForm()
    return render(request, 'catalog/category_form.html', {'form': form, 'title': 'Add New Category'})

@user_passes_test(is_florist_staff, login_url='/accounts/login/')
def category_update(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        form = CategoryForm(request.POST, instance=category)
        if form.is_valid():
            form.save()
            messages.success(request, f"Category '{category.name}' updated successfully.")
            return redirect('catalog:management_list')
    else:
        form = CategoryForm(instance=category)
    return render(request, 'catalog/category_form.html', {'form': form, 'category': category, 'title': f"Edit {category.name}"})

@user_passes_test(is_florist_staff, login_url='/accounts/login/')
def category_delete(request, pk):
    category = get_object_or_404(Category, pk=pk)
    if request.method == 'POST':
        name = category.name
        category.delete()
        messages.success(request, f"Category '{name}' deleted.")
        return redirect('catalog:management_list')
    return render(request, 'catalog/confirm_delete.html', {'item': category, 'type': 'Category'})


# ----------------- 2. FLORIST DASHBOARD & OPERATIONS -----------------
@user_passes_test(is_florist_staff, login_url='/accounts/login/')
def florist_dashboard(request):
    order_type_filter = request.GET.get('order_type', '')
    status_filter = request.GET.get('status', '')

    orders = OrderRequest.objects.select_related('customer').prefetch_related('items__flower').order_by('-created_at')

    if order_type_filter:
        orders = orders.filter(order_type=order_type_filter)
    if status_filter:
        orders = orders.filter(status=status_filter)

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

@user_passes_test(is_florist_staff, login_url='/accounts/login/')
def florist_order_decision(request, order_id):
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

@user_passes_test(is_florist_staff, login_url='/accounts/login/')
def florist_status_transition(request, order_id):
    order = get_object_or_404(OrderRequest, pk=order_id)

    if request.method == 'POST':
        next_step = request.POST.get('next_step')

        if next_step == 'mark_ready' and order.status == 'in_process':
            order.status = 'ready_for_pickup'
            order.save()
            messages.success(request, f"Order #{order.id} is now Ready for Pickup.")

        elif next_step == 'complete_order' and order.status == 'ready_for_pickup':
            order.payment_status = 'paid'
            order.status = 'completed'
            order.save()
            messages.success(request, f"Order #{order.id} payment recorded as Paid and order marked Completed.")

    return redirect('catalog:florist_dashboard')


# ----------------- 3. CUSTOMER REVISION WORKFLOW -----------------
@login_required(login_url='/accounts/login/')
def revise_order_request(request, order_id):
    order = get_object_or_404(OrderRequest, pk=order_id, customer=request.user)

    if order.status != 'changes_required':
        messages.error(request, "This order cannot be revised unless changes were requested by the florist.")
        return redirect('catalog:florist_dashboard')

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

            order.estimated_total = new_total
            order.status = 'pending'
            order.save()

            messages.success(request, "Order revised and resubmitted! It is now pending florist review.")
            return redirect('catalog:florist_dashboard')

    return render(request, 'catalog/revise_order.html', {'order': order})