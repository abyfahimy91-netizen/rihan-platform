from django.test import TestCase, Client
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile
from apps.orders.models import Order
from apps.payments.models import Payment
from apps.payments.gateways.card_to_card import CardToCardGateway

class PaymentsTestCase(TestCase):
    def setUp(self):
        self.order = Order.objects.create(
            customer_name="سارا محمدی",
            customer_phone="09123456789",
            shipping_address="تبریز",
            postal_code="5123456789",
            items_total=500000,
            grand_total=500000
        )

    def test_card_to_card_lifecycle(self):
        gw = CardToCardGateway()
        payment = gw.initiate_payment(self.order)
        self.assertEqual(payment.amount, 500000)
        self.assertEqual(payment.status, 'pending')

        # Submit receipt
        img = SimpleUploadedFile("receipt.jpg", b"sample_image_bytes", content_type="image/jpeg")
        gw.submit_receipt(payment, receipt_image=img, reference="12345678", card_last_four="9988")
        
        payment.refresh_from_db()
        self.order.refresh_from_db()
        self.assertEqual(payment.status, 'submitted')
        self.assertEqual(self.order.status, 'payment_submitted')

        # Verify payment by admin
        gw.verify_payment(payment)
        payment.refresh_from_db()
        self.order.refresh_from_db()
        self.assertEqual(payment.status, 'verified')
        self.assertEqual(self.order.status, 'confirmed')
