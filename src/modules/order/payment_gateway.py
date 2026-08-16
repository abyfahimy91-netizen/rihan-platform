'''
Payment Gateway Service
منطبق بر D-079 (شفافیت کامل در پرداخت)
'''
import uuid
from abc import ABC, abstractmethod
from django.conf import settings
from .models import Payment


class BasePaymentGateway(ABC):
    '''کلاس پایه برای همه درگاه‌های پرداخت'''
    
    @abstractmethod
    def create_payment(self, amount, description, callback_url):
        '''ایجاد پرداخت و بازگشت به URL درگاه'''
        pass
    
    @abstractmethod
    def verify_payment(self, payment):
        '''تایید پرداخت پس از بازگشت از درگاه'''
        pass


class MockPaymentGateway(BasePaymentGateway):
    '''
    درگاه شبیه‌سازی شده برای فاز توسعه
    در فاز بعد با زرین‌پال یا آیدی‌پی جایگزین می‌شود
    '''
    
    def create_payment(self, amount, description, callback_url):
        '''ایجاد پرداخت شبیه‌سازی شده'''
        authority = f"MOCK-{uuid.uuid4().hex[:8]}"
        return {
            'authority': authority,
            'payment_url': f"{settings.FRONTEND_URL}/payment/mock?authority={authority}&amount={amount}&callback={callback_url}",
            'message': 'به درگاه شبیه‌سازی شده منتقل می‌شوید (برای تست، روی لینک زیر کلیک کنید و گزینه "پرداخت موفق" را انتخاب کنید)'
        }
    
    def verify_payment(self, payment):
        '''تایید پرداخت شبیه‌سازی شده - همیشه موفق فرض می‌شود'''
        payment.status = Payment.PaymentStatus.SUCCESS
        payment.ref_id = f"MOCK-{uuid.uuid4().hex[:8]}"
        payment.gateway_response = {
            'status': 'NOK',  # در زرین‌پال NOK یعنی موفق
            'message': 'پرداخت شبیه‌سازی شده با موفقیت انجام شد'
        }
        payment.save()
        return True


class ZarinpalPaymentGateway(BasePaymentGateway):
    '''
    درگاه زرین‌پال - برای استفاده در فاز بعد
    نیاز به ZARINPAL_MERCHANT_ID در settings.py دارد
    '''
    
    def create_payment(self, amount, description, callback_url):
        # TODO: پیاده‌سازی API زرین‌پال
        # url = 'https://api.zarinpal.com/pg/v4/payment/request.json'
        raise NotImplementedError("زرین‌پال هنوز پیاده‌سازی نشده. از MockPaymentGateway استفاده کنید.")
    
    def verify_payment(self, payment):
        # TODO: پیاده‌سازی API زرین‌پال
        raise NotImplementedError("زرین‌پال هنوز پیاده‌سازی نشده.")


def get_payment_gateway():
    '''
    Factory: بازگشت درگاه مناسب بر اساس تنظیمات
    در settings.py می‌توانید PAYMENT_GATEWAY = 'ZARINPAL' را تنظیم کنید
    '''
    gateway_type = getattr(settings, 'PAYMENT_GATEWAY', 'MOCK')
    
    if gateway_type == 'ZARINPAL':
        return ZarinpalPaymentGateway()
    else:
        return MockPaymentGateway()
