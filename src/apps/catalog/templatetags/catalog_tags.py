from django import template
from django.utils.safestring import mark_safe
from django.template.loader import render_to_string

register = template.Library()


@register.simple_tag
def render_content_block(block):
    """Render یک بلوک محتوایی"""
    try:
        template_name = block.get_template_name()
        context = block.get_context()
        return mark_safe(render_to_string(template_name, context))
    except Exception as e:
        return mark_safe(f'<div class="error">خطا در rendering بلوک: {e}</div>')


@register.simple_tag
def render_product_blocks(product):
    """Render همه بلوک‌های یک محصول"""
    blocks = product.content_blocks.filter(is_active=True).order_by('sort_order')
    html_parts = []
    
    for block in blocks:
        try:
            template_name = block.get_template_name()
            context = block.get_context()
            html_parts.append(render_to_string(template_name, context))
        except Exception as e:
            html_parts.append(f'<div class="error">خطا در rendering بلوک: {e}</div>')
    
    return mark_safe(''.join(html_parts))


@register.filter
def block_type_icon(block_type):
    """آیکون برای هر نوع بلوک"""
    icons = {
        'text': '📝',
        'heading': '📌',
        'image': '🖼️',
        'gallery': '🖼️🖼️',
        'video': '🎥',
        'link': '🔗',
        'quote': '💬',
        'table': '📊',
        'spacer': '⬜',
        'cta': '👆',
        'trust_badges': '✅',
        'related_products': '🛍️',
    }
    return icons.get(block_type, '❓')
