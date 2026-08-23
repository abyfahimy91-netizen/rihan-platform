"""
تگ تمپلیت سایدبار اختصاصی پنل ادمین ریحان.
مدل‌ها را گروه‌بندی کرده و لینک هرکدام را فقط برای کاربران دارای دسترسی می‌سازد.
هر مدلی که در آینده ثبت شود، خودکار زیر گروه «سایر» ظاهر می‌شود.
"""
from django import template
from django.urls import NoReverseMatch, reverse
from django.contrib.admin import site as admin_site

register = template.Library()

# (عنوان گروه، [(app_label.model_name, عنوان فارسی), ...])
GROUPS = [
    ("🛍 فروشگاه", [
        ("catalog.product", "محصولات"),
        ("catalog.category", "دسته‌بندی‌ها"),
        ("catalog.supplier", "تامین‌کنندگان"),
        ("catalog.productimage", "تصاویر محصولات"),
    ]),
    ("📦 موجودی انبار", [
        ("catalog.inventory", "موجودی کالاها"),
        ("catalog.inventorytransaction", "تراکنش‌های موجودی"),
    ]),
    ("🧾 سفارش‌ها", [
        ("order.order", "سفارش‌ها"),
        ("order.payment", "پرداخت‌ها"),
        ("order.address", "آدرس‌ها"),
    ]),
    ("⭐ نظرات مشتریان", [
        ("reviews.review", "نظرات"),
    ]),
    ("📞 سرنخ‌های فروش", [
        ("leads.lead", "سرنخ‌ها"),
    ]),
    ("🧩 محتوای سایت", [
        ("pages.sitesettings", "⚙️ تنظیمات صفحه اصلی و سایت"),
        ("catalog.contentblock", "بلوک‌های محتوا"),
    ]),
    ("💰 امور مالی", [
        ("finance.supplierledger", "دفاتر تامین‌کننده"),
        ("finance.suppliertransaction", "تراکنش‌های مالی"),
        ("finance.settlement", "تسویه‌حساب‌ها"),
    ]),
    ("👥 کاربران و نقش‌ها", [
        ("auth.user", "کاربران"),
        ("rbac.role", "نقش‌ها"),
        ("rbac.userrole", "نقش اختصاص‌یافته"),
    ]),
]


@register.simple_tag(takes_context=True)
def rihan_sidebar(context):
    request = context.get("request")
    registry = {}
    for model, model_admin in admin_site._registry.items():
        label = "{}.{}".format(model._meta.app_label, model._meta.model_name)
        try:
            if request is None or not model_admin.has_view_or_change_permission(request, None):
                continue
            url = reverse(
                "admin:{}_{}_changelist".format(model._meta.app_label, model._meta.model_name)
            )
        except Exception:
            continue
        registry[label] = url

    groups, used = [], set()
    for title, entries in GROUPS:
        items = [{"title": t, "url": registry[k]} for k, t in entries if k in registry]
        if items:
            groups.append({"title": title, "items": items})
            used.update(k for k, _t in entries if k in registry)

    leftovers = []
    for label, url in registry.items():
        if label not in used:
            meta = None
            for m in admin_site._registry:
                if "{}.{}".format(m._meta.app_label, m._meta.model_name) == label:
                    meta = m._meta
                    break
            name = str(meta.verbose_name_plural) if meta else label
            leftovers.append({"title": name, "url": url})
    if leftovers:
        groups.append({"title": "🗂 سایر بخش‌ها", "items": leftovers})

    return {"groups": groups}
