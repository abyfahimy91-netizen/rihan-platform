# Migration اصلاح‌شده - فقط AlterField برای فیلدهای موجود
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0005_leadcapture'),
    ]

    operations = [
        # تغییر block_type choices از 5 به 12 نوع
        migrations.AlterField(
            model_name='contentblock',
            name='block_type',
            field=models.CharField(choices=[('text', 'متن آزاد'), ('heading', 'عنوان'), ('image', 'تک عکس'), ('gallery', 'گالری عکس'), ('video', 'ویدیو'), ('link', 'لینک'), ('quote', 'نقل قول'), ('table', 'جدول'), ('spacer', 'فاصله‌گذار'), ('cta', 'دکمه اقدام'), ('trust_badges', 'Trust Badges'), ('related_products', 'محصولات مرتبط')], max_length=30, verbose_name='نوع بلوک'),
        ),
        # تغییر title به blank=True
        migrations.AlterField(
            model_name='contentblock',
            name='title',
            field=models.CharField(blank=True, max_length=200, verbose_name='عنوان (اختیاری)'),
        ),
        # تغییر subtitle به blank=True
        migrations.AlterField(
            model_name='contentblock',
            name='subtitle',
            field=models.CharField(blank=True, max_length=255, verbose_name='زیرعنوان (اختیاری)'),
        ),
        # تغییر content به blank=True
        migrations.AlterField(
            model_name='contentblock',
            name='content',
            field=models.TextField(blank=True, verbose_name='محتوای متنی (Markdown/HTML)'),
        ),
        # تغییر extra_data به blank=True
        migrations.AlterField(
            model_name='contentblock',
            name='extra_data',
            field=models.JSONField(blank=True, default=dict, verbose_name='داده‌های تکمیلی (JSON)'),
        ),
    ]
