"""
Cart Page Views (HTML) - UI سبد خرید
"""
import re as _re
from django.shortcuts import render, redirect
from django.core.exceptions import ValidationError
from django.contrib import messages
from django.views.decorators.http import require_GET, require_POST

from .services import get_or_create_cart, add_to_cart, update_cart_item, remove_from_cart
from src.modules.catalog.models import Product


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
    """افزودن محصول به سبد"""
    product_slug = request.POST.get('product_slug')
    quantity = int(request.POST.get('quantity', 1))
    
    try:
        product = Product.objects.get(slug=product_slug)
        cart = get_or_create_cart(request)
        add_to_cart(cart, str(product.id), quantity)
        messages.success(request, f'{product.name} به سبد خرید اضافه شد.')
    except Product.DoesNotExist:
        messages.error(request, 'محصول مورد نظر یافت نشد.')
    except ValidationError as e:
        messages.error(request, f'خطا در افزودن: {e}')
    except Exception as e:
        messages.error(request, f'خطای غیرمنتظره: {e}')
    
    return redirect('order_pages:cart_page')


@require_POST
def update_cart_item_view(request):
    """به‌روزرسانی تعداد آیتم"""
    item_id = request.POST.get('item_id')
    quantity = int(request.POST.get('quantity', 1))
    
    try:
        cart = get_or_create_cart(request)
        update_cart_item(cart, item_id, quantity)
        messages.success(request, 'سبد خرید به‌روز شد.')
    except Exception as e:
        messages.error(request, f'خطا: {e}')
    
    return redirect('order_pages:cart_page')


@require_POST
def remove_from_cart_view(request):
    """حذف آیتم از سبد"""
    item_id = request.POST.get('item_id')
    
    try:
        cart = get_or_create_cart(request)
        remove_from_cart(cart, item_id)
        messages.success(request, 'آیتم از سبد حذف شد.')
    except Exception as e:
        messages.error(request, f'خطا: {e}')
    
    return redirect('order_pages:cart_page')


def checkout_page_view(request):
    """صفحه تسویه‌حساب — فرم اطلاعات گیرنده (GET) و ثبت سفارش (POST)"""
    from .checkout_service import CheckoutService

    cart = get_or_create_cart(request)
    items = cart.items.select_related('product').all()

    subtotal = sum(item.subtotal for item in items)
    shipping = 0  # D-080: ارسال رایگان
    total = subtotal + shipping

    if request.method == 'POST':
        form_data = {
            'name': (request.POST.get('name') or '').strip(),
            'phone': (request.POST.get('phone') or '').strip(),
            'address': (request.POST.get('address') or '').strip(),
            'postal_code': (request.POST.get('postal_code') or '').strip(),
        }
        errors = []
        if len(form_data['name']) < 3:
            errors.append('لطفاً نام و نام خانوادگی را کامل وارد کنید.')
        if not _re.fullmatch(r'09\d{9}', form_data['phone']):
            errors.append('شماره موبایل معتبر وارد کنید (مثل 09123456789).')
        if len(form_data['address']) < 10:
            errors.append('آدرس را کامل‌تر بنویسید تا بتوانیم ارسال کنیم.')
        if form_data['postal_code'] and not _re.fullmatch(r'\d{10}', form_data['postal_code']):
            errors.append('کد پستی باید ۱۰ رقم باشد.')

        if not items.exists():
            errors.append('سبد خرید شما خالی است.')

        if errors:
            for e in errors:
                messages.error(request, e)
            return render(request, 'order/checkout.html', {
                'items': items, 'subtotal': subtotal,
                'shipping': shipping, 'total': total,
                'form_data': form_data,
            })

        try:
            order = CheckoutService.create_order(
                cart,
                guest_info={
                    'name': form_data['name'],
                    'phone': form_data['phone'],
                    'address': form_data['address'],
                    'postal_code': form_data['postal_code'],
                    'shipping_cost': shipping,
                },
                user=request.user if request.user.is_authenticated else None,
            )
            messages.success(request, f"سفارش شما با شماره {order.order_number} ثبت شد. لطفاً پرداخت را تکمیل کنید.")
            request.session['tracking_order_id'] = str(order.id)
            return redirect('order_pages:payment_page', order_number=order.order_number)
        except ValidationError as e:
            messages.error(request, f'خطا در ثبت سفارش: {e}')
        except Exception:
            import logging
            logging.getLogger(__name__).exception("checkout failed")
            messages.error(request, 'خطای غیرمنتظره رخ داد. لطفاً دوباره تلاش کنید.')

    context = {
        'items': items, 'subtotal': subtotal,
        'shipping': shipping, 'total': total,
        'form_data': (
            {'name': ((request.user.first_name or '') + ' ' + (request.user.last_name or '')).strip(),
             'phone': request.user.username,
             'address': '', 'postal_code': ''}
            if request.user.is_authenticated else {}
        ),
    }
    return render(request, 'order/checkout.html', context)
