"""
فرم‌های پنل تأمین‌کننده (D-105 + D-111): ثبت شرکت حمل + کد رهگیری
- ارقام فارسی خودکار به لاتین تبدیل می‌شود تا تایپی از موبایل هم قبول شود.
- D-111: کد رهگیری با فرمت استاندارد هر شرکت حمل اعتبارسنجی می‌شود:
  پست ۲۰-۲۴ رقم / تیپاکس ۱۵-۲۵ رقم / چاپار ۱۴ رقم / سایر اختیاری
- D-111: برای «سایر» نام شرکت، نام ارسال‌کننده و شماره تماس الزامی است
  (همین‌ها به مشتری در پروفایل نمایش داده می‌شود).
"""
from django import forms

from src.modules.order.models import Shipment
from src.modules.order.fulfillment import (
    FulfillmentError,
    carrier_code_hint,
    normalize_tracking_code,
    validate_tracking_code,
)

# راهنمای هر شرکت حمل — در قالب با JS زیر فیلد نمایش داده می‌شود
CARRIER_HINTS = {value: carrier_code_hint(value) for value, _ in Shipment.Carrier.choices}


class TrackingCodeForm(forms.Form):
    """فرم ثبت کد رهگیری مرسوله (+ جزئیات شرکت حمل «سایر»)"""

    carrier = forms.ChoiceField(
        label='شرکت حمل',
        choices=Shipment.Carrier.choices,
        initial=Shipment.Carrier.POST,
        widget=forms.Select(attrs={'class': 'form-control', 'id': 'id_carrier'}),
    )

    tracking_code = forms.CharField(
        label='کد رهگیری',
        max_length=40,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'کد رهگیری مرسوله را وارد کنید',
            'dir': 'ltr',
            'inputmode': 'latin',
            'autocomplete': 'off',
        }),
        help_text='کد رهگیری روی رسید پست/باربری — ارقام فارسی هم قبول است',
    )

    other_carrier_name = forms.CharField(
        label='نام شرکت حمل / سرویس',
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'مثلاً: پیک موتوری رضایی، باربری سریع‌بار…',
        }),
    )
    other_carrier_person = forms.CharField(
        label='نام ارسال‌کننده / راننده',
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'مثلاً: علی رضایی',
        }),
    )
    other_carrier_phone = forms.CharField(
        label='شماره تماس حمل‌کننده',
        max_length=20,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': '09xxxxxxxxx',
            'dir': 'ltr',
            'inputmode': 'tel',
        }),
        help_text='این اطلاعات برای مشتری در پروفایل نمایش داده می‌شود',
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['carrier'].widget.attrs['data-hints'] = str(CARRIER_HINTS).replace("'", '"')

    def clean_tracking_code(self):
        code = normalize_tracking_code(self.cleaned_data.get('tracking_code') or '')
        carrier = self.cleaned_data.get('carrier')
        if carrier:
            try:
                return validate_tracking_code(carrier, code)
            except FulfillmentError as e:
                raise forms.ValidationError(str(e))
        if len(code) < 5:
            raise forms.ValidationError('کد رهگیری معتبر نیست (حداقل ۵ نویسه حروف/اعداد).')
        return code

    def clean(self):
        cleaned = super().clean()
        carrier = cleaned.get('carrier')
        if carrier == Shipment.Carrier.OTHER:
            for field, label in (
                ('other_carrier_name', 'نام شرکت حمل / سرویس'),
                ('other_carrier_person', 'نام ارسال‌کننده / راننده'),
                ('other_carrier_phone', 'شماره تماس حمل‌کننده'),
            ):
                if not (cleaned.get(field) or '').strip():
                    self.add_error(field, f'برای گزینه «سایر»، {label} الزامی است.')
        return cleaned
