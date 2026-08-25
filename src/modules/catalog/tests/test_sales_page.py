"""تست صفحه فروش اقناعی — D-104 (هشت‌بخشی + اشتراک‌گذاری + نظرات محرمانه + JSON-LD)"""
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase, Client

from src.modules.catalog.models import (
    Category, Supplier, Product, Inventory, ProductFaq,
)
from src.modules.order.models import Order, OrderItem
from src.modules.reviews.models import Review

User = get_user_model()
HOST = 'rihan360.ir'


class SalesPageTestBase(TestCase):
    def setUp(self):
        self.client = Client(HTTP_HOST=HOST)
        cat = Category.objects.create(name='تست دسته', slug='test-cat-d104')
        sup = Supplier.objects.create(title='تست تامین', city='تبریز')
        self.product = Product.objects.create(
            name='محصول تست فروش', slug='test-sales-product',
            category=cat, supplier=sup, unit='عدد',
            base_price=Decimal('100000'), shipping_cost=Decimal('0'),
            margin_percent=0, short_description='توضیح تست',
            origin_story='داستان تست',
            status='active',
        )
        self.product.final_price = self.product.calculate_final_price()
        self.product.save()
        inv, _ = Inventory.objects.get_or_create(product=self.product)
        inv.quantity = Decimal('10')
        inv.save()

    def _make_delivered_order(self, user):
        order = Order.objects.create(
            user=user, status=Order.OrderStatus.DELIVERED,
            guest_name='تست', guest_phone=user.username, guest_address='آدرس تستی طولانی کافی برای سیستم',
        )
        OrderItem.objects.create(
            order=order, product=self.product, quantity=1,
            unit_price_at_purchase=self.product.final_price,
        )
        return order


class SalesPageRenderTest(SalesPageTestBase):
    def test_page_200(self):
        r = self.client.get('/products/test-sales-product/')
        self.assertEqual(r.status_code, 200)

    def test_result_headline_shown_when_set(self):
        self.product.result_headline = 'دیگر نگران کیفیت نباشید'
        self.product.save()
        c = self.client.get('/products/test-sales-product/').content.decode()
        self.assertIn('دیگر نگران کیفیت نباشید', c)

    def test_fit_not_fit_sections(self):
        self.product.fit_for = '- به کیفیت اهمیت می‌دهید'
        self.product.not_fit_for = '- فقط دنبال ارزان‌ترین هستید'
        self.product.save()
        c = self.client.get('/products/test-sales-product/').content.decode()
        self.assertIn('این کالا برای شماست اگر', c)
        self.assertIn('سفارش ندهید اگر', c)
        self.assertIn('به کیفیت اهمیت می‌دهید', c)

    def test_discount_display(self):
        self.product.compare_at_price = Decimal('200000')
        self.product.save()  # final_price=100000 → ۵۰٪
        c = self.client.get('/products/test-sales-product/').content.decode()
        self.assertIn('۵۰٪ تخفیف', c)
        self.assertIn('price-old', c)

    def test_curation_and_deepdive_render(self):
        self.product.curation_story = '# چطور انتخاب شد\n- ده نمونه تست شد'
        self.product.deep_dive = '# راهنمای کامل\nمتن مقاله تستی'
        self.product.save()
        c = self.client.get('/products/test-sales-product/').content.decode()
        self.assertIn('چطور این را انتخاب کردیم؟', c)
        self.assertIn('همه‌چیز درباره', c)
        self.assertIn('متن مقاله تستی', c)

    def test_faq_section(self):
        ProductFaq.objects.create(product=self.product, question='مرجوعی چطور است؟', answer='تا ۷ روز', sort_order=1)
        c = self.client.get('/products/test-sales-product/').content.decode()
        self.assertIn('مرجوعی چطور است؟', c)
        self.assertIn('تا ۷ روز', c)

    def test_fast_buy_button(self):
        c = self.client.get('/products/test-sales-product/').content.decode()
        self.assertIn('fast_buy', c)
        self.assertIn('خرید سریع', c)

    def test_sticky_bar(self):
        c = self.client.get('/products/test-sales-product/').content.decode()
        self.assertIn('stickyBuyBar', c)


class JsonLdTest(SalesPageTestBase):
    def test_product_schema(self):
        c = self.client.get('/products/test-sales-product/').content.decode()
        self.assertIn('"@type": "Product"', c)
        self.assertIn('"priceCurrency": "IRR"', c)
        # قیمت ریالی = final_price * 10
        expected = int(self.product.final_price * 10)
        self.assertIn(f'"price": "{expected}"', c)

    def test_faq_schema(self):
        ProductFaq.objects.create(product=self.product, question='سوال اسکیما؟', answer='پاسخ اسکیما', sort_order=1)
        c = self.client.get('/products/test-sales-product/').content.decode()
        self.assertIn('"@type": "FAQPage"', c)
        self.assertIn('سوال اسکیما؟', c)


class ShareCounterTest(SalesPageTestBase):
    def test_share_increments(self):
        self.assertEqual(self.product.share_count, 0)
        r = self.client.post('/products/test-sales-product/share/', {'channel': 'telegram'})
        self.assertEqual(r.status_code, 200)
        d = r.json()
        self.assertTrue(d['ok'])
        self.assertEqual(d['count'], 1)
        self.product.refresh_from_db()
        self.assertEqual(self.product.share_count, 1)

    def test_share_get_not_allowed(self):
        r = self.client.get('/products/test-sales-product/share/')
        self.assertEqual(r.status_code, 405)

    def test_share_button_in_page(self):
        c = self.client.get('/products/test-sales-product/').content.decode()
        self.assertIn('shareHub', c)
        self.assertIn('استوری اینستاگرام', c)
        self.assertIn('eitaa', c)


class PrivacyReviewsTest(SalesPageTestBase):
    def setUp(self):
        super().setUp()
        self.buyer = User.objects.create_user(
            username='09121404400', password='test123456', email='b@rihan.local',
            first_name='مریم', last_name='احمدی',
        )
        self.order = self._make_delivered_order(self.buyer)

    def test_anonymous_display_by_default(self):
        Review.objects.create(product=self.product, order=self.order, user=self.buyer,
                              rating=5, title='', text='عالی بود', display_anonymously=True,
                              is_approved=True)
        c = self.client.get('/products/test-sales-product/').content.decode()
        self.assertIn('خریدار تأییدشده', c)
        self.assertNotIn('مریم', c)

    def test_named_display_when_allowed(self):
        Review.objects.create(product=self.product, order=self.order, user=self.buyer,
                              rating=4, title='', text='خوب بود', display_anonymously=False,
                              is_approved=True)
        c = self.client.get('/products/test-sales-product/').content.decode()
        self.assertIn('مریم', c)

    def test_unapproved_hidden(self):
        Review.objects.create(product=self.product, order=self.order, user=self.buyer,
                              rating=1, title='', text='بد بود', display_anonymously=True)
        c = self.client.get('/products/test-sales-product/').content.decode()
        self.assertNotIn('بد بود', c)

    def test_inline_submit_success(self):
        self.client.force_login(self.buyer)
        r = self.client.post(f'/reviews/inline/test-sales-product/', {
            'rating': '5', 'text': 'محصول فوق‌العاده بود', 'anonymous': 'on',
        })
        self.assertEqual(r.status_code, 200)
        self.assertTrue(r.json()['success'])
        review = Review.objects.get(order=self.order)
        self.assertFalse(review.is_approved)  # در صف تایید ادمین
        self.assertTrue(review.display_anonymously)

    def test_inline_submit_requires_login(self):
        r = self.client.post(f'/reviews/inline/test-sales-product/', {'rating': '5', 'text': 'تست'})
        self.assertEqual(r.status_code, 403)

    def test_inline_submit_requires_delivered(self):
        stranger = User.objects.create_user(username='09121404401', password='x1234567', email='s@rihan.local')
        self.client.force_login(stranger)
        r = self.client.post(f'/reviews/inline/test-sales-product/', {'rating': '5', 'text': 'تست'})
        self.assertEqual(r.status_code, 403)

    def test_review_form_in_page(self):
        c = self.client.get('/products/test-sales-product/').content.decode()
        self.assertIn('ثبت نظر در ۲ ثانیه', c)
        self.assertIn('نام من به‌صورت ناشناس', c)


class FastBuyRedirectTest(SalesPageTestBase):
    def test_fast_buy_redirects_to_checkout(self):
        r = self.client.post('/order/cart/add/', {
            'product_slug': self.product.slug, 'quantity': 1, 'fast_buy': '1',
        })
        self.assertEqual(r.status_code, 302)
        self.assertIn('/order/checkout/', r['Location'])

    def test_normal_add_goes_to_cart(self):
        r = self.client.post('/order/cart/add/', {
            'product_slug': self.product.slug, 'quantity': 1,
        })
        self.assertEqual(r.status_code, 302)
        self.assertIn('/order/cart/', r['Location'])


class ProductFaqAdminTest(SalesPageTestBase):
    def test_admin_pages(self):
        admin = User.objects.create_superuser(
            username='d104_admin', password='test-pass-123', email='d104@rihan.local'
        )
        self.client.force_login(admin)
        r = self.client.get(f'/admin/catalog/product/{self.product.pk}/change/')
        self.assertEqual(r.status_code, 200)
        c = r.content.decode()
        self.assertIn('صفحه فروش اقناعی', c)
        self.assertIn('سوالات متداول این محصول', c)
        self.assertIn('result_headline', c)
