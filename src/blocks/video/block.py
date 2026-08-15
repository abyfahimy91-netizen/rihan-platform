"""بلوک video"""
from ..base import BlockInterface

class VideoBlock(BlockInterface):
    @property
    def block_type(self) -> str:
        return "video"
    
    @property
    def template_name(self) -> str:
        return f"blocks/video/template.html"
    
    def render(self, context: dict) -> str:
        # TODO: پیاده‌سازی
        pass
    
    def validate(self, data: dict) -> bool:
        # TODO: اعتبارسنجی
        pass
