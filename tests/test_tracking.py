from django.test import TestCase, Client
from django.urls import reverse
from apps.orders.models import Order

class OrderTrackingTestCase(TestCase):
    def setUp(self):
        self.order = Order.objects.create(
            customer_name="سارا محمدی",
            customer_phone="09123456789",
            shipping_address="تبریز، ولیعصر",
            postal_code="5123456789",
            items_total=450000,
            grand_total=450000,
            status='shipped',
            tracking_code='POST-1405-998877'
        )

    def test_tracking_page_and_valid_search(self):
        c = Client()
        # View tracking page
        res = c.get(reverse('order_tracking'))
        self.assertEqual(res.status_code, 200)

        # Search with valid order and phone
        res_search = c.get(reverse('order_tracking'), {
            'order_number': self.order.order_number,
            'phone': '09123456789'
        })
        self.assertEqual(res_search.status_code, 200)
        self.assertContains(res_search, "سارا محمدی")
        self.assertContains(res_search, "POST-1405-998877")
        self.assertContains(res_search, "سامانه پیگیری شرکت ملی پست")

    def test_tracking_phone_mismatch(self):
        c = Client()
        res_mismatch = c.get(reverse('order_tracking'), {
            'order_number': self.order.order_number,
            'phone': '09999999999'
        })
        self.assertEqual(res_mismatch.status_code, 200)
        self.assertContains(res_mismatch, "سفارشی با این مشخصات یافت نشد")
