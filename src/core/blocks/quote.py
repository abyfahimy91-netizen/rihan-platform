"""بلوک نقل قول (D-079 بخش ۳.۱)"""
from ..block_base import BaseBlock, BlockValidationError
from ..block_registry import register_block


@register_block
class QuoteBlock(BaseBlock):
    block_type = 'quote'
    display_name = 'نقل قول'
    description = 'نقل قول با نام گوینده'
    icon = 'quote'
    category = 'content'

    def render(self, context=None) -> str:
        quote = self.data.get('quote', '')
        author = self.data.get('author', '')
        html = f'<blockquote class="block-quote">'
        html += f'<p>{quote}</p>'
        if author:
            html += f'<cite>— {author}</cite>'
        html += '</blockquote>'
        return html

    def validate(self) -> bool:
        if 'quote' not in self.data or not self.data['quote']:
            raise BlockValidationError("بلوک نقل‌قول به فیلد نقل‌قول نیاز دارد")
        return True

    def get_schema(self) -> dict:
        return {
            'fields': [
                {'name': 'quote', 'type': 'textarea', 'required': True, 'label': 'متن نقل قول'},
                {'name': 'author', 'type': 'text', 'required': False, 'label': 'نام گوینده'},
            ]
        }
