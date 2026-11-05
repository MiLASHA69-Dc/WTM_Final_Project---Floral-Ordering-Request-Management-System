from decimal import Decimal

from django.contrib import messages
from django.contrib.auth.views import redirect_to_login
from django.shortcuts import redirect, render
from django.shortcuts import get_object_or_404
from django.urls import NoReverseMatch, reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from catalog.models import Flower

CART_KEY = 'cart'
MAX_QUANTITY = 99


def get_cart(session):
    return session.get(CART_KEY, {})


def save_cart(session, cart):
    session[CART_KEY] = cart
    session.modified = True


def cart_detail(request):
    cart = get_cart(request.session)
    flowers = Flower.objects.filter(pk__in=cart.keys()).select_related('category')

    lines = []
    total = Decimal('0')
    for flower in flowers:
        quantity = cart[str(flower.pk)]
        subtotal = flower.unit_price * quantity
        total += subtotal
        lines.append({'flower': flower, 'quantity': quantity, 'subtotal': subtotal})

    return render(request, 'shop/cart.html', {'lines': lines, 'total': total})


@require_POST
def cart_add(request, pk):
    flower = get_object_or_404(Flower, pk=pk, is_active=True)

    next_url = request.POST.get('next', '')
    if not url_has_allowed_host_and_scheme(next_url, allowed_hosts={request.get_host()}):
        next_url = reverse('catalog')

    if not flower.is_available:
        messages.error(request, f'{flower.name} is currently unavailable.')
        return redirect(next_url)

    try:
        quantity = int(request.POST.get('quantity', 1))
    except ValueError:
        quantity = 0
    if quantity < 1:
        messages.error(request, 'Please enter a quantity of at least 1.')
        return redirect(next_url)

    cart = get_cart(request.session)
    key = str(flower.pk)
    cart[key] = min(cart.get(key, 0) + quantity, MAX_QUANTITY)
    save_cart(request.session, cart)

    messages.success(request, f'Added {flower.name} to your cart.')
    return redirect(next_url)


@require_POST
def cart_update(request, pk):
    cart = get_cart(request.session)
    key = str(pk)
    action = request.POST.get('action')

    if key in cart:
        if action == 'increment':
            flower = Flower.objects.filter(pk=pk, is_active=True, is_available=True).first()
            if flower and cart[key] < MAX_QUANTITY:
                cart[key] += 1
            else:
                messages.error(request, 'No more of that flower can be added.')
        elif action == 'decrement':
            cart[key] -= 1
            if cart[key] <= 0:
                del cart[key]
        elif action == 'remove':
            del cart[key]
        save_cart(request.session, cart)

    return redirect('cart')


def cart_proceed(request):
    if not get_cart(request.session):
        messages.error(request, 'Your cart is empty.')
        return redirect('cart')

    if not request.user.is_authenticated:
        return redirect_to_login(request.get_full_path())

    try:
        return redirect(reverse('orders:select_order_type'))
    except NoReverseMatch:
        messages.info(request, 'Order submission is not available yet.')
        return redirect('cart')