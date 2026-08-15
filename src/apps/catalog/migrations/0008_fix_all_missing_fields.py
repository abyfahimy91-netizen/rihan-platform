"""
Fix all missing fields in ProductReview
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0007_fix_productimage'),
    ]

    operations = [
        # اضافه کردن author_email
        migrations.AddField(
            model_name='productreview',
            name='author_email',
            field=models.EmailField(blank=True, max_length=254, verbose_name='ایمیل'),
        ),
        # اضافه کردن title
        migrations.AddField(
            model_name='productreview',
            name='title',
            field=models.CharField(blank=True, max_length=200, verbose_name='عنوان نظر'),
        ),
        # اضافه کردن order_number
        migrations.AddField(
            model_name='productreview',
            name='order_number',
            field=models.CharField(blank=True, max_length=50, verbose_name='شماره سفارش'),
        ),
        # اضافه کردن is_verified_buyer
        migrations.AddField(
            model_name='productreview',
            name='is_verified_buyer',
            field=models.BooleanField(default=False, verbose_name='خریدار تأییدشده'),
        ),
        # اضافه کردن is_approved
        migrations.AddField(
            model_name='productreview',
            name='is_approved',
            field=models.BooleanField(default=False, verbose_name='تأییدشده برای انتشار'),
        ),
        # اضافه کردن admin_response
        migrations.AddField(
            model_name='productreview',
            name='admin_response',
            field=models.TextField(blank=True, verbose_name='پاسخ ادمین'),
        ),
        # اضافه کردن updated_at
        migrations.AddField(
            model_name='productreview',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
    ]
