"""
سرویس‌های محاسباتی ماژول مالی (M6)

پوشش User Stories:
- US-021: گزارش مالی
- US-030: حساب ماهانه تأمین‌کننده
"""
from decimal import Decimal
from datetime import datetime, timedelta
from django.db.models import Sum, Count, Q
from django.utils import timezone
import jdatetime

from .models import SupplierLedger, SupplierTransaction, Settlement


class FinanceService:
    """سرویس اصلی محاسبات مالی"""

    @staticmethod
    def get_or_create_ledger(supplier):
        """دریافت یا ایجاد دفتر حساب تأمین‌کننده"""
        ledger, created = SupplierLedger.objects.get_or_create(
            supplier=supplier
        )
        return ledger

    @staticmethod
    def create_sale_transaction(order_item, order):
        """
        ثبت تراکنش فروش برای یک قلم سفارش
        
        Args:
            order_item: آیتم سفارش
            order: سفارش مرتبط
            
        Returns:
            SupplierTransaction یا None
        """
        try:
            supplier = order_item.product.supplier
            if not supplier:
                return None

            ledger = FinanceService.get_or_create_ledger(supplier)
            
            # محاسبه مبلغ (قیمت واحد × تعداد)
            amount = order_item.unit_price_at_purchase * order_item.quantity
            
            # بررسی اینکه آیا قبلاً تراکنش ثبت شده
            existing = SupplierTransaction.objects.filter(
                ledger=ledger,
                order=order,
                transaction_type=SupplierTransaction.TransactionType.SALE
            ).exists()
            
            if existing:
                return None  # جلوگیری از ثبت تکراری
            
            transaction = SupplierTransaction.objects.create(
                ledger=ledger,
                order=order,
                transaction_type=SupplierTransaction.TransactionType.SALE,
                amount=amount,
                description=f"فروش {order_item.product_name_snapshot} × {order_item.quantity}"
            )
            return transaction
            
        except Exception as e:
            print(f"خطا در ثبت تراکنش فروش: {e}")
            return None

    @staticmethod
    def create_settlement(ledger, amount, created_by, notes=""):
        """ایجاد تسویه حساب"""
        settlement = Settlement.objects.create(
            ledger=ledger,
            amount=amount,
            status=Settlement.SettlementStatus.PENDING,
            notes=notes,
            created_by=created_by
        )
        return settlement

    @staticmethod
    def get_dashboard_stats(days=30):
        """آمار داشبورد مالی برای ادمین"""
        today = timezone.now()
        start_date = today - timedelta(days=days)
        
        # درآمد کل (از سفارشات تحویل شده)
        from src.modules.order.models import Order
        delivered_orders = Order.objects.filter(
            status=Order.OrderStatus.DELIVERED,
            created_at__gte=start_date
        )
        
        total_revenue = delivered_orders.aggregate(
            total=Sum('total_price')
        )['total'] or Decimal('0')
        
        # تعداد سفارشات
        order_count = delivered_orders.count()
        
        # متوسط ارزش سفارش
        avg_order_value = total_revenue / order_count if order_count > 0 else Decimal('0')
        
        # مجموع بدهی به تأمین‌کنندگان
        total_supplier_debt = Decimal('0')
        for ledger in SupplierLedger.objects.all():
            total_supplier_debt += ledger.balance
        
        return {
            'total_revenue': total_revenue,
            'order_count': order_count,
            'avg_order_value': avg_order_value,
            'total_supplier_debt': total_supplier_debt,
            'period_days': days,
        }

    @staticmethod
    def get_supplier_monthly_report(supplier, year=None, month=None):
        """گزارش ماهانه تأمین‌کننده (US-030)"""
        if year is None or month is None:
            today = jdatetime.date.today()
            year = today.year
            month = today.month
        
        ledger = FinanceService.get_or_create_ledger(supplier)
        
        # تاریخ شروع و پایان ماه شمسی
        start_date = jdatetime.date(year, month, 1).togregorian()
        if month == 12:
            end_date = jdatetime.date(year + 1, 1, 1).togregorian()
        else:
            end_date = jdatetime.date(year, month + 1, 1).togregorian()
        
        # تراکنش‌های ماه
        transactions = ledger.transactions.filter(
            created_at__gte=start_date,
            created_at__lt=end_date
        )
        
        sales_total = transactions.filter(
            transaction_type=SupplierTransaction.TransactionType.SALE
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        settlements_total = transactions.filter(
            transaction_type=SupplierTransaction.TransactionType.SETTLEMENT
        ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        
        sales_count = transactions.filter(
            transaction_type=SupplierTransaction.TransactionType.SALE
        ).count()
        
        return {
            'supplier': supplier,
            'year': year,
            'month': month,
            'sales_total': sales_total,
            'sales_count': sales_count,
            'settlements_total': settlements_total,
            'balance': ledger.balance,
            'transactions': transactions,
        }
