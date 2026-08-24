"""
Payment Gateway Layer - منطبق بر ADR-005 (Payment Abstraction)

Strategy Pattern برای Gateway:
- Interface مشترک (BasePaymentGateway)
- چند پیاده‌سازی (CardToCard, Mock, Zarinpal, IDPay)
- Factory برای انتخاب Gateway بر اساس settings
- Service Layer فقط با Interface کار می‌کند
"""
import uuid
from abc import ABC, abstractmethod
from decimal import Decimal
from django.conf import settings
from django.utils import timezone
from .models import Payment
from src.core.fa import money


class BasePaymentGateway(ABC):
    """کلاس پایه برای همه درگاه‌های پرداخت (Interface مشترک ADR-005)"""
    
    @abstractmethod
    def create_payment(self, order, description=None, callback_url=None):
        """
        ایجاد پرداخت و بازگشت اطلاعات لازم برای کاربر
        
        برای درگاه آنلاین: URL redirect
        برای کارت‌به‌کارت: اطلاعات حساب مقصد
        """
        pass
    
    @abstractmethod
    def submit_evidence(self, payment, evidence_data):
        """
        ثبت evidence پرداخت (D-067)
        
        برای کارت‌به‌کارت: ۴ رقم آخر کارت + زمان واریز + رسید
        برای درگاه آنلاین: callback data
        """
        pass
    
    @abstractmethod
    def verify_payment(self, payment):
        """
        تایید نهایی پرداخت
        
        برای کارت‌به‌کارت: توسط ادمین (manual review)
        برای درگاه آنلاین: بررسی callback خودکار
        """
        pass
    
    @abstractmethod
    def get_gateway_name(self):
        """نام Gateway"""
        pass


class CardToCardGateway(BasePaymentGateway):
    """
    درگاه کارت‌به‌کارت (پیش‌فرض MVP - منطبق بر ADR-005 و D-067)
    
    ویژگی‌ها:
    - اطلاعات حساب مقصد از CARD_TO_CARD_CONFIG خوانده می‌شود
    - ۳ evidence اجباری: sender_card_last4, transfer_time, amount
    - ۱ evidence اختیاری: receipt_image (با threshold قابل اجباری شدن)
    - تایید دستی توسط ادمین (manual review)
    """
    
    def __init__(self):
        self.config = getattr(settings, 'CARD_TO_CARD_CONFIG', {})
        self.receipt_threshold = getattr(settings, 'RECEIPT_REQUIRED_ABOVE', 0)
    
    def create_payment(self, order, description=None, callback_url=None):
        """
        بازگرداندن اطلاعات حساب مقصد برای مشتری
        
        خروجی:
        - destination: اطلاعات حساب مقصد
        - amount: مبلغ پرداختی
        - instructions: راهنمای پرداخت
        """
        return {
            'gateway': 'MANUAL',
            'destination': {
                'card_number': self.config.get('card_number', ''),
                'card_holder': self.config.get('card_holder', ''),
                'bank_name': self.config.get('bank_name', ''),
                'iban': self.config.get('iban', ''),
            },
            'amount': float(order.total_price),
            'amount_display': money(order.total_price) + " تومان",
            'order_number': order.order_number,
            'instructions': [
                'مبلغ را به شماره کارت زیر واریز کنید',
                '۴ رقم آخر کارت خود را در فرم زیر وارد کنید',
                'تاریخ و ساعت دقیق واریز را وارد کنید',
                'در صورت تمایل، تصویر رسید را آپلود کنید',
            ],
            'receipt_required': self.receipt_threshold > 0 and order.total_price >= Decimal(str(self.receipt_threshold)),
        }
    
    def submit_evidence(self, payment, evidence_data):
        """
        ثبت evidence کارت‌به‌کارت
        
        evidence_data باید شامل:
        - sender_card_last4: ۴ رقم آخر کارت فرستنده
        - transfer_time: زمان واریز
        - amount: مبلغ واریزی (باید با مبلغ سفارش منطبق باشد)
        - receipt_image: تصویر رسید (اختیاری)
        """
        sender_card_last4 = evidence_data.get('sender_card_last4', '')
        transfer_time = evidence_data.get('transfer_time')
        amount = evidence_data.get('amount')
        receipt_image = evidence_data.get('receipt_image')
        
        # اعتبارسنجی ۴ رقم کارت
        if not sender_card_last4 or len(str(sender_card_last4)) != 4:
            raise ValueError("۴ رقم آخر کارت باید دقیقاً ۴ رقم باشد")
        
        # اعتبارسنجی زمان واریز
        if not transfer_time:
            raise ValueError("زمان واریز الزامی است")
        
        # اعتبارسنجی مبلغ (باید با مبلغ سفارش منطبق باشد)
        if amount is None:
            raise ValueError("مبلغ واریزی الزامی است")
        
        amount_decimal = Decimal(str(amount))
        if amount_decimal != payment.amount:
            raise ValueError(
                f"مبلغ واریزی ({amount_decimal}) با مبلغ سفارش ({payment.amount}) منطبق نیست"
            )
        
        # اعتبارسنجی رسید (اگر اجباری باشد)
        if self.receipt_threshold > 0 and payment.amount >= Decimal(str(self.receipt_threshold)):
            if not receipt_image:
                raise ValueError(
                    f"برای مبالغ بالای {self.receipt_threshold:,} تومان، آپلود رسید اجباری است"
                )
        
        # ثبت evidence در مدل Payment
        try:
            payment.submit_evidence(
                sender_card_last4=sender_card_last4,
                transfer_time=transfer_time,
                receipt_image=receipt_image,
            )
        except ValueError as e:
            raise
        
        return {
            'status': 'PENDING_REVIEW',
            'message': 'اطلاعات پرداخت با موفقیت ثبت شد. پس از تایید ادمین، سفارش شما نهایی می‌شود.',
            'payment_id': str(payment.id),
            'order_number': payment.order.order_number,
        }
    
    def verify_payment(self, payment):
        """
        در کارت‌به‌کارت، تایید واقعی توسط ادمین انجام می‌شود.
        این متد فقط وضعیت فعلی را برمی‌گرداند.
        """
        return {
            'status': payment.status,
            'is_verified': payment.status == Payment.PaymentStatus.SUCCESS,
            'reviewed_by': str(payment.reviewed_by) if payment.reviewed_by else None,
            'reviewed_at': payment.reviewed_at.isoformat() if payment.reviewed_at else None,
        }
    
    def get_gateway_name(self):
        return 'MANUAL'


class MockPaymentGateway(BasePaymentGateway):
    """درگاه شبیه‌سازی شده برای فاز توسعه"""
    
    def create_payment(self, order, description=None, callback_url=None):
        authority = f"MOCK-{uuid.uuid4().hex[:8]}"
        return {
            'gateway': 'MOCK',
            'authority': authority,
            'payment_url': f"{settings.FRONTEND_URL}/payment/mock?authority={authority}",
            'message': 'به درگاه شبیه‌سازی شده منتقل می‌شوید',
        }
    
    def submit_evidence(self, payment, evidence_data):
        payment.status = Payment.PaymentStatus.SUCCESS
        payment.ref_id = f"MOCK-{uuid.uuid4().hex[:8]}"
        payment.save()
        return {'status': 'SUCCESS', 'message': 'پرداخت شبیه‌سازی شده موفق'}
    
    def verify_payment(self, payment):
        payment.status = Payment.PaymentStatus.SUCCESS
        payment.ref_id = f"MOCK-{uuid.uuid4().hex[:8]}"
        payment.gateway_response = {'status': 'NOK', 'message': 'Mock payment successful'}
        payment.save()
        return {'status': 'SUCCESS', 'is_verified': True}
    
    def get_gateway_name(self):
        return 'MOCK'


class ZarinpalPaymentGateway(BasePaymentGateway):
    """
    درگاه زرین‌پال - برای استفاده در آینده
    نیاز به ZARINPAL_MERCHANT_ID در settings.py دارد
    """
    
    def create_payment(self, order, description=None, callback_url=None):
        raise NotImplementedError("زرین‌پال هنوز پیاده‌سازی نشده. از CardToCardGateway استفاده کنید.")
    
    def submit_evidence(self, payment, evidence_data):
        raise NotImplementedError("زرین‌پال هنوز پیاده‌سازی نشده.")
    
    def verify_payment(self, payment):
        raise NotImplementedError("زرین‌پال هنوز پیاده‌سازی نشده.")
    
    def get_gateway_name(self):
        return 'ZARINPAL'


class IDPayPaymentGateway(BasePaymentGateway):
    """
    درگاه آیدی‌پی - برای استفاده در آینده
    """
    
    def create_payment(self, order, description=None, callback_url=None):
        raise NotImplementedError("آیدی‌پی هنوز پیاده‌سازی نشده.")
    
    def submit_evidence(self, payment, evidence_data):
        raise NotImplementedError("آیدی‌پی هنوز پیاده‌سازی نشده.")
    
    def verify_payment(self, payment):
        raise NotImplementedError("آیدی‌پی هنوز پیاده‌سازی نشده.")
    
    def get_gateway_name(self):
        return 'IDPAY'


def get_payment_gateway():
    """
    Factory: بازگشت Gateway مناسب بر اساس settings.PAYMENT_GATEWAY
    پیش‌فرض: CardToCardGateway (مطابق D-067 و MVP)
    """
    gateway_type = getattr(settings, 'PAYMENT_GATEWAY', 'MANUAL')
    
    gateways = {
        'MANUAL': CardToCardGateway,
        'MOCK': MockPaymentGateway,
        'ZARINPAL': ZarinpalPaymentGateway,
        'IDPAY': IDPayPaymentGateway,
    }
    
    gateway_class = gateways.get(gateway_type.upper())
    if not gateway_class:
        raise ValueError(f"Gateway ناشناخته: {gateway_type}")
    
    return gateway_class()
