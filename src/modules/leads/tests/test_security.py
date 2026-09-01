# -*- coding: utf-8 -*-
"""D-127: تست امنیتی قابلیت واتساپ-کد (throttle/kill-switch/جعل IP)."""
import datetime
import json

from django.apps import apps
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import Client, TestCase

from src.modules.leads.models import VisitorLead
from src.modules.leads import support
from src.modules.pages.models import SiteSettings

DeviceToken = apps.get_model('rihan_auth', 'DeviceToken')
User = get_user_model()


class WafabSecurityTests(TestCase):
    def setUp(self):
        cache.clear()
        s = SiteSettings.load()
        s.whatsapp_number = '989143183790'
        s.wa_fab_enabled = True
        s.save(update_fields=['whatsapp_number', 'wa_fab_enabled'])
        self.lead = VisitorLead.objects.create(ip='2.177.54.249', stage='CART', stage_rank=3)

    def _client(self, ip='2.177.54.249', fake_xff=None):
        # X-Real-IP را شبیه nginx واقعی ست می‌کنیم
        return Client(SERVER_NAME='rihan360.ir', HTTP_X_REAL_IP=ip,
                      **({'HTTP_X_FORWARDED_FOR': fake_xff} if fake_xff else {}))

    def test_disabled_returns_404_and_hides_fab(self):
        s = SiteSettings.load()
        s.wa_fab_enabled = False
        s.save(update_fields=['wa_fab_enabled'])
        r = self._client().get('/leads/support-code/', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(r.status_code, 404)
        r = self._client().get('/order/cart/')
        self.assertNotContains(r, 'waFab')
        # روشن شود → دکمه هست
        s.wa_fab_enabled = True
        s.save(update_fields=['wa_fab_enabled'])
        r = self._client().get('/order/cart/')
        self.assertContains(r, 'waFab')

    def test_per_ip_throttle_30_per_hour(self):
        c = self._client()
        codes = set()
        for i in range(31):
            r = c.get('/leads/support-code/', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
            if i < 30:
                self.assertEqual(r.status_code, 200)
                codes.add(r.json()['code'])
            else:
                self.assertEqual(r.status_code, 429)
        # کد یکتا per IP: همهٔ پاسخ‌های موفق یک کد ثابت دارند
        self.assertEqual(len(codes), 1)

    def test_global_throttle_600(self):
        cache.set('wa_code_rl:__global__', support.RL_GLOBAL, 3600)
        r = self._client().get('/leads/support-code/', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(r.status_code, 429)

    def test_spoofed_xff_cannot_create_lead_for_other_ip(self):
        """کلاینت XFF جعلی می‌فرستد → IP واقعی از X-Real-IP خوانده می‌شود."""
        c = self._client(ip='5.6.7.8', fake_xff='1.2.3.4, 10.0.0.1')
        r = c.get('/leads/support-code/', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(r.status_code, 200)
        # سرنخ ساخته‌شده باید برای 5.6.7.8 باشد نه 1.2.3.4
        self.assertFalse(VisitorLead.objects.filter(ip='1.2.3.4').exists())
        self.assertTrue(VisitorLead.objects.filter(ip='5.6.7.8').exists())

    def test_max_leads_cap(self):
        from unittest.mock import patch
        with patch.object(VisitorLead.objects, 'count', return_value=support.MAX_LEADS):
            c = self._client(ip='9.9.9.9')
            r = c.get('/leads/support-code/', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
            self.assertEqual(r.status_code, 429)
            self.assertFalse(VisitorLead.objects.filter(ip='9.9.9.9').exists())

    def test_import_links_registered_users(self):
        """import_log_leads در پایان اتصال خودکار اعضا را اجرا می‌کند."""
        from src.modules.leads.analytics import import_from_snapshot
        u = User.objects.create_user('09143183790', first_name='ندا', last_name='عباسپور')
        DeviceToken.objects.create(user=u, token_hash='h9', device_fingerprint='fp',
                                   user_agent='ua', ip_address='6.6.6.6',
                                   expires_at=datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=7))
        snap = {
            'generated': 't', 'totals': {}, 'log_files': [],
            'visitors': [{'ip': '6.6.6.6',
                          'geo': {'country': 'Iran', 'city': 'Tehran', 'isp': 'MCI', 'cc': 'IR'},
                          'vpn_suspect': False, 'device': 'iOS', 'ua': 'x', 'channel_first': 'direct',
                          'first': '2026-08-30 10:00', 'last': '2026-08-30 11:00',
                          'views': 5, 'kinds': ['home', 'product'],
                          'sessions': [{'start': '2026-08-30 10:00', 'end': '2026-08-30 11:00',
                                        'pages': 5, 'kinds': ['home', 'product'], 'posted': False,
                                        'post_paths': [], 'paths': ['/'], 'channels': [],
                                        'status': [200], 'mins': 60}]}],
        }
        p = '/tmp/test_snapshot_link.json'
        with open(p, 'w') as f:
            json.dump(snap, f)
        stats = import_from_snapshot(p)
        self.assertEqual(stats['linked'], 1)
        lead = VisitorLead.objects.get(ip='6.6.6.6')
        self.assertEqual(lead.phone, '09143183790')
