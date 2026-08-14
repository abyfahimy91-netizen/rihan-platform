import os
from pathlib import Path

BASE = Path("/root/rihan-platform")

# Update src/apps/orders/models.py to add OrderFinance model
models_file = BASE / "src/apps/orders/models.py"
models_text = models_file.read_text(encoding="utf-8")

finance_model_code = """

class OrderFinance(models.Model):
    \"\"\"دفتر مالی و محاسبه حاشیه سود سفارش (M6 - D-046 & MVP-SCOPE)\"\"\"
    order = models.OneToOneField('Order', on_delete=models.CASCADE, related_name='finance', verbose_name="سفارش")
    gross_revenue = models.PositiveBigIntegerField(default=0, verbose_name="درآمد ناخالص (تومان)")
    total_supply_cost = models.PositiveBigIntegerField(default=0, verbose_name="مجموع هزینه تأمین کالا (تومان)")
    actual_shipping_cost = models.PositiveBigIntegerField(default=45000, verbose_name="هزینه واقعی ارسال پستی (تومان)")
    net_profit = models.BigIntegerField(default=0, verbose_name="سود ناخالص واقعی (تومان)")
    margin_percent = models.FloatField(default=0.0, verbose_name="حاشیه سود واقعی (درصد)")
    supplier_paid = models.BooleanField(default=False, verbose_name="تسویه با تأمین‌کننده")

    class Meta:
        verbose_name = "حساب و کتاب مالی سفارش (M6)"
        verbose_name_plural = "حساب و کتاب مالی سفارش‌ها"
        ordering = ['-order__created_at']

    def calculate_finance(self):
        \"\"\"فرمول رسمی D-046: سود واقعی = قیمت فروش - قیمت تأمین - هزینه واقعی ارسال\"\"\"
        self.gross_revenue = self.order.grand_total
        supply_sum = 0
        for item in self.order.items.all():
            if item.product and item.product.supply_cost:
                supply_sum += (item.product.supply_cost * item.quantity)
            else:
                # حاشیه پیش‌فرض ۲۵٪ در صورت عدم درج هزینه تأمین
                supply_sum += int(item.unit_price * 0.75) * item.quantity
        
        self.total_supply_cost = supply_sum
        self.net_profit = self.gross_revenue - self.total_supply_cost - self.actual_shipping_cost
        if self.gross_revenue > 0:
            self.margin_percent = round((self.net_profit / self.gross_revenue) * 100, 1)
        else:
            self.margin_percent = 0.0
        self.save()

    def __str__(self):
        return f"مالی {self.order.order_number}: سود {self.net_profit:,} تومان ({self.margin_percent}%)"
"""

if "class OrderFinance" not in models_text:
    models_text += finance_model_code
    models_file.write_text(models_text, encoding="utf-8")
    print("✓ Added OrderFinance model to src/apps/orders/models.py")

# Update src/apps/orders/admin.py to add OrderFinance and inline
admin_file = BASE / "src/apps/orders/admin.py"
admin_text = admin_file.read_text(encoding="utf-8")
if "OrderFinance" not in admin_text:
    admin_text = admin_text.replace(
        "from .models import Order, OrderItem",
        "from .models import Order, OrderItem, OrderFinance"
    )
    
    finance_admin_code = """

class OrderFinanceInline(admin.StackedInline):
    model = OrderFinance
    can_delete = False
    readonly_fields = ['gross_revenue', 'total_supply_cost', 'net_profit', 'margin_percent']
    extra = 0

@admin.register(OrderFinance)
class OrderFinanceAdmin(admin.ModelAdmin):
    list_display = ['order', 'gross_revenue_display', 'supply_cost_display', 'actual_shipping_display', 'net_profit_display', 'margin_display', 'supplier_paid']
    list_filter = ['supplier_paid', 'order__created_at']
    search_fields = ['order__order_number', 'order__customer_name']
    readonly_fields = ['order', 'gross_revenue', 'total_supply_cost', 'net_profit', 'margin_percent']

    @admin.display(description="درآمد فروش")
    def gross_revenue_display(self, obj):
        return f"{obj.gross_revenue:,} تومان"

    @admin.display(description="هزینه تأمین")
    def supply_cost_display(self, obj):
        return f"{obj.total_supply_cost:,} تومان"

    @admin.display(description="هزینه ارسال")
    def actual_shipping_display(self, obj):
        return f"{obj.actual_shipping_cost:,} تومان"

    @admin.display(description="سود خالص واقعی (D-046)")
    def net_profit_display(self, obj):
        color = "#198754" if obj.net_profit > 0 else "#dc3545"
        return format_html('<strong style="color: {};">{:,} تومان</strong>', color, obj.net_profit)

    @admin.display(description="حاشیه سود")
    def margin_display(self, obj):
        return f"{obj.margin_percent}%"
"""
    # Add inline to OrderAdmin
    admin_text = admin_text.replace("inlines = [OrderItemInline]", "inlines = [OrderItemInline, OrderFinanceInline]")
    admin_text += finance_admin_code
    admin_file.write_text(admin_text, encoding="utf-8")
    print("✓ Registered OrderFinance in orders/admin.py")

# Create Unit Tests: tests/test_finance.py
test_file = BASE / "tests/test_finance.py"
test_code = """from django.test import TestCase
from apps.catalog.models import Category, Product
from apps.orders.models import Order, OrderItem, OrderFinance

class FinanceModuleTestCase(TestCase):
    def setUp(self):
        self.cat = Category.objects.create(name="خشکبار", slug="dry-fruits-f")
        self.p1 = Product.objects.create(
            category=self.cat, title="سماق هوراند", slug="somagh-hurand-f",
            sku="RIHAN-SM-F1", summary="سماق ۱ کیلو",
            price=2550000, supply_cost=2000000, stock=20
        )
        self.order = Order.objects.create(
            customer_name="مریم کارمند", customer_phone="09121112233",
            shipping_address="تبریز", postal_code="5123456789",
            items_total=2550000, grand_total=2550000, status='confirmed'
        )
        self.item = OrderItem.objects.create(
            order=self.order, product=self.p1, product_title=self.p1.title,
            product_sku=self.p1.sku, unit_price=2550000, quantity=1, subtotal=2550000
        )

    def test_d046_financial_formula(self):
        # تست فرمول D-046:
        # قیمت فروش ۲,۵۵۰,۰۰۰ - قیمت تأمین ۲,۰۰۰,۰۰۰ - هزینه پست ۴۵,۰۰۰ = سود ۵۰۵,۰۰۰ تومان (۱۹.۸٪)
        finance, _ = OrderFinance.objects.get_or_create(order=self.order, actual_shipping_cost=45000)
        finance.calculate_finance()
        
        self.assertEqual(finance.gross_revenue, 2550000)
        self.assertEqual(finance.total_supply_cost, 2000000)
        self.assertEqual(finance.actual_shipping_cost, 45000)
        self.assertEqual(finance.net_profit, 505000)
        self.assertEqual(finance.margin_percent, 19.8)
        self.assertIn("505,000", str(finance))
"""
test_file.write_text(test_code, encoding="utf-8")
print("✓ Created tests/test_finance.py")

# Update PluginRegistry to mark M6 as active
plugins_file = BASE / "src/apps/core/plugins.py"
plugins_text = plugins_file.read_text(encoding="utf-8")
if 'PluginRegistry.register("M6"' not in plugins_text:
    plugins_text += '\nPluginRegistry.register("M6", "حساب و کتاب مالی و سود ناخالص D-046", "0.5.9", is_system=True)\n'
    plugins_file.write_text(plugins_text, encoding="utf-8")
    print("✓ Registered M6 in PluginRegistry")

print("Module M6 (Financial Accounting) Deployed Successfully.")
