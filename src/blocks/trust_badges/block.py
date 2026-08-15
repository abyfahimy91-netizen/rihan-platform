"""بلوک trust_badges"""
from ..base import BlockInterface

class TrustBadgesBlock(BlockInterface):
    @property
    def block_type(self) -> str:
        return "trust_badges"
    
    @property
    def template_name(self) -> str:
        return f"blocks/trust_badges/template.html"
    
    def render(self, context: dict) -> str:
        # TODO: پیاده‌سازی
        pass
    
    def validate(self, data: dict) -> bool:
        # TODO: اعتبارسنجی
        pass
