import os
from pathlib import Path

BASE = Path("/root/rihan-platform")

files = {
    BASE / "src/apps/accounts/__init__.py": "",
    BASE / "src/apps/accounts/apps.py": """from django.apps import AppConfig

class AccountsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.accounts'
    verbose_name = 'مدیریت کاربران و احراز هویت'
""",

    BASE / "src/apps/accounts/models.py": """from django.db import models
from django.utils import timezone
from datetime import timedelta
import random

class PhoneOTP(models.Model):
    phone = models.CharField(max_length=15, verbose_name="شماره موبایل")
    otp_code = models.CharField(max_length=6, verbose_name="کد یکبارمصرف (۶ رقم)")
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="زمان ایجاد")
    expires_at = models.DateTimeField(verbose_name="زمان انقضا")
    is_used = models.BooleanField(default=False, verbose_name="استفاده‌شده")
    attempts = models.PositiveIntegerField(default=0, verbose_name="تعداد تلاش‌ها")

    class Meta:
        verbose_name = "کد یکبارمصرف (OTP)"
        verbose_name_plural = "کدهای یکبارمصرف"
        ordering = ['-created_at']

    @classmethod
    def generate_otp(cls, phone):
        cls.objects.filter(phone=phone, is_used=False).update(is_used=True)
        # تولید کد ۶ رقمی استاندارد ADR-006
        code = str(random.randint(100000, 999999))
        expiry = timezone.now() + timedelta(minutes=2)
        return cls.objects.create(phone=phone, otp_code=code, expires_at=expiry)

    def is_valid(self):
        return (not self.is_used) and (timezone.now() <= self.expires_at) and (self.attempts < 3)
""",

    BASE / "src/apps/accounts/services.py": """import os
import logging
from django.core.cache import cache
from .models import PhoneOTP

logger = logging.getLogger(__name__)

class SMSAuthService:
    @staticmethod
    def send_otp(phone):
        otp_obj = PhoneOTP.generate_otp(phone)
        code = otp_obj.otp_code
        
        # ذخیره در ردیس با انقضای ۱۲۰ ثانیه (ADR-006)
        cache.set(f"otp:{phone}", code, timeout=120)
        
        kavenegar_key = os.environ.get('KAVENEGAR_API_KEY')
        if kavenegar_key and kavenegar_key != 'MOCK_KEY':
            try:
                from kavenegar import KavenegarAPI
                api = KavenegarAPI(kavenegar_key)
                params = {'receptor': phone, 'message': f'کد ورود به پلتفرم ریهان: {code}'}
                api.sms_send(params)
                logger.info(f"SMS OTP sent via Kavenegar to {phone}")
            except Exception as e:
                logger.error(f"Kavenegar SMS Error: {e}")
        else:
            print(f"\\n==========================================")
            print(f"  [SMS MOCK] RIHAN OTP (6-Digit) for {phone}: {code}")
            print(f"==========================================\\n")
            
        return code

    @staticmethod
    def verify_otp(phone, input_code):
        cached_code = cache.get(f"otp:{phone}")
        if cached_code and str(cached_code) == str(input_code).strip():
            cache.delete(f"otp:{phone}")
            PhoneOTP.objects.filter(phone=phone, otp_code=input_code).update(is_used=True)
            return True

        otp_record = PhoneOTP.objects.filter(phone=phone, is_used=False).first()
        if otp_record and otp_record.is_valid():
            otp_record.attempts += 1
            otp_record.save()
            if otp_record.otp_code == str(input_code).strip():
                otp_record.is_used = True
                otp_record.save()
                return True
                
        return False
""",

    BASE / "src/apps/accounts/views.py": """from django.shortcuts import render, redirect
from django.contrib.auth import login, logout, authenticate, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from apps.orders.models import Order
from .services import SMSAuthService

User = get_user_model()

def login_view(request):
    if request.user.is_authenticated:
        return redirect('user_profile')

    mode = request.GET.get('mode', 'otp') # otp or password
    step = 'phone' # phone or verify
    phone = request.session.get('auth_phone', '')
    error = None

    if request.method == 'POST':
        action = request.POST.get('action')
        
        # ۱. جریان پیش‌فرض: درخواست پیامک
        if action == 'send_otp':
            phone = request.POST.get('phone', '').strip()
            if len(phone) >= 10 and phone.startswith(('09', '9', '+98')):
                if phone.startswith('+98'):
                    phone = '0' + phone[3:]
                elif phone.startswith('9') and len(phone) == 10:
                    phone = '0' + phone
                
                request.session['auth_phone'] = phone
                SMSAuthService.send_otp(phone)
                step = 'verify'
            else:
                error = "لطفاً یک شماره موبایل معتبر ۱۱ رقمی (مانند ۰۹۱۲۳۴۵۶۷۸۹) وارد فرمایید."

        # ۲. جریان پیش‌فرض: تأیید کد ۶ رقمی
        elif action == 'verify_otp':
            input_code = request.POST.get('otp_code', '').strip()
            phone = request.session.get('auth_phone', '')
            
            if phone and SMSAuthService.verify_otp(phone, input_code):
                user, _ = User.objects.get_or_create(username=phone)
                login(request, user)
                if 'auth_phone' in request.session:
                    del request.session['auth_phone']
                next_url = request.GET.get('next') or 'user_profile'
                return redirect(next_url)
            else:
                step = 'verify'
                error = "کد تایید ۶ رقمی واردشده نادرست است یا منقضی شده است."

        # ۳. جریان جایگزین اضطراری (Fallback): ورود با رمز عبور پشتیبان
        elif action == 'login_password':
            phone = request.POST.get('phone', '').strip()
            password = request.POST.get('password', '').strip()
            
            user = authenticate(request, username=phone, password=password)
            if user is not None:
                login(request, user)
                next_url = request.GET.get('next') or 'user_profile'
                return redirect(next_url)
            else:
                mode = 'password'
                error = "شماره موبایل یا رمز عبور پشتیبان واردشده صحیح نمی‌باشد."

    context = {'mode': mode, 'step': step, 'phone': phone, 'error': error}
    return render(request, 'accounts/login.html', context)

def logout_view(request):
    logout(request)
    return redirect('product_list')

@login_required
def profile_view(request):
    orders = Order.objects.filter(customer_phone__icontains=request.user.username[-10:]).order_by('-created_at')
    
    if request.method == 'POST' and request.POST.get('action') == 'set_password':
        new_pass = request.POST.get('new_password', '').strip()
        confirm_pass = request.POST.get('confirm_password', '').strip()
        
        if len(new_pass) >= 6 and new_pass == confirm_pass:
            request.user.set_password(new_pass)
            request.user.save()
            # حفظ لاگین کاربر پس از تغییر پسورد
            login(request, request.user)
            messages.success(request, "رمز عبور پشتیبان با موفقیت ثبت شد.")
        else:
            messages.error(request, "رمز عبور باید حداقل ۶ کاراکتر بوده و با تکرار آن یکسان باشد.")

    return render(request, 'accounts/profile.html', {'orders': orders})

# REST APIs (ADR-003 & ADR-006)
class RequestOTPAPI(APIView):
    def post(self, request):
        phone = request.data.get('phone', '').strip()
        if not phone or len(phone) < 10:
            return Response({"error": "شماره موبایل معتبر الزامی است."}, status=status.HTTP_400_BAD_REQUEST)
        SMSAuthService.send_otp(phone)
        return Response({"message": "کد ۶ رقمی ارسال شد.", "phone": phone}, status=status.HTTP_200_OK)

class VerifyOTPAPI(APIView):
    def post(self, request):
        phone = request.data.get('phone', '').strip()
        code = request.data.get('code', '').strip()
        if phone and code and SMSAuthService.verify_otp(phone, code):
            user, _ = User.objects.get_or_create(username=phone)
            login(request, user)
            return Response({"status": "success", "message": "ورود با موفقیت انجام شد."}, status=status.HTTP_200_OK)
        return Response({"error": "کد نامعتبر است."}, status=status.HTTP_400_BAD_REQUEST)
""",

    BASE / "src/apps/accounts/urls.py": """from django.urls import path
from . import views

urlpatterns = [
    path('accounts/login/', views.login_view, name='login'),
    path('accounts/logout/', views.logout_view, name='logout'),
    path('accounts/profile/', views.profile_view, name='user_profile'),
    path('api/auth/otp/request/', views.RequestOTPAPI.as_view(), name='api_otp_request'),
    path('api/auth/otp/verify/', views.VerifyOTPAPI.as_view(), name='api_otp_verify'),
]
""",

    BASE / "src/templates/accounts/login.html": """{% extends 'base.html' %}
{% block title %}ورود به حساب کاربری | ریهان{% endblock %}
{% block content %}
<div class="max-w-md mx-auto px-4 py-16">
    <div class="bg-white rounded-3xl border border-gray-100 p-8 sm:p-10 shadow-sm text-center">
        
        <span class="text-4xl block mb-3">✨</span>
        <h1 class="text-2xl font-black text-rihan-900">ورود به پلتفرم ریهان</h1>
        <p class="text-xs text-gray-500 mt-1 mb-6">احراز هویت پیامکی امن یا ورود با رمز عبور پشتیبان (ADR-006)</p>

        <!-- Tab Switcher (OTP vs Password Fallback) -->
        <div class="flex bg-gray-50 p-1.5 rounded-2xl border border-gray-200 mb-6 text-xs font-bold">
            <a href="{% url 'login' %}?mode=otp" class="flex-1 py-2 rounded-xl transition {% if mode != 'password' %}bg-white text-rihan-900 shadow-sm{% else %}text-gray-500 hover:text-gray-800{% endif %}">
                📱 پیامک یکبارمصرف (پیش‌فرض)
            </a>
            <a href="{% url 'login' %}?mode=password" class="flex-1 py-2 rounded-xl transition {% if mode == 'password' %}bg-white text-rihan-900 shadow-sm{% else %}text-gray-500 hover:text-gray-800{% endif %}">
                🔑 رمز عبور پشتیبان
            </a>
        </div>

        {% if error %}
        <div class="mb-6 p-3.5 bg-red-50 text-red-700 rounded-2xl border border-red-100 text-xs">
            {{ error }}
        </div>
        {% endif %}

        {% if mode == 'password' %}
        <!-- Mode 2: Password Fallback Login -->
        <form method="post" action="{% url 'login' %}">
            {% csrf_token %}
            <input type="hidden" name="action" value="login_password">
            
            <div class="text-right mb-4">
                <label class="block text-xs font-semibold text-gray-700 mb-1.5">شماره تلفن همراه *</label>
                <input type="tel" name="phone" required class="w-full bg-gray-50 border border-gray-200 rounded-2xl p-3 text-xs text-gray-900 focus:outline-none focus:border-rihan-gold" placeholder="09123456789">
            </div>

            <div class="text-right mb-6">
                <label class="block text-xs font-semibold text-gray-700 mb-1.5">رمز عبور پشتیبان *</label>
                <input type="password" name="password" required class="w-full bg-gray-50 border border-gray-200 rounded-2xl p-3 text-xs text-gray-900 focus:outline-none focus:border-rihan-gold" placeholder="••••••••">
            </div>

            <button type="submit" class="w-full bg-rihan-900 hover:bg-rihan-800 text-white font-bold py-3.5 rounded-2xl shadow-md transition text-xs">
                ورود با رمز عبور →
            </button>
        </form>

        {% else %}
        <!-- Mode 1: SMS OTP Login (Default) -->
            {% if step == 'phone' %}
            <form method="post" action="{% url 'login' %}">
                {% csrf_token %}
                <input type="hidden" name="action" value="send_otp">
                
                <div class="text-right mb-5">
                    <label class="block text-xs font-semibold text-gray-700 mb-2">شماره تلفن همراه *</label>
                    <input type="tel" name="phone" value="{{ phone }}" required autofocus
                           class="w-full bg-gray-50 border border-gray-200 rounded-2xl p-3.5 text-sm text-center font-mono text-gray-900 focus:outline-none focus:border-rihan-gold" 
                           placeholder="09123456789">
                </div>

                <button type="submit" class="w-full bg-rihan-900 hover:bg-rihan-800 text-white font-bold py-3.5 rounded-2xl shadow-md transition text-xs">
                    دریافت کد پیامکی ورود (۶ رقم) →
                </button>
            </form>

            {% else %}
            <form method="post" action="{% url 'login' %}" x-data="{ timer: 60, interval: null }" x-init="interval = setInterval(() => { if(timer > 0) timer--; }, 1000)">
                {% csrf_token %}
                <input type="hidden" name="action" value="verify_otp">
                
                <div class="text-right mb-5">
                    <span class="text-xs text-gray-500 block mb-2">کد ۶ رقمی ارسال‌شده به <strong class="font-mono text-gray-800">{{ phone }}</strong>:</span>
                    <input type="text" name="otp_code" required maxlength="6" autofocus
                           class="w-full bg-gray-50 border border-gray-200 rounded-2xl p-3.5 text-lg text-center font-mono font-bold tracking-widest text-gray-900 focus:outline-none focus:border-rihan-gold" 
                           placeholder="• • • • • •">
                </div>

                <button type="submit" class="w-full bg-rihan-900 hover:bg-rihan-800 text-white font-bold py-3.5 rounded-2xl shadow-md transition text-xs mb-4">
                    تأیید و ورود به ریهان
                </button>

                <div class="text-xs text-gray-400">
                    <span x-show="timer > 0">امکان ارسال مجدد کد تا <span x-text="timer" class="font-bold text-gray-700 font-mono"></span> ثانیه دیگر</span>
                    <a x-show="timer === 0" href="{% url 'login' %}" class="text-rihan-gold font-bold hover:underline">ارسال مجدد کد پیامکی</a>
                </div>
            </form>
            {% endif %}
        {% endif %}

    </div>
</div>
{% endblock %}
""",

    BASE / "src/templates/accounts/profile.html": """{% extends 'base.html' %}
{% block title %}حساب کاربری من | ریهان{% endblock %}
{% block content %}
<div class="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
    <div class="flex justify-between items-center mb-8 border-b border-gray-100 pb-4">
        <div>
            <h1 class="text-2xl font-black text-rihan-900">حساب کاربری</h1>
            <p class="text-xs text-gray-500 mt-1">شماره همراه شما: <strong class="font-mono text-gray-800">{{ request.user.username }}</strong></p>
        </div>
        <a href="{% url 'logout' %}" class="text-xs text-red-600 hover:text-red-700 bg-red-50 px-4 py-2 rounded-xl border border-red-100 font-semibold transition">
            خروج از حساب
        </a>
    </div>

    {% if messages %}
    <div class="mb-6 space-y-2">
        {% for message in messages %}
        <div class="p-3.5 rounded-2xl text-xs {% if message.tags == 'success' %}bg-green-50 text-green-800 border border-green-200{% else %}bg-red-50 text-red-800 border border-red-200{% endif %}">
            {{ message }}
        </div>
        {% endfor %}
    </div>
    {% endif %}

    <div class="grid grid-cols-1 md:grid-cols-3 gap-8">
        <!-- Order History (2 Cols) -->
        <div class="md:col-span-2 bg-white rounded-3xl border border-gray-100 p-6 sm:p-8 shadow-sm">
            <h2 class="text-base font-bold text-gray-900 mb-6">سفارش‌های شما در ریهان</h2>

            {% if orders %}
            <div class="space-y-4">
                {% for order in orders %}
                <div class="border border-gray-100 rounded-2xl p-5 hover:border-rihan-100 transition flex flex-wrap justify-between items-center gap-4 bg-gray-50">
                    <div>
                        <span class="text-xs font-bold text-rihan-900 bg-white px-3 py-1 rounded-lg border border-gray-200 font-mono">{{ order.order_number }}</span>
                        <span class="text-xs text-gray-500 block mt-2">ثبت در تاریخ: {{ order.created_at|date:"Y/m/d H:i" }}</span>
                    </div>
                    <div>
                        <span class="text-xs text-gray-500 block">مبلغ سفارش:</span>
                        <span class="text-sm font-extrabold text-gray-900">{{ order.grand_total|floatformat:"0" }} تومان</span>
                    </div>
                    <div>
                        <span class="text-xs px-3 py-1 rounded-full font-bold bg-white border border-gray-200">{{ order.get_status_display }}</span>
                    </div>
                    <a href="{% url 'order_tracking' %}?order_number={{ order.order_number }}&phone={{ request.user.username }}" 
                       class="bg-rihan-900 hover:bg-rihan-800 text-white text-xs font-semibold px-4 py-2 rounded-xl transition shadow-sm">
                        رهگیری مرسوله →
                    </a>
                </div>
                {% endfor %}
            </div>
            {% else %}
            <div class="text-center py-12">
                <span class="text-4xl block mb-2 text-gray-300">📦</span>
                <p class="text-xs text-gray-500">هنوز سفارشی با این شماره ثبت نشده است.</p>
                <a href="{% url 'product_list' %}" class="inline-block bg-rihan-900 text-white text-xs font-bold px-6 py-2.5 rounded-xl mt-4">مشاهده کاتالوگ</a>
            </div>
            {% endif %}
        </div>

        <!-- Optional Backup Password Card (ADR-006 Section 6) -->
        <div class="bg-white rounded-3xl border border-gray-100 p-6 shadow-sm h-fit">
            <h3 class="text-xs font-bold text-rihan-900 mb-2">🔑 رمز عبور پشتیبان (اختیاری)</h3>
            <p class="text-[11px] text-gray-500 leading-relaxed mb-4">برای ورود در زمان قطعی پیامک، می‌توانید یک رمز عبور پشتیبان تعریف فرمایید.</p>

            <form method="post" action="{% url 'user_profile' %}" class="space-y-3">
                {% csrf_token %}
                <input type="hidden" name="action" value="set_password">
                <div>
                    <label class="block text-[11px] font-semibold text-gray-700 mb-1">رمز عبور جدید</label>
                    <input type="password" name="new_password" required minlength="6" class="w-full bg-gray-50 border border-gray-200 rounded-xl p-2 text-xs text-gray-900 focus:outline-none focus:border-rihan-gold" placeholder="حداقل ۶ کاراکتر">
                </div>
                <div>
                    <label class="block text-[11px] font-semibold text-gray-700 mb-1">تکرار رمز عبور</label>
                    <input type="password" name="confirm_password" required minlength="6" class="w-full bg-gray-50 border border-gray-200 rounded-xl p-2 text-xs text-gray-900 focus:outline-none focus:border-rihan-gold" placeholder="تکرار مجدد">
                </div>
                <button type="submit" class="w-full bg-rihan-900 hover:bg-rihan-800 text-white font-bold py-2.5 rounded-xl text-xs transition">
                    ذخیره رمز پشتیبان
                </button>
            </form>
        </div>
    </div>
</div>
{% endblock %}
""",

    BASE / "tests/test_accounts.py": """from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse
from apps.accounts.services import SMSAuthService
from apps.accounts.models import PhoneOTP

User = get_user_model()

class HybridAccountsTestCase(TestCase):
    def test_6_digit_otp_flow(self):
        phone = "09121112233"
        code = SMSAuthService.send_otp(phone)
        self.assertEqual(len(code), 6) # ADR-006 6-digit requirement
        self.assertTrue(SMSAuthService.verify_otp(phone, code))

    def test_login_and_password_fallback(self):
        c = Client()
        phone = "09124445566"
        
        # 1. Login with OTP first
        SMSAuthService.send_otp(phone)
        otp = PhoneOTP.objects.filter(phone=phone, is_used=False).first().otp_code
        c.post(reverse('login'), {'action': 'verify_otp', 'otp_code': otp})
        
        # 2. Set backup password in profile (ADR-006 Section 6)
        res_set = c.post(reverse('user_profile'), {
            'action': 'set_password',
            'new_password': 'MyStrongBackupPass1405',
            'confirm_password': 'MyStrongBackupPass1405'
        })
        self.assertEqual(res_set.status_code, 200)

        # 3. Logout
        c.get(reverse('logout'))

        # 4. Login with Password Fallback
        res_pass_login = c.post(reverse('login'), {
            'action': 'login_password',
            'phone': phone,
            'password': 'MyStrongBackupPass1405'
        })
        self.assertEqual(res_pass_login.status_code, 302) # Logged in successfully!
"""
}

for path, content in files.items():
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"✓ Created: {path.name}")

# Update settings.py
settings_file = BASE / "src/rihan/settings.py"
settings_content = settings_file.read_text(encoding="utf-8")
if "'apps.accounts'" not in settings_content:
    settings_content = settings_content.replace("'apps.orders',", "'apps.orders',\n    'apps.accounts',")
    settings_file.write_text(settings_content, encoding="utf-8")
    print("✓ Registered apps.accounts in settings.py")

# Update urls.py
urls_file = BASE / "src/rihan/urls.py"
urls_content = urls_file.read_text(encoding="utf-8")
if "apps.accounts.urls" not in urls_content:
    urls_content = urls_content.replace("path('', include('apps.orders.urls')),", "path('', include('apps.orders.urls')),\n    path('', include('apps.accounts.urls')),")
    urls_file.write_text(urls_content, encoding="utf-8")
    print("✓ Registered accounts urls in urls.py")

# Update base.html navbar
base_template = BASE / "src/templates/base.html"
base_content = base_template.read_text(encoding="utf-8")
if "accounts/login" not in base_content:
    import re
    auth_nav = """
                <div class="flex items-center gap-3">
                    {% if user.is_authenticated %}
                    <a href="/accounts/profile/" class="text-xs text-rihan-900 font-bold bg-rihan-100 px-3 py-1.5 rounded-lg hover:bg-rihan-200 transition font-mono">{{ user.username }} 👤</a>
                    {% else %}
                    <a href="/accounts/login/" class="text-xs text-rihan-900 font-semibold border border-gray-200 px-3 py-1.5 rounded-lg hover:border-rihan-gold transition">ورود / حساب کاربری</a>
                    {% endif %}
                    <a href="/admin/" class="text-xs text-gray-500 hover:text-gray-900 border border-gray-200 px-3 py-1.5 rounded-lg transition">پنل مدیریت</a>
                </div>
"""
    base_content = re.sub(r'<div class="flex items-center gap-4">.*?</div>\s*</div>\s*</div>\s*</header>', auth_nav + '            </div>\n        </div>\n    </header>', base_content, flags=re.DOTALL)
    base_template.write_text(base_content, encoding="utf-8")
    print("✓ Updated Auth Navigation in base.html")

print("Module 5 (Hybrid Auth ADR-006) Deployed Successfully.")
