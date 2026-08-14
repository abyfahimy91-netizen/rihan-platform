from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from apps.accounts.services import SMSAuthService
from apps.accounts.models import PhoneOTP

User = get_user_model()

class HybridAccountsTestCase(TestCase):
    def test_6_digit_otp_flow(self):
        phone = "09121112233"
        code = SMSAuthService.send_otp(phone)
        self.assertEqual(len(code), 6) # ADR-006 6-digit requirement
        self.assertTrue(SMSAuthService.verify_otp(phone, code))

    def test_login_and_password_fallback(self):
        c = Client()
        phone = "09124445566"
        
        # 1. Login with OTP first
        SMSAuthService.send_otp(phone)
        otp = PhoneOTP.objects.filter(phone=phone, is_used=False).first().otp_code
        c.post(reverse('login'), {'action': 'verify_otp', 'otp_code': otp})
        
        # 2. Set backup password in profile (ADR-006 Section 6)
        res_set = c.post(reverse('user_profile'), {
            'action': 'set_password',
            'new_password': 'MyStrongBackupPass1405',
            'confirm_password': 'MyStrongBackupPass1405'
        })
        self.assertEqual(res_set.status_code, 200)

        # 3. Logout
        c.get(reverse('logout'))

        # 4. Login with Password Fallback
        res_pass_login = c.post(reverse('login'), {
            'action': 'login_password',
            'phone': phone,
            'password': 'MyStrongBackupPass1405'
        })
        self.assertEqual(res_pass_login.status_code, 302) # Logged in successfully!
