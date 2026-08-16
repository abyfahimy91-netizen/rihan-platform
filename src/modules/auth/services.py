import uuid
from django.core.mail import send_mail
from django.conf import settings
from django.contrib.auth import get_user_model
from .models import EmailVerification, PasswordResetToken


User = get_user_model()


def generate_token():
    """تولید توکن یکتا برای تایید"""
    return uuid.uuid4().hex


def send_verification_email(user):
    """ارسال ایمیل تایید به کاربر"""
    token = generate_token()
    EmailVerification.objects.create(
        user=user,
        token=token,
        email=user.email
    )
    
    verify_url = f"{settings.FRONTEND_URL}/verify-email?token={token}"
    
    send_mail(
        subject='تایید ایمیل حساب ریهان',
        message=f"سلام {user.first_name or user.username} عزیز!\n\nبرای تایید ایمیل خود، روی لینک زیر کلیک کنید:\n{verify_url}\n\nاین لینک تا ۲۴ ساعت معتبر است.",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
    )
    return token


def verify_email_token(token):
    """تایید توکن ایمیل"""
    try:
        verification = EmailVerification.objects.get(token=token)
    except EmailVerification.DoesNotExist:
        raise Exception('توکن تایید یافت نشد')
    
    if verification.is_used:
        raise Exception('این توکن قبلاً استفاده شده است')
    
    if verification.is_expired:
        raise Exception('این توکن منقضی شده است. لطفاً درخواست جدید ارسال کنید')
    
    verification.is_used = True
    verification.save()
    
    user = verification.user
    user.is_active = True
    user.save()
    
    if hasattr(user, 'profile'):
        user.profile.email_verified = True
        user.profile.save()
    
    return True


def send_password_reset_email(email):
    """ارسال ایمیل بازیابی رمز عبور"""
    try:
        user = User.objects.get(email=email)
    except User.DoesNotExist:
        raise Exception('کاربری با این ایمیل یافت نشد')
    
    token = generate_token()
    PasswordResetToken.objects.create(
        user=user,
        token=token,
        email=email
    )
    
    reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"
    
    send_mail(
        subject='بازیابی رمز عبور حساب ریهان',
        message=f"سلام {user.first_name or user.username} عزیز!\n\nبرای بازیابی رمز عبور خود، روی لینک زیر کلیک کنید:\n{reset_url}\n\nاین لینک تا ۱ ساعت معتبر است.",
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[email],
    )
    return token


def reset_password(token, new_password):
    """بازیابی رمز عبور با توکن تایید شده"""
    try:
        reset_token = PasswordResetToken.objects.get(token=token)
    except PasswordResetToken.DoesNotExist:
        raise Exception('توکن بازیابی یافت نشد')
    
    if reset_token.is_used:
        raise Exception('این توکن قبلاً استفاده شده است')
    
    if reset_token.is_expired:
        raise Exception('این توکن منقضی شده است. لطفاً درخواست جدید ارسال کنید')
    
    user = reset_token.user
    user.set_password(new_password)
    user.save()
    
    reset_token.is_used = True
    reset_token.save()
    
    return True


def merge_guest_cart(user, session_key):
    """ادغام سبد خرید مهمان با سبد خرید کاربر پس از لاگین"""
    from src.modules.order.models import Cart
    
    guest_cart = Cart.objects.filter(session_key=session_key, is_active=True, user__isnull=True).first()
    if not guest_cart:
        return None
    
    existing_cart = Cart.objects.filter(user=user, is_active=True).first()
    
    if existing_cart:
        for guest_item in guest_cart.items.all():
            existing_item = existing_cart.items.filter(product=guest_item.product).first()
            if existing_item:
                existing_item.quantity += guest_item.quantity
                existing_item.save()
            else:
                guest_item.cart = existing_cart
                guest_item.save()
        guest_cart.is_active = False
        guest_cart.save()
    else:
        guest_cart.user = user
        guest_cart.session_key = ''
        guest_cart.save()
    
    return guest_cart
