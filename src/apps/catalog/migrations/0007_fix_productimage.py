"""
Fix ProductImage - اضافه کردن فیلد image و created_at
"""
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0006_add_block_fields'),
    ]

    operations = [
        # اضافه کردن فیلد image (ImageField)
        migrations.AddField(
            model_name='productimage',
            name='image',
            field=models.ImageField(blank=True, null=True, upload_to='products/', verbose_name='عکس'),
        ),
        # اضافه کردن فیلد created_at
        migrations.AddField(
            model_name='productimage',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
    ]
