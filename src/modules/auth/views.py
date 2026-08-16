from rest_framework.views import APIView
from rest_framework import status, permissions
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


class RegisterView(APIView):
    """ثبت‌نام کاربر جدید"""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
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


class LoginView(APIView):
    """ورود کاربر و دریافت JWT"""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
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


class LogoutView(APIView):
    """خروج کاربر (بلاک کردن refresh token)"""
    
    def post(self, request):
        try:
            refresh_token = request.data.get('refresh')
            if not refresh_token:
                return Response({'error': 'refresh token الزامی است'}, status=status.HTTP_400_BAD_REQUEST)
            
            token = RefreshToken(refresh_token)
            token.blacklist()
            
            return Response({'message': 'خروج موفقیت‌آمیز بود'})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class VerifyEmailView(APIView):
    """تایید ایمیل با توکن"""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
        token = request.data.get('token')
        if not token:
            return Response({'error': 'token الزامی است'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            verify_email_token(token)
            return Response({'message': 'ایمیل شما با موفقیت تایید شد. اکنون می‌توانید وارد شوید.'})
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_400_BAD_REQUEST)


class ResendVerificationView(APIView):
    """ارسال مجدد ایمیل تایید"""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
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


class ForgotPasswordView(APIView):
    """درخواست بازیابی رمز عبور"""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
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


class ResetPasswordView(APIView):
    """بازیابی رمز عبور با توکن"""
    permission_classes = [permissions.AllowAny]
    
    def post(self, request):
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


class MeView(APIView):
    """مشاهده و ویرایش اطلاعات کاربر فعلی"""
    
    def get(self, request):
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
    
    def put(self, request):
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


class ChangePasswordView(APIView):
    """تغییر رمز عبور"""
    
    def post(self, request):
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
