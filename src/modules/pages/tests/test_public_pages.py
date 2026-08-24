"""تست صفحات عمومی ماژول pages — D-100 (FAQ + اتصال صفحات به تنظیمات سایت)"""
from django.test import TestCase, Client
from django.urls import reverse, NoReverseMatch

from src.modules.pages.markup import render_page_markup
from src.modules.pages.models import FaqItem, SiteSettings

HOST = 'rihan360.ir'  # طبق ALLOWED_HOSTS


class MarkupRendererTest(TestCase):
    """تست موتور رندر متن ادیت‌پذیر ادمین"""

    def test_empty_text(self):
        self.assertEqual(render_page_markup(''), '')
        self.assertEqual(render_page_markup(None), '')
        self.assertEqual(render_page_markup('   \n  '), '')

    def test_paragraph(self):
        html = render_page_markup('سلام این یک متن است.')
        self.assertEqual(html, '<p class="pm-p">سلام این یک متن است.</p>')

    def test_heading(self):
        html = render_page_markup('# شرایط مرجوعی')
        self.assertIn('<h2 class="pm-heading">شرایط مرجوعی</h2>', html)

    def test_dash_list(self):
        html = render_page_markup('- مورد اول\n- مورد دوم')
        self.assertIn('<ul class="pm-list">', html)
        self.assertIn('<li>مورد اول</li>', html)
        # علامت لیست نباید داخل آیتم‌ها لو برود
        self.assertNotIn('<li>-', html)
        self.assertNotIn('</li>-', html)

    def test_numbered_list_persian_digits(self):
        html = render_page_markup('۱. تماس بگیرید\n۲. اعلام کنید')
        self.assertIn('<ol class="pm-olist">', html)
        self.assertIn('<li>تماس بگیرید</li>', html)
        self.assertNotIn('۱.', html)

    def test_quote(self):
        html = render_page_markup('> محصول متغیر است.')
        self.assertIn('<blockquote class="pm-quote">محصول متغیر است.</blockquote>', html)

    def test_html_is_escaped(self):
        html = render_page_markup('<script>alert(1)</script>')
        self.assertNotIn('<script>', html)
        self.assertIn('&lt;script&gt;', html)

    def test_mixed_blocks(self):
        html = render_page_markup(
            'پاراگراف اول\n\n# تیتر\n\n- آیتم'
        )
        self.assertIn('<p class="pm-p">پاراگراف اول</p>', html)
        self.assertIn('<h2', html)
        self.assertIn('<ul', html)


class PublicPagesTest(TestCase):
    """صفحات عمومی باید 200 بدهند و از تنظیمات سایت بخوانند"""

    def setUp(self):
        self.client = Client(HTTP_HOST=HOST)
        s = SiteSettings.load()
        s.contact_phone = '09143183790'
        s.save()

    def test_faq_url_resolves(self):
        """لینک فوتر /faq/ دیگر 404 نمی‌دهد"""
        try:
            url = reverse('pages:faq')
        except NoReverseMatch:
            self.fail('pages:faq در URLconf ثبت نشده است')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        # مسیر مستقیم هم باید کار کند
        response = self.client.get('/faq/')
        self.assertEqual(response.status_code, 200)

    def test_faq_shows_active_items(self):
        FaqItem.objects.create(question='چگونه سفارش دهم؟', answer='از صفحه محصول شروع کنید.', sort_order=1)
        FaqItem.objects.create(question='سوال غیرفعال', answer='نباید دیده شود', is_active=False)

        response = self.client.get('/faq/')
        content = response.content.decode()

        self.assertIn('چگونه سفارش دهم؟', content)
        self.assertIn('از صفحه محصول شروع کنید.', content)
        self.assertNotIn('سوال غیرفعال', content)

    def test_faq_ordering(self):
        FaqItem.objects.create(question='دوم', sort_order=2)
        FaqItem.objects.create(question='اول', sort_order=1)

        response = self.client.get('/faq/')
        content = response.content.decode()

        self.assertLess(content.index('اول'), content.index('دوم'))

    def test_contact_uses_settings_phone(self):
        """شماره تلفن واقعی ادمین باید نمایش داده شود، نه شماره تست هاردکد"""
        response = self.client.get('/contact/')
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()

        # لینک tel با مقدار دیتابیس
        self.assertIn('tel:09143183790', content)
        # شماره تست قدیمی نباید هیچ‌جا باشد
        self.assertNotIn('۰۹۱۲-۳۴۵-۶۷۸۹', content)
        self.assertNotIn('tel:09123456789', content)

    def test_contact_no_broken_tracking_link(self):
        """/order/tracking/ وجود خارجی ندارد؛ باید lookup باشد"""
        response = self.client.get('/contact/')
        content = response.content.decode()
        self.assertNotIn('href="/order/tracking/"', content)

    def test_contact_empty_fields_hidden(self):
        """فیلدهای خالی تنظیمات، کارت خالی نمایش ندهند"""
        s = SiteSettings.load()
        s.contact_phone = ''
        s.contact_email = ''
        s.save()

        response = self.client.get('/contact/')
        content = response.content.decode()
        self.assertNotIn('tel:', content)
        self.assertNotIn('mailto:', content)

    def test_about_renders_settings_content(self):
        s = SiteSettings.load()
        s.about_body = '# تیتر تستی\n\nمتن تستی درباره ما'
        s.save()

        response = self.client.get('/about/')
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('تیتر تستی', content)
        self.assertIn('متن تستی درباره ما', content)

    def test_return_policy_renders_settings_content(self):
        s = SiteSettings.load()
        s.return_policy_body = '- شرط تستی مرجوعی'
        s.save()

        response = self.client.get('/return-policy/')
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn('شرط تستی مرجوعی', content)


class FaqItemAdminTest(TestCase):
    """ادمین سوالات متداول باید کار کند"""

    def setUp(self):
        from django.contrib.auth import get_user_model
        User = get_user_model()
        self.admin = User.objects.create_superuser(
            username='faq_admin_test', password='test-pass-123', email='faq_admin_test@rihan.local'
        )
        self.client = Client(HTTP_HOST=HOST)

    def test_faq_changelist(self):
        self.client.force_login(self.admin)
        response = self.client.get('/admin/pages/faqitem/')
        self.assertEqual(response.status_code, 200)

    def test_faq_add_form(self):
        self.client.force_login(self.admin)
        response = self.client.get('/admin/pages/faqitem/add/')
        self.assertEqual(response.status_code, 200)
