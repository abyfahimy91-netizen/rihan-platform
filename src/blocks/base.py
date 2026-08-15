"""
پایه مشترک همه بلوک‌های ریهان

هر بلوک باید این interface را پیاده‌سازی کند.
"""
from abc import ABC, abstractmethod

class BlockInterface(ABC):
    """رابط مشترک همه بلوک‌ها"""
    
    @property
    @abstractmethod
    def block_type(self) -> str:
        """نوع بلوک (مثلاً 'text', 'image')"""
        pass
    
    @property
    @abstractmethod
    def template_name(self) -> str:
        """مسیر template بلوک"""
        pass
    
    @abstractmethod
    def render(self, context: dict) -> str:
        """رندر بلوک با context داده‌شده"""
        pass
    
    @abstractmethod
    def validate(self, data: dict) -> bool:
        """اعتبارسنجی داده‌های بلوک"""
        pass
