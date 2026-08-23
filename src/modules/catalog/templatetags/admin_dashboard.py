"""
تمپلیت‌تگ داشبورد مدیریت ریحان — آمار کلیدی روی صفحه اول /admin/
"""
import jdatetime
from django import template
from django.utils import timezone
from datetime import timedelta

register = template.Library()


@register.simple_tag
def rihan_dashboard_stats():
    stats = {}
    try:
        from src.modules.order.models import Order, Payment
        now = timezone.now()
        today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        week_ago = now - timedelta(days=7)

        stats['orders_today'] = Order.objects.filter(created_at__gte=today_start).count()
        stats['orders_total'] = Order.objects.count()

        # پرداخت‌های کارت‌به‌کارت منتظر تایید ادمین
        pending_payments = Payment.objects.filter(status=Payment.PaymentStatus.PENDING_REVIEW)
        stats['pending_payments'] = pending_payments.count()

        # فروش موفق امروز (تومانی)
        from django.db.models import Sum
        paid_today = Payment.objects.filter(
            status=Payment.PaymentStatus.SUCCESS,
            reviewed_at__gte=today_start,
        ).aggregate(s=Sum('amount'))['s'] or 0
        stats['paid_today'] = paid_today

        # نظرات در انتظار تایید
        try:
            from src.modules.reviews.models import Review
            stats['pending_reviews'] = Review.objects.filter(is_approved=False).count()
        except Exception:
            stats['pending_reviews'] = 0

        # سرنخ‌های جدید هفته گذشته
        try:
            from src.modules.leads.models import Lead
            stats['new_leads'] = Lead.objects.filter(created_at__gte=week_ago).count()
        except Exception:
            stats['new_leads'] = 0
    except Exception as e:
        stats['error'] = str(e)

    try:
        from src.modules.catalog.models import Inventory, Product
        low, out = [], []
        for inv in Inventory.objects.select_related('product'):
            avail = inv.available_quantity
            name = inv.product.name
            if avail <= 0:
                out.append(name)
            elif inv.is_low_stock:
                low.append(name)
        stats['low_stock'] = low[:5]
        stats['low_stock_more'] = max(0, len(low) - 5)
        stats['out_stock'] = out[:5]
        stats['out_stock_more'] = max(0, len(out) - 5)

        # محصولات پیش‌نویس که هنوز منتشر نشده‌اند
        stats['draft_products'] = Product.objects.filter(status='draft').count()
    except Exception as e:
        stats['inv_error'] = str(e)

    # سفارش‌های اخیر
    try:
        from src.modules.order.models import Order
        recent = []
        STATUS_FA = {
            'DRAFT': 'پیش‌نویس', 'PENDING': 'در انتظار پرداخت', 'PAID': 'پرداخت شده',
            'PROCESSING': 'در حال پردازش', 'SHIPPED': 'ارسال شده',
            'DELIVERED': 'تحویل شده', 'CANCELLED': 'لغو شده',
        }
        COLOR = {
            'PENDING': '#ffc107', 'PAID': '#28a745', 'PROCESSING': '#17a2b8',
            'SHIPPED': '#007bff', 'DELIVERED': '#28a745', 'CANCELLED': '#dc3545',
            'DRAFT': '#6c757d',
        }
        for o in Order.objects.order_by('-created_at')[:6]:
            recent.append({
                'number': o.order_number,
                'status_fa': STATUS_FA.get(o.status, o.status),
                'color': COLOR.get(o.status, '#888'),
                'total': f'{o.total_price:,.0f}',
                'date': jdatetime.datetime.fromgregorian(datetime=o.created_at).strftime('%m/%d %H:%M'),
            })
        stats['recent_orders'] = recent
    except Exception as e:
        stats['orders_error'] = str(e)

    return stats


@register.simple_tag
def jalali_today():
    return jdatetime.datetime.fromgregorian(datetime=timezone.now()).strftime('%Y/%m/%d')
