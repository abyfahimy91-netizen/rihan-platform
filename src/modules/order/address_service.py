"""
سرویس آدرس‌های کاربر (D-102) — اعتبارسنجی و چرخه حیات
از مدل موجود order.Address استفاده می‌کند (schema از ابتدا آماده بود ولی UI نداشت).

قانون: پیام‌های خطا فارسی و محترمانه، در لایه سرویس نه ویو (D-096).
"""
import re

from django.db import transaction

from .models import Address


PHONE_RE = re.compile(r'^09\d{9}$')


def validate_address_data(data: dict) -> tuple[dict, list]:
    """اعتبارسنجی داده‌های آدرس — خروجی: (داده تمیز, لیست خطاها)"""
    clean = {
        'title': (data.get('title') or '').strip()[:50],
        'full_name': (data.get('full_name') or data.get('name') or '').strip(),
        'phone': (data.get('phone') or '').strip(),
        'detailed_address': (data.get('address') or data.get('detailed_address') or '').strip(),
        'postal_code': (data.get('postal_code') or '').strip(),
    }
    errors = []
    if len(clean['full_name']) < 3:
        errors.append('لطفاً نام و نام خانوادگی گیرنده را کامل وارد کنید.')
    if not PHONE_RE.match(clean['phone']):
        errors.append('شماره موبایل معتبر وارد کنید (مثل 09123456789).')
    if len(clean['detailed_address']) < 10:
        errors.append('آدرس را کامل‌تر بنویسید تا بتوانیم ارسال کنیم.')
    # D-111: کد پستی ۱۰ رقمی الزامی است (الزام اداره پست برای ثبت مرسوله)
    if not re.match(r'^\d{10}$', clean['postal_code']):
        errors.append('کد پستی ۱۰ رقمی الزامی است — اداره پست بدون آن مرسوله را ثبت نمی‌کند.')
    return clean, errors


@transaction.atomic
def create_for_user(user, data: dict, make_default: bool = None) -> Address:
    """ساخت آدرس برای کاربر؛ اولین آدرس همیشه پیش‌فرض می‌شود."""
    clean, errors = validate_address_data(data)
    if errors:
        raise ValueError(' | '.join(errors))

    if make_default is None:
        make_default = not user.addresses.exists()

    return Address.objects.create(
        user=user,
        title=clean['title'],
        full_name=clean['full_name'],
        phone=clean['phone'],
        detailed_address=clean['detailed_address'],
        postal_code=clean['postal_code'],
        is_default=make_default,
    )


def get_for_user(user, address_id) -> Address | None:
    """آدرس متعلق به کاربر — برای جلوگیری از دسترسی به آدرس دیگران"""
    if not address_id:
        return None
    try:
        return user.addresses.get(pk=str(address_id))
    except (Address.DoesNotExist, ValueError, TypeError):
        return None


def set_default(user, address_id) -> bool:
    addr = get_for_user(user, address_id)
    if not addr:
        return False
    addr.is_default = True
    addr.save()
    return True


def delete_address(user, address_id) -> bool:
    addr = get_for_user(user, address_id)
    if not addr:
        return False
    was_default = addr.is_default
    addr.delete()
    # اگر پیش‌فرض حذف شد، جدیدترین آدرس باقی‌مانده پیش‌فرض شود
    if was_default:
        next_addr = user.addresses.first()
        if next_addr and not next_addr.is_default:
            next_addr.is_default = True
            next_addr.save()
    return True
