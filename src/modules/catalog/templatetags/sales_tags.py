"""تگ‌های قالب صفحه فروش — D-104"""
from django import template

from src.modules.pages.markup import render_page_markup

register = template.Library()


@register.filter
def render_markup(value):
    """رندر متن ساختارمند ادمین به HTML امن (قواعد: # تیتر، - فهرست، ۱. شماره‌ای، > نقل‌قول)"""
    return render_page_markup(value)
