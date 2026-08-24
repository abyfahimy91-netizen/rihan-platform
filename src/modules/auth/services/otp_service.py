"""
OTP Service برای ماژول احراز هویت
منطبق بر ADR-006 بخش ۲: جریان احراز هویت اصلی

ویژگی‌ها:
- تولید OTP ۶ رقمی
- hash با bcrypt
- طول عمر ۲ دقیقه
- ۳ تلاش مجاز
- قفل موقت ۳۰ دقیقه
"""
from __future__ import annotations

import logging
import random
import string
from typing import Optional, Tuple

from django.contrib.auth import get_user_model
from django.utils import timezone
from datetime import timedelta

try:
    from django.contrib.auth.hashers import make_password, check_password
except ImportError:
    from django.contrib.auth.hashers import make_password, check_password

from ..models import PhoneOTP, LoginAttempt
from .rate_limiter import RateLimiter

logger = logging.getLogger(__name__)

User = get_user_model()


class OtpService:
    """
    سرویس مرکزی برای مدیریت OTP.
    
    منطبق بر ADR-006 بخش ۲:
    - OTP ۶ رقمی
    - hash bcrypt
    - طول عمر ۲ دقیقه
    - ۳ تلاش مجاز
    """
    
    OTP_LENGTH = 6
    OTP_TTL_MINUTES = 5  # پیش‌فرض؛ مقدار واقعی از AuthSettings ادمین خوانده می‌شود (D-103)
    MAX_ATTEMPTS = 3
    LOCKOUT_MINUTES = 30

    @classmethod
    def _settings(cls):
        """تنظیمات ورود از پنل ادمین (D-103) — در صورت خطا None"""
        try:
            from ..models import AuthSettings
            return AuthSettings.load()
        except Exception:
            return None
    
    @classmethod
    def generate_otp(cls) -> str:
        """تولید OTP ۶ رقمی تصادفی"""
        return ''.join(random.choices(string.digits, k=cls.OTP_LENGTH))
    
    @classmethod
    def validate_phone(cls, phone: str) -> Tuple[bool, str]:
        """
        اعتبارسنجی شماره موبایل ایرانی.
        
        Args:
            phone: شماره موبایل
            
        Returns:
            (is_valid, error_message)
        """
        if not phone:
            return False, "شماره موبایل الزامی است."
        
        # نرمال‌سازی: حذف فاصله و خط تیره
        phone = phone.replace(' ', '').replace('-', '')
        
        # تبدیل ۰۰۹۸ و +۹۸ به ۰
        if phone.startswith('+98'):
            phone = '0' + phone[3:]
        elif phone.startswith('0098'):
            phone = '0' + phone[4:]
        elif phone.startswith('98') and len(phone) == 12:
            phone = '0' + phone[2:]
        
        # بررسی فرمت ایرانی: ۰۹xxxxxxxxx (۱۱ رقم)
        if not phone.startswith('09') or len(phone) != 11:
            return False, "شماره موبایل نامعتبر است. لطفاً شماره ۱۱ رقمی وارد کنید."
        
        # بررسی ارقام
        if not phone.isdigit():
            return False, "شماره موبایل باید فقط شامل ارقام باشد."
        
        return True, phone
    
    @classmethod
    def request_otp(cls, phone: str, ip: str = None) -> Tuple[bool, str, Optional[str]]:
        """
        درخواست OTP جدید.
        
        Args:
            phone: شماره موبایل
            ip: آدرس IP (برای Rate Limiting)
            
        Returns:
            (success, message, otp_code) - otp_code فقط برای Mock
        """
        # اعتبارسنجی شماره
        is_valid, phone_or_error = cls.validate_phone(phone)
        if not is_valid:
            return False, phone_or_error, None
        
        phone = phone_or_error
        
        # بررسی Rate Limit
        allowed, message = RateLimiter.check_otp_request(phone, ip)
        if not allowed:
            return False, message, None
        
        # بررسی قفل موقت
        is_locked, minutes_left = RateLimiter.check_lockout(phone)
        if is_locked:
            return False, f"حساب شما موقتاً قفل شده است. لطفاً {minutes_left} دقیقه صبر کنید.", None
        
        # بررسی OTP موجود (اگر هنوز منقضی نشده، از آن استفاده کن)
        existing_otp = PhoneOTP.objects.filter(
            phone=phone,
            expires_at__gt=timezone.now(),
            verified_at__isnull=True,
            locked_until__isnull=True
        ).first()
        
        if existing_otp:
            # OTP موجود است، نیازی به ارسال جدید نیست
            # اما برای Mock، کد را برمی‌گردانیم
            logger.info(f"OTP already exists for {phone[:4]}***{phone[-4:]}")
            return True, "کد قبلی هنوز معتبر است.", None
        
        # تولید OTP جدید
        otp_code = cls.generate_otp()
        otp_hash = make_password(otp_code)
        
        # غیرفعال کردن OTPهای قبلی
        PhoneOTP.objects.filter(
            phone=phone,
            verified_at__isnull=True
        ).update(expires_at=timezone.now())
        
        # ایجاد OTP جدید (TTL و تلاش‌ها از تنظیمات ادمین — D-103)
        _settings = cls._settings()
        ttl_minutes = _settings.otp_ttl_minutes if _settings else cls.OTP_TTL_MINUTES
        max_attempts = _settings.otp_max_attempts if _settings else cls.MAX_ATTEMPTS
        otp = PhoneOTP.objects.create(
            phone=phone,
            otp_hash=otp_hash,
            expires_at=timezone.now() + timedelta(minutes=ttl_minutes),
            max_attempts=max_attempts
        )
        
        # ثبت در Rate Limiter
        RateLimiter.record_otp_request(phone, ip)
        
        # ثبت در LoginAttempt
        LoginAttempt.objects.create(
            phone=phone,
            action='otp_request',
            ip_address=ip,
            success=True
        )
        
        # D-103: ارسال از طریق سرویس‌دهنده فعال (با جایگزینی خودکار و Mock اضطراری)
        from .sms_service import SmsService
        sent_via_sms, show_code, provider_name = SmsService.send_otp_or_mock(phone, otp_code)
        otp.sent_via = provider_name or ('screen' if show_code else 'failed')
        otp.save(update_fields=['sent_via'])
        
        logger.info(f"OTP requested for {phone[:4]}***{phone[-4:]} via {provider_name or 'N/A'}")
        if sent_via_sms:
            return True, "کد تأیید پیامک شد.", None
        if show_code:
            return True, "ارسال پیامک موقتاً امکان‌پذیر نیست؛ کد به‌صورت آزمایشی نمایش داده می‌شود.", otp_code
        # هیچ سرویسی در دسترس نیست و ادمین نمایش کد را هم خاموش کرده است
        otp.delete()  # کد بلااستفاده باقی نماند
        return False, "ارسال پیامک موقتاً امکان‌پذیر نیست. لطفاً چند دقیقه بعد دوباره تلاش کنید یا با پشتیبانی تماس بگیرید.", None
    
    @classmethod
    def verify_otp(cls, phone: str, otp_code: str, ip: str = None) -> Tuple[bool, str, Optional[User]]:
        """
        تأیید OTP.
        
        Args:
            phone: شماره موبایل
            otp_code: کد ۶ رقمی وارد شده
            ip: آدرس IP
            
        Returns:
            (success, message, user) - user فقط در صورت موفقیت
        """
        # اعتبارسنجی شماره
        is_valid, phone_or_error = cls.validate_phone(phone)
        if not is_valid:
            return False, phone_or_error, None
        
        phone = phone_or_error
        
        # بررسی Rate Limit
        allowed, message = RateLimiter.check_otp_verify(phone)
        if not allowed:
            return False, message, None
        
        # بررسی قفل موقت
        is_locked, minutes_left = RateLimiter.check_lockout(phone)
        if is_locked:
            return False, f"حساب شما موقتاً قفل شده است. لطفاً {minutes_left} دقیقه صبر کنید.", None
        
        # پیدا کردن OTP معتبر
        otp = PhoneOTP.objects.filter(
            phone=phone,
            verified_at__isnull=True,
            expires_at__gt=timezone.now(),
            locked_until__isnull=True
        ).order_by('-created_at').first()
        
        if otp is None:
            # پیام یکسان برای جلوگیری از Account Enumeration
            return False, "کد ارسال‌شده نادرست است. لطفاً دوباره تلاش کنید.", None
        
        # بررسی OTP
        if check_password(otp_code, otp.otp_hash):
            # موفق - علامت‌گذاری به‌عنوان تأیید شده
            otp.mark_verified()
            
            # پاکسازی Rate Limit
            RateLimiter.clear_all(phone)
            
            # پیدا کردن یا ایجاد کاربر
            user, created = User.objects.get_or_create(
                username=phone,
                defaults={
                    'first_name': '',
                    'last_name': '',
                    'is_active': True,
                }
            )
            
            if created:
                user.set_unusable_password()
                user.save()
                logger.info(f"New user created: {phone[:4]}***{phone[-4:]}")
            
            # ثبت در LoginAttempt
            LoginAttempt.objects.create(
                phone=phone,
                action='otp_verify_success',
                ip_address=ip,
                success=True,
                user=user
            )
            
            logger.info(f"OTP verified for {phone[:4]}***{phone[-4:]}")
            
            return True, "ورود موفق.", user
        else:
            # ناموفق - افزایش تعداد تلاش‌ها
            otp.increment_attempts()
            
            # ثبت در LoginAttempt
            LoginAttempt.objects.create(
                phone=phone,
                action='otp_verify_failed',
                ip_address=ip,
                success=False
            )
            
            # ثبت در Rate Limiter
            RateLimiter.record_otp_verify(phone)
            
            # اگر ۳ بار ناموفق بود، قفل موقت
            if otp.attempts >= otp.max_attempts:
                RateLimiter.set_lockout(phone, cls.LOCKOUT_MINUTES)
                LoginAttempt.objects.create(
                    phone=phone,
                    action='lockout',
                    ip_address=ip,
                    success=False
                )
                return False, "به دلیل تلاش‌های متعدد، حساب شما موقتاً قفل شده است. لطفاً ۳۰ دقیقه صبر کنید.", None
            
            attempts_left = otp.attempts_left
            return False, f"کد نادرست است. {attempts_left} تلاش باقی مانده است.", None
    
    @classmethod
    def get_or_create_user(cls, phone: str) -> User:
        """دریافت یا ایجاد کاربر بر اساس شماره موبایل"""
        is_valid, phone_or_error = cls.validate_phone(phone)
        if not is_valid:
            raise ValueError(phone_or_error)
        
        phone = phone_or_error
        user, created = User.objects.get_or_create(
            username=phone,
            defaults={'is_active': True}
        )
        
        if created:
            user.set_unusable_password()
            user.save()
        
        return user
