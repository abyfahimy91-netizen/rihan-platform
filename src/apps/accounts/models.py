from django.db import models
from django.utils import timezone
from datetime import timedelta
import random

class PhoneOTP(models.Model):
    phone = models.CharField(max_length=15, verbose_name="شماره موبایل")
    otp_code = models.CharField(max_length=6, verbose_name="کد یکبارمصرف (۶ رقم)")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="زمان ایجاد")
    expires_at = models.DateTimeField(verbose_name="زمان انقضا")
    is_used = models.BooleanField(default=False, verbose_name="استفاده‌شده")
    attempts = models.PositiveIntegerField(default=0, verbose_name="تعداد تلاش‌ها")

    class Meta:
        verbose_name = "کد یکبارمصرف (OTP)"
        verbose_name_plural = "کدهای یکبارمصرف"
        ordering = ['-created_at']

    @classmethod
    def generate_otp(cls, phone):
        cls.objects.filter(phone=phone, is_used=False).update(is_used=True)
        # تولید کد ۶ رقمی استاندارد ADR-006
        code = str(random.randint(100000, 999999))
        expiry = timezone.now() + timedelta(minutes=2)
        return cls.objects.create(phone=phone, otp_code=code, expires_at=expiry)

    def is_valid(self):
        return (not self.is_used) and (timezone.now() <= self.expires_at) and (self.attempts < 3)
