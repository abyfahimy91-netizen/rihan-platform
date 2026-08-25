"""
فرم‌های پنل تامین‌کننده (D-105): ثبت شرکت حمل + کد رهگیری
ارقام فارسی خودکار به لاتین تبدیل می‌شود تا تایپی از موبایل هم قبول شود.
"""
from django import forms

from src.modules.order.models import Shipment
from src.modules.order.fulfillment import normalize_tracking_code


class TrackingCodeForm(forms.Form):
    """فرم ثبت کد رهگیری مرسوله"""

    carrier = forms.ChoiceField(
        label='شرکت حمل',
        choices=Shipment.Carrier.choices,
        initial=Shipment.Carrier.POST,
        widget=forms.Select(attrs={'class': 'form-control'}),
    )

    tracking_code = forms.CharField(
        label='کد رهگیری',
        max_length=40,
        min_length=5,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'کد رهگیری مرسوله را وارد کنید',
            'dir': 'ltr',
            'inputmode': 'latin',
            'autocomplete': 'off',
        }),
        help_text='کد رهگیری روی رسید پست/باربری — ارقام فارسی هم قبول است',
    )

    def clean_tracking_code(self):
        code = normalize_tracking_code(self.cleaned_data['tracking_code'])
        if len(code) < 5:
            raise forms.ValidationError('کد رهگیری معتبر نیست (حداقل ۵ نویسه حروف/اعداد).')
        return code
