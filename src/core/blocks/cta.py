"""بلوک دکمه اقدام (D-079 بخش ۳.۱)"""
from ..block_base import BaseBlock, BlockValidationError
from ..block_registry import register_block


@register_block
class CTABlock(BaseBlock):
    block_type = 'cta'
    display_name = 'دکمه اقدام'
    description = 'دکمه CTA باوقار (مطابق D-079 بخش ۳.۳)'
    icon = 'cta'
    category = 'action'

    def render(self, context=None) -> str:
        text = self.data.get('text', '')
        action = self.data.get('action', '')
        # مطابق D-079: CTA باوقار، نه پرخاشگر
        return f'<button class="block-cta" data-action="{action}">{text}</button>'

    def validate(self) -> bool:
        if 'text' not in self.data or not self.data['text']:
            raise BlockValidationError("بلوک فراخوان به فیلد متن نیاز دارد")
        if 'action' not in self.data or not self.data['action']:
            raise BlockValidationError("بلوک فراخوان به فیلد اقدام نیاز دارد")
        return True

    def get_schema(self) -> dict:
        return {
            'fields': [
                {'name': 'text', 'type': 'text', 'required': True, 'label': 'متن دکمه'},
                {'name': 'action', 'type': 'text', 'required': True, 'label': 'اقدام',
                 'help': 'مثال: add_to_cart, view_product'},
            ]
        }
