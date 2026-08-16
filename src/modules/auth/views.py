from rest_framework import viewsets, status, permissions
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate, get_user_model
from .serializers import (
    UserRegisterSerializer, UserLoginSerializer, ChangePasswordSerializer,
    ForgotPasswordSerializer, ResetPasswordSerializer, ProfileSerializer
)
from .services import (
    send_verification_email, verify_email_token, send_password_reset_email,
    reset_password, merge_guest_cart
)


User = get_user_model()


class AuthViewSet(viewsets.ViewSet):
    """
    API احراز هویت و مدیریت حساب کاربری
    - POST /auth/register/            : ثبت‌نام کاربر جدید
    - POST /auth/login/               : ورود و دریافت JWT
    - POST /auth/logout/              : خروج (بلاک کردن refresh token)
    - POST /auth/verify-email/        : تایید ایمیل با توکن
    - POST /auth/resend-verification/ : ارسال مجدد ایمیل تایید
    - POST /auth/forgot-password/     : درخواست بازیابی رمز
    - POST /auth/reset-password/      : بازیابی رمز با توکن
    - GET  /auth/me/                  : اطلاعات کاربر فعلی
    - PUT  /auth/me/                  : ویرایش پروفایل
    - POST /auth/change-password/     : تغییر رمز عبور
    """
    
    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny])
    def register(self, request):
        """ثبت‌نام کاربر جدید"""
        serializer = UserRegisterSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        user = serializer.save()
        send_verification_email(user)
        
        return Response({
            'message': 'ثبت‌نام با موفقیت انجام شد. لطفاً ایمیل خود را تایید کنید.',
            'user_id': user.id,
            'email': user.email,
            'username': user.username
        }, status=status.HTTP_201_CREATED)
    
    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny])
    def login(self, request):
        """ورود کاربر و دریافت JWT"""
        serializer = UserLoginSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        username = serializer.validated_data['username']
        password = serializer.validated_data['password']
        
        # تلاش برای احراز هویت با username یا email
        user = authenticate(username=username, password=password)
        if not user:
            try:
                user_obj = User.objects.get(email=username)
                user = authenticate(username=user_obj.username, password=password)
            except User.DoesNotExist:
                pass
        
        if not user:
            return Response(
                {'error': 'نام کاربری/ایمیل یا رمز عبور اشتباه است'},
                status=status.HTTP_401_UNAUTHORIZED
            )
        
        if not user.is_active:
            return Response(
                {'error': 'حساب شما غیرفعال است. لطفاً ایمیل خود را تایید کنید.'},
                status=status.HTTP_403_FORBIDDEN
            )
        
        # تولید JWT
        refresh = RefreshToken.for_user(user)
        
        # ادغام سبد خرید مهمان
        session_key = request.session.session_key
        if session_key:
            merge_guest_cart(user, session_key)
        
        return Response({
            'message': 'ورود موفقیت‌آمیز بود',
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name
            }
        })

    
    @action(detail=False, methods=['post'])
    def logout(self, request):
        """خروج کاربر (بلاک کردن refresh token)"""
        try:
            refresh_token = request.data.get('refresh')
            if not refresh_token:
                return Response({'error': 'refresh token الزامی است'}, status=status.HTTP_400_BAD_REQUEST)
            
            token = RefreshToken(refresh_token)
            token.blacklist()
            
            return Response({'message': 'خروج موفقیت‌آمیز بود'})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny])
    def verify_email(self, request):
        """تایید ایمیل با توکن"""
        token = request.data.get('token')
        if not token:
            return Response({'error': 'token الزامی است'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            verify_email_token(token)
            return Response({'message': 'ایمیل شما با موفقیت تایید شد. اکنون می‌توانید وارد شوید.'})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny])
    def resend_verification(self, request):
        """ارسال مجدد ایمیل تایید"""
        email = request.data.get('email')
        if not email:
            return Response({'error': 'email الزامی است'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = User.objects.get(email=email)
            if user.is_active:
                return Response({'error': 'ایمیل این کاربر قبلاً تایید شده است'}, status=status.HTTP_400_BAD_REQUEST)
            
            send_verification_email(user)
            return Response({'message': 'ایمیل تایید مجدداً ارسال شد'})
        except User.DoesNotExist:
            return Response({'error': 'کاربری با این ایمیل یافت نشد'}, status=status.HTTP_404_NOT_FOUND)
    
    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny])
    def forgot_password(self, request):
        """درخواست بازیابی رمز عبور"""
        serializer = ForgotPasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        email = serializer.validated_data['email']
        
        try:
            send_password_reset_email(email)
            return Response({
                'message': 'ایمیل بازیابی رمز عبور ارسال شد (در صورت وجود کاربر)'
            })
        except Exception:
            # برای امنیت، حتی اگر کاربر وجود نداشت، پیام موفقیت برمی‌گردانیم
            return Response({
                'message': 'اگر کاربری با این ایمیل وجود داشته باشد، ایمیل بازیابی ارسال می‌شود'
            })
    
    @action(detail=False, methods=['post'], permission_classes=[permissions.AllowAny])
    def reset_password(self, request):
        """بازیابی رمز عبور با توکن"""
        serializer = ResetPasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            reset_password(
                token=serializer.validated_data['token'],
                new_password=serializer.validated_data['new_password']
            )
            return Response({'message': 'رمز عبور با موفقیت تغییر کرد. اکنون می‌توانید با رمز جدید وارد شوید.'})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)

    
    @action(detail=False, methods=['get'])
    def me(self, request):
        """دریافت اطلاعات کاربر فعلی"""
        user = request.user
        profile_serializer = ProfileSerializer(user.profile)
        
        return Response({
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'first_name': user.first_name,
                'last_name': user.last_name,
                'is_active': user.is_active
            },
            'profile': profile_serializer.data
        })
    
    @me.mapping.put
    def update_me(self, request):
        """ویرایش پروفایل کاربر فعلی"""
        user = request.user
        profile = user.profile
        
        # به‌روزرسانی فیلدهای کاربر
        user.first_name = request.data.get('first_name', user.first_name)
        user.last_name = request.data.get('last_name', user.last_name)
        user.save()
        
        # به‌روزرسانی فیلدهای پروفایل
        profile_serializer = ProfileSerializer(profile, data=request.data, partial=True)
        if profile_serializer.is_valid():
            profile_serializer.save()
            return Response({
                'message': 'پروفایل با موفقیت به‌روزرسانی شد',
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name
                },
                'profile': profile_serializer.data
            })
        return Response(profile_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    @action(detail=False, methods=['post'])
    def change_password(self, request):
        """تغییر رمز عبور"""
        serializer = ChangePasswordSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        user = request.user
        if not user.check_password(serializer.validated_data['current_password']):
            return Response(
                {'current_password': 'رمز عبور فعلی اشتباه است'},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        
        return Response({'message': 'رمز عبور با موفقیت تغییر کرد'})
