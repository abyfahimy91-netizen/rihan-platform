"""تست UX بازطراحی‌شده پروفایل — D-122 (1405/06/08)

قفل‌کردن فیکس‌های گزارش کاربر:
۱) منوی عمودی «هاب حساب» جایگزین تب‌های افقی اسکرولی — همهٔ بخش‌ها همیشه پیدا
۲) حذف دایرهٔ حرف اول نام (آواتار) از هدر — فقط نام + شمارهٔ واضح
۳) شمارهٔ موبایل درشت و پررنگ (#pfPhone)
۴) خطای فرم آدرس → تب آدرس‌ها خودکار باز می‌شود (pfInitial = 'addresses')
"""
from django.contrib.auth import get_user_model
from django.test import TestCase, Client
from django.urls import reverse

User = get_user_model()
HOST = 'rihan360.ir'


class ProfileUXTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='09121550000', password='test123456',
            first_name='مریم', last_name='احمدی',
        )
        self.client = Client(HTTP_HOST=HOST)
        self.client.force_login(self.user)

    def _get(self):
        r = self.client.get('/accounts/profile/')
        self.assertEqual(r.status_code, 200)
        return r.content.decode()

    def test_vertical_menu_replaces_scroll_tabs(self):
        """تب‌های افقی اسکرولی (pf-tabs) حذف و منوی عمودی (pf-home) آمده است"""
        c = self._get()
        self.assertIn('pf-home', c)
        self.assertIn('data-tab="orders"', c)
        self.assertNotIn('pf-tab', c)  # هیچ ردی از تب افقی قدیمی

    def test_header_has_no_avatar_and_shows_phone(self):
        """دایرهٔ حرف اول حذف شده؛ نام + شمارهٔ موبایل واضح مانده"""
        c = self._get()
        self.assertNotIn('pf-avatar', c)
        self.assertIn('id="pfPhone"', c)
        self.assertIn('مریم احمدی', c)

    def test_menu_covers_all_sections(self):
        """هر ۵ بخش در منو + دکمهٔ بازگشت در هر پنل"""
        c = self._get()
        for name in ('orders', 'addresses', 'account', 'security', 'devices'):
            self.assertIn(f'data-tab="{name}"', c)
        self.assertEqual(c.count('data-back'), 5)

    def test_exit_is_standalone_menu_row(self):
        """خروج، ردیف مستقل منو است (نه تب چسبیده به تب‌ها)"""
        c = self._get()
        self.assertIn('خروج از حساب', c)
        self.assertIn(reverse('auth_pages:logout'), c)

    def test_address_error_reopens_addresses_panel(self):
        """D-113c + D-122: خطای اعتبارسنجی آدرس → پنل آدرس‌ها خودکار باز شود
        (قبلاً فقط با edit_address باز می‌شد؛ خطای «افزودن آدرس» پنل را باز نمی‌کرد)"""
        r = self.client.post('/accounts/profile/', {
            'action': 'address_save',
            'full_name': 'مریم احمدی',
            'phone': '09121550000',
            'address': 'تبریز، خیابان آزادی، پلاک ۱۰',
            # postal_code عمداً غایب → خطای الزام کدپستی
        })
        c = r.content.decode()
        self.assertIn('adr-errors', c)
        self.assertIn("pfInitial = 'addresses'", c)
