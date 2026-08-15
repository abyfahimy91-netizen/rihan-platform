# Generated manually for 12 block types
from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0005_leadcapture'),
    ]

    operations = [
        # حذف block_type محدود قبلی
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
        
        # تغییر content به blank=True
        migrations.AlterField(
            model_name='contentblock',
            name='content',
            field=models.TextField(blank=True, verbose_name='محتوای متنی (Markdown/HTML)'),
        ),
        
        # اضافه کردن فیلدهای media
        migrations.AddField(
            model_name='contentblock',
            name='image',
            field=models.ImageField(blank=True, upload_to='blocks/', verbose_name='عکس'),
        ),
        migrations.AddField(
            model_name='contentblock',
            name='video_url',
            field=models.URLField(blank=True, verbose_name='لینک ویدیو (YouTube/Aparat)'),
        ),
        migrations.AddField(
            model_name='contentblock',
            name='video_file',
            field=models.FileField(blank=True, upload_to='blocks/videos/', verbose_name='فایل ویدیو'),
        ),
        
        # اضافه کردن فیلدهای link
        migrations.AddField(
            model_name='contentblock',
            name='link_url',
            field=models.URLField(blank=True, verbose_name='لینک'),
        ),
        migrations.AddField(
            model_name='contentblock',
            name='link_text',
            field=models.CharField(blank=True, max_length=100, verbose_name='متن لینک'),
        ),
        migrations.AddField(
            model_name='contentblock',
            name='link_target',
            field=models.CharField(blank=True, choices=[('_blank', 'پنجره جدید'), ('_self', 'همان پنجره')], max_length=20, verbose_name='نحوه باز شدن'),
        ),
        
        # اضافه کردن quote_author
        migrations.AddField(
            model_name='contentblock',
            name='quote_author',
            field=models.CharField(blank=True, max_length=100, verbose_name='نویسنده نقل قول'),
        ),
        
        # اضافه کردن فیلدهای ظاهری
        migrations.AddField(
            model_name='contentblock',
            name='css_class',
            field=models.CharField(blank=True, max_length=100, verbose_name='CSS Class سفارشی'),
        ),
        migrations.AddField(
            model_name='contentblock',
            name='background_color',
            field=models.CharField(blank=True, max_length=20, verbose_name='رنگ پس‌زمینه (hex)'),
        ),
        migrations.AddField(
            model_name='contentblock',
            name='is_full_width',
            field=models.BooleanField(default=False, verbose_name='تمام عرض'),
        ),
        
        # اضافه کردن created_at و updated_at
        migrations.AddField(
            model_name='contentblock',
            name='created_at',
            field=models.DateTimeField(default=django.utils.timezone.now),
        ),
        migrations.AddField(
            model_name='contentblock',
            name='updated_at',
            field=models.DateTimeField(auto_now=True),
        ),
        
        # اضافه کردن get_absolute_url به Product
        migrations.AlterModelOptions(
            name='product',
            options={'ordering': ['-is_featured', '-created_at'], 'verbose_name': 'محصول', 'verbose_name_plural': 'محصولات'},
        ),
    ]
