"""بلوک link"""
from ..base import BlockInterface

class LinkBlock(BlockInterface):
    @property
    def block_type(self) -> str:
        return "link"
    
    @property
    def template_name(self) -> str:
        return f"blocks/link/template.html"
    
    def render(self, context: dict) -> str:
        # TODO: پیاده‌سازی
        pass
    
    def validate(self, data: dict) -> bool:
        # TODO: اعتبارسنجی
        pass
