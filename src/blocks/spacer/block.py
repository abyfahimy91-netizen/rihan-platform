"""بلوک spacer"""
from ..base import BlockInterface

class SpacerBlock(BlockInterface):
    @property
    def block_type(self) -> str:
        return "spacer"
    
    @property
    def template_name(self) -> str:
        return f"blocks/spacer/template.html"
    
    def render(self, context: dict) -> str:
        # TODO: پیاده‌سازی
        pass
    
    def validate(self, data: dict) -> bool:
        # TODO: اعتبارسنجی
        pass
