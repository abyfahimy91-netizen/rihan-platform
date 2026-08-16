"""
Initial migration for core module - FeatureFlag + AuditLog
Generated manually for reliability
"""
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('auth', '__first__'),
    ]

    operations = [
        # جدول AuditLog
        migrations.CreateModel(
            name='AuditLog',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('action', models.CharField(
                    choices=[
                        ('create', 'ایجاد'),
                        ('update', 'به‌روزرسانی'),
                        ('delete', 'حذف'),
                        ('enabled', 'فعال شد'),
                        ('disabled', 'غیرفعال شد'),
                    ],
                    max_length=50,
                    verbose_name='نوع عملیات'
                )),
                ('entity_type', models.CharField(
                    help_text='مثال: feature_flag, product, order',
                    max_length=50,
                    verbose_name='نوع موجودیت'
                )),
                ('entity_id', models.CharField(
                    max_length=50,
                    verbose_name='شناسه موجودیت'
                )),
                ('changes', models.JSONField(
                    blank=True,
                    default=dict,
                    verbose_name='تغییرات'
                )),
                ('ip_address', models.GenericIPAddressField(
                    blank=True,
                    null=True,
                    verbose_name='آدرس IP'
                )),
                ('created_at', models.DateTimeField(
                    auto_now_add=True,
                    db_index=True,
                    verbose_name='تاریخ'
                )),
                ('user', models.ForeignKey(
                    blank=True,
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='audit_logs',
                    to='auth.user',
                    verbose_name='کاربر'
                )),
            ],
            options={
                'verbose_name': 'لاگ ممیزی',
                'verbose_name_plural': 'لاگ‌های ممیزی',
                'ordering': ['-created_at'],
            },
        ),
        # جدول FeatureFlag
        migrations.CreateModel(
            name='FeatureFlag',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(
                    db_index=True,
                    help_text='مثال: MODULE_CATALOG, FEATURE_REVIEW_RATING',
                    max_length=100,
                    unique=True,
                    verbose_name='کد یکتا'
                )),
                ('name', models.CharField(
                    help_text='مثال: ماژول کاتالوگ محصول',
                    max_length=200,
                    verbose_name='نام نمایشی'
                )),
                ('description', models.TextField(
                    blank=True,
                    default='',
                    verbose_name='توضیحات'
                )),
                ('category', models.CharField(
                    choices=[
                        ('MODULE', 'ماژول کامل (M1 تا M14)'),
                        ('FEATURE', 'ویژگی خاص در یک ماژول'),
                        ('EXPERIMENT', 'آزمایش A/B'),
                        ('SYSTEM', 'سیستمی (فقط ادمین‌های ارشد)'),
                    ],
                    default='FEATURE',
                    max_length=20,
                    verbose_name='دسته‌بندی'
                )),
                ('is_enabled', models.BooleanField(
                    db_index=True,
                    default=False,
                    verbose_name='فعال است؟'
                )),
                ('is_system', models.BooleanField(
                    default=False,
                    help_text='اگر true باشد، حذف از ادمین غیرممکن است',
                    verbose_name='سیستمی (حذف ممنوع)'
                )),
                ('rollout_percentage', models.PositiveSmallIntegerField(
                    default=100,
                    help_text='0 تا 100 - برای انتشار تدریجی',
                    verbose_name='درصد rollout'
                )),
                ('metadata', models.JSONField(
                    blank=True,
                    default=dict,
                    verbose_name='داده‌های اضافی'
                )),
                ('enabled_at', models.DateTimeField(
                    blank=True,
                    null=True,
                    verbose_name='زمان فعال‌سازی'
                )),
                ('disabled_at', models.DateTimeField(
                    blank=True,
                    null=True,
                    verbose_name='زمان غیرفعال‌سازی'
                )),
                ('created_at', models.DateTimeField(
                    auto_now_add=True,
                    verbose_name='تاریخ ایجاد'
                )),
                ('updated_at', models.DateTimeField(
                    auto_now=True,
                    verbose_name='آخرین به‌روزرسانی'
                )),
            ],
            options={
                'verbose_name': 'پرچم قابلیت',
                'verbose_name_plural': 'پرچم‌های قابلیت',
                'ordering': ['category', 'code'],
            },
        ),
        # شاخص‌ها
        migrations.AddIndex(
            model_name='auditlog',
            index=models.Index(
                fields=['entity_type', 'entity_id'],
                name='core_auditl_entity_idx'
            ),
        ),
        migrations.AddIndex(
            model_name='featureflag',
            index=models.Index(
                fields=['is_enabled', 'category'],
                name='core_featur_is_enab_idx'
            ),
        ),
    ]
