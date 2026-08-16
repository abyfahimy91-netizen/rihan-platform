"""
Base Block Interface ریهان
===========================
Interface مشترک برای تمام بلوک‌ها (D-079 بخش ۸.۲)

هر بلوک باید:
- از BaseBlock ارث‌بری کند
- متد render() را پیاده‌سازی کند
- متد validate() را پیاده‌سازی کند
- متد get_schema() را پیاده‌سازی کند
"""
from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class BlockValidationError(Exception):
    """خطای اعتبارسنجی بلوک"""
    pass


class BaseBlock(ABC):
    """
    کلاس پایه برای تمام بلوک‌ها.
    
    هر بلوک باید این interface را پیاده‌سازی کند:
    - render(): تبدیل داده به HTML
    - validate(): اعتبارسنجی داده‌ها
    - get_schema(): تعریف فیلدهای بلوک (برای فرم ادمین)
    """

    # متغیرهای کلاسی که باید در هر بلوک تعریف شوند
    block_type: str = ''           # نوع بلوک (مثلاً 'text')
    display_name: str = ''         # نام نمایشی (مثلاً 'متن آزاد')
    description: str = ''          # توضیح کوتاه
    icon: str = ''                 # آیکون (برای UI ادمین)
    category: str = 'content'      # دسته‌بندی (content, media, layout, action)
    is_system: bool = False        # بلوک سیستمی (غیرقابل حذف)

    def __init__(self, data: Dict[str, Any], config: Optional[Dict] = None):
        """
        Args:
            data: داده‌های بلوک (از دیتابیس)
            config: تنظیمات اضافی (اختیاری)
        """
        self.data = data or {}
        self.config = config or {}
        self._validated = False

    @abstractmethod
    def render(self, context: Optional[Dict] = None) -> str:
        """
        تبدیل داده بلوک به HTML.
        
        Args:
            context: context اضافی برای render (مثلاً product, user)
            
        Returns:
            HTML string
        """
        pass

    @abstractmethod
    def validate(self) -> bool:
        """
        اعتبارسنجی داده‌های بلوک.
        
        Returns:
            True اگر معتبر باشد
            
        Raises:
            BlockValidationError: اگر نامعتبر باشد
        """
        pass

    @abstractmethod
    def get_schema(self) -> Dict[str, Any]:
        """
        تعریف schema فیلدهای بلوک (برای ساخت فرم ادمین).
        
        Returns:
            dict با ساختار:
            {
                'fields': [
                    {'name': 'content', 'type': 'richtext', 'required': True, 'label': 'متن'},
                    ...
                ]
            }
        """
        pass

    def get_data(self) -> Dict[str, Any]:
        """دریافت داده‌های بلوک"""
        return self.data

    def set_data(self, data: Dict[str, Any]) -> None:
        """تنظیم داده‌های بلوک"""
        self.data = data or {}
        self._validated = False

    def is_valid(self) -> bool:
        """بررسی معتبر بودن (با cache)"""
        if not self._validated:
            try:
                self._validated = self.validate()
            except BlockValidationError:
                self._validated = False
        return self._validated

    def to_dict(self) -> Dict[str, Any]:
        """تبدیل بلوک به dict (برای ذخیره در دیتابیس)"""
        return {
            'block_type': self.block_type,
            'data': self.data,
            'config': self.config,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'BaseBlock':
        """ساخت بلوک از dict"""
        return cls(data.get('data', {}), data.get('config', {}))

    def __repr__(self) -> str:
        return f"<{self.__class__.__name__} type={self.block_type!r}>"


class SimpleBlock(BaseBlock):
    """
    بلوک ساده با render پیش‌فرض.
    برای بلوک‌هایی که فقط یک فیلد اصلی دارند.
    """

    # فیلد اصلی بلوک (در子类 تعریف می‌شود)
    main_field: str = 'content'

    def validate(self) -> bool:
        """اعتبارسنجی ساده: فیلد اصلی باید وجود داشته باشد"""
        if self.main_field not in self.data:
            raise BlockValidationError(
                f"Block '{self.block_type}' requires field '{self.main_field}'"
            )
        return True

    def get_schema(self) -> Dict[str, Any]:
        """Schema پیش‌فرض با یک فیلد"""
        return {
            'fields': [
                {
                    'name': self.main_field,
                    'type': 'text',
                    'required': True,
                    'label': self.display_name,
                }
            ]
        }
