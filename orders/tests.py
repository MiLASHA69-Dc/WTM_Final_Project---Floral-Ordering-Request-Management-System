from datetime import date, datetime, time, timedelta
from decimal import Decimal
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.contrib.auth import get_user_model
from django.db import IntegrityError
from django.test import Client, TestCase
from django.urls import reverse

from catalog.models import Category, Flower
from orders.forms import QuickOrderForm, ScheduledOrderForm
from orders.models import OrderItem, OrderRequest
from orders.views import update_order_status

User = get_user_model()


class OrderModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="alice", password="password123"
        )
        self.category = Category.objects.create(name="Roses")
        self.flower = Flower.objects.create(
            category=self.category,
            name="Red Rose",
            color="Red",
            unit_price=Decimal("250.00"),
            stock_quantity=50,
            is_available=True,
            is_active=True,
        )

    def test_order_creation_and_str(self):
        order = OrderRequest.objects.create(
            customer=self.user,
            order_type=OrderRequest.OrderType.QUICK,
            pickup_date=date.today(),
            pickup_time=time(10, 30),
            contact_phone="0771234567",
            estimated_total=Decimal("500.00"),
        )
        self.assertIn(f"Order #{order.pk}", str(order))

    def test_order_item_subtotal_and_str(self):
        order = OrderRequest.objects.create(
            customer=self.user,
            order_type=OrderRequest.OrderType.QUICK,
            pickup_date=date.today(),
            pickup_time=time(10, 30),
            contact_phone="0771234567",
            estimated_total=Decimal("500.00"),
        )
        item = OrderItem.objects.create(
            order_request=order,
            flower=self.flower,
            quantity=3,
            unit_price_at_request=Decimal("250.00"),
        )
        self.assertEqual(item.subtotal, Decimal("750.00"))
        self.assertEqual(str(item), "Red Rose x 3")

    def test_unique_flower_per_order_constraint(self):
        order = OrderRequest.objects.create(
            customer=self.user,
            order_type=OrderRequest.OrderType.QUICK,
            pickup_date=date.today(),
            pickup_time=time(10, 30),
            contact_phone="0771234567",
            estimated_total=Decimal("250.00"),
        )
        OrderItem.objects.create(
            order_request=order,
            flower=self.flower,
            quantity=1,
            unit_price_at_request=Decimal("250.00"),
        )
        with self.assertRaises(IntegrityError):
            OrderItem.objects.create(
                order_request=order,
                flower=self.flower,
                quantity=2,
                unit_price_at_request=Decimal("250.00"),
            )

    def test_order_request_helper_properties(self):
        order = OrderRequest.objects.create(
            customer=self.user,
            order_type=OrderRequest.OrderType.QUICK,
            pickup_date=date.today(),
            pickup_time=time(10, 30),
            contact_phone="0771234567",
            status=OrderRequest.OrderStatus.PENDING,
        )
        self.assertFalse(order.can_be_revised)
        self.assertFalse(order.is_terminal)
        self.assertIn("amber", order.status_badge_class)

        order.status = OrderRequest.OrderStatus.CHANGES_REQUIRED
        self.assertTrue(order.can_be_revised)
        self.assertFalse(order.is_terminal)
        self.assertIn("orange", order.status_badge_class)

        order.status = OrderRequest.OrderStatus.COMPLETED
        self.assertFalse(order.can_be_revised)
        self.assertTrue(order.is_terminal)

        order.status = OrderRequest.OrderStatus.REJECTED
        self.assertTrue(order.is_terminal)

        order.status = OrderRequest.OrderStatus.CANCELLED
        self.assertTrue(order.is_terminal)

    def test_order_request_transition_helpers(self):
        order = OrderRequest.objects.create(
            customer=self.user,
            order_type=OrderRequest.OrderType.SCHEDULED,
            pickup_date=date.today() + timedelta(days=2),
            pickup_time=time(11, 0),
            contact_phone="0771234567",
            status=OrderRequest.OrderStatus.PENDING,
        )

        order.request_changes("Need alternative color")
        self.assertEqual(order.status, OrderRequest.OrderStatus.CHANGES_REQUIRED)
        self.assertEqual(order.revision_reason, "Need alternative color")

        order.mark_in_process()
        self.assertEqual(order.status, OrderRequest.OrderStatus.IN_PROCESS)

        order.mark_ready_for_pickup()
        self.assertEqual(order.status, OrderRequest.OrderStatus.READY_FOR_PICKUP)

        order.mark_completed()
        self.assertEqual(order.status, OrderRequest.OrderStatus.COMPLETED)
        self.assertEqual(order.payment_status, OrderRequest.PaymentStatus.PAID)

        order.reject("Out of stock")
        self.assertEqual(order.status, OrderRequest.OrderStatus.REJECTED)
        self.assertEqual(order.rejection_reason, "Out of stock")

        order.cancel()
        self.assertEqual(order.status, OrderRequest.OrderStatus.CANCELLED)

    def test_update_order_status_helper(self):
        order = OrderRequest.objects.create(
            customer=self.user,
            order_type=OrderRequest.OrderType.SCHEDULED,
            pickup_date=date.today() + timedelta(days=2),
            pickup_time=time(11, 0),
            contact_phone="0771234567",
            status=OrderRequest.OrderStatus.PENDING,
        )
        update_order_status(order, OrderRequest.OrderStatus.CHANGES_REQUIRED, reason="Adjust count")
        self.assertEqual(order.status, OrderRequest.OrderStatus.CHANGES_REQUIRED)
        self.assertEqual(order.revision_reason, "Adjust count")

        update_order_status(order, OrderRequest.OrderStatus.IN_PROCESS)
        self.assertEqual(order.status, OrderRequest.OrderStatus.IN_PROCESS)




class OrderFormTests(TestCase):
    def test_quick_order_form_valid_before_cutoff(self):
        fixed_time = datetime(2026, 11, 5, 9, 30, tzinfo=ZoneInfo("Asia/Colombo"))
        with patch("django.utils.timezone.now", return_value=fixed_time):
            form = QuickOrderForm(
                data={
                    "contact_phone": "0771234567",
                    "pickup_time": "14:00",
                    "instructions": "Leave at front desk",
                }
            )
            self.assertTrue(form.is_valid())

    def test_quick_order_form_invalid_after_11am_cutoff(self):
        fixed_time = datetime(2026, 11, 5, 11, 15, tzinfo=ZoneInfo("Asia/Colombo"))
        with patch("django.utils.timezone.now", return_value=fixed_time):
            form = QuickOrderForm(
                data={
                    "contact_phone": "0771234567",
                    "pickup_time": "14:00",
                }
            )
            self.assertFalse(form.is_valid())
            self.assertTrue(any("11:00 AM" in err for err in form.non_field_errors()))

    def test_quick_order_form_outside_operating_hours(self):
        fixed_time = datetime(2026, 11, 5, 9, 0, tzinfo=ZoneInfo("Asia/Colombo"))
        with patch("django.utils.timezone.now", return_value=fixed_time):
            # Before 8:00 AM
            form_early = QuickOrderForm(
                data={"contact_phone": "0771234567", "pickup_time": "07:30"}
            )
            self.assertFalse(form_early.is_valid())
            self.assertIn("pickup_time", form_early.errors)

            # After 4:30 PM (16:30)
            form_late = QuickOrderForm(
                data={"contact_phone": "0771234567", "pickup_time": "17:00"}
            )
            self.assertFalse(form_late.is_valid())
            self.assertIn("pickup_time", form_late.errors)

    def test_scheduled_order_form_valid(self):
        tomorrow = date.today() + timedelta(days=2)
        form = ScheduledOrderForm(
            data={
                "occasion": "Birthday",
                "pickup_date": tomorrow.isoformat(),
                "pickup_time": "10:00",
                "contact_phone": "0771234567",
                "instructions": "Wrap in pink paper",
            }
        )
        self.assertTrue(form.is_valid())

    def test_scheduled_order_form_same_day_or_past_date_invalid(self):
        today = date.today()
        form = ScheduledOrderForm(
            data={
                "occasion": "Anniversary",
                "pickup_date": today.isoformat(),
                "pickup_time": "10:00",
                "contact_phone": "0771234567",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("pickup_date", form.errors)


class OrderCreationAndConfirmationTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="bob", password="password123"
        )
        self.other_user = User.objects.create_user(
            username="charlie", password="password123"
        )
        self.category = Category.objects.create(name="Lilies")
        self.flower1 = Flower.objects.create(
            category=self.category,
            name="White Lily",
            color="White",
            unit_price=Decimal("300.00"),
            stock_quantity=20,
            is_available=True,
            is_active=True,
        )
        self.flower2 = Flower.objects.create(
            category=self.category,
            name="Orange Lily",
            color="Orange",
            unit_price=Decimal("400.00"),
            stock_quantity=15,
            is_available=True,
            is_active=True,
        )

    def test_create_quick_order_success_and_cart_cleared(self):
        self.client.login(username="bob", password="password123")
        session = self.client.session
        session["cart"] = {str(self.flower1.id): 2, str(self.flower2.id): 1}
        session.save()

        fixed_time = datetime(2026, 11, 5, 9, 0, tzinfo=ZoneInfo("Asia/Colombo"))
        with patch("django.utils.timezone.now", return_value=fixed_time):
            response = self.client.post(
                reverse("orders:create_quick_order"),
                {"contact_phone": "0719876543", "pickup_time": "12:00"},
            )

        order = OrderRequest.objects.filter(customer=self.user).first()
        self.assertIsNotNone(order)
        self.assertRedirects(
            response, reverse("orders:order_confirmation", kwargs={"order_id": order.id})
        )
        # Check total: (300 * 2) + (400 * 1) = 1000
        self.assertEqual(order.estimated_total, Decimal("1000.00"))
        self.assertEqual(order.items.count(), 2)

        # Check cart was cleared
        self.assertNotIn("cart", self.client.session)

    def test_confirmation_view_access_control(self):
        order = OrderRequest.objects.create(
            customer=self.user,
            order_type=OrderRequest.OrderType.QUICK,
            pickup_date=date.today(),
            pickup_time=time(10, 0),
            contact_phone="0719876543",
            estimated_total=Decimal("500.00"),
        )

        # Owner can view confirmation
        self.client.login(username="bob", password="password123")
        response = self.client.get(
            reverse("orders:order_confirmation", kwargs={"order_id": order.id})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, f"Order Request Received!")

        # Other customer gets 404
        self.client.login(username="charlie", password="password123")
        response_other = self.client.get(
            reverse("orders:order_confirmation", kwargs={"order_id": order.id})
        )
        self.assertEqual(response_other.status_code, 404)


class OrderHistoryAndDetailViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="diana", password="password123"
        )
        self.other_user = User.objects.create_user(
            username="edward", password="password123"
        )
        self.category = Category.objects.create(name="Tulips")
        self.flower = Flower.objects.create(
            category=self.category,
            name="Yellow Tulip",
            color="Yellow",
            unit_price=Decimal("150.00"),
            stock_quantity=30,
            is_available=True,
            is_active=True,
        )

        # Create multiple orders for Diana
        for i in range(15):
            order = OrderRequest.objects.create(
                customer=self.user,
                order_type=OrderRequest.OrderType.SCHEDULED,
                pickup_date=date.today() + timedelta(days=i + 1),
                pickup_time=time(11, 0),
                contact_phone="0779998888",
                estimated_total=Decimal("150.00") * (i + 1),
            )
            OrderItem.objects.create(
                order_request=order,
                flower=self.flower,
                quantity=i + 1,
                unit_price_at_request=Decimal("150.00"),
            )

        # Create one order for Edward
        self.edward_order = OrderRequest.objects.create(
            customer=self.other_user,
            order_type=OrderRequest.OrderType.QUICK,
            pickup_date=date.today(),
            pickup_time=time(15, 0),
            contact_phone="0711112222",
            estimated_total=Decimal("300.00"),
        )

    def test_my_orders_requires_login(self):
        response = self.client.get(reverse("orders:my_orders"))
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url)

    def test_my_orders_shows_only_customer_orders_and_paginates(self):
        self.client.login(username="diana", password="password123")
        response = self.client.get(reverse("orders:my_orders"))
        self.assertEqual(response.status_code, 200)

        # 10 items on page 1
        page_obj = response.context["page_obj"]
        self.assertEqual(len(page_obj), 10)
        self.assertEqual(page_obj.paginator.count, 15)

        # Edward's order should not be in Diana's history
        for order in page_obj:
            self.assertEqual(order.customer, self.user)
            self.assertNotEqual(order.id, self.edward_order.id)

        # Page 2 has the remaining 5
        response_page2 = self.client.get(reverse("orders:my_orders") + "?page=2")
        self.assertEqual(len(response_page2.context["page_obj"]), 5)

    def test_order_detail_requires_login(self):
        order = OrderRequest.objects.filter(customer=self.user).first()
        response = self.client.get(
            reverse("orders:order_detail", kwargs={"order_id": order.id})
        )
        self.assertEqual(response.status_code, 302)

    def test_order_detail_view_success(self):
        self.client.login(username="diana", password="password123")
        order = OrderRequest.objects.filter(customer=self.user).first()
        response = self.client.get(
            reverse("orders:order_detail", kwargs={"order_id": order.id})
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.context["order"].id, order.id)
        self.assertContains(response, f"Order #{order.id}")
        self.assertContains(response, "Yellow Tulip")

    def test_order_detail_unauthorized_access_returns_404(self):
        # Diana tries to view Edward's order -> 404
        self.client.login(username="diana", password="password123")
        response = self.client.get(
            reverse("orders:order_detail", kwargs={"order_id": self.edward_order.id})
        )
        self.assertEqual(response.status_code, 404)


class OrderRevisionViewTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="fiona", password="password123"
        )
        self.other_user = User.objects.create_user(
            username="george", password="password123"
        )
        self.category = Category.objects.create(name="Orchids")
        self.flower1 = Flower.objects.create(
            category=self.category,
            name="Purple Orchid",
            color="Purple",
            unit_price=Decimal("500.00"),
            stock_quantity=10,
            is_available=True,
            is_active=True,
        )
        self.flower2 = Flower.objects.create(
            category=self.category,
            name="White Orchid",
            color="White",
            unit_price=Decimal("600.00"),
            stock_quantity=5,
            is_available=True,
            is_active=True,
        )

        # Order with changes_required
        self.order = OrderRequest.objects.create(
            customer=self.user,
            order_type=OrderRequest.OrderType.SCHEDULED,
            pickup_date=date.today() + timedelta(days=2),
            pickup_time=time(14, 0),
            contact_phone="0775554444",
            estimated_total=Decimal("1700.00"),
            status=OrderRequest.OrderStatus.CHANGES_REQUIRED,
            revision_reason="White Orchid is out of stock. Please adjust or remove.",
        )
        self.item1 = OrderItem.objects.create(
            order_request=self.order,
            flower=self.flower1,
            quantity=1,
            unit_price_at_request=Decimal("500.00"),
        )
        self.item2 = OrderItem.objects.create(
            order_request=self.order,
            flower=self.flower2,
            quantity=2,
            unit_price_at_request=Decimal("600.00"),
        )

    def test_revise_order_requires_login(self):
        response = self.client.get(
            reverse("orders:revise_order", kwargs={"order_id": self.order.id})
        )
        self.assertEqual(response.status_code, 302)
        self.assertIn("login", response.url)

    def test_revise_order_unauthorized_access_returns_404(self):
        self.client.login(username="george", password="password123")
        response = self.client.get(
            reverse("orders:revise_order", kwargs={"order_id": self.order.id})
        )
        self.assertEqual(response.status_code, 404)

    def test_revise_order_not_changes_required_redirects(self):
        self.client.login(username="fiona", password="password123")
        self.order.status = OrderRequest.OrderStatus.PENDING
        self.order.save()

        response = self.client.get(
            reverse("orders:revise_order", kwargs={"order_id": self.order.id})
        )
        self.assertRedirects(
            response, reverse("orders:order_detail", kwargs={"order_id": self.order.id})
        )

    def test_revise_order_get_success(self):
        self.client.login(username="fiona", password="password123")
        response = self.client.get(
            reverse("orders:revise_order", kwargs={"order_id": self.order.id})
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "White Orchid is out of stock")
        self.assertContains(response, "Purple Orchid")

    def test_revise_order_post_update_and_remove(self):
        self.client.login(username="fiona", password="password123")
        # Catalog price updated for flower1
        self.flower1.unit_price = Decimal("550.00")
        self.flower1.save()

        # Update item1 quantity to 3, and remove item2
        post_data = {
            f"quantity_{self.item1.id}": "3",
            f"remove_{self.item2.id}": "1",
        }
        response = self.client.post(
            reverse("orders:revise_order", kwargs={"order_id": self.order.id}),
            data=post_data,
        )
        self.assertRedirects(
            response, reverse("orders:order_detail", kwargs={"order_id": self.order.id})
        )

        self.order.refresh_from_db()
        # Status reset back to PENDING
        self.assertEqual(self.order.status, OrderRequest.OrderStatus.PENDING)
        # Total updated: 3 * 550.00 = 1650.00
        self.assertEqual(self.order.estimated_total, Decimal("1650.00"))
        # item2 was removed
        self.assertEqual(self.order.items.count(), 1)
        self.item1.refresh_from_db()
        self.assertEqual(self.item1.quantity, 3)
        self.assertEqual(self.item1.unit_price_at_request, Decimal("550.00"))

    def test_revise_order_remove_all_items_fails(self):
        self.client.login(username="fiona", password="password123")
        # Remove both items
        post_data = {
            f"remove_{self.item1.id}": "1",
            f"remove_{self.item2.id}": "1",
        }
        response = self.client.post(
            reverse("orders:revise_order", kwargs={"order_id": self.order.id}),
            data=post_data,
        )
        self.assertRedirects(
            response, reverse("orders:revise_order", kwargs={"order_id": self.order.id})
        )

        self.order.refresh_from_db()
        # Status should NOT be set to PENDING
        self.assertEqual(self.order.status, OrderRequest.OrderStatus.CHANGES_REQUIRED)

