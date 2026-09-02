"""
SALES-14050610 — سرویس کد تخفیف
"""
from decimal import Decimal

from django.core.exceptions import ValidationError

from .models import Coupon, CouponUse

FA_DIGITS = str.maketrans('۰۱۲۳۴۵۶۷۸۹', '0123456789')


def normalize(code):
    return (code or '').strip().upper().translate(FA_DIGITS)


def apply(code, subtotal, phone=''):
    """اعتبارسنجی کد روی subtotal → (coupon, discount) یا raise ValidationError با پیام فارسی"""
    code = normalize(code)
    if not code:
        raise ValidationError('کد تخفیف را وارد کنید.')
    try:
        coupon = Coupon.objects.get(code=code)
    except Coupon.DoesNotExist:
        raise ValidationError('کد تخفیف معتبر نیست.')
    ok, err = coupon.is_valid_window()
    if not ok:
        raise ValidationError(err)
    subtotal = Decimal(str(subtotal))
    if subtotal <= 0:
        raise ValidationError('سبد خرید شما خالی است.')
    if subtotal < coupon.min_cart:
        raise ValidationError(f'این کد برای سبدهای بالای {int(coupon.min_cart):,} تومان است.')
    if coupon.max_uses_per_user and phone and coupon.uses_by_phone(phone) >= coupon.max_uses_per_user:
        raise ValidationError('شما قبلاً از این کد استفاده کرده‌اید.')
    return coupon, coupon.discount_for(subtotal)


def attach_to_order(order, coupon, discount):
    """ثبت تخفیف روی سفارش + رکورد استفاده + شمارنده"""
    from decimal import Decimal
    order.discount_amount = Decimal(str(discount))
    order.coupon = coupon
    order.total_price = max(order.subtotal - order.discount_amount, Decimal('0'))
    order.save(update_fields=['discount_amount', 'total_price'])
    phone = order.guest_phone or (order.user.username if order.user else '')
    CouponUse.objects.create(coupon=coupon, order=order, phone=phone or '', amount=order.discount_amount)
    Coupon.objects.filter(pk=coupon.pk).update(used_count=coupon.used_count + 1)
