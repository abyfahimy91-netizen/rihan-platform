import uuid
from django.db import models
from django.conf import settings
from django.utils import timezone

class Category(models.Model):
    '''دسته‌بندی محصولات - ADR-002'''
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=150, verbose_name="نام دسته‌بندی")
    slug = models.SlugField(max_length=180, unique=True, allow_unicode=True, verbose_name="اسلاگ")
    description = models.TextField(blank=True, verbose_name="توضیحات")
    icon = models.CharField(max_length=50, blank=True, verbose_name="آیکون")
    parent = models.ForeignKey('self', on_delete=models.CASCADE, null=True, blank=True, related_name='children', verbose_name="دسته والد")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    sort_order = models.PositiveIntegerField(default=0, verbose_name="ترتیب نمایش")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "دسته‌بندی"
        verbose_name_plural = "دسته‌بندی‌ها"
        ordering = ['sort_order', 'name']

    def __str__(self):
        return self.name


class Supplier(models.Model):
    '''مدل تأمین‌کننده - M4 (ADR-002)'''
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='supplier_profile')
    title = models.CharField(max_length=150, verbose_name="نام کارگاه / تأمین‌کننده")
    contact_name = models.CharField(max_length=100, verbose_name="نام مسئول")
    phone = models.CharField(max_length=20, verbose_name="شماره تماس")
    city = models.CharField(max_length=100, verbose_name="شهر / منطقه")
    address = models.TextField(blank=True, verbose_name="نشانی کارگاه / مزرعه")
    is_active = models.BooleanField(default=True, verbose_name="فعال")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "تأمین‌کننده"
        verbose_name_plural = "تأمین‌کنندگان"
        ordering = ['title']

    def __str__(self):
        return f"{self.title} ({self.city})"
