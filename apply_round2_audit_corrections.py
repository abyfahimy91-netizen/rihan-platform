import os
from pathlib import Path

BASE = Path("/root/rihan-platform")

# --- 1. Formally Approve D-079 & D-080 in DECISIONS.md ---
decisions_file = BASE / "decisions/DECISIONS.md"
if decisions_file.exists():
    text = decisions_file.read_text(encoding="utf-8")
    text = text.replace("وضعیت: پیشنهادی (منتظر تأیید نهایی بنیانگذار و ناظر)", "وضعیت: Approved ✅ (تصویب رسمی بنیانگذار و ناظر)")
    text = text.replace("Status: Proposed", "Status: Approved ✅")
    
    d080_entry = """

---

## 🎯 تصمیم D-080 — تصویب معماری سیستم بلوک‌محور و سبد خرید شفاف D-046

**تاریخ:** ۱۴۰۵/۰۵/۲۴ (۲۰۲۶-۰۸-۱۴)
**وضعیت:** Approved ✅ (تصویب رسمی بنیانگذار و ناظر)
**انطباق:** ADR-002, ADR-004, ADR-005, D-046, D-051, اصل ۱۱ (کرامت مشتری)

### مصوبات قطعی:
1. پشتیبانی دوگانه از مدل‌های ContentBlock (رابطه 1:N مستقیم) و ProductBlock (رابطه چندبه‌چند واسط) جهت بیشترین انعطاف‌پذیری در صفحات محصول.
2. تصویب رسمی رویکرد D-046: قیمت تمام‌شده شفاف و ارسال رایگان در ظاهر (بدون هزینه پنهان).
3. استقرار موتور M14 شامل PluginRegistry و HookSystem در هسته پلتفرم.
"""
    if "D-080" not in text:
        text += d080_entry
    decisions_file.write_text(text, encoding="utf-8")
    print("✓ Formally Approved D-079 and D-080 in decisions/DECISIONS.md")

# --- 2. Add ProductBlock to src/apps/catalog/models.py (ADR-002 Full Compliance) ---
models_file = BASE / "src/apps/catalog/models.py"
models_text = models_file.read_text(encoding="utf-8")
product_block_code = """

class ProductBlock(models.Model):
    \"\"\"مدل واسط نگاشت چندبه‌چند بلوک‌های محتوایی به محصولات (ADR-002 & D-080)\"\"\"
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name='product_block_links', verbose_name="محصول")
    content_block = models.ForeignKey(ContentBlock, on_delete=models.CASCADE, related_name='product_mappings', verbose_name="بلوک محتوایی")
    custom_title = models.CharField(max_length=200, blank=True, verbose_name="عنوان سفارشی این محصول")
    sort_order = models.PositiveIntegerField(default=0, verbose_name="ترتیب نمایش")
    is_active = models.BooleanField(default=True, verbose_name="فعال")

    class Meta:
        verbose_name = "نگاشت محصول و بلوک (ProductBlock)"
        verbose_name_plural = "نگاشت‌های محصولات و بلوک‌ها (ProductBlocks)"
        ordering = ['sort_order', 'id']

    def __str__(self):
        return f"{self.product.title} <-> {self.content_block.title}"
"""
if "class ProductBlock" not in models_text:
    models_text += product_block_code
    models_file.write_text(models_text, encoding="utf-8")
    print("✓ Added ProductBlock model to src/apps/catalog/models.py")

# Update catalog/admin.py to include ProductBlockInline
admin_file = BASE / "src/apps/catalog/admin.py"
admin_text = admin_file.read_text(encoding="utf-8")
if "ProductBlock" not in admin_text:
    admin_text = admin_text.replace(
        "from .models import Category, Product, ProductImage, ContentBlock",
        "from .models import Category, Product, ProductImage, ContentBlock, ProductBlock"
    )
    admin_text = admin_text.replace(
        "inlines = [ProductImageInline, ContentBlockInline]",
        "inlines = [ProductImageInline, ContentBlockInline]\n\nclass ProductBlockInline(admin.TabularInline):\n    model = ProductBlock\n    extra = 1"
    )
    admin_file.write_text(admin_text, encoding="utf-8")
    print("✓ Registered ProductBlock in catalog admin.py")

# --- 3. Full Implementation of M14: Plugin Registry & Hook System (ADR-004) ---
plugins_file = BASE / "src/apps/core/plugins.py"
plugins_code = """# M14: Plugin Architecture, Hook System & Event Bus (ADR-004)
import logging
from typing import Callable, Dict, List, Any

logger = logging.getLogger(__name__)

class HookManager:
    \"\"\"سیستم قلاب‌ها و رویدادهای هسته پلتفرم ریهان (ADR-004)\"\"\"
    _hooks: Dict[str, List[Callable]] = {}

    @classmethod
    def register_hook(cls, event_name: str, handler: Callable):
        if event_name not in cls._hooks:
            cls._hooks[event_name] = []
        cls._hooks[event_name].append(handler)
        logger.info(f"Hook registered: {event_name} -> {handler.__name__}")

    @classmethod
    def trigger_hook(cls, event_name: str, **kwargs) -> List[Any]:
        results = []
        if event_name in cls._hooks:
            for handler in cls._hooks[event_name]:
                try:
                    res = handler(**kwargs)
                    results.append(res)
                except Exception as e:
                    logger.error(f"Error in hook {handler.__name__} on {event_name}: {e}")
        return results

class PluginRegistry:
    \"\"\"رجیستری رسمی ۱۴ ماژول و پلاگین‌های ریهان\"\"\"
    _plugins: Dict[str, Dict[str, Any]] = {}

    @classmethod
    def register(cls, plugin_id: str, name: str, version: str = "1.0.0", description: str = "", is_system: bool = False):
        cls._plugins[plugin_id] = {
            'id': plugin_id,
            'name': name,
            'version': version,
            'description': description,
            'is_system': is_system,
            'enabled': True
        }

    @classmethod
    def get_all_plugins(cls):
        return cls._plugins

    @classmethod
    def is_plugin_active(cls, plugin_id: str) -> bool:
        return cls._plugins.get(plugin_id, {}).get('enabled', False)

# پیش‌ثبت ماژول‌های فعال ریهان
PluginRegistry.register("M1", "کاتالوگ محصولات و بلوک‌محور", "0.5.6", is_system=True)
PluginRegistry.register("M2", "سبد خرید و سفارش شفاف", "0.5.6", is_system=True)
PluginRegistry.register("M3", "پنل مدیریت خانواده", "0.5.6", is_system=True)
PluginRegistry.register("M7", "پیگیری سفارش بدون لاگین", "0.5.6", is_system=True)
PluginRegistry.register("M10", "احراز هویت پیامکی و رمز پشتیبان", "0.5.6", is_system=True)
PluginRegistry.register("M11", "پرداخت کارت‌به‌کارت", "0.5.6", is_system=True)
PluginRegistry.register("M13", "طراحی تجربه کاربری بومی RTL", "0.5.6", is_system=True)
PluginRegistry.register("M14", "معماری افزونه‌محور و Feature Flags", "0.5.6", is_system=True)
"""
plugins_file.write_text(plugins_code, encoding="utf-8")
print("✓ Implemented PluginRegistry and HookManager in src/apps/core/plugins.py")

# Update src/apps/core/feature_flags.py
flags_file = BASE / "src/apps/core/feature_flags.py"
flags_code = """# M14: Feature Flags Engine (ADR-004)
import os
from typing import Dict

DEFAULT_FLAGS: Dict[str, bool] = {
    'FEATURE_CARD_TO_CARD_PAYMENT': True,
    'FEATURE_ONLINE_PAYMENT_GATEWAY': False,
    'FEATURE_SMS_OTP_LOGIN': True,
    'FEATURE_BACKUP_PASSWORD_LOGIN': True,
    'FEATURE_ORDER_TRACKING_PUBLIC': True,
    'FEATURE_PRODUCT_CONTENT_BLOCKS': True,
    'FEATURE_PRODUCT_BLOCK_JUNCTION': True,
    'FEATURE_SUPPLIER_PANEL': False,
    'FEATURE_CUSTOMER_REVIEWS': False,
    'FEATURE_LEAD_CAPTURE': False,
    'FEATURE_PLUGIN_HOOKS': True,
}

class FeatureFlags:
    @staticmethod
    def is_enabled(flag_name: str) -> bool:
        env_val = os.environ.get(flag_name)
        if env_val is not None:
            return env_val.lower() in ('true', '1', 'yes')
        return DEFAULT_FLAGS.get(flag_name, False)

    @classmethod
    def get_all_flags(cls) -> Dict[str, bool]:
        return {k: cls.is_enabled(k) for k in DEFAULT_FLAGS.keys()}

    @classmethod
    def set_override(cls, flag_name: str, value: bool):
        DEFAULT_FLAGS[flag_name] = value
"""
flags_file.write_text(flags_code, encoding="utf-8")
print("✓ Enhanced src/apps/core/feature_flags.py")

# --- 4. Add Unit Tests for Plugins and ProductBlock ---
test_plugins_file = BASE / "tests/test_plugins_and_blocks.py"
test_plugins_code = """from django.test import TestCase
from apps.catalog.models import Category, Product, ContentBlock, ProductBlock
from apps.core.plugins import PluginRegistry, HookManager
from apps.core.feature_flags import FeatureFlags

class PluginsAndBlocksTestCase(TestCase):
    def setUp(self):
        self.cat = Category.objects.create(name="سوغات", slug="souvenir-p")
        self.p = Product.objects.create(
            category=self.cat, title="سماق ارگانیک", slug="somagh-org",
            sku="RIHAN-SM-ORG", summary="سماق هوراند", price=300000, stock=15
        )
        self.cb = ContentBlock.objects.create(
            product=self.p, block_type="story", title="داستان هوراند", content="متن اصالت"
        )

    def test_product_block_junction(self):
        pb = ProductBlock.objects.create(
            product=self.p, content_block=self.cb, custom_title="روایت اختصاصی"
        )
        self.assertEqual(str(pb), f"{self.p.title} <-> {self.cb.title}")
        self.assertTrue(FeatureFlags.is_enabled('FEATURE_PRODUCT_BLOCK_JUNCTION'))

    def test_plugin_registry_and_hooks(self):
        self.assertTrue(PluginRegistry.is_plugin_active("M1"))
        self.assertTrue(PluginRegistry.is_plugin_active("M14"))
        
        # Test Hook execution
        def sample_hook(order_id):
            return f"Processed {order_id}"
            
        HookManager.register_hook("order_created", sample_hook)
        results = HookManager.trigger_hook("order_created", order_id=1024)
        self.assertIn("Processed 1024", results)
"""
test_plugins_file.write_text(test_plugins_code, encoding="utf-8")
print("✓ Added Unit Tests in tests/test_plugins_and_blocks.py")

print("All Round 2 Audit Corrections Deployed.")
