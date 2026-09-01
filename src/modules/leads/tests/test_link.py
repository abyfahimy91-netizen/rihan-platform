# -*- coding: utf-8 -*-
"""D-126: تست اتصال بدون اصطکاک لیدها (واتساپ-کد + اتصال اعضا)."""
import datetime
import json
import uuid

from django.apps import apps
from django.contrib.auth import get_user_model
from django.test import Client, TestCase

from src.modules.leads.analytics import import_from_snapshot
from src.modules.leads.models import VisitorLead
from src.modules.leads import support

DeviceToken = apps.get_model('rihan_auth', 'DeviceToken')
User = get_user_model()


class SupportCodeTests(TestCase):
    def setUp(self):
        from src.modules.pages.models import SiteSettings
        s = SiteSettings.objects.first() or SiteSettings.objects.create()
        s.whatsapp_number = '989143183790'
        s.save(update_fields=['whatsapp_number'])
        VisitorLead.objects.create(ip='2.177.54.249', stage='CART', stage_rank=3)

    def test_code_generated_and_wa_url(self):
        c = Client(SERVER_NAME='rihan360.ir', HTTP_X_FORWARDED_FOR='2.177.54.249')
        r = c.get('/leads/support-code/', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(r.status_code, 200)
        d = r.json()
        self.assertTrue(d['ok'])
        self.assertEqual(len(d['code']), 6)
        self.assertIn('wa.me/989143183790', d['wa_url'])
        self.assertIn(d['code'], d['wa_url'])
        lead = VisitorLead.objects.get(ip='2.177.54.249')
        self.assertEqual(lead.link_code, d['code'])

    def test_code_reused_not_regenerated(self):
        c = Client(SERVER_NAME='rihan360.ir', HTTP_X_FORWARDED_FOR='2.177.54.249')
        c.get('/leads/support-code/', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        first = VisitorLead.objects.get(ip='2.177.54.249').link_code
        c.get('/leads/support-code/', HTTP_X_REQUESTED_WITH='XMLHttpRequest')
        self.assertEqual(VisitorLead.objects.get(ip='2.177.54.249').link_code, first)

    def test_non_ajax_rejected(self):
        c = Client(SERVER_NAME='rihan360.ir')
        r = c.get('/leads/support-code/')
        self.assertEqual(r.status_code, 400)

    def test_panel_link_flow(self):
        admin = User.objects.create_user('flink', password='x', is_staff=True, is_superuser=True)
        lead = VisitorLead.objects.get(ip='2.177.54.249')
        lead.link_code = 'AB23CD'
        lead.save(update_fields=['link_code'])
        c = Client(SERVER_NAME='rihan360.ir')
        c.force_login(admin)
        r = c.post(f'/leads/panel/link/{lead.id}/', {'phone': '۰۹۱۴۳۲۶۲۱۹۹', 'name': 'سعید'})
        self.assertEqual(r.status_code, 302)
        lead.refresh_from_db()
        self.assertEqual(lead.phone, '09143262199')
        self.assertEqual(lead.name, 'سعید')
        self.assertEqual(lead.status, 'CONTACTED')

    def test_link_registered_users_by_devicetoken(self):
        u = User.objects.create_user('09143183790', password='x', first_name='ندا', last_name='عباسپور')
        DeviceToken.objects.create(user=u, token_hash='h1', device_fingerprint='fp1',
                                   user_agent='test', ip_address='89.196.126.9',
                                   expires_at=datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=30))
        DeviceToken.objects.create(user=u, token_hash='h2', device_fingerprint='fp2',
                                   user_agent='test', ip_address='5.121.195.0',
                                   expires_at=datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=30))
        VisitorLead.objects.create(ip='89.196.126.9', stage='CART', stage_rank=3)
        VisitorLead.objects.create(ip='5.121.195.0', stage='CART', stage_rank=3)
        n = support.link_registered_users()
        self.assertEqual(n, 2)
        l1 = VisitorLead.objects.get(ip='89.196.126.9')
        self.assertEqual(l1.phone, '09143183790')
        self.assertIn('ندا', l1.name)
        # اجرای دوباره = بدون کار تکراری
        self.assertEqual(support.link_registered_users(), 0)
