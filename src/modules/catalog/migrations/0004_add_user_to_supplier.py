# Generated for M4 Supplier Panel - D-085

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('catalog', '0003_alter_inventorytransaction_reference_id'),
    ]

    operations = [
        migrations.AddField(
            model_name='supplier',
            name='user',
            field=models.OneToOneField(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='supplier_profile',
                to=settings.AUTH_USER_MODEL,
                verbose_name='کاربر سیستمی مرتبط',
            ),
        ),
    ]
