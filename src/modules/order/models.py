import uuid
from django.db import models
from django.conf import settings

class Cart(models.Model):
    '''سبد خرید - منطبق بر D-079 و D-080'''
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    session_key = models.CharField(max_length=100, blank=True, verbose_name="شناسه نشست (برای مهمان)")
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name='carts')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "سبد خرید"
        verbose_name_plural = "سبدهای خرید"
        ordering = ['-created_at']

    def __str__(self):
        return f"سبد {self.id} ({self.items.count()} کالا)"

    @property
    def total_items(self):
        return sum(item.quantity for item in self.items.all())

    @property
    def subtotal(self):
        return sum(item.subtotal for item in self.items.all())


class CartItem(models.Model):
    '''اقلام سبد خرید - بدون هزینه پنهان (D-046)'''
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey('catalog.Product', on_delete=models.CASCADE, related_name='cart_items')
    quantity = models.PositiveIntegerField(default=1, verbose_name="تعداد")
    unit_price_at_add = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="قیمت واحد در لحظه افزودن")
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "کالای سبد"
        verbose_name_plural = "کالاهای سبد"

    def __str__(self):
        return f"{self.product.name} x {self.quantity}"

    @property
    def subtotal(self):
        return self.unit_price_at_add * self.quantity

    def clean(self):
        if self.quantity < 1:
            self.quantity = 1
