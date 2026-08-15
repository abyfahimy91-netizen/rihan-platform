"""
M5: Authentication Views

Fixes:
- Post-Redirect-Get (PRG) pattern برای جلوگیری از resubmit
- Logout کامل با session flush
- Cache control برای جلوگیری از caching login page
- Session duration بر اساس نقش
"""
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.views.decorators.cache import never_cache
from django.utils.translation import gettext as _
from django.contrib.auth import get_user_model

from .models import UserProfile, LoginAttempt

User = get_user_model()


@never_cache
@require_http_methods(["GET", "POST"])
def login_view(request):
    """
    صفحه ورود با طراحی فاخر M13
    
    منطبق بر:
    - US-016: فرم نام کاربری + رمز عبور
    - M13: هویت بصری فاخر
    - PRG pattern برای جلوگیری از resubmit
    """
    # اگر کاربر لاگین است، redirect به admin
    if request.user.is_authenticated:
        return redirect('/admin/')
    
    if request.method == 'POST':
        username = request.POST.get('username', '').strip()
        password = request.POST.get('password', '')
        remember_me = request.POST.get('remember_me') == 'on'
        
        if not username or not password:
            messages.error(request, 'لطفاً نام کاربری و رمز عبور را وارد کنید.')
            return render(request, 'rbac/login.html', {'username': username})
        
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            # Login موفق
            login(request, user)
            
            # تنظیم session duration بر اساس نقش
            try:
                profile = user.profile
                if remember_me:
                    # با remember_me: ۳۰ روز
                    request.session.set_expiry(30 * 24 * 3600)
                else:
                    # بدون remember_me: بر اساس نقش (پیش‌فرض ۸ ساعت)
                    request.session.set_expiry(profile.role.session_duration_hours * 3600)
            except UserProfile.DoesNotExist:
                # اگر profile نداشت، ۸ ساعت پیش‌فرض
                request.session.set_expiry(8 * 3600)
            
            messages.success(request, f'خوش آمدید، {user.first_name or user.username}!')
            
            # Redirect به next یا admin (PRG pattern)
            next_url = request.GET.get('next', request.POST.get('next', '/admin/'))
            return redirect(next_url)
        else:
            # Login ناموفق
            recent_attempt = LoginAttempt.objects.filter(
                username=username
            ).order_by('-timestamp').first()
            
            if recent_attempt and recent_attempt.failure_reason == 'account_locked':
                try:
                    user_obj = User.objects.get(username=username)
                    profile = user_obj.profile
                    lock_minutes = profile.role.lockout_duration_minutes
                    messages.error(
                        request, 
                        f'حساب شما به دلیل ۵ بار تلاش ناموفق قفل شد. '
                        f'لطفاً {lock_minutes} دقیقه دیگر دوباره تلاش کنید.'
                    )
                except:
                    messages.error(request, 'حساب قفل شده است.')
            elif recent_attempt and recent_attempt.failure_reason == 'user_not_found':
                messages.error(request, 'نام کاربری یا رمز عبور اشتباه است.')
            else:
                # نمایش تعداد تلاش‌های باقی‌مانده
                try:
                    user_obj = User.objects.get(username=username)
                    profile = user_obj.profile
                    attempts_left = profile.role.max_login_attempts - profile.failed_login_attempts
                    if attempts_left > 0:
                        messages.error(
                            request, 
                            f'نام کاربری یا رمز عبور اشتباه است. '
                            f'{attempts_left} تلاش باقی‌مانده.'
                        )
                    else:
                        messages.error(request, 'حساب قفل شد.')
                except:
                    messages.error(request, 'نام کاربری یا رمز عبور اشتباه است.')
            
            return render(request, 'rbac/login.html', {'username': username})
    
    # GET request - نمایش فرم خالی
    return render(request, 'rbac/login.html')


@never_cache
def logout_view(request):
    """
    خروج از حساب
    
    - پاک کردن کامل session
    - Activity tracking
    - Redirect به login با پیام موفقیت
    """
    if request.user.is_authenticated:
        from modules.plugin_arch.core import log_admin_activity
        log_admin_activity(
            user=request.user,
            action='logout',
            resource_type='User',
            resource_id=request.user.id,
            description='خروج از حساب',
            request=request,
        )
    
    # Logout کاربر
    logout(request)
    
    # پاک کردن کامل session
    request.session.flush()
    
    messages.success(request, 'با موفقیت خارج شدید.')
    
    # Redirect به login page
    response = redirect('/panel/login/')
    
    # Cache control headers برای جلوگیری از caching
    response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
    response['Pragma'] = 'no-cache'
    response['Expires'] = '0'
    
    return response
