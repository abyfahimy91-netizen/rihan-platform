"""
Standard Blocks for Rihan (D-079 Section 3.1)

12 block types:
1. text - Free text
2. heading - Heading
3. image - Image
4. gallery - Image gallery
5. video - Video
6. link - Link
7. quote - Quote
8. table - Table
9. spacer - Spacer
10. cta - Call to action button
11. trust_badges - Trust badges
12. related_products - Related products
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

# Auto-register all blocks in block_registry
def register_all_blocks():
    """Register all standard blocks in block_registry"""
    from src.core.block_registry import block_registry
    
    blocks = [
        TextBlock,
        HeadingBlock,
        ImageBlock,
        GalleryBlock,
        VideoBlock,
        LinkBlock,
        QuoteBlock,
        TableBlock,
        SpacerBlock,
        CTABlock,
        TrustBadgesBlock,
        RelatedProductsBlock,
    ]
    
    registered_count = 0
    for block_class in blocks:
        try:
            block_registry.register(block_class)
            registered_count += 1
        except ValueError:
            # Already registered
            pass
        except Exception as e:
            import logging
            logger = logging.getLogger(__name__)
            logger.error(f"Failed to register {block_class.__name__}: {e}")
    
    return registered_count

# Auto-register when module is imported
try:
    register_all_blocks()
except Exception:
    # Silently fail during initial import
    pass

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
    'register_all_blocks',
]
