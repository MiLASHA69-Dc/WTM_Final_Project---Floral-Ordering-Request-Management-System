from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from catalog.models import Category, Flower

User = get_user_model()
PASSWORD = 'Floral2026Bloom!'


class CartTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        category = Category.objects.create(name='Roses')
        cls.rose = Flower.objects.create(
            category=category, name='Velvet Ruby', color='Deep Red',
            unit_price=Decimal('24.99'), stock_quantity=10,
        )
        cls.unavailable = Flower.objects.create(
            category=category, name='White Avalanche', color='White',
            unit_price=Decimal('29.99'), is_available=False,
        )
        cls.inactive = Flower.objects.create(
            category=category, name='Stargazer', color='Pink',
            unit_price=Decimal('19.99'), is_active=False,
        )
        cls.user = User.objects.create_user(username='tester', password=PASSWORD)

    # helpers
    def cart(self):
        return self.client.session.get('cart', {})

    def set_cart(self, data):
        session = self.client.session
        session['cart'] = data
        session.save()

    def add(self, flower, quantity=1):
        return self.client.post(
            reverse('cart_add', args=[flower.pk]), {'quantity': quantity}
        )

    # adding
    def test_add_available_flower(self):
        self.add(self.rose, 2)
        self.assertEqual(self.cart(), {str(self.rose.pk): 2})

    def test_adding_same_flower_twice_increases_quantity(self):
        self.add(self.rose, 1)
        self.add(self.rose, 3)
        self.assertEqual(self.cart(), {str(self.rose.pk): 4})

    def test_unavailable_flower_is_rejected(self):
        self.add(self.unavailable)
        self.assertEqual(self.cart(), {})

    def test_inactive_flower_returns_404(self):
        response = self.add(self.inactive)
        self.assertEqual(response.status_code, 404)
        self.assertEqual(self.cart(), {})

    def test_invalid_quantity_is_rejected(self):
        for bad in ('0', '-1', 'abc', ''):
            with self.subTest(quantity=bad):
                self.add(self.rose, bad)
                self.assertEqual(self.cart(), {})

    def test_quantity_is_capped(self):
        self.add(self.rose, 150)
        self.assertEqual(self.cart(), {str(self.rose.pk): 99})

    def test_add_requires_post(self):
        response = self.client.get(reverse('cart_add', args=[self.rose.pk]))
        self.assertEqual(response.status_code, 405)

    # total
    def test_total_uses_database_price(self):
        self.client.post(
            reverse('cart_add', args=[self.rose.pk]),
            {'quantity': 2, 'price': '0.01'},  # a tampered price must be ignored
        )
        response = self.client.get(reverse('cart'))
        self.assertEqual(response.context['total'], Decimal('49.98'))

    # changing quantities
    def test_increment_and_decrement(self):
        self.set_cart({str(self.rose.pk): 1})
        url = reverse('cart_update', args=[self.rose.pk])
        self.client.post(url, {'action': 'increment'})
        self.assertEqual(self.cart(), {str(self.rose.pk): 2})
        self.client.post(url, {'action': 'decrement'})
        self.assertEqual(self.cart(), {str(self.rose.pk): 1})

    def test_decrement_to_zero_removes_item(self):
        self.set_cart({str(self.rose.pk): 1})
        self.client.post(
            reverse('cart_update', args=[self.rose.pk]), {'action': 'decrement'}
        )
        self.assertEqual(self.cart(), {})

    def test_remove(self):
        self.set_cart({str(self.rose.pk): 5})
        self.client.post(
            reverse('cart_update', args=[self.rose.pk]), {'action': 'remove'}
        )
        self.assertEqual(self.cart(), {})

    # login and proceeding
    def test_cart_survives_login(self):
        self.add(self.rose, 2)
        self.client.post(
            reverse('login'), {'username': 'tester', 'password': PASSWORD}
        )
        self.assertIn('_auth_user_id', self.client.session)
        self.assertEqual(self.cart(), {str(self.rose.pk): 2})

    def test_empty_cart_cannot_proceed(self):
        response = self.client.get(reverse('cart_proceed'))
        self.assertRedirects(response, reverse('cart'))

    def test_anonymous_user_sent_to_login_when_proceeding(self):
        self.add(self.rose)
        response = self.client.get(reverse('cart_proceed'))
        self.assertRedirects(
            response, f"{reverse('login')}?next={reverse('cart_proceed')}"
        )