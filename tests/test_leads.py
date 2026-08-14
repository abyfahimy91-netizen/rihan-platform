from django.test import TestCase, Client
from django.urls import reverse
from apps.catalog.models import Category, Product, LeadCapture

class LeadCaptureTestCase(TestCase):
    def setUp(self):
        self.cat = Category.objects.create(name="سوغات", slug="souvenir-l")
        self.p = Product.objects.create(
            category=self.cat, title="توت خشک هوراند", slug="tut-khoshk",
            sku="RIHAN-TUT-01", summary="توت خشک ارگانیک", price=320000, stock=0, is_available=False
        )

    def test_submit_lead_for_custom_product(self):
        c = Client()
        res = c.post(reverse('submit_lead'), {
            'phone': '09121112233',
            'full_name': 'حسن معلم',
            'requested_product_name': 'گردوی درجه یک کلیبر',
            'notes': 'پوست کاغذی و پرچرب'
        })
        self.assertEqual(res.status_code, 302)
        
        lead = LeadCapture.objects.filter(phone='09121112233').first()
        self.assertIsNotNone(lead)
        self.assertEqual(lead.requested_product_name, 'گردوی درجه یک کلیبر')
        self.assertEqual(lead.status, 'new')

    def test_submit_lead_for_out_of_stock_product(self):
        c = Client()
        res = c.post(reverse('submit_lead'), {
            'phone': '09149998877',
            'product_id': self.p.id
        })
        self.assertEqual(res.status_code, 302)
        
        lead = LeadCapture.objects.filter(product=self.p).first()
        self.assertIsNotNone(lead)
        self.assertEqual(lead.product.title, 'توت خشک هوراند')
