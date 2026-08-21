"""
Cart Page Views (HTML) - UI سبد خرید
"""
from django.shortcuts import render, redirect
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
    except Exception as e:
        messages.error(request, f'خطا: {e}')
    
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
