from django.db.models import Q
from django.shortcuts import get_object_or_404, render

from catalog.models import Category, Flower


def catalog_list(request):
    flowers = Flower.objects.filter(is_active=True).select_related('category')
    query = request.GET.get('q', '').strip()
    category_id = request.GET.get('category', '')

    if query:
        flowers = flowers.filter(
            Q(name__icontains=query)
            | Q(color__icontains=query)
            | Q(description__icontains=query)
        )
    if category_id.isdigit():
        flowers = flowers.filter(category_id=category_id)

    return render(request, 'shop/catalog_list.html', {
        'flowers': flowers.order_by('name'),
        'categories': Category.objects.all(),
        'query': query,
        'selected_category': category_id,
    })


def flower_detail(request, pk):
    flower = get_object_or_404(Flower, pk=pk, is_active=True)
    return render(request, 'shop/flower_detail.html', {'flower': flower})

def home(request):
    featured = (
        Flower.objects.filter(is_active=True, is_available=True)
        .select_related('category')
        .order_by('-id')[:4]
    )
    return render(request, 'shop/home.html', {'featured': featured})