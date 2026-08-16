"""
Initial migration for auth module
Generated manually for reliability
"""
from django.db import migrations, models
import django.db.models.deletion
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '__first__'),
    ]

    operations = [
        # جدول PhoneOTP
        migrations.CreateModel(
            name='PhoneOTP',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('phone', models.CharField(db_index=True, help_text='فرمت ایرانی: ۰۹xxxxxxxxx', max_length=11, verbose_name='شماره موبایل')),
                ('otp_hash', models.CharField(help_text='hash شده با bcrypt', max_length=128, verbose_name='هش OTP')),
                ('attempts', models.PositiveSmallIntegerField(default=0, verbose_name='تعداد تلاش‌ها')),
                ('max_attempts', models.PositiveSmallIntegerField(default=3, verbose_name='حداکثر تلاش مجاز')),
                ('expires_at', models.DateTimeField(help_text='پیش‌فرض: ۲ دقیقه از زمان ایجاد', verbose_name='زمان انقضا')),
                ('verified_at', models.DateTimeField(blank=True, null=True, verbose_name='زمان تأیید')),
                ('locked_until', models.DateTimeField(blank=True, help_text='پس از ۳ تلاش ناموفق: ۳۰ دقیقه', null=True, verbose_name='قفل موقت تا')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='زمان ایجاد')),
            ],
            options={
                'verbose_name': 'کد یکبارمصرف',
                'verbose_name_plural': 'کدهای یکبارمصرف',
                'ordering': ['-created_at'],
            },
        ),
        # جدول DeviceToken
        migrations.CreateModel(
            name='DeviceToken',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False, verbose_name='شناسه توکن')),
                ('token_hash', models.CharField(help_text='hash شده با bcrypt', max_length=128, unique=True, verbose_name='هش توکن')),
                ('device_fingerprint', models.CharField(blank=True, default='', max_length=255, verbose_name='اثر انگشت دستگاه')),
                ('user_agent', models.TextField(blank=True, default='', verbose_name='User Agent')),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True, verbose_name='آدرس IP')),
                ('last_used_at', models.DateTimeField(blank=True, null=True, verbose_name='آخرین استفاده')),
                ('expires_at', models.DateTimeField(help_text='پیش‌فرض: ۳۰ روز از آخرین استفاده', verbose_name='زمان انقضا')),
                ('is_active', models.BooleanField(default=True, verbose_name='فعال است؟')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='زمان ایجاد')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='device_tokens', to='auth.user', verbose_name='کاربر')),
            ],
            options={
                'verbose_name': 'توکن دستگاه',
                'verbose_name_plural': 'توکن‌های دستگاه',
                'ordering': ['-last_used_at'],
            },
        ),
        # جدول LoginAttempt
        migrations.CreateModel(
            name='LoginAttempt',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('phone', models.CharField(db_index=True, max_length=11, verbose_name='شماره موبایل')),
                ('action', models.CharField(choices=[('otp_request', 'درخواست OTP'), ('otp_verify_success', 'تأیید موفق OTP'), ('otp_verify_failed', 'تأیید ناموفق OTP'), ('device_login', 'ورود با DeviceToken'), ('password_login', 'ورود با رمز پشتیبان'), ('logout', 'خروج'), ('lockout', 'قفل موقت')], max_length=50, verbose_name='نوع عملیات')),
                ('ip_address', models.GenericIPAddressField(blank=True, null=True, verbose_name='آدرس IP')),
                ('user_agent', models.TextField(blank=True, default='', verbose_name='User Agent')),
                ('success', models.BooleanField(default=False, verbose_name='موفق بود؟')),
                ('created_at', models.DateTimeField(auto_now_add=True, db_index=True, verbose_name='زمان')),
                ('user', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='login_attempts', to='auth.user', verbose_name='کاربر')),
            ],
            options={
                'verbose_name': 'تلاش ورود',
                'verbose_name_plural': 'تلاش‌های ورود',
                'ordering': ['-created_at'],
            },
        ),
        # شاخص‌ها
        migrations.AddIndex(
            model_name='phoneotp',
            index=models.Index(fields=['phone', 'created_at'], name='auth_phoneo_phone_c_idx'),
        ),
        migrations.AddIndex(
            model_name='devicetoken',
            index=models.Index(fields=['user', 'is_active'], name='auth_device_user_i_idx'),
        ),
        migrations.AddIndex(
            model_name='loginattempt',
            index=models.Index(fields=['phone', 'created_at'], name='auth_login_phone_c_idx'),
        ),
        migrations.AddIndex(
            model_name='loginattempt',
            index=models.Index(fields=['ip_address', 'created_at'], name='auth_login_ip_c_idx'),
        ),
    ]
