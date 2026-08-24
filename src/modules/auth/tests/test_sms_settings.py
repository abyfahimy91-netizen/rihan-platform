"""تست تنظیمات ورود + سرویس‌دهنده‌های پیامک — D-103"""
from unittest.mock import Mock, patch

from django.contrib.auth import get_user_model
from django.test import TestCase, Client

from src.modules.auth.models import AuthSettings, PhoneOTP, SmsProvider
from src.modules.auth.services import OtpService
from src.modules.auth.services.rate_limiter import RateLimiter
from src.modules.auth.services.sms_service import SmsService

User = get_user_model()
HOST = 'rihan360.ir'


def _kavenegar_ok():
    resp = Mock()
    resp.json.return_value = {'return': {'status': 200, 'message': 'تلقایی موفق'}}
    resp.status_code = 200
    return resp


def _kavenegar_fail():
    resp = Mock()
    resp.json.return_value = {'return': {'status': 418, 'message': 'تلقایی شکست'}}
    resp.status_code = 418
    return resp


class AuthSettingsTest(TestCase):
    def test_singleton(self):
        s1 = AuthSettings.load()
        s2 = AuthSettings.load()
        self.assertEqual(s1.pk, 1)
        self.assertEqual(s1.pk, s2.pk)

    def test_both_disabled_rejected(self):
        s = AuthSettings(otp_enabled=False, password_enabled=False)
        with self.assertRaises(Exception):
            s.full_clean()

    def test_defaults(self):
        s = AuthSettings.load()
        self.assertTrue(s.otp_enabled)
        self.assertTrue(s.password_enabled)
        self.assertEqual(s.default_method, 'otp')


class SmsProviderModelTest(TestCase):
    def test_only_one_active(self):
        a = SmsProvider.objects.create(name='اولی', provider_type='kavenegar', api_key='k1', is_active=True)
        b = SmsProvider.objects.create(name='دومی', provider_type='kavenegar', api_key='k2', is_active=True)
        a.refresh_from_db()
        self.assertTrue(b.is_active)
        self.assertFalse(a.is_default if hasattr(a, 'is_default') else False)  # no-op guard
        self.assertFalse(a.is_active)

    def test_ordering_active_first(self):
        SmsProvider.objects.create(name='غیرفعال', api_key='k', priority=1)
        active = SmsProvider.objects.create(name='فعال', api_key='k', priority=99, is_active=True)
        self.assertEqual(SmsProvider.objects.first().pk, active.pk)


class SmsServiceTest(TestCase):
    def setUp(self):
        RateLimiter.clear_all('09121110001')

    def test_active_provider_used(self):
        row = SmsProvider.objects.create(
            name='کاوه اصلی', api_key='KEY', is_active=True, otp_template='rihan-otp',
        )
        with patch('src.modules.auth.sms_providers.kavenegar.requests.post', return_value=_kavenegar_ok()):
            sent, name = SmsService.send_otp('09121110001', '123456')
        self.assertTrue(sent)
        self.assertEqual(name, 'کاوه اصلی')
        row.refresh_from_db()
        self.assertIn('موفق', row.last_status)

    def test_failover_to_standby(self):
        active = SmsProvider.objects.create(name='قطع‌شده', api_key='K1', is_active=True, priority=1)
        standby = SmsProvider.objects.create(name='پشتیبان', api_key='K2', priority=2)
        # اولین فراخوانی (سرویس فعال) شکست، دومین (پشتیبان) موفق
        with patch('src.modules.auth.sms_providers.kavenegar.requests.post',
                   side_effect=[_kavenegar_fail(), _kavenegar_ok()]):
            sent, name = SmsService.send_otp('09121110001', '123456')
        self.assertTrue(sent)
        self.assertEqual(name, 'پشتیبان')
        active.refresh_from_db()
        self.assertIn('ناموفق', active.last_status)
        standby.refresh_from_db()
        self.assertIn('موفق', standby.last_status)

    def test_all_fail_returns_false(self):
        SmsProvider.objects.create(name='خراب', api_key='K', is_active=True)
        with patch('src.modules.auth.sms_providers.kavenegar.requests.post', return_value=_kavenegar_fail()):
            sent, name = SmsService.send_otp('09121110001', '123456')
        self.assertFalse(sent)

    def test_unsupported_type_marked(self):
        SmsProvider.objects.create(name='قاصدک', provider_type='ghasedak', api_key='K', is_active=True)
        sent, name = SmsService.send_otp('09121110001', '123456')
        self.assertFalse(sent)
        row = SmsProvider.objects.first()
        self.assertIn('پیاده‌سازی نشده', row.last_status)


class OtpServiceSettingsTest(TestCase):
    def setUp(self):
        RateLimiter.clear_all('09121110002')

    def test_no_provider_mock_shows_code(self):
        s = AuthSettings.load()
        s.show_code_on_sms_fail = True
        s.save()
        success, message, code = OtpService.request_otp('09121110002')
        self.assertTrue(success)
        self.assertIsNotNone(code)  # کد روی صفحه

    def test_no_provider_and_screen_off_rejected(self):
        s = AuthSettings.load()
        s.show_code_on_sms_fail = False
        s.save()
        success, message, code = OtpService.request_otp('09121110002')
        self.assertFalse(success)
        self.assertIsNone(code)
        self.assertIn('موقتاً امکان‌پذیر نیست', message)

    def test_sms_success_no_code_leak(self):
        SmsProvider.objects.create(name='کاوه', api_key='KEY', is_active=True)
        with patch('src.modules.auth.sms_providers.kavenegar.requests.post', return_value=_kavenegar_ok()):
            success, message, code = OtpService.request_otp('09121110002')
        self.assertTrue(success)
        self.assertIsNone(code)
        otp = PhoneOTP.objects.filter(phone='09121110002').first()
        self.assertEqual(otp.sent_via, 'کاوه')

    def test_ttl_from_settings(self):
        s = AuthSettings.load()
        s.otp_ttl_minutes = 7
        s.save()
        SmsProvider.objects.create(name='کاوه', api_key='KEY', is_active=True)
        with patch('src.modules.auth.sms_providers.kavenegar.requests.post', return_value=_kavenegar_ok()):
            OtpService.request_otp('09121110002')
        otp = PhoneOTP.objects.filter(phone='09121110002').order_by('-created_at').first()
        minutes = (otp.expires_at - otp.created_at).total_seconds() / 60
        self.assertAlmostEqual(minutes, 7, delta=0.1)


class LoginPageMethodsTest(TestCase):
    """کنترل روش‌های ورود از ادمین — صفحه ورود باید تابع تنظیمات باشد"""

    def setUp(self):
        self.client = Client(HTTP_HOST=HOST)

    def _set(self, **kw):
        s = AuthSettings.load()
        for k, v in kw.items():
            setattr(s, k, v)
        s.save()

    def test_both_enabled_shows_tabs(self):
        r = self.client.get('/accounts/login/')
        c = r.content.decode()
        self.assertEqual(r.status_code, 200)
        self.assertIn('کد پیامکی', c)
        self.assertIn('method=password', c)

    def test_password_disabled_hides_link(self):
        self._set(password_enabled=False)
        c = self.client.get('/accounts/login/').content.decode()
        self.assertNotIn('method=password', c)

    def test_otp_disabled_lands_on_password(self):
        self._set(otp_enabled=False)
        c = self.client.get('/accounts/login/').content.decode()
        self.assertIn('ورود با رمز عبور', c)

    def test_default_method_password(self):
        self._set(default_method='password')
        c = self.client.get('/accounts/login/').content.decode()
        self.assertIn('ورود با رمز عبور', c)

    def test_both_disabled_shows_notice(self):
        self._set(otp_enabled=False, password_enabled=False)
        c = self.client.get('/accounts/login/').content.decode()
        self.assertIn('ورود موقتاً غیرفعال است', c)

    def test_otp_request_blocked_when_disabled(self):
        self._set(otp_enabled=False)
        r = self.client.post('/accounts/login/', {
            'action': 'request_otp', 'phone': '09121110003', 'method': 'otp',
        })
        c = r.content.decode()
        self.assertIn('غیرفعال است', c)
        self.assertEqual(PhoneOTP.objects.filter(phone='09121110003').count(), 0)

    def test_password_login_blocked_when_disabled(self):
        self._set(password_enabled=False)
        r = self.client.post('/accounts/login/', {
            'action': 'password_login', 'phone': '09121110003',
            'password': 'whatever123', 'method': 'password',
        })
        self.assertIn('غیرفعال است', r.content.decode())


class SmsAdminTest(TestCase):
    def setUp(self):
        self.admin = User.objects.create_superuser(
            username='otp_admin_test', password='test-pass-123', email='a@rihan.local'
        )
        self.client = Client(HTTP_HOST=HOST)
        self.client.force_login(self.admin)

    def test_authsettings_page(self):
        r = self.client.get('/admin/rihan_auth/authsettings/')
        self.assertEqual(r.status_code, 200)

    def test_provider_list_page(self):
        SmsProvider.objects.create(name='کاوه', api_key='K', is_active=True)
        r = self.client.get('/admin/rihan_auth/smsprovider/')
        self.assertEqual(r.status_code, 200)
        self.assertIn('کاوه', r.content.decode())

    def test_add_provider_masks_key(self):
        r = self.client.post('/admin/rihan_auth/smsprovider/add/', {
            'name': 'کاوه اصلی',
            'provider_type': 'kavenegar',
            'api_key': 'SECRET-KEY-123',
            'otp_template': 'rihan-otp',
            'sender': '',
            'is_active': 'on',
            'priority': 1,
        })
        self.assertEqual(r.status_code, 302)
        row = SmsProvider.objects.first()
        self.assertEqual(row.api_key, 'SECRET-KEY-123')
        self.assertTrue(row.is_active)

        # در فرم ویرایش، کلید نباید plaintext باشد
        r2 = self.client.get(f'/admin/rihan_auth/smsprovider/{row.pk}/change/')
        self.assertEqual(r2.status_code, 200)
        self.assertNotIn('SECRET-KEY-123', r2.content.decode())
        self.assertIn('type="password"', r2.content.decode())

    def test_empty_key_keeps_old(self):
        row = SmsProvider.objects.create(name='کاوه', api_key='OLD-KEY')
        self.client.post(f'/admin/rihan_auth/smsprovider/{row.pk}/change/', {
            'name': 'کاوه',
            'provider_type': 'kavenegar',
            'api_key': '',
            'otp_template': 'rihan-otp',
            'sender': '',
            'is_active': 'on',
            'priority': 1,
        })
        row.refresh_from_db()
        self.assertEqual(row.api_key, 'OLD-KEY')
        self.assertTrue(row.is_active)
