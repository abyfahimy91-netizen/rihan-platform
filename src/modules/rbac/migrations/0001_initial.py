"""
Initial migration for rbac module
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
        # جدول Role
        migrations.CreateModel(
            name='Role',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False, verbose_name='شناسه نقش')),
                ('name', models.CharField(help_text='مثال: مدیر، عضو خانواده، تأمین‌کننده', max_length=50, unique=True, verbose_name='نام نقش')),
                ('code', models.CharField(help_text='مثال: admin, family_admin, customer', max_length=50, unique=True, verbose_name='کد فنی')),
                ('description', models.TextField(blank=True, default='', verbose_name='توضیحات')),
                ('permissions', models.JSONField(blank=True, default=list, help_text='مثال: ["product.create", "order.view"]', verbose_name='لیست مجوزها')),
                ('is_system', models.BooleanField(default=False, help_text='نقش‌های سیستمی قابل حذف نیستند', verbose_name='نقش سیستمی')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')),
                ('updated_at', models.DateTimeField(auto_now=True, verbose_name='آخرین به‌روزرسانی')),
            ],
            options={
                'verbose_name': 'نقش',
                'verbose_name_plural': 'نقش‌ها',
                'ordering': ['name'],
            },
        ),
        # جدول UserRole
        migrations.CreateModel(
            name='UserRole',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False, verbose_name='شناسه')),
                ('granted_at', models.DateTimeField(default=django.utils.timezone.now, verbose_name='تاریخ اعطا')),
                ('is_primary', models.BooleanField(default=False, help_text='در MVP هر کاربر یک نقش اصلی دارد', verbose_name='نقش اصلی')),
                ('created_at', models.DateTimeField(auto_now_add=True, verbose_name='تاریخ ایجاد')),
                ('user', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='roles', to='auth.user', verbose_name='کاربر')),
                ('role', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='user_roles', to='rbac.role', verbose_name='نقش')),
                ('granted_by', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='granted_roles', to='auth.user', verbose_name='اعطاکننده')),
            ],
            options={
                'verbose_name': 'نقش کاربر',
                'verbose_name_plural': 'نقش‌های کاربران',
                'ordering': ['-is_primary', '-granted_at'],
            },
        ),
        # Constraints
        migrations.AddConstraint(
            model_name='userrole',
            constraint=models.UniqueConstraint(fields=('user', 'role'), name='unique_user_role'),
        ),
        migrations.AddConstraint(
            model_name='userrole',
            constraint=models.UniqueConstraint(condition=models.Q(is_primary=True), fields=('user',), name='unique_primary_role_per_user'),
        ),
    ]
