"""بلوک gallery"""
from ..base import BlockInterface

class GalleryBlock(BlockInterface):
    @property
    def block_type(self) -> str:
        return "gallery"
    
    @property
    def template_name(self) -> str:
        return f"blocks/gallery/template.html"
    
    def render(self, context: dict) -> str:
        # TODO: پیاده‌سازی
        pass
    
    def validate(self, data: dict) -> bool:
        # TODO: اعتبارسنجی
        pass
