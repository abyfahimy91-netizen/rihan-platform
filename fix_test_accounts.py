from pathlib import Path
BASE = Path("/root/rihan-platform")

test_content = """from django.test import TestCase, Client
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
        
        # 1. Step 1: Send OTP through web request (sets session auth_phone)
        c.post(reverse('login'), {'action': 'send_otp', 'phone': phone})
        otp = PhoneOTP.objects.filter(phone=phone, is_used=False).first().otp_code
        
        # 2. Step 2: Verify OTP
        res_verify = c.post(reverse('login'), {'action': 'verify_otp', 'otp_code': otp})
        self.assertEqual(res_verify.status_code, 302)
        
        # 3. Step 3: Set backup password in profile (ADR-006 Section 6)
        res_set = c.post(reverse('user_profile'), {
            'action': 'set_password',
            'new_password': 'MyStrongBackupPass1405',
            'confirm_password': 'MyStrongBackupPass1405'
        })
        self.assertEqual(res_set.status_code, 200)

        # 4. Step 4: Logout
        c.get(reverse('logout'))

        # 5. Step 5: Login with Password Fallback (ADR-006 Section 6)
        res_pass_login = c.post(reverse('login'), {
            'action': 'login_password',
            'phone': phone,
            'password': 'MyStrongBackupPass1405'
        })
        self.assertEqual(res_pass_login.status_code, 302) # Logged in successfully!
"""
(BASE / "tests/test_accounts.py").write_text(test_content, encoding="utf-8")
print("✓ Fixed test_accounts.py")
