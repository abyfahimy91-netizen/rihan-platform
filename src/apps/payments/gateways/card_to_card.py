from django.utils import timezone
from .base import BasePaymentGateway
from apps.payments.models import Payment

class CardToCardGateway(BasePaymentGateway):
    def initiate_payment(self, order):
        payment, _ = Payment.objects.get_or_create(
            order=order,
            defaults={'amount': order.grand_total, 'gateway_type': 'card_to_card', 'status': 'pending'}
        )
        return payment

    def submit_receipt(self, payment, receipt_image=None, reference='', card_last_four=''):
        payment.status = 'submitted'
        if receipt_image:
            payment.receipt_image = receipt_image
        payment.transaction_reference = reference
        payment.card_last_four = card_last_four
        payment.save()
        
        # به‌روزرسانی وضعیت سفارش به رسید ثبت‌شده
        order = payment.order
        order.status = 'payment_submitted'
        order.save()
        return payment

    def verify_payment(self, payment, admin_user=None, notes=''):
        payment.status = 'verified'
        payment.verified_at = timezone.now()
        if notes:
            payment.admin_notes = notes
        payment.save()

        # تغییر خودکار وضعیت سفارش به تأییدشده
        order = payment.order
        order.status = 'confirmed'
        order.save()
        return payment
