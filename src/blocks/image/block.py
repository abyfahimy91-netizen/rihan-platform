"""بلوک image"""
from ..base import BlockInterface

class ImageBlock(BlockInterface):
    @property
    def block_type(self) -> str:
        return "image"
    
    @property
    def template_name(self) -> str:
        return f"blocks/image/template.html"
    
    def render(self, context: dict) -> str:
        # TODO: پیاده‌سازی
        pass
    
    def validate(self, data: dict) -> bool:
        # TODO: اعتبارسنجی
        pass
