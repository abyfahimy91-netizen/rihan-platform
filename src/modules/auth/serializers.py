from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Profile, EmailVerification, PasswordResetToken


User = get_user_model()


class ProfileSerializer(serializers.ModelSerializer):
    """نمایش پروفایل کاربر"""
    class Meta:
        model = Profile
        fields = ['phone_number', 'date_of_birth', 'gender', 'email_verified',
                  'phone_verified', 'newsletter_subscription']
        read_only_fields = ['email_verified', 'phone_verified']


class UserRegisterSerializer(serializers.ModelSerializer):
    """ثبت‌نام کاربر جدید"""
    password = serializers.CharField(write_only=True, min_length=8)
    password_confirm = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = ['username', 'email', 'first_name', 'last_name', 'password', 'password_confirm']
        extra_kwargs = {
            'password': {'write_only': True}
        }
    
    def validate(self, attrs):
        if attrs.get('password') != attrs.get('password_confirm'):
            raise serializers.ValidationError(
                {'password_confirm': 'رمز عبور و تکرار آن یکسان نیستند'}
            )
        if User.objects.filter(email=attrs.get('email')).exists():
            raise serializers.ValidationError(
                {'email': 'کاربری با این ایمیل قبلاً ثبت‌نام کرده است'}
            )
        return attrs
    
    def create(self, validated_data):
        validated_data.pop('password_confirm')
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', ''),
        )
        user.is_active = False  # غیرفعال تا زمانی که ایمیل تایید شود
        user.save()
        return user


class UserLoginSerializer(serializers.Serializer):
    """ورود کاربر"""
    username = serializers.CharField()
    password = serializers.CharField(write_only=True)


class ChangePasswordSerializer(serializers.Serializer):
    """تغییر رمز عبور"""
    current_password = serializers.CharField(write_only=True)
    new_password = serializers.CharField(min_length=8, write_only=True)
    new_password_confirm = serializers.CharField(write_only=True)
    
    def validate(self, attrs):
        if attrs.get('new_password') != attrs.get('new_password_confirm'):
            raise serializers.ValidationError(
                {'new_password_confirm': 'رمز عبور جدید و تکرار آن یکسان نیستند'}
            )
        return attrs


class ForgotPasswordSerializer(serializers.Serializer):
    """درخواست بازیابی رمز عبور"""
    email = serializers.EmailField()


class ResetPasswordSerializer(serializers.Serializer):
    """بازیابی رمز عبور با توکن"""
    token = serializers.CharField(write_only=True)
    new_password = serializers.CharField(min_length=8, write_only=True)
    new_password_confirm = serializers.CharField(write_only=True)
    
    def validate(self, attrs):
        if attrs.get('new_password') != attrs.get('new_password_confirm'):
            raise serializers.ValidationError(
                {'new_password_confirm': 'رمز عبور جدید و تکرار آن یکسان نیستند'}
            )
        return attrs
