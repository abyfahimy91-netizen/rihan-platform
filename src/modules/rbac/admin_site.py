"""
M5: Custom Admin Site

- داشبورد با KPI های M3
- Activity tracking در همه عملیات
- فارسی‌سازی کامل
- هویت بصری M13
"""
from django.contrib import admin
from django.contrib.admin import AdminSite
from django.template.response import TemplateResponse
from django.urls import path, reverse
from django.utils import timezone
from django.db.models import Count, Sum, Q
from django.utils.timezone import now, timedelta

from modules.plugin_arch.core import log_admin_activity


class RihanAdminSite(AdminSite):
    """Custom Admin Site برای ریهان"""
    
    site_header = 'سامانه مدیریت ریهان'
    site_title = 'پنل خانواده ریهان'
    index_title = 'داشبورد مدیریت'
    index_template = 'admin/rihan_index.html'
    login_template = 'rbac/login.html'
    
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('dashboard/', self.admin_view(self.dashboard_view), name='dashboard'),
        ]
        return custom_urls + urls
    
    def dashboard_view(self, request):
        """داشبورد با KPI های M3"""
        context = {
            **self.each_context(request),
            'title': 'داشبورد',
        }
        return TemplateResponse(request, 'admin/rihan_dashboard.html', context)
    
    def each_context(self, request):
        context = super().each_context(request)
        
        # اضافه کردن KPI های داشبورد
        context['kpi'] = self._get_dashboard_kpi()
        context['recent_activities'] = self._get_recent_activities()
        
        return context
    
    def _get_dashboard_kpi(self):
        """محاسبه KPI های داشبورد مطابق M3"""
        from django.apps import apps
        
        kpi = {
            'today_orders': 0,
            'today_revenue': 0,
            'pending_orders': 0,
            'low_stock_products': 0,
            'pending_reviews': 0,
            'new_leads': 0,
        }
        
        # Orders
        try:
            Order = apps.get_model('orders', 'Order')
            today = now().replace(hour=0, minute=0, second=0, microsecond=0)
            
            # سفارش‌های امروز
            today_orders = Order.objects.filter(created_at__gte=today)
            kpi['today_orders'] = today_orders.count()
            
            # درآمد امروز
            try:
                kpi['today_revenue'] = today_orders.aggregate(
                    total=Sum('total_amount')
                )['total'] or 0
            except:
                kpi['today_revenue'] = 0
            
            # سفارش‌های در انتظار
            try:
                kpi['pending_orders'] = Order.objects.filter(
                    status__in=['pending', 'awaiting_payment']
                ).count()
            except:
                kpi['pending_orders'] = 0
        except:
            pass
        
        # Products - موجودی کم
        try:
            Product = apps.get_model('catalog', 'Product')
            kpi['low_stock_products'] = Product.objects.filter(
                stock__lt=5,
                is_available=True
            ).count()
        except:
            pass
        
        # Reviews - در انتظار تأیید
        try:
            Review = apps.get_model('catalog', 'ProductReview')
            kpi['pending_reviews'] = Review.objects.filter(is_approved=False).count()
        except:
            pass
        
        # Leads - جدید
        try:
            Lead = apps.get_model('catalog', 'LeadCapture')
            kpi['new_leads'] = Lead.objects.filter(
                status='new'
            ).count()
        except:
            pass
        
        return kpi
    
    def _get_recent_activities(self):
        """آخرین فعالیت‌های ادمین (از M14)"""
        try:
            from modules.plugin_arch.models import AdminActivityLog
            return AdminActivityLog.objects.select_related('user').all()[:10]
        except:
            return []


# جایگزینی admin site پیش‌فرض
rihan_admin = RihanAdminSite(name='rihan_admin')

# Copy all registered models from default admin
for model, model_admin in admin.site._registry.items():
    rihan_admin.register(model, type(model_admin))
