from django.test import TestCase
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
