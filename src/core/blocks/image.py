"""بلوک عکس (D-079 بخش ۳.۱)"""
from ..block_base import BaseBlock, BlockValidationError
from ..block_registry import register_block


@register_block
class ImageBlock(BaseBlock):
    block_type = 'image'
    display_name = 'عکس'
    description = 'عکس با alt text و caption'
    icon = 'image'
    category = 'media'

    def render(self, context=None) -> str:
        image_url = self.data.get('image', '')
        alt = self.data.get('alt_text', '')
        caption = self.data.get('caption', '')
        width = self.data.get('width', 'full')

        html = f'<figure class="block-image block-image--{width}">'
        html += f'<img src="{image_url}" alt="{alt}" loading="lazy">'
        if caption:
            html += f'<figcaption>{caption}</figcaption>'
        html += '</figure>'
        return html

    def validate(self) -> bool:
        if 'image' not in self.data or not self.data['image']:
            raise BlockValidationError("بلوک تصویر به فیلد عکس نیاز دارد")
        return True

    def get_schema(self) -> dict:
        return {
            'fields': [
                {'name': 'image', 'type': 'image', 'required': True, 'label': 'عکس'},
                {'name': 'alt_text', 'type': 'text', 'required': True, 'label': 'متن جایگزین'},
                {'name': 'caption', 'type': 'text', 'required': False, 'label': 'زیرنویس'},
                {'name': 'width', 'type': 'select', 'required': False, 'label': 'عرض',
                 'options': ['full', 'medium', 'small'], 'default': 'full'},
            ]
        }
