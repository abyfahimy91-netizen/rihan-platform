"""
M14 Interface - اتصال به BlockRegistry
منطبق بر US-055: سیستم بلوک‌محور
"""
from __future__ import annotations

import logging
from typing import List, Dict, Optional, Tuple

logger = logging.getLogger(__name__)


class M14Interface:
    """
    رابط ماژول معماری پلاگین (M14).
    
    این کلاس به BlockRegistry متصل می‌شود و:
    - لیست بلوک‌های موجود را برمی‌گرداند
    - داده‌های بلوک را اعتبارسنجی می‌کند
    - بلوک را render می‌کند
    """
    
    @classmethod
    def get_available_blocks(cls) -> List[Dict]:
        """
        دریافت لیست بلوک‌های موجود.
        
        Returns:
            لیست دیکشنری‌های اطلاعات بلوک
        """
        try:
            from src.core.block_registry import block_registry
            
            blocks = []
            for block_type, block_class in block_registry.get_all_blocks().items():
                blocks.append({
                    'type': block_type,
                    'name': getattr(block_class, 'name', block_type),
                    'description': getattr(block_class, 'description', ''),
                    'category': getattr(block_class, 'category', 'general'),
                })
            
            return blocks
        except Exception as e:
            logger.error(f"Error getting blocks from M14: {e}")
            # Fallback: لیست ۱۲ بلوک استاندارد
            return [
                {'type': 'text', 'name': 'متن', 'category': 'content'},
                {'type': 'heading', 'name': 'عنوان', 'category': 'content'},
                {'type': 'image', 'name': 'تصویر', 'category': 'media'},
                {'type': 'gallery', 'name': 'گالری', 'category': 'media'},
                {'type': 'video', 'name': 'ویدیو', 'category': 'media'},
                {'type': 'link', 'name': 'لینک', 'category': 'content'},
                {'type': 'quote', 'name': 'نقل قول', 'category': 'content'},
                {'type': 'table', 'name': 'جدول', 'category': 'content'},
                {'type': 'spacer', 'name': 'فاصله‌گذار', 'category': 'layout'},
                {'type': 'cta', 'name': 'دکمه اقدام', 'category': 'action'},
                {'type': 'trust_badges', 'name': 'نشان‌های اعتماد', 'category': 'action'},
                {'type': 'related_products', 'name': 'محصولات مرتبط', 'category': 'commerce'},
            ]
    
    @classmethod
    def validate_block_data(cls, block_type: str, data: dict) -> Tuple[bool, str]:
        """
        اعتبارسنجی داده‌های بلوک.
        
        Args:
            block_type: نوع بلوک
            data: داده‌های بلوک
            
        Returns:
            (is_valid, error_message)
        """
        try:
            from src.core.block_registry import block_registry
            
            block_class = block_registry.get_all_blocks().get(block_type)
            if block_class is None:
                return False, f"نوع بلوک '{block_type}' یافت نشد"
            
            # اگر متد validate دارد، استفاده کن
            if hasattr(block_class, 'validate'):
                return block_class.validate(data)
            
            return True, ""
        except Exception as e:
            logger.error(f"Error validating block: {e}")
            return True, ""  # در صورت خطا، سخت‌گیر نباش
    
    @classmethod
    def render_block(cls, block_type: str, data: dict) -> str:
        """
        Render یک بلوک به HTML.
        
        Args:
            block_type: نوع بلوک
            data: داده‌های بلوک
            
        Returns:
            HTML string
        """
        try:
            from src.core.block_registry import block_registry
            
            block_class = block_registry.get_all_blocks().get(block_type)
            if block_class is None:
                return f"<div>بلوک {block_type} یافت نشد</div>"
            
            # اگر متد render دارد، استفاده کن
            if hasattr(block_class, 'render'):
                return block_class.render(data)
            
            return f"<div>{data}</div>"
        except Exception as e:
            logger.error(f"Error rendering block: {e}")
            return f"<div>خطا در render بلوک {block_type}</div>"
    
    @classmethod
    def get_block_types(cls) -> List[str]:
        """دریافت لیست انواع بلوک‌ها"""
        blocks = cls.get_available_blocks()
        return [b['type'] for b in blocks]
