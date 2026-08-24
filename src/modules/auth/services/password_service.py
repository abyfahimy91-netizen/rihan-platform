"""
Password Service - ورود دومرحله‌ای با رمز عبور
منطبق بر D-095: احراز هویت دوکاناله (OTP + Password)

قوانین امنیتی:
- نام کاربری همه نقش‌ها = شماره موبایل
- حداقل ۸ کاراکتر، حداقل یک حرف و یک رقم
- حداکثر ۵ تلاش ناموفق در ۱۵ دقیقه → قفل ۱۵ دقیقه‌ای
- پیام خطای یکسان برای جلوگیری از Account Enumeration
- لاگ کامل در LoginAttempt
"""
from __future__ import annotations

import logging
import re
from typing import Optional, Tuple

from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import check_password

from ..models import LoginAttempt
from .rate_limiter import RateLimiter

logger = logging.getLogger(__name__)

User = get_user_model()


class PasswordService:
    """سرویس مرکزی رمز عبور — ورود، تنظیم، تغییر و بازنشانی."""

    MIN_LENGTH = 8

    @classmethod
    def validate_strength(cls, password: str) -> Tuple[bool, str]:
        """اعتبارسنجی قدرت رمز عبور."""
        if not password or len(password) < cls.MIN_LENGTH:
            return False, f"رمز عبور باید حداقل {cls.MIN_LENGTH} کاراکتر باشد."
        if not re.search(r'[A-Za-zآ-ی]', password):
            return False, "رمز عبور باید حداقل یک حرف داشته باشد."
        if not re.search(r'[0-9]', password):
            return False, "رمز عبور باید حداقل یک رقم داشته باشد."
        if len(password) > 128:
            return False, "رمز عبور بیش از حد طولانی است."
        return True, ""

    # ────────────────────────── ورود ──────────────────────────

    @classmethod
    def attempt_login(cls, phone: str, password: str, ip: str = None,
                      user_agent: str = '') -> Tuple[bool, str, Optional[User]]:
        """
        تلاش ورود با شماره موبایل + رمز عبور.

        Returns:
            (success, message, user)
        """
        from .otp_service import OtpService
        is_valid, phone_or_error = OtpService.validate_phone(phone or '')
        if not is_valid:
            return False, phone_or_error, None
        phone = phone_or_error

        # محدودیت تلاش + قفل موقت
        allowed, message = RateLimiter.check_password_attempt(phone)
        if not allowed:
            LoginAttempt.objects.create(phone=phone, action='lockout',
                                        ip_address=ip, success=False)
            return False, message, None

        user = User.objects.filter(username=phone).first()
        generic_error = "شماره موبایل یا رمز عبور نادرست است."

        if user is None or not user.has_usable_password():
            RateLimiter.record_password_attempt(phone)
            LoginAttempt.objects.create(phone=phone, action='password_failed',
                                        ip_address=ip, user_agent=user_agent,
                                        success=False)
            return False, generic_error, None

        if user.check_password(password):
            RateLimiter.clear_all(phone)
            LoginAttempt.objects.create(phone=phone, action='password_login',
                                        ip_address=ip, user_agent=user_agent,
                                        success=True, user=user)
            logger.info(f"Password login OK for {phone[:4]}***{phone[-4:]}")
            return True, "ورود موفق.", user

        # رمز نادرست
        left = RateLimiter.record_password_attempt(phone)
        LoginAttempt.objects.create(phone=phone, action='password_failed',
                                    ip_address=ip, user_agent=user_agent,
                                    success=False, user=user)
        if left <= 0:
            RateLimiter.set_lockout(phone, RateLimiter.PASSWORD_LOCKOUT_MINUTES)
            return False, ("به دلیل تلاش‌های متعدد ناموفق، ورود با رمز عبور برای این شماره "
                           "موقتاً قفل شد. می‌توانید با کد پیامکی وارد شوید یا ۱۵ دقیقه صبر کنید."), None
        return False, f"{generic_error} ({left} تلاش باقی مانده)", None

    # ─────────────────── تنظیم / تغییر / بازنشانی ───────────────────

    @classmethod
    def set_password(cls, user: User, password: str, confirm: str = None) -> Tuple[bool, str]:
        """تنظیم یا تغییر رمز عبور کاربر (همراه اعتبارسنجی قدرت)."""
        if confirm is not None and password != confirm:
            return False, "رمز عبور و تکرار آن یکسان نیستند."
        ok, message = cls.validate_strength(password)
        if not ok:
            return False, message
        user.set_password(password)
        user.save(update_fields=['password'])
        LoginAttempt.objects.create(phone=user.username, action='password_reset',
                                    success=True, user=user)
        logger.info(f"Password set for {user.username[:4]}***{user.username[-4:]}")
        return True, "رمز عبور با موفقیت ذخیره شد ✅"

    @classmethod
    def has_password(cls, user: User) -> bool:
        """آیا کاربر رمز عبور قابل استفاده دارد؟"""
        return bool(user and user.has_usable_password())

    @classmethod
    def change_password(cls, user: User, current: str, new: str, confirm: str) -> Tuple[bool, str]:
        """تغییر رمز با تأیید رمز فعلی."""
        if not user.check_password(current):
            return False, "رمز عبور فعلی نادرست است."
        return cls.set_password(user, new, confirm)
