"""
بلوک‌های استاندارد ریهان (D-079 بخش ۳.۱)

۱۲ نوع بلوک:
1. text - متن آزاد
2. heading - عنوان
3. image - عکس
4. gallery - گالری عکس
5. video - ویدیو
6. link - لینک
7. quote - نقل قول
8. table - جدول
9. spacer - فاصله‌گذار
10. cta - دکمه اقدام
11. trust_badges - Trust Badges
12. related_products - محصولات مرتبط
"""
from .text import TextBlock
from .heading import HeadingBlock
from .image import ImageBlock
from .gallery import GalleryBlock
from .video import VideoBlock
from .link import LinkBlock
from .quote import QuoteBlock
from .table import TableBlock
from .spacer import SpacerBlock
from .cta import CTABlock
from .trust_badges import TrustBadgesBlock
from .related_products import RelatedProductsBlock

__all__ = [
    'TextBlock',
    'HeadingBlock',
    'ImageBlock',
    'GalleryBlock',
    'VideoBlock',
    'LinkBlock',
    'QuoteBlock',
    'TableBlock',
    'SpacerBlock',
    'CTABlock',
    'TrustBadgesBlock',
    'RelatedProductsBlock',
]
