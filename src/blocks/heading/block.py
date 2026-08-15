"""بلوک heading"""
from ..base import BlockInterface

class HeadingBlock(BlockInterface):
    @property
    def block_type(self) -> str:
        return "heading"
    
    @property
    def template_name(self) -> str:
        return f"blocks/heading/template.html"
    
    def render(self, context: dict) -> str:
        # TODO: پیاده‌سازی
        pass
    
    def validate(self, data: dict) -> bool:
        # TODO: اعتبارسنجی
        pass
