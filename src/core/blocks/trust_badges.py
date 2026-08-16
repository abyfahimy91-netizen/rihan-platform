"""بلوک Trust Badges ایرانی (D-079 بخش ۶.۲)"""
from ..block_base import BaseBlock, BlockValidationError
from ..block_registry import register_block


@register_block
class TrustBadgesBlock(BaseBlock):
    block_type = 'trust_badges'
    display_name = 'نشان‌های اعتماد'
    description = 'Trust Badges ایرانی (پرداخت امن، گارانتی، ارسال، پشتیبانی)'
    icon = 'shield'
    category = 'action'
    is_system = True

    # Trust Badges استاندارد ایرانی (D-079 بخش ۶.۲)
    DEFAULT_BADGES = [
        {'id': 'secure_payment', 'text': 'پرداخت امن', 'icon': 'shield'},
        {'id': 'return_guarantee', 'text': 'گارانتی مرجوعی', 'icon': 'refresh'},
        {'id': 'safe_shipping', 'text': 'ارسال مطمئن', 'icon': 'truck'},
        {'id': 'phone_support', 'text': 'پشتیبانی تلفنی', 'icon': 'phone'},
    ]

    def render(self, context=None) -> str:
        badges = self.data.get('badges', self.DEFAULT_BADGES)
        html = '<div class="block-trust-badges">'
        for badge in badges:
            text = badge.get('text', '') if isinstance(badge, dict) else badge
            icon = badge.get('icon', 'shield') if isinstance(badge, dict) else 'shield'
            html += f'<div class="trust-badge trust-badge--{icon}">'
            html += f'<span class="trust-badge__icon">{icon}</span>'
            html += f'<span class="trust-badge__text">{text}</span>'
            html += '</div>'
        html += '</div>'
        return html

    def validate(self) -> bool:
        badges = self.data.get('badges', self.DEFAULT_BADGES)
        if not isinstance(badges, list):
            raise BlockValidationError("Trust badges must be a list")
        return True

    def get_schema(self) -> dict:
        return {
            'fields': [
                {'name': 'badges', 'type': 'badge_list', 'required': False,
                 'label': 'نشان‌ها', 'default': self.DEFAULT_BADGES},
            ]
        }
