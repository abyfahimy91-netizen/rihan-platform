"""
Views ماژول احراز هویت
منطبق بر ADR-006: احراز هویت Passwordless

Endpoints:
- POST /api/v1/auth/otp/request/ - درخواست OTP
- POST /api/v1/auth/otp/verify/ - تأیید OTP
"""
from rest_framework import status
from rest_framework.decorators import api_view
from rest_framework.response import Response

from .serializers import OtpRequestSerializer, OtpVerifySerializer, UserSerializer
from .services.otp_service import OtpService


def get_client_ip(request):
    """دریافت آدرس IP کلاینت"""
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        return x_forwarded_for.split(',')[0].strip()
    return request.META.get('REMOTE_ADDR')


@api_view(['POST'])
def otp_request(request):
    """
    درخواست OTP.
    
    منطبق بر ADR-006 بخش ۲ مرحله ۱:
    - اعتبارسنجی شماره
    - بررسی Rate Limit
    - تولید و ارسال OTP
    """
    serializer = OtpRequestSerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(
            {'error': 'شماره موبایل الزامی است.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    phone = serializer.validated_data['phone']
    ip = get_client_ip(request)
    
    success, message, otp_code = OtpService.request_otp(phone, ip)
    
    if not success:
        return Response(
            {'error': message},
            status=status.HTTP_429_TOO_MANY_REQUESTS
        )
    
    response_data = {
        'message': message,
        'expires_in': 120,  # ۲ دقیقه
    }
    
    # در حالت توسعه، OTP را برمی‌گردانیم
    if otp_code:
        response_data['otp_code'] = otp_code
    
    return Response(response_data, status=status.HTTP_200_OK)


@api_view(['POST'])
def otp_verify(request):
    """
    تأیید OTP.
    
    منطبق بر ADR-006 بخش ۲ مرحله ۲:
    - بررسی OTP
    - ایجاد Session/Token
    - Device Remembering
    """
    serializer = OtpVerifySerializer(data=request.data)
    
    if not serializer.is_valid():
        return Response(
            {'error': 'شماره موبایل و کد ۶ رقمی الزامی است.'},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    phone = serializer.validated_data['phone']
    otp_code = serializer.validated_data['otp_code']
    ip = get_client_ip(request)
    
    success, message, user = OtpService.verify_otp(phone, otp_code, ip)
    
    if not success:
        return Response(
            {'error': message},
            status=status.HTTP_400_BAD_REQUEST
        )
    
    # ایجاد Session (برای کانال Web - ADR-003)
    from django.contrib.auth import login
    login(request, user)
    
    return Response({
        'message': message,
        'user': UserSerializer(user).data,
    }, status=status.HTTP_200_OK)
