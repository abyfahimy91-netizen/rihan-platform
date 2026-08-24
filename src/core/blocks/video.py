"""بلوک ویدیو (D-079 بخش ۳.۱)"""
from ..block_base import BaseBlock, BlockValidationError
from ..block_registry import register_block


@register_block
class VideoBlock(BaseBlock):
    block_type = 'video'
    display_name = 'ویدیو'
    description = 'ویدیو با poster و caption'
    icon = 'video'
    category = 'media'

    def render(self, context=None) -> str:
        video_url = self.data.get('video_url', '')
        video_file = self.data.get('video_file', '')
        poster = self.data.get('poster', '')
        caption = self.data.get('caption', '')

        source = video_url or video_file
        html = f'<figure class="block-video">'
        html += f'<video controls poster="{poster}" preload="metadata">'
        html += f'<source src="{source}">'
        html += '</video>'
        if caption:
            html += f'<figcaption>{caption}</figcaption>'
        html += '</figure>'
        return html

    def validate(self) -> bool:
        if not self.data.get('video_url') and not self.data.get('video_file'):
            raise BlockValidationError("بلوک ویدیو به نشانی یا فایل ویدیو نیاز دارد")
        return True

    def get_schema(self) -> dict:
        return {
            'fields': [
                {'name': 'video_file', 'type': 'video', 'required': False, 'label': 'فایل ویدیو'},
                {'name': 'video_url', 'type': 'url', 'required': False, 'label': 'لینک ویدیو'},
                {'name': 'poster', 'type': 'image', 'required': False, 'label': 'تصویر پوستر'},
                {'name': 'caption', 'type': 'text', 'required': False, 'label': 'زیرنویس'},
            ]
        }
