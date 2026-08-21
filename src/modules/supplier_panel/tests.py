"""
تست‌های پنل تأمین‌کننده (M4)
منطبق بر US-028 و US-029
"""
from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from django.urls import reverse

from src.modules.catalog.models import Supplier, Product, Category
from src.modules.order.models import Order, OrderItem
from src.modules.rbac.services.role_service import RoleService

User = get_user_model()


class SupplierPanelTestCase(TestCase):
    """تست‌های پایه پنل تأمین‌کننده"""
    
    def setUp(self):
        """ایجاد داده‌های تست"""
        self.client = Client()
        
        # ایجاد نقش‌های سیستمی
        RoleService.create_system_roles()
        
        # ایجاد کاربر تأمین‌کننده
        self.supplier_user = User.objects.create_user(
            username='supplier1',
            password='testpass123',
        )
        
        # ایجاد Supplier و اتصال به کاربر
        self.supplier = Supplier.objects.create(
            title='تأمین‌کننده خشکبار هوراند',
            city='هوراند',
            phone='09121234567',
            user=self.supplier_user,
        )
        
        # اعطای نقش supplier
        RoleService.assign_role(self.supplier_user, 'supplier')
        
        # ایجاد کاربر عادی (بدون نقش supplier)
        self.regular_user = User.objects.create_user(
            username='customer1',
            password='testpass123',
        )
        
        # ایجاد دسته‌بندی و محصول
        self.category = Category.objects.create(
            name='خشکبار',
            slug='dried-fruits',
        )
        
        self.product = Product.objects.create(
            name='سماق هوراند',
            slug='sumac-horand',
            category=self.category,
            supplier=self.supplier,
            base_price=50000,
            final_price=65000,
            short_description='سماق درجه یک هوراند',
            origin_story='از مزارع هوراند',
            status='active',
        )
        
        # ایجاد سفارش با محصول تأمین‌کننده
        self.order = Order.objects.create(
            user=self.regular_user,
            status='PAID',
            subtotal=65000,
            total_price=65000,
            guest_name='تست مشتری',
            guest_phone='09129876543',
        )
        
        self.order_item = OrderItem.objects.create(
            order=self.order,
            product=self.product,
            quantity=1,
            unit_price_at_purchase=65000,
            product_name_snapshot='سماق هوراند',
        )
    
    def test_supplier_dashboard_access(self):
        """US-028: تأمین‌کننده می‌تواند وارد داشبورد شود"""
        self.client.login(username='supplier1', password='testpass123')
        response = self.client.get(reverse('supplier_panel:dashboard'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'پنل تأمین‌کننده')
    
    def test_regular_user_cannot_access_supplier_panel(self):
        """امنیت: کاربر عادی نمی‌تواند به پنل تأمین‌کننده دسترسی پیدا کند"""
        self.client.login(username='customer1', password='testpass123')
        response = self.client.get(reverse('supplier_panel:dashboard'))
        self.assertEqual(response.status_code, 403)
    
    def test_supplier_sees_only_own_orders(self):
        """US-029: تأمین‌کننده فقط سفارشات خودش را می‌بیند"""
        self.client.login(username='supplier1', password='testpass123')
        response = self.client.get(reverse('supplier_panel:order_list'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.order.order_number)
    
    def test_submit_tracking_code(self):
        """US-029: تأمین‌کننده می‌تواند کد رهگیری ثبت کند"""
        self.client.login(username='supplier1', password='testpass123')
        
        url = reverse('supplier_panel:submit_tracking', args=[self.order.id])
        response = self.client.post(url, {
            'tracking_code': '12345678901234567890',
            'shipping_method': 'post',
        })
        
        self.assertEqual(response.status_code, 302)  # Redirect
        
        # بررسی تغییر وضعیت سفارش
        self.order.refresh_from_db()
        self.assertEqual(self.order.status, 'SHIPPED')
        self.assertEqual(self.order.tracking_code, '12345678901234567890')
    
    def test_supplier_cannot_submit_tracking_for_other_orders(self):
        """امنیت: تأمین‌کننده نمی‌تواند برای سفارش دیگران کد ثبت کند"""
        # ایجاد سفارش بدون محصول این تأمین‌کننده
        other_order = Order.objects.create(
            user=self.regular_user,
            status='PAID',
            subtotal=100000,
            total_price=100000,
            guest_name='مشتری دیگر',
            guest_phone='09121111111',
        )
        
        self.client.login(username='supplier1', password='testpass123')
        url = reverse('supplier_panel:submit_tracking', args=[other_order.id])
        response = self.client.get(url)
        
        # باید 404 برگردد چون سفارش مرتبط با این تأمین‌کننده نیست
        self.assertEqual(response.status_code, 404)
