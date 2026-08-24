"""
فیلترهای قالبی فارسی ریحان

استفاده در قالب‌ها:
    {% load fa_tags %}
    {{ order.total_price|money }}          <- ۱۸۰٬۰۰۰
    {{ product.final_price|fa }}           <- تبدیل ارقام
    {{ order.created_at|jdate }}           <- ۱۴۰۵/۰۶/۰۱
    {{ order.created_at|jtime }}           <- ۱۴۰۵/۰۶/۰۱ - ۱۴:۲۵
    {{ order.created_at|jdate_human }}     <- ۱ شهریور ۱۴۰۵
"""
from django import template

from src.core.fa import (
    fa_digits,
    money,
    jalali_date,
    jalali_datetime_str,
    jalali_human,
)

register = template.Library()


@register.filter(name="fa")
def fa_filter(value):
    return fa_digits(value)


@register.filter(name="money")
def money_filter(value):
    return money(value)


@register.filter(name="jdate")
def jdate_filter(value):
    return jalali_date(value)


@register.filter(name="jtime")
def jtime_filter(value):
    return jalali_datetime_str(value)


@register.filter(name="jdate_human")
def jdate_human_filter(value):
    return jalali_human(value)
