"""بلوک لینک (D-079 بخش ۳.۱)"""
from ..block_base import BaseBlock, BlockValidationError
from ..block_registry import register_block


@register_block
class LinkBlock(BaseBlock):
    block_type = 'link'
    display_name = 'لینک'
    description = 'لینک با متن و target'
    icon = 'link'
    category = 'content'

    VALID_TARGETS = ['_self', '_blank']

    def render(self, context=None) -> str:
        text = self.data.get('text', '')
        url = self.data.get('url', '')
        target = self.data.get('target', '_self')
        return f'<a href="{url}" target="{target}" class="block-link">{text}</a>'

    def validate(self) -> bool:
        if 'url' not in self.data or not self.data['url']:
            raise BlockValidationError("بلوک پیوند به فیلد نشانی نیاز دارد")
        if 'text' not in self.data or not self.data['text']:
            raise BlockValidationError("بلوک پیوند به فیلد متن نیاز دارد")
        target = self.data.get('target', '_self')
        if target not in self.VALID_TARGETS:
            raise BlockValidationError(f"مقدار هدف پیوند نامعتبر است: {target}")
        return True

    def get_schema(self) -> dict:
        return {
            'fields': [
                {'name': 'text', 'type': 'text', 'required': True, 'label': 'متن لینک'},
                {'name': 'url', 'type': 'url', 'required': True, 'label': 'آدرس'},
                {'name': 'target', 'type': 'select', 'required': False, 'label': 'باز شدن در',
                 'options': self.VALID_TARGETS, 'default': '_self'},
            ]
        }
