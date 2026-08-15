"""
M5: Custom Authentication Backend

منطبق بر:
- US-016: قفل ۱۵ دقیقه پس از ۵ بار اشتباه، جلسه ۸ ساعته
- USER-PERSONAS.md: P4, P5, P6
- D-079: برند مستقل

ویژگی‌ها:
- احراز هویت با نام کاربری + رمز عبور
- بررسی قفل بودن حساب
- ثبت تلاش‌های ورود (LoginAttempt)
- Activity tracking با M14
- Session duration بر اساس نقش
"""
from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.utils import timezone

from .models import UserProfile, LoginAttempt
from modules.plugin_arch.core import log_admin_activity

User = get_user_model()


class RihanAuthBackend(ModelBackend):
    """
    Custom Authentication Backend برای ریهان
    
    - بررسی قفل حساب
    - ثبت تلاش‌های ورود
    - Activity tracking
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        """
        احراز هویت با بررسی قفل و ثبت لاگ
        """
        if username is None or password is None:
            return None
        
        # گرفتن IP و User Agent
        ip_address = self._get_client_ip(request) if request else '127.0.0.1'
        user_agent = request.META.get('HTTP_USER_AGENT', '') if request else ''
        
        try:
            user = User.objects.get(username=username)
        except User.DoesNotExist:
            # ثبت تلاش ناموفق - کاربر وجود ندارد
            self._log_attempt(
                username=username,
                ip_address=ip_address,
                user_agent=user_agent,
                success=False,
                failure_reason='user_not_found'
            )
            return None
        
        # بررسی فعال بودن
        if not user.is_active:
            self._log_attempt(
                username=username,
                ip_address=ip_address,
                user_agent=user_agent,
                success=False,
                failure_reason='user_inactive'
            )
            return None
        
        # بررسی قفل بودن حساب
        try:
            profile = user.profile
        except UserProfile.DoesNotExist:
            # اگر profile نداشت، بساز با نقش پیش‌فرض
            from .models import Role
            default_role = Role.objects.filter(name='staff').first()
            if not default_role:
                self._log_attempt(
                    username=username,
                    ip_address=ip_address,
                    user_agent=user_agent,
                    success=False,
                    failure_reason='no_default_role'
                )
                return None
            profile = UserProfile.objects.create(user=user, role=default_role)
        
        if profile.is_locked():
            self._log_attempt(
                username=username,
                ip_address=ip_address,
                user_agent=user_agent,
                success=False,
                failure_reason='account_locked'
            )
            return None
        
        # بررسی رمز عبور
        if user.check_password(password) and self.user_can_authenticate(user):
            # موفقیت!
            profile.record_successful_login(request)
            
            self._log_attempt(
                username=username,
                ip_address=ip_address,
                user_agent=user_agent,
                success=True,
                failure_reason=''
            )
            
            # Activity log
            if request:
                log_admin_activity(
                    user=user,
                    action='login',
                    resource_type='User',
                    resource_id=user.id,
                    description=f"ورود موفق از IP: {ip_address}",
                    request=request,
                )
            
            return user
        else:
            # رمز اشتباه
            profile.record_failed_login()
            
            self._log_attempt(
                username=username,
                ip_address=ip_address,
                user_agent=user_agent,
                success=False,
                failure_reason='invalid_password'
            )
            
            # اگر قفل شد، activity log
            if profile.is_locked():
                if request:
                    log_admin_activity(
                        user=user,
                        action='update',
                        resource_type='User',
                        resource_id=user.id,
                        description=f"حساب قفل شد ({profile.role.lockout_duration_minutes} دقیقه) - ۵ تلاش ناموفق",
                        request=request,
                    )
            
            return None
    
    def _log_attempt(self, username, ip_address, user_agent, success, failure_reason):
        """ثبت تلاش ورود"""
        try:
            LoginAttempt.objects.create(
                username=username,
                ip_address=ip_address,
                user_agent=user_agent,
                success=success,
                failure_reason=failure_reason,
            )
        except Exception:
            # سکوت در خطا - نباید احراز هویت را مختل کند
            pass
    
    def _get_client_ip(self, request):
        """دریافت IP کاربر"""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            return x_forwarded_for.split(',')[0].strip()
        return request.META.get('REMOTE_ADDR', '127.0.0.1')
    
    def get_user(self, user_id):
        """دریافت کاربر با ID"""
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
