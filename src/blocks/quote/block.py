"""بلوک quote"""
from ..base import BlockInterface

class QuoteBlock(BlockInterface):
    @property
    def block_type(self) -> str:
        return "quote"
    
    @property
    def template_name(self) -> str:
        return f"blocks/quote/template.html"
    
    def render(self, context: dict) -> str:
        # TODO: پیاده‌سازی
        pass
    
    def validate(self, data: dict) -> bool:
        # TODO: اعتبارسنجی
        pass
