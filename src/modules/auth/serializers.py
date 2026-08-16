"""
Serializers ماژول احراز هویت
منطبق بر ADR-006 بخش ۸: پیام‌های خطای محترمانه
"""
from rest_framework import serializers


class OtpRequestSerializer(serializers.Serializer):
    """درخواست OTP"""
    phone = serializers.CharField(max_length=15)


class OtpVerifySerializer(serializers.Serializer):
    """تأیید OTP"""
    phone = serializers.CharField(max_length=15)
    otp_code = serializers.CharField(max_length=6, min_length=6)


class UserSerializer(serializers.Serializer):
    """اطلاعات کاربر"""
    id = serializers.IntegerField(read_only=True)
    username = serializers.CharField(read_only=True)
    phone = serializers.SerializerMethodField()
    
    def get_phone(self, obj):
        # فقط ۴ رقم اول و آخر نمایش داده شود (ADR-006 بخش ۹)
        phone = obj.username
        if len(phone) >= 8:
            return f"{phone[:4]}***{phone[-4:]}"
        return phone
