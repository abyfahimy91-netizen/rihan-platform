'''
منطق کسب‌وکار سبد خرید
منطبق بر D-079 (شفافیت)، D-080 (سبد مهمان)، D-046 (بدون هزینه پنهان)
'''
from django.core.exceptions import ValidationError
from src.modules.catalog.models import Product
from .models import Cart, CartItem


def get_or_create_cart(request):
    '''گرفتن یا ساختن سبد خرید - منطبق بر ADR-002 (Session-based)'''
    session_key = request.session.session_key
    if not session_key:
        request.session.create()
        session_key = request.session.session_key
    
    user = request.user if request.user.is_authenticated else None
    
    # اولویت: سبد کاربر لاگین‌کرده، سپس سبد نشست
    if user:
        cart = Cart.objects.filter(user=user, is_active=True).first()
        if not cart:
            # ادغام سبد مهمان با سبد کاربر (merge)
            guest_cart = Cart.objects.filter(session_key=session_key, is_active=True).first()
            if guest_cart:
                guest_cart.user = user
                guest_cart.session_key = ''
                guest_cart.save()
                return guest_cart
            cart = Cart.objects.create(user=user)
        return cart
    
    cart, created = Cart.objects.get_or_create(
        session_key=session_key,
        user=None,
        is_active=True
    )
    return cart


def add_to_cart(cart, product_id, quantity=1):
    '''افزودن کالا به سبد با چک موجودی - منطبق بر D-046 (شفافیت)'''
    try:
        product = Product.objects.get(id=product_id)
    except Product.DoesNotExist:
        raise ValidationError("محصول یافت نشد")
    
    # بررسی موجودی انبار
    if quantity < 1:
        raise ValidationError("تعداد باید حداقل ۱ باشد")
    
    existing_item = CartItem.objects.filter(cart=cart, product=product).first()
    new_quantity = (existing_item.quantity + quantity) if existing_item else quantity
    
    if product.stock_quantity < new_quantity:
        raise ValidationError(
            f"موجودی کافی نیست. حداکثر موجودی: {product.stock_quantity} عدد"
        )
    
    if existing_item:
        existing_item.quantity = new_quantity
        existing_item.unit_price_at_add = product.price  # به‌روزرسانی با قیمت جاری
        existing_item.save()
        return existing_item
    else:
        return CartItem.objects.create(
            cart=cart,
            product=product,
            quantity=quantity,
            unit_price_at_add=product.price
        )


def update_cart_item(cart, item_id, quantity):
    '''به‌روزرسانی تعداد - چک موجودی'''
    try:
        item = CartItem.objects.get(id=item_id, cart=cart)
    except CartItem.DoesNotExist:
        raise ValidationError("کالا در سبد یافت نشد")
    
    if quantity < 1:
        item.delete()
        return None
    
    if item.product.stock_quantity < quantity:
        raise ValidationError(
            f"موجودی کافی نیست. حداکثر موجودی: {item.product.stock_quantity} عدد"
        )
    
    item.quantity = quantity
    item.save()
    return item


def remove_from_cart(cart, item_id):
    '''حذف کالا از سبد'''
    CartItem.objects.filter(id=item_id, cart=cart).delete()
