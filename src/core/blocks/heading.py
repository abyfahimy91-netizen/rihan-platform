"""بلوک عنوان (D-079 بخش ۳.۱)"""
from ..block_base import BaseBlock, BlockValidationError
from ..block_registry import register_block


@register_block
class HeadingBlock(BaseBlock):
    block_type = 'heading'
    display_name = 'عنوان'
    description = 'عنوان با سطح H2/H3/H4'
    icon = 'heading'
    category = 'content'

    VALID_LEVELS = ['h2', 'h3', 'h4']

    def render(self, context=None) -> str:
        text = self.data.get('text', '')
        level = self.data.get('level', 'h2')
        if level not in self.VALID_LEVELS:
            level = 'h2'
        return f'<{level} class="block-heading">{text}</{level}>'

    def validate(self) -> bool:
        if 'text' not in self.data or not self.data['text']:
            raise BlockValidationError("بلوک تیتر به فیلد متن نیاز دارد")
        level = self.data.get('level', 'h2')
        if level not in self.VALID_LEVELS:
            raise BlockValidationError(f"سطح تیتر نامعتبر است: {level}")
        return True

    def get_schema(self) -> dict:
        return {
            'fields': [
                {'name': 'text', 'type': 'text', 'required': True, 'label': 'متن عنوان'},
                {'name': 'level', 'type': 'select', 'required': False, 'label': 'سطح',
                 'options': self.VALID_LEVELS, 'default': 'h2'},
            ]
        }
