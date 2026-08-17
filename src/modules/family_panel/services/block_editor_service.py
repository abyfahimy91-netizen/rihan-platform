"""
Block Editor Service برای ماژول family_panel
منطبق بر US-055: سیستم بلوک‌محور
"""
from __future__ import annotations

import logging
from typing import Dict, List, Optional, Tuple

from django.contrib.auth import get_user_model
from django.utils import timezone

from ..models import ProductContent
from ..interfaces.m14_interface import M14Interface
from .family_service import FamilyService

logger = logging.getLogger(__name__)

User = get_user_model()


class BlockEditorService:
    """
    سرویس ویرایشگر بلوک‌محور.
    
    منطبق بر US-055:
    - افزودن/حذف/ویرایش بلوک
    - تغییر ترتیب بلوک‌ها
    - ذخیره draft (خودکار)
    - پیش‌نمایش قبل از انتشار
    """
    
    @classmethod
    def get_or_create_content(
        cls,
        product_id: int,
        user=None
    ) -> ProductContent:
        """
        دریافت یا ایجاد محتوای محصول.
        
        Args:
            product_id: شناسه محصول
            user: کاربر (برای created_by)
            
        Returns:
            ProductContent
        """
        content, created = ProductContent.objects.get_or_create(
            product_id=product_id,
            status__in=['draft', 'published'],
            defaults={
                'status': 'draft',
                'created_by': user,
                'updated_by': user,
            }
        )
        
        if created:
            logger.info(f"Created ProductContent for product {product_id}")
        
        return content
    
    @classmethod
    def add_block(
        cls,
        product_id: int,
        block_type: str,
        data: dict,
        user=None,
        order: int = None
    ) -> Tuple[bool, str, Optional[dict]]:
        """
        افزودن بلوک جدید.
        
        Args:
            product_id: شناسه محصول
            block_type: نوع بلوک
            data: داده‌های بلوک
            user: کاربر
            order: ترتیب (اختیاری)
            
        Returns:
            (success, message, block)
        """
        # اعتبارسنجی نوع بلوک
        valid_types = M14Interface.get_block_types()
        if block_type not in valid_types:
            return False, f"نوع بلوک '{block_type}' معتبر نیست", None
        
        # اعتبارسنجی داده‌ها
        is_valid, error = M14Interface.validate_block_data(block_type, data)
        if not is_valid:
            return False, error, None
        
        # دریافت یا ایجاد محتوا
        content = cls.get_or_create_content(product_id, user)
        
        # افزودن بلوک
        block = content.add_block(block_type, data, order)
        content.updated_by = user
        content.save()
        
        # ثبت لاگ
        if user:
            FamilyService.log_activity(
                user=user,
                action='product_update',
                description=f"افزودن بلوک {block_type} به محصول {product_id}",
                entity_type='product',
                entity_id=str(product_id),
            )
        
        logger.info(f"Added block {block_type} to product {product_id}")
        return True, "بلوک اضافه شد", block
    
    @classmethod
    def update_block(
        cls,
        product_id: int,
        block_id: str,
        data: dict,
        user=None
    ) -> Tuple[bool, str]:
        """
        به‌روزرسانی بلوک.
        
        Returns:
            (success, message)
        """
        try:
            content = ProductContent.objects.get(
                product_id=product_id,
                status__in=['draft', 'published']
            )
        except ProductContent.DoesNotExist:
            return False, "محتوای محصول یافت نشد"
        
        block = content.get_block(block_id)
        if not block:
            return False, "بلوک یافت نشد"
        
        # اعتبارسنجی داده‌های جدید
        is_valid, error = M14Interface.validate_block_data(block['type'], data)
        if not is_valid:
            return False, error
        
        content.update_block(block_id, data)
        content.updated_by = user
        content.save()
        
        logger.info(f"Updated block {block_id} in product {product_id}")
        return True, "بلوک به‌روز شد"
    
    @classmethod
    def remove_block(
        cls,
        product_id: int,
        block_id: str,
        user=None
    ) -> Tuple[bool, str]:
        """
        حذف بلوک.
        
        Returns:
            (success, message)
        """
        try:
            content = ProductContent.objects.get(
                product_id=product_id,
                status__in=['draft', 'published']
            )
        except ProductContent.DoesNotExist:
            return False, "محتوای محصول یافت نشد"
        
        if content.remove_block(block_id):
            content.updated_by = user
            content.save()
            logger.info(f"Removed block {block_id} from product {product_id}")
            return True, "بلوک حذف شد"
        
        return False, "بلوک یافت نشد"
    
    @classmethod
    def reorder_blocks(
        cls,
        product_id: int,
        block_ids: List[str],
        user=None
    ) -> Tuple[bool, str]:
        """
        تغییر ترتیب بلوک‌ها (drag & drop).
        
        Args:
            product_id: شناسه محصول
            block_ids: لیست IDهای بلوک به ترتیب جدید
            
        Returns:
            (success, message)
        """
        try:
            content = ProductContent.objects.get(
                product_id=product_id,
                status__in=['draft', 'published']
            )
        except ProductContent.DoesNotExist:
            return False, "محتوای محصول یافت نشد"
        
        if content.reorder_blocks(block_ids):
            content.updated_by = user
            content.save()
            logger.info(f"Reordered blocks in product {product_id}")
            return True, "ترتیب بلوک‌ها به‌روز شد"
        
        return False, "خطا در تغییر ترتیب بلوک‌ها"
    
    @classmethod
    def get_blocks(cls, product_id: int) -> List[Dict]:
        """دریافت لیست بلوک‌های محصول"""
        try:
            content = ProductContent.objects.get(
                product_id=product_id,
                status__in=['draft', 'published']
            )
            return content.blocks or []
        except ProductContent.DoesNotExist:
            return []
    
    @classmethod
    def preview_product(cls, product_id: int) -> Dict:
        """
        پیش‌نمایش محصول (قبل از انتشار).
        
        Returns:
            dict با HTML بلوک‌ها
        """
        blocks = cls.get_blocks(product_id)
        
        rendered_blocks = []
        for block in sorted(blocks, key=lambda b: b.get('order', 0)):
            html = M14Interface.render_block(block['type'], block['data'])
            rendered_blocks.append({
                'id': block['id'],
                'type': block['type'],
                'order': block.get('order', 0),
                'html': html,
            })
        
        return {
            'product_id': product_id,
            'blocks_count': len(rendered_blocks),
            'blocks': rendered_blocks,
        }
    
    @classmethod
    def publish_product(
        cls,
        product_id: int,
        user=None
    ) -> Tuple[bool, str]:
        """
        انتشار محصول.
        
        Returns:
            (success, message)
        """
        try:
            content = ProductContent.objects.get(
                product_id=product_id,
                status='draft'
            )
        except ProductContent.DoesNotExist:
            return False, "پیش‌نویس یافت نشد"
        
        if content.blocks_count == 0:
            return False, "محصول باید حداقل یک بلوک داشته باشد"
        
        content.status = 'published'
        content.published_at = timezone.now()
        content.updated_by = user
        content.save()
        
        # ثبت لاگ
        if user:
            FamilyService.log_activity(
                user=user,
                action='product_update',
                description=f"انتشار محصول {product_id}",
                entity_type='product',
                entity_id=str(product_id),
            )
        
        logger.info(f"Published product {product_id}")
        return True, "محصول منتشر شد"
    
    @classmethod
    def save_draft(
        cls,
        product_id: int,
        blocks: List[Dict],
        user=None
    ) -> Tuple[bool, str]:
        """
        ذخیره خودکار draft.
        
        Args:
            product_id: شناسه محصول
            blocks: لیست کامل بلوک‌ها
            
        Returns:
            (success, message)
        """
        content = cls.get_or_create_content(product_id, user)
        content.blocks = blocks
        content.status = 'draft'
        content.updated_by = user
        content.save()
        
        logger.info(f"Saved draft for product {product_id}")
        return True, "پیش‌نویس ذخیره شد"
