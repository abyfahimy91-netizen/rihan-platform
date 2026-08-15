# Generated manually - تطبیق models با database موجود
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('catalog', '0007_fix_productimage'),
    ]

    operations = [
        # تغییر admin_response به admin_reply
        migrations.RenameField(
            model_name='productreview',
            old_name='admin_response',
            new_name='admin_reply',
        ),
        # اضافه کردن replied_at
        migrations.AddField(
            model_name='productreview',
            name='replied_at',
            field=models.DateTimeField(blank=True, null=True, verbose_name='تاریخ پاسخ'),
        ),
        # تغییر author_email به nullable
        migrations.AlterField(
            model_name='productreview',
            name='author_email',
            field=models.EmailField(blank=True, max_length=254, null=True, verbose_name='ایمیل'),
        ),
        # تغییر title به nullable
        migrations.AlterField(
            model_name='productreview',
            name='title',
            field=models.CharField(blank=True, max_length=200, null=True, verbose_name='عنوان نظر'),
        ),
        # حذف updated_at
        migrations.RemoveField(
            model_name='productreview',
            name='updated_at',
        ),
    ]
