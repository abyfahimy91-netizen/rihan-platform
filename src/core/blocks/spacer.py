"""بلوک فاصله‌گذار (D-079 بخش ۳.۱)"""
from ..block_base import BaseBlock, BlockValidationError
from ..block_registry import register_block


@register_block
class SpacerBlock(BaseBlock):
    block_type = 'spacer'
    display_name = 'فاصله‌گذار'
    description = 'فاصله عمودی small/medium/large'
    icon = 'spacer'
    category = 'layout'

    VALID_HEIGHTS = ['small', 'medium', 'large']
    HEIGHT_VALUES = {'small': '1rem', 'medium': '2rem', 'large': '4rem'}

    def render(self, context=None) -> str:
        height = self.data.get('height', 'medium')
        if height not in self.VALID_HEIGHTS:
            height = 'medium'
        value = self.HEIGHT_VALUES[height]
        return f'<div class="block-spacer" style="height: {value}"></div>'

    def validate(self) -> bool:
        height = self.data.get('height', 'medium')
        if height not in self.VALID_HEIGHTS:
            raise BlockValidationError(f"ارتفاع واردشده نامعتبر است: {height}")
        return True

    def get_schema(self) -> dict:
        return {
            'fields': [
                {'name': 'height', 'type': 'select', 'required': False, 'label': 'ارتفاع',
                 'options': self.VALID_HEIGHTS, 'default': 'medium'},
            ]
        }
