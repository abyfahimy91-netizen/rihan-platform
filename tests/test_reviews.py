from django.test import TestCase, Client
from django.urls import reverse
from apps.catalog.models import Category, Product, ProductReview
from apps.orders.models import Order

class ProductReviewsTestCase(TestCase):
    def setUp(self):
        self.cat = Category.objects.create(name="چاشنی", slug="spices-r")
        self.p = Product.objects.create(
            category=self.cat, title="زعفران قائنات", slug="zaferan-qaenat",
            sku="RIHAN-ZAF-01", summary="زعفران نگین", price=650000, stock=20
        )
        self.order = Order.objects.create(
            customer_name="مریم کارمند", customer_phone="09121112233",
            shipping_address="تبریز", postal_code="5123456789",
            items_total=650000, grand_total=650000, status='delivered'
        )

    def test_review_submission_and_moderation(self):
        c = Client()
        # 1. Submit review
        res = c.post(reverse('submit_review', kwargs={'slug': self.p.slug}), {
            'author_name': 'مریم کارمند',
            'order_number': self.order.order_number,
            'rating': 5,
            'comment': 'عطر و رنگدهی فوق‌العاده بود.'
        })
        self.assertEqual(res.status_code, 302)

        # 2. Check in DB (is_approved=False by default)
        review = ProductReview.objects.filter(product=self.p).first()
        self.assertIsNotNone(review)
        self.assertFalse(review.is_approved)
        self.assertTrue(review.is_verified_buyer)

        # 3. Unapproved review does not appear on detail page
        res_detail = c.get(reverse('product_detail', kwargs={'slug': self.p.slug}))
        self.assertNotContains(res_detail, "عطر و رنگدهی فوق‌العاده بود")

        # 4. Admin approves review
        review.is_approved = True
        review.admin_reply = "از رضایت شما خرسندیم."
        review.save()

        # 5. Approved review appears with admin reply
        res_detail_approved = c.get(reverse('product_detail', kwargs={'slug': self.p.slug}))
        self.assertContains(res_detail_approved, "عطر و رنگدهی فوق‌العاده بود")
        self.assertContains(res_detail_approved, "از رضایت شما خرسندیم")
        self.assertEqual(self.p.average_rating, 5.0)
        self.assertEqual(self.p.reviews_count, 1)
