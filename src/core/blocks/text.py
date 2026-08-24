"""بلوک متن آزاد (D-079 بخش ۳.۱)"""
from ..block_base import BaseBlock, BlockValidationError
from ..block_registry import register_block


@register_block
class TextBlock(BaseBlock):
    block_type = 'text'
    display_name = 'متن آزاد'
    description = 'متن آزاد با پشتیبانی از Rich Text'
    icon = 'text'
    category = 'content'

    def render(self, context=None) -> str:
        content = self.data.get('content', '')
        return f'<div class="block-text">{content}</div>'

    def validate(self) -> bool:
        if 'content' not in self.data or not self.data['content']:
            raise BlockValidationError("بلوک متن به فیلد محتوا نیاز دارد")
        return True

    def get_schema(self) -> dict:
        return {
            'fields': [
                {'name': 'content', 'type': 'richtext', 'required': True, 'label': 'متن'},
            ]
        }
