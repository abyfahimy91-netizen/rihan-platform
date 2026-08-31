# -*- coding: utf-8 -*-
"""D-125: تست پنل سرنخ‌های بازدید (VisitorLead + import + پannel + سxidbar)."""
import json

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from src.modules.leads.analytics import import_from_snapshot
from src.modules.leads.models import VisitorLead

# try order model — mtnavi dar barxi mohit be kar mikhord
from django.apps import apps
Order = apps.get_model('order', 'Order')


def _fixture(path):
    snap = {
        'generated': '2026-08-31 22:00',
        'totals': {'visitor_ips': 3, 'visitor_sessions': 4, 'visitor_page_views': 20},
        'log_files': ['/var/log/nginx/access.log'],
        'visitors': [
            {
                'ip': '2.177.54.249',
                'geo': {'country': 'Iran', 'city': 'Tehran', 'isp': 'Information Technology Company',
                        'mobile': False, 'cc': 'IR'},
                'vpn_suspect': False,
                'device': 'iOS', 'ua': 'Mozilla/5.0 (iPhone)',
                'channel_first': 'share_link',
                'first': '2026-08-28 15:00', 'last': '2026-08-28 15:25',
                'views': 16, 'kinds': ['product', 'shortlink', 'cart', 'checkout', 'payment', 'tracking'],
                'sessions': [
                    {'start': '2026-08-28 15:00', 'end': '2026-08-28 15:25', 'pages': 16,
                     'kinds': ['product', 'shortlink', 'cart', 'checkout', 'payment'],
                     'posted': True,
                     'post_paths': ['/order/checkout/', '/order/payment/RH-1405-00003/'],
                     'paths': ['/order/payment/RH-1405-00003/', '/order/checkout/', '/order/cart/'],
                     'channels': [], 'status': [200, 302], 'mins': 25},
                ],
            },
            {
                'ip': '89.196.126.9',
                'geo': {'country': 'Iran', 'city': 'Tehran', 'isp': 'Mobile Communication Company of Iran',
                        'mobile': True, 'cc': 'IR'},
                'vpn_suspect': False,
                'device': 'Android', 'ua': 'Mozilla/5.0 (Linux; Android 13)',
                'channel_first': 'direct',
                'first': '2026-08-28 20:00', 'last': '2026-08-28 22:45',
                'views': 37, 'kinds': ['product', 'shortlink', 'cart', 'checkout'],
                'sessions': [
                    {'start': '2026-08-28 20:00', 'end': '2026-08-28 22:45', 'pages': 30,
                     'kinds': ['product', 'cart', 'checkout'],
                     'posted': True, 'post_paths': ['/order/checkout/'],
                     'paths': ['/order/checkout/', '/order/cart/'],
                     'channels': [], 'status': [200], 'mins': 120},
                ],
            },
            {
                'ip': '5.121.195.0',
                'geo': {'country': 'Iran', 'city': 'Tabriz', 'isp': 'Tabriz', 'mobile': False, 'cc': 'IR'},
                'vpn_suspect': False,
                'device': 'iOS', 'ua': 'Mozilla/5.0 (iPhone)',
                'channel_first': 'direct',
                'first': '2026-08-31 10:12', 'last': '2026-08-31 11:14',
                'views': 6, 'kinds': ['home', 'login', 'product', 'register'],
                'sessions': [
                    {'start': '2026-08-31 10:12', 'end': '2026-08-31 11:14', 'pages': 6,
                     'kinds': ['home', 'login', 'product', 'register'],
                     'posted': True, 'post_paths': ['/accounts/register/'],
                     'paths': ['/', '/accounts/register/'],
                     'channels': [], 'status': [200, 302], 'mins': 40},
                ],
            },
        ],
    }
    with open(path, 'w') as f:
        json.dump(snap, f)
    return snap


class VisitorLeadImportTests(TestCase):
    def setUp(self):
        self.path = '/tmp/test_snapshot_leads.json'

    def test_import_maps_stages_and_hot(self):
        _fixture(self.path)
        stats = import_from_snapshot(self.path)
        self.assertEqual(stats['created'], 3)
        buyer = VisitorLead.objects.get(ip='2.177.54.249')
        # سفارش RH-1405-00003 در DB نیست → به پرداخت رسید ولی تبدیل نشده
        self.assertEqual(buyer.stage, VisitorLead.Stage.PAYMENT)
        self.assertTrue(buyer.is_hot)
        self.assertTrue(buyer.hot_active)
        window_shopper = VisitorLead.objects.get(ip='89.196.126.9')
        self.assertEqual(window_shopper.stage, VisitorLead.Stage.CHECKOUT)
        self.assertTrue(window_shopper.is_hot)
        simple = VisitorLead.objects.get(ip='5.121.195.0')
        self.assertEqual(simple.stage, VisitorLead.Stage.PRODUCT)
        self.assertFalse(simple.is_hot)
        self.assertEqual(simple.device, 'iOS')
        self.assertEqual(VisitorLead.objects.count(), 3)

    def test_import_updates_not_duplicates(self):
        _fixture(self.path)
        import_from_snapshot(self.path)
        stats2 = import_from_snapshot(self.path)
        self.assertEqual(stats2['created'], 0)
        self.assertEqual(stats2['updated'], 3)
        self.assertEqual(VisitorLead.objects.count(), 3)

    def test_converted_stage_with_real_order(self):
        _fixture(self.path)
        Order.objects.create(order_number='RH-1405-00003', status='DELIVERED')
        import_from_snapshot(self.path)
        buyer = VisitorLead.objects.get(ip='2.177.54.249')
        self.assertEqual(buyer.stage, VisitorLead.Stage.CONVERTED)
        self.assertFalse(buyer.is_hot)
        self.assertEqual(buyer.orders_matched[0]['number'], 'RH-1405-00003')
        self.assertEqual(buyer.orders_matched[0]['status'], 'DELIVERED')


@override_settings(LEADS_SNAPSHOT_PATH='/tmp/test_snapshot_leads.json')
class VisitorPanelTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.admin = User.objects.create_user(username='panelt', password='x', is_staff=True, is_superuser=True)
        self.path = '/tmp/test_snapshot_leads.json'
        _fixture(self.path)
        import_from_snapshot(self.path)
        self.client = Client(SERVER_NAME='rihan360.ir')

    def test_anonymous_redirected(self):
        r = self.client.get('/leads/panel/')
        self.assertEqual(r.status_code, 302)

    def test_staff_sees_panel_and_rows(self):
        self.client.force_login(self.admin)
        r = self.client.get('/leads/panel/')
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, '2.177.54.249')
        self.assertContains(r, 'سرنخ داغ فعال')
        self.assertContains(r, 'Tehran')

    def test_filters(self):
        self.client.force_login(self.admin)
        r = self.client.get('/leads/panel/?q=2.177')
        self.assertContains(r, '2.177.54.249')
        self.assertNotContains(r, '89.196.126.9')
        r = self.client.get('/leads/panel/?stage=CHECKOUT')
        self.assertContains(r, '89.196.126.9')
        self.assertNotContains(r, '2.177.54.249')
        r = self.client.get('/leads/panel/?hot=1')
        self.assertContains(r, '89.196.126.9')
        self.assertNotContains(r, '5.121.195.0')
        r = self.client.get('/leads/panel/?device=iOS')
        self.assertContains(r, '5.121.195.0')
        self.assertNotContains(r, '89.196.126.9')

    def test_status_change(self):
        self.client.force_login(self.admin)
        v = VisitorLead.objects.get(ip='89.196.126.9')
        r = self.client.post(f'/leads/panel/status/{v.id}/', {'status': 'CONTACTED'})
        self.assertEqual(r.status_code, 302)
        v.refresh_from_db()
        self.assertEqual(v.status, 'CONTACTED')
        self.assertFalse(v.hot_active)

    def test_csv_export(self):
        self.client.force_login(self.admin)
        r = self.client.get('/leads/panel/export/csv/')
        self.assertEqual(r.status_code, 200)
        body = r.content.decode('utf-8-sig')
        self.assertIn('2.177.54.249', body)
        self.assertIn('صفحه پرداخت', body)

    def test_refresh_button(self):
        self.client.force_login(self.admin)
        r = self.client.post('/leads/panel/refresh/')
        self.assertEqual(r.status_code, 302)
        self.assertEqual(VisitorLead.objects.count(), 3)

    def test_sidebar_has_link_and_badge(self):
        self.client.force_login(self.admin)
        r = self.client.get('/admin/')
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, '/leads/panel/')
        self.assertContains(r, 'داشبورد سرنخ‌های بازدید')
