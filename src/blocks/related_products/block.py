"""بلوک related_products"""
from ..base import BlockInterface

class RelatedProductsBlock(BlockInterface):
    @property
    def block_type(self) -> str:
        return "related_products"
    
    @property
    def template_name(self) -> str:
        return f"blocks/related_products/template.html"
    
    def render(self, context: dict) -> str:
        # TODO: پیاده‌سازی
        pass
    
    def validate(self, data: dict) -> bool:
        # TODO: اعتبارسنجی
        pass
