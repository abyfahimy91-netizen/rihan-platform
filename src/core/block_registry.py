"""
Block Registry ریهان
=====================
ثبت و مدیریت بلوک‌ها (D-079 بخش ۸.۲)

ویژگی‌ها:
- ثبت بلوک با type یکتا
- دریافت بلوک بر اساس type
- پشتیبانی از Feature Flag برای هر بلوک
- Isolation بین بلوک‌ها
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional, Type

from .block_base import BaseBlock

logger = logging.getLogger(__name__)


class BlockRegistry:
    """
    Registry مرکزی برای تمام بلوک‌ها.
    """

    _instance: Optional[BlockRegistry] = None
    _blocks: Dict[str, Type[BaseBlock]] = {}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    @classmethod
    def get_instance(cls) -> BlockRegistry:
        return cls()

    def register(self, block_class: Type[BaseBlock]) -> None:
        """
        ثبت یک کلاس بلوک.
        
        Args:
            block_class: کلاس بلوک (نه instance)
            
        Raises:
            ValueError: اگر block_type تکراری باشد
        """
        if not issubclass(block_class, BaseBlock):
            raise TypeError(f"{block_class} must be a subclass of BaseBlock")

        block_type = block_class.block_type
        if not block_type:
            raise ValueError(f"Block class {block_class.__name__} has no block_type")

        if block_type in self._blocks:
            raise ValueError(f"Block type '{block_type}' is already registered")

        self._blocks[block_type] = block_class
        logger.debug(f"Block registered: {block_type} ({block_class.__name__})")

    def unregister(self, block_type: str) -> bool:
        """لغو ثبت یک بلوک"""
        if block_type in self._blocks:
            del self._blocks[block_type]
            return True
        return False

    def get_block_class(self, block_type: str) -> Optional[Type[BaseBlock]]:
        """دریافت کلاس بلوک بر اساس type"""
        return self._blocks.get(block_type)

    def create_block(
        self,
        block_type: str,
        data: Dict,
        config: Optional[Dict] = None
    ) -> Optional[BaseBlock]:
        """
        ساخت instance بلوک.
        
        Args:
            block_type: نوع بلوک
            data: داده‌های بلوک
            config: تنظیمات اضافی
            
        Returns:
            BaseBlock instance یا None اگر type یافت نشد
        """
        block_class = self.get_block_class(block_type)
        if block_class is None:
            logger.warning(f"Unknown block type: {block_type}")
            return None
        return block_class(data, config)

    def get_all_blocks(self) -> Dict[str, Type[BaseBlock]]:
        """دریافت تمام بلوک‌های ثبت‌شده"""
        return dict(self._blocks)

    def get_block_types(self) -> List[str]:
        """دریافت لیست typeهای ثبت‌شده"""
        return list(self._blocks.keys())

    def get_blocks_by_category(self, category: str) -> List[Type[BaseBlock]]:
        """دریافت بلوک‌های یک دسته‌بندی"""
        return [
            b for b in self._blocks.values()
            if b.category == category
        ]

    def is_registered(self, block_type: str) -> bool:
        """بررسی ثبت‌شدن یک بلوک"""
        return block_type in self._blocks

    def clear(self) -> None:
        """پاکسازی کامل (فقط برای تست)"""
        self._blocks.clear()

    def get_stats(self) -> Dict:
        """آمار بلوک‌ها (برای admin panel)"""
        categories = {}
        for block in self._blocks.values():
            cat = block.category
            categories[cat] = categories.get(cat, 0) + 1

        return {
            'total_blocks': len(self._blocks),
            'categories': categories,
            'block_types': list(self._blocks.keys()),
        }


# نمونه سراسری
block_registry = BlockRegistry.get_instance()


def register_block(block_class: Type[BaseBlock]) -> Type[BaseBlock]:
    """
    Decorator برای ثبت بلوک.
    
    مثال:
        @register_block
        class TextBlock(SimpleBlock):
            block_type = 'text'
            ...
    """
    block_registry.register(block_class)
    return block_class
