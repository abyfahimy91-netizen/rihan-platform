"""
ویوهای صفحات عمومی — درباره ما، تماس با ما، سیاست مرجوعی، سوالات متداول.
محتوای همهٔ صفحات از تنظیمات سایت (پنل ادمین) خوانده می‌شود. (D-100)
"""
from django.shortcuts import render

from .markup import render_page_markup
from .models import FaqItem, SiteSettings


def about_view(request):
    """صفحه درباره ریهان - US-013 — محتوا کاملاً از تنظیمات سایت"""
    s = SiteSettings.load()
    context = {
        "page_title": s.about_title,
        "about_title": s.about_title,
        "about_html": render_page_markup(s.about_body),
    }
    return render(request, "pages/about.html", context)


def contact_view(request):
    """صفحه تماس با ما - US-014 — اطلاعات تماس از SiteSettings (D-100)"""
    s = SiteSettings.load()
    context = {
        "page_title": "تماس با ما",
        "contact_phone": s.contact_phone,
        "contact_email": s.contact_email,
        "contact_address": s.contact_address,
        "contact_hours": s.contact_hours,
        "instagram_url": s.instagram_url,
        "telegram_url": s.telegram_url,
        "whatsapp_number": s.whatsapp_number,
    }
    return render(request, "pages/contact.html", context)


def return_policy_view(request):
    """صفحه سیاست مرجوعی - US-015 — محتوا کاملاً از تنظیمات سایت"""
    s = SiteSettings.load()
    context = {
        "page_title": s.return_policy_title,
        "policy_title": s.return_policy_title,
        "policy_html": render_page_markup(s.return_policy_body),
    }
    return render(request, "pages/return_policy.html", context)


def privacy_view(request):
    """صفحه حریم خصوصی — محتوا از تنظیمات سایت (D-109 — پیش‌نیاز اینماد)"""
    s = SiteSettings.load()
    context = {
        "page_title": s.privacy_title,
        "privacy_title": s.privacy_title,
        "privacy_html": render_page_markup(s.privacy_body),
    }
    return render(request, "pages/privacy.html", context)


def faq_view(request):
    """سوالات متداول — سوال‌ها از پنل ادمین مدیریت می‌شوند (D-100)"""
    s = SiteSettings.load()
    context = {
        "page_title": "سوالات متداول",
        "faq_items": FaqItem.objects.filter(is_active=True),
        "faq_intro": s.faq_intro,
    }
    return render(request, "pages/faq.html", context)
