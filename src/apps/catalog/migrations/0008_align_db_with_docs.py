"""
Migration برای sync کردن state Django با تغییرات دستی database
(این migration فقط state را به‌روز می‌کند، تغییرات real در مرحله ۱ با SQL اعمال شد)
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0007_fix_productimage'),
    ]

    operations = [
        # اضافه کردن فیلدهای گمشده (طبق مستندات D-044)
        migrations.AddField(
            model_name='productreview',
            name='author_email',
            field=models.EmailField(blank=True, max_length=254, verbose_name='ایمیل'),
        ),
        migrations.AddField(
            model_name='productreview',
            name='title',
            field=models.CharField(blank=True, max_length=200, verbose_name='عنوان نظر'),
        ),
        migrations.AddField(
            model_name='productreview',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
        # تغییر نام admin_reply به admin_response (مطابق مستندات)
        migrations.RenameField(
            model_name='productreview',
            old_name='admin_reply',
            new_name='admin_response',
        ),
        # حذف replied_at (در مستندات وجود ندارد)
        migrations.RemoveField(
            model_name='productreview',
            name='replied_at',
        ),
    ]
