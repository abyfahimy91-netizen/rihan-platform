"""بلوک text"""
from ..base import BlockInterface

class TextBlock(BlockInterface):
    @property
    def block_type(self) -> str:
        return "text"
    
    @property
    def template_name(self) -> str:
        return f"blocks/text/template.html"
    
    def render(self, context: dict) -> str:
        # TODO: پیاده‌سازی
        pass
    
    def validate(self, data: dict) -> bool:
        # TODO: اعتبارسنجی
        pass
