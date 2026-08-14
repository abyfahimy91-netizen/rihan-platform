import os
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
            print(f"\n==========================================")
            print(f"  [SMS MOCK] RIHAN OTP (6-Digit) for {phone}: {code}")
            print(f"==========================================\n")
            
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
