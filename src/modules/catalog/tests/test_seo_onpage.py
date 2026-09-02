"""
SEO-14050610 فاز ۲: متا دیسکریپشن‌ها + تایتل دسته‌بندی + اسکیمای Organization + alt گالری
"""
from decimal import Decimal

from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

from src.modules.catalog.models import Category, Product, ProductImage, ProductVariant

HOME_DESC_KEY = 'خرید سماق قرمز اصل هوراند'
ORG_LOGO = '"logo":"https://rihan360.ir/static/img/logo/rihan-logo-badge.png"'
ORG_SAMEAS = 'https://www.instagram.com/rihan360.ir'

TINY_PNG = bytes.fromhex(
    '89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489'
    '0000000d49444154789c626001000000ffff03000006000557bfabd400000000'
    '49454e44ae426082'
)


def make_product(slug, name):
    cat = Category.objects.create(name='دستهٔ ' + slug, slug='cat-' + slug)
    p = Product.objects.create(
        name=name, slug=slug, category=cat,
        base_price=Decimal('100000'),
        short_description='توضیح کوتاه', origin_story='x', status='active',
    )
    ProductVariant.objects.create(product=p, title='بسته ۱۰۰ گرمی', price=Decimal('295000'), stock_quantity=5)
    return p


class HomeSeoTests(TestCase):
    def test_home_has_rich_meta_description(self):
        r = self.client.get('/')
        self.assertEqual(r.status_code, 200)
        self.assertIn(HOME_DESC_KEY, r.content.decode())

    def test_home_organization_schema_has_logo_and_sameas(self):
        c = self.client.get('/').content.decode()
        self.assertIn(ORG_LOGO, c)
        self.assertIn(ORG_SAMEAS, c)

    def test_category_page_title_is_distinct(self):
        make_product('catprod', 'محصول دسته')
        home = self.client.get('/').content.decode()
        r = self.client.get('/?category=cat-catprod')
        self.assertEqual(r.status_code, 200)
        cat_html = r.content.decode()
        self.assertIn('خرید دستهٔ catprod | ریهان', cat_html)
        self.assertNotEqual(
            home.split('<title>')[1].split('</title>')[0],
            cat_html.split('<title>')[1].split('</title>')[0],
        )


class GalleryAltTests(TestCase):
    def setUp(self):
        self.product = make_product('galprod', 'سماق گالری')
        for i in (1, 2):
            ProductImage.objects.create(
                product=self.product,
                image=SimpleUploadedFile(f'g{i}.png', TINY_PNG, 'image/png'),
                caption=f'توضیح تصویر {i} سماق',
                sort_order=i,
            )

    def test_gallery_items_property_returns_alt(self):
        items = self.product.gallery_items
        self.assertEqual(len(items), 2)
        self.assertEqual(items[0]['alt'], 'توضیح تصویر 1 سماق')
        self.assertTrue(items[0]['url'])

    def test_product_page_thumbs_have_alt(self):
        r = self.client.get('/products/galprod/')
        c = r.content.decode()
        self.assertEqual(r.status_code, 200)
        self.assertIn('alt="توضیح تصویر 1 سماق"', c)
        self.assertIn('alt="توضیح تصویر 2 سماق"', c)


class StaticPagesSeoTests(TestCase):
    def _assert_key(self, url, key):
        r = self.client.get(url)
        self.assertEqual(r.status_code, 200)
        c = r.content.decode()
        self.assertIn('name="description"', c)
        self.assertIn(key, c)
        m = c.split('name="description" content="')[1].split('"')[0]
        self.assertGreaterEqual(len(m), 100, f'{url} description too short: {len(m)}')

    def test_about(self):
        self._assert_key('/about/', 'خرید محصولات اصیل را مطمئن و ساده')

    def test_contact(self):
        self._assert_key('/contact/', 'پاسخگوی شما هستیم')

    def test_faq(self):
        self._assert_key('/faq/', 'شرایط مرجوعی در فروشگاه اینترنتی ریهان')

    def test_return_policy(self):
        self._assert_key('/return-policy/', 'بازپرداخت وجه')
