# Create your views here.
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib import messages
from .models import Category, Flower
from .forms import CategoryForm, FlowerForm

def is_florist_staff(user):
    return user.is_authenticated and user.is_staff

# ----------------- INVENTORY OVERVIEW -----------------
@user_passes_test(is_florist_staff, login_url='/accounts/login/')
def flower_management_list(request):
    flowers = Flower.objects.select_related('category').all().order_by('name')
    categories = Category.objects.all().order_by('name')
    return render(request, 'catalog/management_list.html', {
        'flowers': flowers,
        'categories': categories,
    })

# ----------------- FLOWER CRUD -----------------
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

# ----------------- CATEGORY CRUD -----------------
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
