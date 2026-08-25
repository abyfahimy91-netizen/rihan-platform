"""کانتکست پروسسور تنظیمات سایت — متغیر site_settings در همه قالب‌ها در دسترس است."""
from .models import SiteSettings


def site_settings(request):
    return {"site_settings": SiteSettings.load()}
