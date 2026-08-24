"""
ابزارهای قالب‌بندی فارسی ریحان (Farsi formatting utilities)

قاعده پروژه: هر عدد و تاریخی که به کاربر نمایش داده می‌شود باید
با ارقام فارسی، جداکننده هزارگان و تقویم جلالی باشد.

توابع:
    fa_digits(value)          تبدیل ارقام لاتین به فارسی
    money(value)              مبلغ با جداکننده هزارگان + ارقام فارسی (۱۸۰٬۰۰۰)
    jalali_date(value)        تاریخ شمسی عددی (۱۴۰۵/۰۶/۰۱)
    jalali_datetime_str(v)    تاریخ و ساعت شمسی (۱۴۰۵/۰۶/۰۱ - ۱۴:۲۵)
    jalali_human(value)       تاریخ خوانای شمسی (۱ شهریور ۱۴۰۵)
"""
from datetime import date as _date, datetime as _datetime
from decimal import Decimal, InvalidOperation

import jdatetime

FA_DIGITS_MAP = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")
FA_THOUSANDS = "٬"
FA_DECIMAL = "٫"

JALALI_MONTHS = [
    "فروردین", "اردیبهشت",
    "خرداد", "تیر", "مرداد",
    "شهریور", "مهر", "آبان",
    "آذر", "دی", "بهمن", "اسفند",
]


def fa_digits(value):
    """تبدیل همه ارقام لاتین یک مقدار به ارقام فارسی"""
    if value is None:
        return ""
    s = str(value)
    s = s.translate(FA_DIGITS_MAP)
    s = s.replace(",", FA_THOUSANDS)
    return s


def money(value):
    """مبلغ با جداکننده هزارگان و ارقام فارسی - مثل ۱۸۰٬۰۰۰"""
    if value is None or value == "":
        return ""
    try:
        d = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return fa_digits(value)
    try:
        if d == d.to_integral_value():
            s = "{:,}".format(int(d))
        else:
            s = ("{:,}".format(d)).rstrip("0").rstrip(".")
    except Exception:
        return fa_digits(value)
    return fa_digits(s)


def to_jalali(value):
    """تبدیل تاریخ/زمان میلادی به جلالی - با منطقه زمانی تهران برای مقادیر aware"""
    if value is None or value == "":
        return None
    if isinstance(value, (jdatetime.datetime, jdatetime.date)):
        return value
    dt = value
    if isinstance(dt, _datetime) and dt.tzinfo is not None:
        try:
            from django.utils import timezone as dj_tz
            dt = dj_tz.localtime(dt)
        except Exception:
            pass
    if isinstance(dt, _datetime):
        return jdatetime.datetime.fromgregorian(datetime=dt)
    if isinstance(dt, _date):
        return jdatetime.date.fromgregorian(date=dt)
    return None


def _num_date(jd):
    return "{}/{:02d}/{:02d}".format(jd.year, jd.month, jd.day)


def jalali_date(value):
    """تاریخ شمسی عددی: ۱۴۰۵/۰۶/۰۱"""
    jd = to_jalali(value)
    if jd is None:
        return fa_digits(value) if value else ""
    return fa_digits(_num_date(jd))


def jalali_datetime_str(value):
    """تاریخ و ساعت شمسی: ۱۴۰۵/۰۶/۰۱ - ۱۴:۲۵"""
    jd = to_jalali(value)
    if jd is None:
        return fa_digits(value) if value else ""
    if isinstance(jd, jdatetime.datetime):
        return fa_digits("{} - {:02d}:{:02d}".format(_num_date(jd), jd.hour, jd.minute))
    return fa_digits(_num_date(jd))


def jalali_human(value, with_time=False):
    """تاریخ خوانای شمسی: ۱ شهریور ۱۴۰۵"""
    jd = to_jalali(value)
    if jd is None:
        return fa_digits(value) if value else ""
    txt = "{} {} {}".format(fa_digits(jd.day), JALALI_MONTHS[jd.month - 1], fa_digits(jd.year))
    if with_time and isinstance(jd, jdatetime.datetime):
        txt += "، ساعت {}".format(fa_digits("{:02d}:{:02d}".format(jd.hour, jd.minute)))
    return txt
