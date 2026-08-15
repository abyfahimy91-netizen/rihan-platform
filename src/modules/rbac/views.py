"""
M5: Authentication Views
"""
from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib import messages
from django.views.decorators.http import require_http_methods
from django.utils.translation import gettext as _

from .models import UserProfile, LoginAttempt


@require_http_methods(["GET", "POST"])
def login_view(request):
    """
    صفحه ورود با طراحی فاخر M13
    
    منطبق بر:
    - US-016: فرم نام کاربری + رمز عبور
    - M13: هویت بصری فاخر
    """
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
            login(request, user)
            
            # تنظیم session duration بر اساس نقش
            try:
                profile = user.profile
                if not remember_me:
                    # اگر remember_me نبود، session ۸ ساعته پیش‌فرض
                    request.session.set_expiry(profile.role.session_duration_hours * 3600)
                else:
                    # با remember_me: ۳۰ روز
                    request.session.set_expiry(30 * 24 * 3600)
            except UserProfile.DoesNotExist:
                pass
            
            messages.success(request, f'خوش آمدید، {user.first_name or user.username}!')
            
            # redirect به next یا admin
            next_url = request.GET.get('next', '/admin/')
            return redirect(next_url)
        else:
            # بررسی دلیل شکست
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
    
    # GET request
    return render(request, 'rbac/login.html')


def logout_view(request):
    """خروج از حساب"""
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
    
    logout(request)
    messages.success(request, 'با موفقیت خارج شدید.')
    return redirect('/panel/login/')
