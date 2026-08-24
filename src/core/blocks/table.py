"""بلوک جدول (D-079 بخش ۳.۱)"""
from ..block_base import BaseBlock, BlockValidationError
from ..block_registry import register_block


@register_block
class TableBlock(BaseBlock):
    block_type = 'table'
    display_name = 'جدول'
    description = 'جدول با ردیف‌ها و سربرگ'
    icon = 'table'
    category = 'content'

    def render(self, context=None) -> str:
        rows = self.data.get('rows', [])
        header_row = self.data.get('header_row', True)

        html = '<table class="block-table">'
        for i, row in enumerate(rows):
            tag = 'th' if (i == 0 and header_row) else 'td'
            html += '<tr>'
            for cell in row:
                html += f'<{tag}>{cell}</{tag}>'
            html += '</tr>'
        html += '</table>'
        return html

    def validate(self) -> bool:
        rows = self.data.get('rows', [])
        if not rows or not isinstance(rows, list):
            raise BlockValidationError("بلوک جدول به فهرست ردیف‌ها نیاز دارد")
        # بررسی یکسان بودن تعداد ستون‌ها
        if len(rows) > 1:
            first_len = len(rows[0])
            for row in rows[1:]:
                if len(row) != first_len:
                    raise BlockValidationError("همه ردیف‌ها باید تعداد ستون‌های یکسان داشته باشند")
        return True

    def get_schema(self) -> dict:
        return {
            'fields': [
                {'name': 'rows', 'type': 'table', 'required': True, 'label': 'ردیف‌ها'},
                {'name': 'header_row', 'type': 'checkbox', 'required': False,
                 'label': 'ردیف اول سربرگ است', 'default': True},
            ]
        }
