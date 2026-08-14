from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.views.decorators.http import require_POST
from apps.orders.models import Order
from .models import Payment
from .gateways.card_to_card import CardToCardGateway

@require_POST
def upload_receipt_view(request, order_number):
    order = get_object_or_404(Order, order_number=order_number)
    gw = CardToCardGateway()
    payment = gw.initiate_payment(order)

    receipt_file = request.FILES.get('receipt_image')
    reference = request.POST.get('reference', '').strip()
    card_last_four = request.POST.get('card_last_four', '').strip()

    if receipt_file or reference:
        gw.submit_receipt(
            payment=payment,
            receipt_image=receipt_file,
            reference=reference,
            card_last_four=card_last_four
        )
        messages.success(request, "رسید واریزی شما با موفقیت ثبت شد و در حال بررسی توسط مدیریت است.")
    else:
        messages.error(request, "لطفاً تصویر فیش یا شماره پیگیری تراکنش را وارد فرمایید.")

    return redirect('order_success', order_number=order_number)
