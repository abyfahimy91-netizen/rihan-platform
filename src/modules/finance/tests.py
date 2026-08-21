"""
تست‌های ماژول مالی (M6)

User Stories پوشش داده شده:
- US-021: گزارش مالی
- US-030: حساب ماهانه تأمین‌کننده
"""
from decimal import Decimal
from django.test import TestCase
from django.contrib.auth.models import User

from src.modules.catalog.models import Supplier, Product, Category
from src.modules.order.models import Order, OrderItem
from .models import SupplierLedger, SupplierTransaction, Settlement
from .services import FinanceService


class FinanceServiceTestCase(TestCase):
    """تست سرویس‌های مالی"""
    
    def setUp(self):
        # ایجاد کاربر ادمین
        self.admin = User.objects.create_user(
            username='admin',
            password='testpass123'
        )
        
        # ایجاد دسته‌بندی
        self.category = Category.objects.create(
            name="خشکبار",
            slug="dried-fruits"
        )
        
        # ایجاد تأمین‌کننده (فیلدهای صحیح: title, city)
        self.supplier = Supplier.objects.create(
            title="تأمین‌کننده تست",
            city="هوراند",
            phone="09123456789"
        )
        
        # ایجاد محصول (فیلدهای اجباری: name, slug, category, short_description, origin_story, base_price)
        self.product = Product.objects.create(
            name="سماق هوراند",
            slug="somagh-horand",
            category=self.category,
            supplier=self.supplier,
            base_price=Decimal('50000'),
            final_price=Decimal('50000'),
            short_description="سماق اعلا از هوراند",
            origin_story="سماق طبیعی از کوه‌های هوراند",
            status='active'
        )
        
        # ایجاد سفارش
        self.order = Order.objects.create(
            status=Order.OrderStatus.DRAFT,
            total_price=Decimal('100000')
        )
        
        # ایجاد آیتم سفارش
        self.order_item = OrderItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=2,
            unit_price_at_purchase=Decimal('50000'),
            product_name_snapshot="سماق هوراند"
        )
    
    def test_get_or_create_ledger(self):
        """تست ایجاد دفتر حساب"""
        ledger = FinanceService.get_or_create_ledger(self.supplier)
        self.assertIsInstance(ledger, SupplierLedger)
        self.assertEqual(ledger.supplier, self.supplier)
        
        # فراخوانی دوم نباید ledger جدید بسازد
        ledger2 = FinanceService.get_or_create_ledger(self.supplier)
        self.assertEqual(ledger.id, ledger2.id)
    
    def test_create_sale_transaction(self):
        """تست ثبت تراکنش فروش"""
        transaction = FinanceService.create_sale_transaction(
            self.order_item,
            self.order
        )
        
        self.assertIsNotNone(transaction)
        self.assertEqual(transaction.amount, Decimal('100000'))
        self.assertEqual(
            transaction.transaction_type,
            SupplierTransaction.TransactionType.SALE
        )
    
    def test_duplicate_transaction_prevention(self):
        """تست جلوگیری از ثبت تکراری"""
        # ثبت اول
        FinanceService.create_sale_transaction(self.order_item, self.order)
        
        # ثبت دوم (نباید ایجاد شود)
        transaction2 = FinanceService.create_sale_transaction(
            self.order_item,
            self.order
        )
        
        self.assertIsNone(transaction2)
        self.assertEqual(
            SupplierTransaction.objects.filter(order=self.order).count(),
            1
        )
    
    def test_create_settlement(self):
        """تست ایجاد تسویه"""
        ledger = FinanceService.get_or_create_ledger(self.supplier)
        
        settlement = FinanceService.create_settlement(
            ledger=ledger,
            amount=Decimal('50000'),
            created_by=self.admin,
            notes="تسویه ماه اول"
        )
        
        self.assertEqual(settlement.amount, Decimal('50000'))
        self.assertEqual(settlement.status, Settlement.SettlementStatus.PENDING)
    
    def test_supplier_balance_calculation(self):
        """تست محاسبه موجودی تأمین‌کننده"""
        ledger = FinanceService.get_or_create_ledger(self.supplier)
        
        # ثبت فروش
        SupplierTransaction.objects.create(
            ledger=ledger,
            order=self.order,
            transaction_type=SupplierTransaction.TransactionType.SALE,
            amount=Decimal('100000')
        )
        
        # ثبت تسویه
        Settlement.objects.create(
            ledger=ledger,
            amount=Decimal('30000'),
            status=Settlement.SettlementStatus.COMPLETED
        )
        
        # محاسبه موجودی (۱۰۰۰۰۰ - ۳۰۰۰۰ = ۷۰۰۰۰)
        self.assertEqual(ledger.balance, Decimal('70000'))
    
    def test_product_without_supplier_skipped(self):
        """تست رد کردن محصول بدون تأمین‌کننده"""
        product_no_supplier = Product.objects.create(
            name="محصول بدون تأمین‌کننده",
            slug="no-supplier-product",
            category=self.category,
            supplier=None,
            base_price=Decimal('10000'),
            final_price=Decimal('10000'),
            short_description="تست",
            origin_story="تست",
            status='active'
        )
        
        order = Order.objects.create(
            status=Order.OrderStatus.DELIVERED,
            total_price=Decimal('10000')
        )
        
        order_item = OrderItem.objects.create(
            order=order,
            product=product_no_supplier,
            quantity=1,
            unit_price_at_purchase=Decimal('10000'),
            product_name_snapshot="محصول بدون تأمین‌کننده"
        )
        
        # نباید تراکنش ایجاد شود
        transaction = FinanceService.create_sale_transaction(order_item, order)
        self.assertIsNone(transaction)


class FinanceDashboardTestCase(TestCase):
    """تست داشبورد مالی"""
    
    def setUp(self):
        # ایجاد چند سفارش با وضعیت‌های مختلف
        Order.objects.create(
            status=Order.OrderStatus.DELIVERED,
            total_price=Decimal('100000')
        )
        Order.objects.create(
            status=Order.OrderStatus.DELIVERED,
            total_price=Decimal('150000')
        )
        Order.objects.create(
            status=Order.OrderStatus.CANCELLED,
            total_price=Decimal('50000')
        )
    
    def test_dashboard_stats(self):
        """تست آمار داشبورد"""
        stats = FinanceService.get_dashboard_stats(days=30)
        
        # فقط ۲ سفارش DELIVERED شمرده می‌شوند
        self.assertEqual(stats['order_count'], 2)
        self.assertEqual(stats['total_revenue'], Decimal('250000'))
        self.assertEqual(stats['avg_order_value'], Decimal('125000'))
        self.assertEqual(stats['period_days'], 30)
