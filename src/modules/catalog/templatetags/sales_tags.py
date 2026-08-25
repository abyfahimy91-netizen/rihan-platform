"""تگ‌های قالب صفحه فروش — D-104"""
from django import template
from django.utils.safestring import mark_safe

from src.modules.pages.markup import render_page_markup

register = template.Library()


@register.filter
def render_markup(value):
    """رندر متن ساختارمند ادمین به HTML امن (قواعد: # تیتر، - فهرست، ۱. شماره‌ای، > نقل‌قول)

    خروجی markup.py قبلاً به‌صورت امن escape شده است؛ باید SafeString برگردد تا
    اتواسکیپ جنگو آن را دوباره تبدیل به متن نکند (باگ نمایش خام <ul class="pm-list">).
    """
    return mark_safe(render_page_markup(value))
