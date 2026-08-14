from django.shortcuts import render, redirect
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
