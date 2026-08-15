"""
Feature Flags ریهان - کنترل فعال/غیرفعال کردن ویژگی‌ها

مطابق D-079، هر ماژول و هر بلوک باید از پنل ادمین قابل فعال/غیرفعال کردن باشد.
"""

DEFAULT_FEATURE_FLAGS = {
    # ماژول‌ها
    "MODULE_CATALOG": True,
    "MODULE_CART": True,
    "MODULE_FAMILY_PANEL": True,
    "MODULE_SUPPLIER_PANEL": True,
    "MODULE_RBAC": True,
    "MODULE_FINANCE": True,
    "MODULE_TRACKING": True,
    "MODULE_REVIEWS": True,
    "MODULE_LEADS": True,
    "MODULE_AUTH": True,
    "MODULE_PAYMENTS": True,
    "MODULE_ABOUT": True,
    "MODULE_VISUAL_IDENTITY": True,
    "MODULE_PLUGIN_ARCH": True,
    
    # ویژگی‌ها
    "FEATURE_SEO": True,           # سئو از روز اول (D-079)
    "FEATURE_SALES_FUNNEL": True,   # قیف فروش (D-079)
    "FEATURE_BLOCK_BASED": True,    # بلوک‌محور (D-079)
    "FEATURE_INDEPENDENT_BRAND": True,  # برند مستقل (D-079)
    
    # Feature Flags فعلی (از Gemini)
    "FEATURE_LEAD_CAPTURE": True,   # ← فعال شود (قبلاً False بود)
}
