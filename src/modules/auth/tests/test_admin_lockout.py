"""تست قفل ورود ادمین و اعتبارسنج آپلود — فاز ۶"""
from django.core.exceptions import ValidationError
from django.test import TestCase, Client

from src.core.upload_validation import validate_upload_image
from src.modules.auth.models import AdminLoginAttempt

HOST = 'rihan360.ir'


class FakeFile:
    """جایگزین سبک فایل آپلودی برای تست ولیدیتور."""
    def __init__(self, name, size=1000, content_type='image/png'):
        self.name = name
        self.size = size
        self.content_type = content_type


class UploadValidatorTest(TestCase):
    def test_valid_image_passes(self):
        validate_upload_image(FakeFile('receipt.png'))

    def test_bad_extension_rejected(self):
        with self.assertRaises(ValidationError):
            validate_upload_image(FakeFile('malware.exe'))
        with self.assertRaises(ValidationError):
            validate_upload_image(FakeFile('shell.php.png'.replace('.php', ''), content_type='application/php'))
        with self.assertRaises(ValidationError):
            validate_upload_image(FakeFile('doc.pdf', content_type='application/pdf'))

    def test_oversize_rejected(self):
        with self.assertRaises(ValidationError):
            validate_upload_image(FakeFile('big.jpg', size=6 * 1024 * 1024))


class AdminLockoutTest(TestCase):
    def _fail(self, n, username='admin', ip='203.0.113.10'):
        for _ in range(n):
            AdminLoginAttempt.objects.create(username=username, ip=ip, succeeded=False)

    def test_fresh_login_not_blocked(self):
        c = Client(HTTP_HOST=HOST)
        r = c.post('/admin/login/', {'username': 'admin', 'password': 'wrong-pass'})
        self.assertNotEqual(r.status_code, 403)

    def test_locked_after_five_failures(self):
        self._fail(5)
        c = Client(HTTP_HOST=HOST)
        r = c.post('/admin/login/', {'username': 'admin', 'password': 'right-or-wrong'})
        self.assertEqual(r.status_code, 403)

    def test_lock_by_ip_even_other_username(self):
        self._fail(5, username='attacker1')
        c = Client(HTTP_HOST=HOST)
        r = c.post('/admin/login/', {'username': 'admin', 'password': 'x'}, REMOTE_ADDR='203.0.113.10')
        self.assertEqual(r.status_code, 403)
