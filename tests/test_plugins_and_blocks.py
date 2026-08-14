from django.test import TestCase
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
