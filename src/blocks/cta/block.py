"""بلوک cta"""
from ..base import BlockInterface

class CtaBlock(BlockInterface):
    @property
    def block_type(self) -> str:
        return "cta"
    
    @property
    def template_name(self) -> str:
        return f"blocks/cta/template.html"
    
    def render(self, context: dict) -> str:
        # TODO: پیاده‌سازی
        pass
    
    def validate(self, data: dict) -> bool:
        # TODO: اعتبارسنجی
        pass
