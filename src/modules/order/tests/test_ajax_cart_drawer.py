"""D-121: افزودن AJAX به سبد + payload سبد کناری (mini-cart)

تجربه هدف: کاربر در صفحه محصول چند بسته (مثلاً ۱کیلو + ۲۵۰گرم) را بدون
ترک صفحه به سبد اضافه کند؛ پاسخ JSON وضعیت کامل سبد را می‌دهد تا سبد
کناری رندر شود و بج هدر همان لحظه به‌روز شود.
"""
from decimal import Decimal

from django.test import TestCase, Client

from src.modules.catalog.models import Category, Supplier, Product, ProductVariant

HOST = 'rihan360.ir'
AJAX = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}


class AjaxCartDrawerBase(TestCase):
    def setUp(self):
        self.client = Client(HTTP_HOST=HOST)
        cat = Category.objects.create(name='دسته تست D-121', slug='cat-d121')
        sup = Supplier.objects.create(title='تامین تست D-121', city='تبریز')
        self.product = Product.objects.create(
            name='سماق تست D-121', slug='sumac-d121',
            category=cat, supplier=sup, unit='بسته',
            base_price=Decimal('100000'), shipping_cost=Decimal('0'),
            margin_percent=0, short_description='توضیح تست',
            status='active',
        )
        self.product.final_price = self.product.calculate_final_price()
        self.product.save()
        self.v1 = ProductVariant.objects.create(
            product=self.product, title='بسته ۱ کیلوگرمی',
            price=Decimal('2950000'), stock_quantity=7,
            is_default=True, low_stock_threshold=5,
        )
        self.v2 = ProductVariant.objects.create(
            product=self.product, title='بسته ۲۵۰ گرمی',
            price=Decimal('740000'), stock_quantity=11,
            low_stock_threshold=5,
        )

    def add(self, variant=None, quantity='1', ajax=True, fast_buy=False):
        data = {
            'product_slug': self.product.slug,
            'quantity': quantity,
            'variant_id': str(variant.id) if variant else '',
        }
        if fast_buy:
            data['fast_buy'] = '1'
        kwargs = dict(AJAX) if ajax else {}
        return self.client.post('/order/cart/add/', data, **kwargs)


class AjaxAddToCartTests(AjaxCartDrawerBase):
    def test_ajax_add_returns_full_cart_payload(self):
        resp = self.add(self.v1)
        self.assertEqual(resp.status_code, 200)
        d = resp.json()
        self.assertTrue(d['ok'])
        self.assertEqual(d['item_count'], 1)
        self.assertEqual(d['count_fa'], '۱')
        self.assertEqual(len(d['items']), 1)
        item = d['items'][0]
        self.assertEqual(item['variant_title'], 'بسته ۱ کیلوگرمی')
        self.assertEqual(item['subtotal'], '۲٬۹۵۰٬۰۰۰')
        self.assertEqual(item['quantity_fa'], '۱')
        self.assertEqual(item['max_available'], 7)
        # سازگاری با صفحه سبد (applyTotals) — per_item کلیدش id کالای سبد است
        self.assertEqual(list(d['per_item'].keys()), [item['id']])
        self.assertTrue(d['shipping_free'])
        self.assertIn('سماق تست D-121', d['message'])

    def test_ajax_add_two_variants_in_one_flow(self):
        """سناریوی اصلی کاربر: ۱کیلو + ۲عدد ۲۵۰گرم بدون ترک صفحه"""
        r1 = self.add(self.v1).json()
        r2 = self.add(self.v2, quantity='2').json()
        self.assertTrue(r2['ok'])
        self.assertEqual(r2['item_count'], 3)
        self.assertEqual(r2['count_fa'], '۳')
        self.assertEqual(len(r2['items']), 2)
        titles = {i['variant_title'] for i in r2['items']}
        self.assertEqual(titles, {'بسته ۱ کیلوگرمی', 'بسته ۲۵۰ گرمی'})
        self.assertEqual(r2['subtotal'], '۴٬۴۳۰٬۰۰۰')

    def test_non_ajax_add_still_redirects_to_cart(self):
        resp = self.add(self.v1, ajax=False)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp['Location'], '/order/cart/')

    def test_fast_buy_still_redirects_to_checkout(self):
        resp = self.add(self.v1, ajax=False, fast_buy=True)
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp['Location'], '/order/checkout/')

    def test_ajax_stock_error_returns_json_400(self):
        resp = self.add(self.v1, quantity='99')
        self.assertEqual(resp.status_code, 400)
        d = resp.json()
        self.assertFalse(d['ok'])
        self.assertIn('موجودی', d['message'])

    def test_ajax_invalid_quantity_defaults_to_one(self):
        resp = self.add(self.v1, quantity='abc')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['item_count'], 1)

    def test_ajax_farsi_quantity_digits_accepted(self):
        resp = self.add(self.v2, quantity='۲')
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()['item_count'], 2)


class CartJsonSyncTests(AjaxCartDrawerBase):
    """همان payload توسط update/remove هم برمی‌گردد تا سبد کناری همیشه سینک بماند"""

    def test_update_via_ajax_returns_items(self):
        self.add(self.v1)
        r = self.add(self.v2).json()
        item_id = next(i['id'] for i in r['items'] if i['variant_title'] == 'بسته ۲۵۰ گرمی')
        resp = self.client.post('/order/cart/update/', {
            'item_id': item_id, 'quantity': '3',
        }, **AJAX)
        self.assertEqual(resp.status_code, 200)
        d = resp.json()
        self.assertTrue(d['ok'])
        self.assertEqual(d['item_count'], 4)  # ۱×۱کیلو + ۳×۲۵۰گرم
        item = next(i for i in d['items'] if i['id'] == item_id)
        self.assertEqual(item['quantity_fa'], '۳')
        self.assertEqual(item['subtotal'], '۲٬۲۲۰٬۰۰۰')

    def test_remove_via_ajax_empties_items(self):
        r = self.add(self.v1).json()
        item_id = r['items'][0]['id']
        resp = self.client.post('/order/cart/remove/', {
            'item_id': item_id,
        }, **AJAX)
        self.assertEqual(resp.status_code, 200)
        d = resp.json()
        self.assertTrue(d['ok'])
        self.assertEqual(d['item_count'], 0)
        self.assertEqual(d['items'], [])


class ProductPageDrawerMarkupTests(AjaxCartDrawerBase):
    def test_product_page_contains_drawer_and_sticky_price(self):
        resp = self.client.get('/products/sumac-d121/')
        self.assertEqual(resp.status_code, 200)
        c = resp.content.decode()
        self.assertIn('id="cartDrawer"', c)
        self.assertIn('id="cartDrawerOverlay"', c)
        self.assertIn('id="sbbPrice"', c)
        self.assertIn('data-add-cart', c)
        self.assertIn('data-fast-buy', c)
        self.assertIn('qty-stepper', c)
        self.assertIn('data-base=', c)
        self.assertIn('/order/checkout/', c)

    def test_sticky_price_initially_shows_default_variant(self):
        resp = self.client.get('/products/sumac-d121/')
        c = resp.content.decode()
        self.assertIn('۲٬۹۵۰٬۰۰۰', c)  # قیمت بسته استاندارد ۱ کیلوگرمی
        self.assertIn('بسته ۲۵۰ گرمی', c)
        self.assertIn('بسته ۱ کیلوگرمی', c)

    def test_drawer_urls_resolved_in_markup(self):
        resp = self.client.get('/products/sumac-d121/')
        c = resp.content.decode()
        self.assertIn('data-update-url="/order/cart/update/"', c)
        self.assertIn('data-remove-url="/order/cart/remove/"', c)
