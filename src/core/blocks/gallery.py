"""بلوک گالری عکس (D-079 بخش ۳.۱)"""
from ..block_base import BaseBlock, BlockValidationError
from ..block_registry import register_block


@register_block
class GalleryBlock(BaseBlock):
    block_type = 'gallery'
    display_name = 'گالری عکس'
    description = 'گالری با چند عکس و تعداد ستون'
    icon = 'gallery'
    category = 'media'

    VALID_COLUMNS = [2, 3, 4]

    def render(self, context=None) -> str:
        images = self.data.get('images', [])
        columns = self.data.get('columns', 3)

        html = f'<div class="block-gallery block-gallery--cols-{columns}">'
        for img in images:
            url = img.get('url', '') if isinstance(img, dict) else img
            alt = img.get('alt', '') if isinstance(img, dict) else ''
            html += f'<img src="{url}" alt="{alt}" loading="lazy">'
        html += '</div>'
        return html

    def validate(self) -> bool:
        images = self.data.get('images', [])
        if not images or not isinstance(images, list):
            raise BlockValidationError("Gallery block requires 'images' list")
        columns = self.data.get('columns', 3)
        if columns not in self.VALID_COLUMNS:
            raise BlockValidationError(f"Invalid columns: {columns}")
        return True

    def get_schema(self) -> dict:
        return {
            'fields': [
                {'name': 'images', 'type': 'image_list', 'required': True, 'label': 'عکس‌ها'},
                {'name': 'columns', 'type': 'select', 'required': False, 'label': 'تعداد ستون',
                 'options': self.VALID_COLUMNS, 'default': 3},
            ]
        }
