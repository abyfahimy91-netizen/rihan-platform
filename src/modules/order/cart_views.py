"""
Cart Page Views (HTML) - UI سبد خرید
"""
import re as _re
from django.shortcuts import render, redirect
from django.core.exceptions import ValidationError
from django.contrib import messages
from django.http import JsonResponse
from django.views.decorators.http import require_GET, require_POST

from src.core.fa import money, fa_digits

from .services import get_or_create_cart, add_to_cart, update_cart_item, remove_from_cart
from .address_service import normalize_phone, normalize_postal_code  # D-120: ورودی آدرسِ بخشنده
from src.modules.catalog.models import Product
from src.modules.catalog.services.exceptions import InsufficientStockError
from src.modules.catalog.services.inventory_service import InventoryService
from src.modules.catalog.services.variant_stock_service import VariantStockService

# D-111: نرمال‌سازی ارقام فارسی/عربی کد پستی به لاتین
_FA_EN_DIGITS = str.maketrans('۰۱۲۳۴۵۶۷۸۹٠١٢٣٤٥٦٧٨٩', '01234567890123456789')


def _to_en(value: str) -> str:
    return str(value or '').translate(_FA_EN_DIGITS).strip()


@require_GET
def cart_page_view(request):
    """نمایش صفحه سبد خرید"""
    cart = get_or_create_cart(request)
    cart_items = cart.items.select_related('product').all()
    
    # محاسبه جمع کل
    subtotal = sum(item.subtotal for item in cart_items)
    shipping = 0  # D-080: ارسال رایگان
    total = subtotal
    
    context = {
        'cart': cart,
        'items': cart_items,
        'subtotal': subtotal,
        'shipping': shipping,
        'total': total,
        'item_count': sum(item.quantity for item in cart_items),
    }
    return render(request, 'order/cart.html', context)


@require_POST
def add_to_cart_view(request):
    """افزودن محصول به سبد

    D-121: درخواست AJAX (X-Requested-With) پاسخ JSON با وضعیت کامل سبد می‌دهد
    تا سبد کناری (mini-cart) بدون ترک صفحه محصول بازشود و کاربر بتواند
    بسته‌های دیگر را هم اضافه کند. بدون AJAX همان رفتار قبلی (ریدایرکت).
    """
    product_slug = request.POST.get('product_slug')
    variant_id = request.POST.get("variant_id") or None
    # D-121: تعداد امن — ارقام فارسی/حرف هم به ۱ برمی‌گردد نه خطای ۵۰۰
    try:
        quantity = max(1, int(_to_en(request.POST.get('quantity', '1')) or '1'))
    except (TypeError, ValueError):
        quantity = 1
    wants_json = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    try:
        product = Product.objects.get(slug=product_slug)
        cart = get_or_create_cart(request)
        item = add_to_cart(cart, str(product.id), quantity, variant_id)
        if wants_json:
            payload = _cart_totals_payload(cart)
            payload["added_id"] = str(item.id)
            payload["message"] = f'{product.name} به سبد خرید اضافه شد.'
            return JsonResponse(payload)
        # D-104: خرید سریع — مستقیم به تسویه‌حساب
        if request.POST.get('fast_buy'):
            return redirect('order_pages:checkout_page')
        messages.success(request, f'{product.name} به سبد خرید اضافه شد.')
    except Product.DoesNotExist:
        if wants_json:
            return JsonResponse({"ok": False, "message": 'محصول مورد نظر یافت نشد.'}, status=400)
        messages.error(request, 'محصول مورد نظر یافت نشد.')
    except ValidationError as e:
        msg = e.messages[0] if getattr(e, 'messages', None) else str(e)
        if wants_json:
            return JsonResponse({"ok": False, "message": msg}, status=400)
        messages.error(request, msg)
    except Exception:
        import logging
        logging.getLogger(__name__).exception("cart add failed")
        msg = 'متأسفانه در افزودن به سبد خرید خطایی رخ داد. لطفاً دوباره تلاش بفرمایید.'
        if wants_json:
            return JsonResponse({"ok": False, "message": msg}, status=400)
        messages.error(request, msg)

    return redirect('order_pages:cart_page')


def _cart_items_payload(cart):
    """اقلام سبد برای سبد کناری (D-121) — همه اعداد از پیش قالب‌بندی فارسی"""
    items = []
    for i in cart.items.select_related("product", "variant").all():
        try:
            if i.variant_id:
                available = int(VariantStockService.get_available_stock(i.variant))
            else:
                available = int(InventoryService.get_available_stock(i.product))
        except Exception:
            available = 0
        items.append({
            "id": str(i.id),
            "name": str(i.product.name),
            "variant_title": (i.variant.title if i.variant_id else ""),
            "quantity": i.quantity,
            "quantity_fa": fa_digits(i.quantity),
            "unit_price": money(i.unit_price_at_add),
            "subtotal": money(i.subtotal),
            "image": i.product.main_image_url or "",
            "max_available": max(0, available),
        })
    return items


def _cart_totals_payload(cart):
    """خلاصه سبد برای پاسخ JSON — به‌روزرسانی بی‌وقفه بدون بارگذاری مجدد صفحه

    D-121: آرایه items اضافه شد تا سبد کناریِ صفحه محصول بتواند محتوا را
    رندر کند؛ per_item برای سازگاری با صفحه سبد حفظ شده است.
    """
    items = list(cart.items.select_related("product").all())
    subtotal = sum(i.subtotal for i in items)
    item_count = sum(i.quantity for i in items)
    return {
        "ok": True,
        "item_count": item_count,
        "count_fa": fa_digits(item_count),
        "subtotal": money(subtotal),
        "total": money(subtotal),
        "per_item": {str(i.id): money(i.subtotal) for i in items},
        "items": _cart_items_payload(cart),
        "shipping_free": True,
    }


@require_POST
def update_cart_item_view(request):
    """به‌روزرسانی تعداد آیتم — با پاسخ JSON برای تجربه بدون پرش صفحه"""
    item_id = request.POST.get('item_id')
    try:
        quantity = int(request.POST.get('quantity', 1))
    except (TypeError, ValueError):
        quantity = 1
    wants_json = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    try:
        cart = get_or_create_cart(request)
        result = update_cart_item(cart, item_id, quantity)
        if wants_json:
            payload = _cart_totals_payload(cart)
            payload["quantity"] = quantity
            payload["remove_item"] = result is None
            if result is None:
                payload["message"] = 'محصول مورد نظر از سبد خرید شما حذف شد.'
            return JsonResponse(payload)
        messages.success(request, 'سبد خرید شما با موفقیت به‌روزرسانی شد.')
    except ValidationError as e:
        msg = e.messages[0] if getattr(e, 'messages', None) else str(e)
        if wants_json:
            return JsonResponse({"ok": False, "message": msg})
        messages.error(request, msg)
    except Exception:
        import logging
        logging.getLogger(__name__).exception("cart update failed")
        msg = 'متأسفانه در به‌روزرسانی سبد خطایی رخ داد. لطفاً دوباره تلاش بفرمایید.'
        if wants_json:
            return JsonResponse({"ok": False, "message": msg})
        messages.error(request, msg)

    return redirect('order_pages:cart_page')


@require_POST
def remove_from_cart_view(request):
    """حذف آیتم از سبد — با پاسخ JSON برای تجربه بدون پرش صفحه"""
    item_id = request.POST.get('item_id')
    wants_json = request.headers.get('X-Requested-With') == 'XMLHttpRequest'

    try:
        cart = get_or_create_cart(request)
        remove_from_cart(cart, item_id)
        if wants_json:
            payload = _cart_totals_payload(cart)
            payload["removed_id"] = str(item_id)
            return JsonResponse(payload)
        messages.success(request, 'محصول مورد نظر با موفقیت از سبد خرید شما حذف شد.')
    except Exception:
        import logging
        logging.getLogger(__name__).exception("cart remove failed")
        msg = 'متأسفانه در حذف این آیتم خطایی رخ داد. لطفاً دوباره تلاش بفرمایید.'
        if wants_json:
            return JsonResponse({"ok": False, "message": msg})
        messages.error(request, msg)

    return redirect('order_pages:cart_page')


def checkout_page_view(request):
    """صفحه تسویه‌حساب — فرم اطلاعات گیرنده (GET) و ثبت سفارش (POST)

    D-102: کاربر لاگین‌کرده آدرس‌های ذخیره‌شده‌اش را می‌بیند و با یک کلیک
    انتخاب می‌کند؛ آدرس دستی جدید هم (با رضایت کاربر) در پروفایل ذخیره می‌شود.
    """
    from .checkout_service import CheckoutService
    from . import address_service  # D-102: آدرس‌های ذخیره‌شده کاربر

    cart = get_or_create_cart(request)
    items = cart.items.select_related('product').all()

    subtotal = sum(item.subtotal for item in items)
    shipping = 0  # D-080: ارسال رایگان
    total = subtotal + shipping

    is_auth = request.user.is_authenticated
    saved_addresses = list(request.user.addresses.all()) if is_auth else []

    if request.method == 'POST':
        choice = (request.POST.get('address_choice') or 'new').strip()
        save_address = is_auth and request.POST.get('save_address') == 'on'

        selected_address = None
        if is_auth and choice.startswith('id:'):
            selected_address = address_service.get_for_user(request.user, choice[3:])
            if selected_address is None:
                messages.error(request, 'آدرس انتخابی پیدا نشد؛ لطفاً دوباره انتخاب کنید.')
                return render(request, 'order/checkout.html', {
                    'items': items, 'subtotal': subtotal,
                    'shipping': shipping, 'total': total,
                    'saved_addresses': saved_addresses, 'address_choice': 'new',
                    'form_data': _default_form_data(request),
                })
            # D-111: آدرس ذخیره‌شده قدیمی ممکن است کد پستی نداشته باشد
            if selected_address and not (selected_address.postal_code or '').strip():
                messages.error(request,
                    'آدرس ذخیره‌شده شما کد پستی ندارد. لطفاً گزینه «افزودن آدرس جدید» را انتخاب کنید '
                    'و کد پستی ۱۰ رقمی را وارد کنید (اداره پست بدون آن مرسوله را قبول نمی‌کند).')
                return render(request, 'order/checkout.html', {
                    'items': items, 'subtotal': subtotal,
                    'shipping': shipping, 'total': total,
                    'saved_addresses': saved_addresses, 'address_choice': 'new',
                    'form_data': _default_form_data(request),
                })

        if selected_address is not None:
            # آدرس ذخیره‌شده — بدون تکرار اعتبارسنجی دستی
            guest_info = {
                'name': selected_address.full_name,
                'phone': selected_address.phone,
                'address': selected_address.detailed_address,
                'postal_code': selected_address.postal_code,
                'shipping_cost': shipping,
            }
            form_data = None
        else:
            form_data = {
                'name': (request.POST.get('name') or '').strip(),
                # D-120: نرمال‌سازی بخشنده — «0912 345 6789» / +98 / ارقام فارسی / «۵۱۵۱۴-۱۱۱۱۱» هم قبول است
                'phone': normalize_phone(request.POST.get('phone')),
                'address': (request.POST.get('address') or '').strip(),
                'postal_code': normalize_postal_code(request.POST.get('postal_code')),
                'title': (request.POST.get('title') or '').strip(),
            }
            errors = []
            if len(form_data['name']) < 3:
                errors.append('لطفاً نام و نام خانوادگی را کامل وارد کنید.')
            if not _re.fullmatch(r'09\d{9}', form_data['phone']):
                errors.append('شماره موبایل معتبر وارد کنید (مثل 09123456789).')
            if len(form_data['address']) < 10:
                errors.append('آدرس را کامل‌تر بنویسید تا بتوانیم ارسال کنیم.')
            # D-111: کد پستی الزامی است — پست بدون کد پستی ۱۰ رقمی مرسوله را ثبت نمی‌کند
            if not _re.fullmatch(r'\d{10}', _to_en(form_data['postal_code'])):
                errors.append('کد پستی ۱۰ رقمی الزامی است — اداره پست بدون آن مرسوله را ثبت نمی‌کند. (مثلاً 5151411111)')

            if not items.exists():
                errors.append('سبد خرید شما خالی است.')

            if errors:
                for e in errors:
                    messages.error(request, e)
                return render(request, 'order/checkout.html', {
                    'items': items, 'subtotal': subtotal,
                    'shipping': shipping, 'total': total,
                    'form_data': form_data,
                    'saved_addresses': saved_addresses,
                    'address_choice': 'new',
                })

            guest_info = {
                'name': form_data['name'],
                'phone': form_data['phone'],
                'address': form_data['address'],
                'postal_code': form_data['postal_code'],
                'shipping_cost': shipping,
            }

        if not items.exists():
            messages.error(request, 'سبد خرید شما خالی است.')
            return redirect('order_pages:cart_page')

        try:
            order = CheckoutService.create_order(
                cart,
                guest_info=guest_info,
                user=request.user if is_auth else None,
            )
            # D-102: ذخیره خودکار آدرس دستی جدید در پروفایل (با رضایت کاربر)
            if form_data is not None and save_address:
                try:
                    address_service.create_for_user(
                        request.user,
                        {
                            'title': form_data.get('title', ''),
                            'full_name': form_data['name'],
                            'phone': form_data['phone'],
                            'address': form_data['address'],
                            'postal_code': form_data['postal_code'],
                        },
                    )
                    messages.success(request, 'آدرس شما در پروفایل ذخیره شد؛ دفعه بعد فقط یک کلیک ✅')
                except ValueError:
                    pass  # ذخیره آدرس نباید ثبت سفارش را متوقف کند
            messages.success(request, f"سفارش شما با شماره {order.order_number} ثبت شد. لطفاً پرداخت را تکمیل کنید.")
            request.session['tracking_order_id'] = str(order.id)
            return redirect('order_pages:payment_page', order_number=order.order_number)
        except ValidationError as e:
            messages.error(request, e.messages[0] if getattr(e, 'messages', None) else str(e))
        except InsufficientStockError as e:
            messages.error(request, str(e))
        except Exception:
            import logging
            logging.getLogger(__name__).exception("checkout failed")
            messages.error(request, 'خطای غیرمنتظره رخ داد. لطفاً دوباره تلاش کنید.')

    context = {
        'items': items, 'subtotal': subtotal,
        'shipping': shipping, 'total': total,
        'saved_addresses': saved_addresses,
        'selected_address_pk': saved_addresses[0].pk if saved_addresses else None,
        'form_data': (
            {'name': ((request.user.first_name or '') + ' ' + (request.user.last_name or '')).strip(),
             'phone': request.user.username,
             'address': '', 'postal_code': '', 'title': ''}
            if is_auth else {}
        ),
    }
    return render(request, 'order/checkout.html', context)


def _default_form_data(request):
    """پیش‌پرکردن نام/موبایل از پروفایل کاربر"""
    if request.user.is_authenticated:
        return {
            'name': ((request.user.first_name or '') + ' ' + (request.user.last_name or '')).strip(),
            'phone': request.user.username,
            'address': '', 'postal_code': '', 'title': '',
        }
    return {}
