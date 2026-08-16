import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone
from datetime import timedelta


class Profile(models.Model):
    '''پروفایل کاربر - اطلاعات تکمیلی'''
    class Gender(models.TextChoices):
        MALE = 'MALE', 'مرد'
        FEMALE = 'FEMALE', 'زن'
        OTHER = 'OTHER', 'سایر'
        PREFER_NOT_TO_SAY = 'PREFER_NOT_TO_SAY', 'ترجیح می‌دهم نگویم'
    
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='profile')
    
    # اطلاعات شخصی
    phone_number = models.CharField(max_length=20, blank=True, verbose_name="شماره تلفن همراه")
    date_of_birth = models.DateField(null=True, blank=True, verbose_name="تاریخ تولد")
    gender = models.CharField(max_length=20, choices=Gender.choices, blank=True, verbose_name="جنسیت")
    
    # تنظیمات
    email_verified = models.BooleanField(default=False, verbose_name="ایمیل تایید شده")
    phone_verified = models.BooleanField(default=False, verbose_name="تلفن تایید شده")
    newsletter_subscription = models.BooleanField(default=True, verbose_name="اشتراک خبرنامه")
    
    # متادیتا
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        verbose_name = "پروفایل"
        verbose_name_plural = "پروفایل‌ها"
    
    def __str__(self):
        return f"پروفایل {self.user.username}"


class EmailVerification(models.Model):
    '''توکن تایید ایمیل'''
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='email_verifications')
    token = models.CharField(max_length=100, unique=True)
    email = models.EmailField(verbose_name="ایمیل برای تایید")
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = "تایید ایمیل"
        verbose_name_plural = "تاییدهای ایمیل"
    
    def __str__(self):
        return f"تایید ایمیل {self.email}"
    
    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(hours=24)
        super().save(*args, **kwargs)
    
    @property
    def is_expired(self):
        return timezone.now() > self.expires_at


class PasswordResetToken(models.Model):
    '''توکن بازیابی رمز عبور'''
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='password_resets')
    token = models.CharField(max_length=100, unique=True)
    email = models.EmailField(verbose_name="ایمیل برای بازیابی")
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    is_used = models.BooleanField(default=False)
    
    class Meta:
        verbose_name = "توکن بازیابی رمز"
        verbose_name_plural = "توکن‌های بازیابی رمز"
    
    def __str__(self):
        return f"بازیابی رمز {self.email}"
    
    def save(self, *args, **kwargs):
        if not self.expires_at:
            self.expires_at = timezone.now() + timedelta(hours=1)
        super().save(*args, **kwargs)
    
    @property
    def is_expired(self):
        return timezone.now() > self.expires_at
