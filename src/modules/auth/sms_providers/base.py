"""
SmsProvider Interface
منطبق بر ADR-006 بخش ۶: Strategy Pattern
"""
from abc import ABC, abstractmethod
from typing import Optional


class SmsProvider(ABC):
    """
    Interface مشترک برای تمام SMS Providers.
    
    منطبق بر ADR-006:
    - Provider پیش‌فرض: Kavenegar
    - Provider ثانویه: فرازاس‌ام‌اس، اس‌ام‌اس.آی‌آر
    - حذف ManualSmsProvider
    """
    
    @property
    @abstractmethod
    def name(self) -> str:
        """نام Provider"""
        pass
    
    @abstractmethod
    def send_otp(self, phone: str, otp_code: str) -> bool:
        """
        ارسال OTP به شماره موبایل.
        
        Args:
            phone: شماره موبایل (فرمت ایرانی)
            otp_code: کد ۶ رقمی
            
        Returns:
            True اگر ارسال موفق بود
        """
        pass
    
    @abstractmethod
    def is_available(self) -> bool:
        """
        بررسی در دسترس بودن Provider.
        
        Returns:
            True اگر Provider در دسترس است
        """
        pass
