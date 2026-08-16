"""بلوک محصولات مرتبط (D-079 بخش ۳.۱)"""
from ..block_base import BaseBlock, BlockValidationError
from ..block_registry import register_block


@register_block
class RelatedProductsBlock(BaseBlock):
    block_type = 'related_products'
    display_name = 'محصولات مرتبط'
    description = 'نمایش محصولات مرتبط با حداکثر تعداد'
    icon = 'products'
    category = 'action'

    def render(self, context=None) -> str:
        products = self.data.get('products', [])
        max_count = self.data.get('max_count', 4)

        html = f'<div class="block-related-products" data-max="{max_count}">'
        for product in products[:max_count]:
            name = product.get('name', '') if isinstance(product, dict) else product
            html += f'<div class="related-product">{name}</div>'
        html += '</div>'
        return html

    def validate(self) -> bool:
        max_count = self.data.get('max_count', 4)
        if not isinstance(max_count, int) or max_count < 1:
            raise BlockValidationError("max_count must be a positive integer")
        return True

    def get_schema(self) -> dict:
        return {
            'fields': [
                {'name': 'products', 'type': 'product_list', 'required': False, 'label': 'محصولات'},
                {'name': 'max_count', 'type': 'number', 'required': False,
                 'label': 'حداکثر تعداد', 'default': 4},
            ]
        }
