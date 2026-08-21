"""
فرم‌های پنل تأمین‌کننده (M4)
منطبق بر US-029: ثبت کد رهگیری
"""
from django import forms


class TrackingCodeForm(forms.Form):
    """فرم ثبت کد رهگیری پست"""
    
    tracking_code = forms.CharField(
        label='کد رهگیری پست',
        max_length=50,
        min_length=10,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'کد رهگیری ۲۴ رقمی پست را وارد کنید',
            'dir': 'ltr',
        }),
        help_text='کد رهگیری مرسوله پستی را وارد کنید',
    )
    
    shipping_method = forms.ChoiceField(
        label='روش ارسال',
        choices=[
            ('post', 'پست پیشتاز'),
            ('tipax', 'تیپاکس'),
            ('courier', 'پیک'),
        ],
        initial='post',
        widget=forms.Select(attrs={'class': 'form-control'}),
    )
    
    def clean_tracking_code(self):
        code = self.cleaned_data['tracking_code'].strip()
        if not code.isalnum():
            raise forms.ValidationError('کد رهگیری فقط می‌تواند شامل حروف و اعداد باشد')
        return code
