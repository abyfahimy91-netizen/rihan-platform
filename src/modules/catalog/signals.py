"""سیگنال‌های کاتالوگ — اطلاع‌رسانی IndexNow هنگام تغییر محصولات (D-118 GEO)."""
from django.db.models.signals import post_save
from django.dispatch import receiver

from .indexnow import submit_product_async
from .models import Product


@receiver(post_save, sender=Product)
def product_saved_indexnow(sender, instance, **kwargs):
    """ایجاد/ویرایش محصول فعال → IndexNow فوراً باخبر شود (best-effort، پس‌زمینه)."""
    if kwargs.get('update_fields'):  # آپدیت‌های جزئی مثل share_count → بی‌خیال
        return
    submit_product_async(instance)
