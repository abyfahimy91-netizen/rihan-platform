# -*- coding: utf-8 -*-
"""D-125: موtor import سrnх-hay basdid az snapshot talil lag nginx.

Snapshot tavasat scripts/log_analytics.py rooye host tolid mishavad
(va ba docker cp daxel kontiner miayad). Har visitor = yek VisitorLead.
"""
import json
import re
import datetime

from django.core.cache import cache
from django.utils import timezone

from .models import VisitorLead

ORDER_CODE_RE = re.compile(r'RH-\d{4}-\d{5}')

# kind dar snapshot → marhal
KIND2STAGE = {
    'shortlink': 'PRODUCT', 'product': 'PRODUCT', 'search': 'PRODUCT',
    'cart': 'CART',
    'checkout': 'CHECKOUT',
    'payment': 'PAYMENT', 'confirm': 'PAYMENT',
}

PAID_STATUSES = {'PAID', 'PAYMENT_CONFIRMED', 'PROCESSING', 'SHIPPED', 'DELIVERED'}

SNAPSHOT_CACHE_KEY = 'leads_snapshot_meta'


def _order_model():
    from django.apps import apps
    return apps.get_model('order', 'Order')


def _parse_dt(s):
    if not s:
        return None
    try:
        # زمان‌های snapshot به وقت تهران هستند → aware بساز
        return datetime.datetime.fromisoformat(s).replace(
            tzinfo=datetime.timezone(datetime.timedelta(hours=3, minutes=30)))
    except Exception:
        return None


def import_from_snapshot(path):
    """Snapshot-ra mixanad va VisitorLead-ha ra update_or_create mikonad.

    Returns: dict {created, updated, converted, hot, visitors}
    """
    with open(path, 'r') as f:
        data = json.load(f)

    Order = _order_model()
    order_status = dict(Order.objects.values_list('order_number', 'status'))

    created = updated = converted = hot = 0
    now = timezone.now()

    for v in data.get('visitors', []):
        ip = v.get('ip')
        if not ip:
            continue
        kinds = set(v.get('kinds', []))
        paths = set()
        posts = []
        sessions_compact = []
        for s in v.get('sessions', [])[:20]:
            kinds |= set(s.get('kinds', []))
            paths |= set(s.get('paths', []))
            posts += s.get('post_paths', [])
            sessions_compact.append({
                'start': s.get('start'), 'end': s.get('end'),
                'pages': s.get('pages'), 'kinds': s.get('kinds', []),
                'posted': s.get('posted', False),
            })
        order_refs = sorted(set(ORDER_CODE_RE.findall(' '.join(posts)) + ORDER_CODE_RE.findall(' '.join(paths))))
        orders_matched = [
            {'number': num, 'status': order_status.get(num, '?')}
            for num in order_refs if num in order_status
        ]
        is_converted = any(m['status'] in PAID_STATUSES for m in orders_matched)

        if is_converted:
            stage = 'CONVERTED'
        elif 'payment' in kinds or 'confirm' in kinds:
            stage = 'PAYMENT'
        elif 'checkout' in kinds:
            stage = 'CHECKOUT'
        elif 'cart' in kinds:
            stage = 'CART'
        elif kinds & {'product', 'shortlink', 'search'}:
            stage = 'PRODUCT'
        else:
            stage = 'HOME'

        geo = v.get('geo') or {}
        obj, was_created = VisitorLead.objects.update_or_create(
            ip=ip,
            defaults=dict(
                country=geo.get('country') or '',
                city=geo.get('city') or '',
                isp=(geo.get('isp') or '')[:120],
                is_vpn=bool(v.get('vpn_suspect')),
                device=(v.get('device') or '')[:20],
                channel_first=(v.get('channel_first') or 'direct')[:40],
                channels=v.get('sessions') and sorted({c for s in v['sessions'] for c in (s.get('channels') or [])}) or [],
                first_seen=_parse_dt(v.get('first')) or now,
                last_seen=_parse_dt(v.get('last')) or now,
                sessions_count=len(v.get('sessions', [])),
                page_views=int(v.get('views') or 0),
                stage=stage,
                stage_rank=VisitorLead.StageRank[stage],
                is_hot=(stage in ('CHECKOUT', 'PAYMENT')) and not is_converted,
                actions={'posts': len(posts), 'post_paths': sorted(set(p.split('?')[0] for p in posts))[:20]},
                order_refs=', '.join(order_refs)[:200],
                orders_matched=orders_matched,
                sessions=sessions_compact,
            ),
        )
        if was_created:
            created += 1
        else:
            updated += 1
        if is_converted:
            converted += 1
        if obj.is_hot and obj.status == VisitorLead.LeadStatus.NEW:
            hot += 1

    meta = {
        'generated': data.get('generated'),
        'imported_at': now.isoformat(),
        'totals': data.get('totals', {}),
        'log_files': data.get('log_files', []),
    }
    cache.set(SNAPSHOT_CACHE_KEY, meta, None)
    # کش per-process است؛ نسخهٔ پایدار روی فایل هم نوشته می‌شود
    try:
        with open('/tmp/rihan_snapshot_meta.json', 'w') as f:
            json.dump(meta, f)
    except Exception:
        pass
    return {'created': created, 'updated': updated, 'converted': converted,
            'hot': hot, 'visitors': len(data.get('visitors', [])),
            'meta': meta}


def funnel_counts():
    """Tedad lead-ha ke be har marhale reside-and (stage_rank >= marhale)."""
    qs = VisitorLead.objects.all()
    out = []
    for stage, rank, _label in VisitorLead.STAGES:
        out.append({'stage': stage, 'label': _label, 'rank': rank,
                    'count': qs.filter(stage_rank__gte=rank).count()})
    return out
