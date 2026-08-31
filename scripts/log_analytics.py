#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# rihan full-history nginx analytics (D-117 algorithm extended)
import os, re, sys, json, gzip, time, datetime, collections, urllib.request

OUT = sys.argv[1] if len(sys.argv) > 1 else '/tmp/rihan_analytics.json'
LOG_DIR = '/var/log/nginx'
specs = [(f'{LOG_DIR}/access.log', False), (f'{LOG_DIR}/access.log.1', False)]
for i in range(2, 31):
    p = f'{LOG_DIR}/access.log.{i}.gz'
    if os.path.exists(p):
        specs.append((p, True))
specs.sort(key=lambda x: x[0])

LINE_RE = re.compile(r'^(\S+) \S+ \S+ \[([^\]]+)\] "([^"]*)" (\d{3}) (\d+|-) "([^"]*)" "([^"]*)"')
TS_RE = re.compile(r'(\d{2})/([A-Za-z]{3})/(\d{4}):(\d{2}):(\d{2}):(\d{2})')
MON = {'Jan':1,'Feb':2,'Mar':3,'Apr':4,'May':5,'Jun':6,'Jul':7,'Aug':8,'Sep':9,'Oct':10,'Nov':11,'Dec':12}

ASSET_EXT = ('.css','.js','.png','.jpg','.jpeg','.webp','.gif','.ico','.svg','.woff','.woff2','.ttf','.otf','.map','.avif','.mp4','.txt','.xml')
ASSET_PREFIX = ('/static/','/media/','/favicon','/robots.txt','/llms.txt','/sitemap','/ads.txt','/.well-known/','/apple-touch','/indexnow')
OWNER_RE = re.compile(r'^/(admin|supplier|finance)(/|$)|jsi18n')
PROBE_RE = re.compile(r'weblanguage|/sdk/|/cgi-bin/|gponform|boaform|/vendor/|wp-content|wp-login|wp-admin|/\.env|/\.git|phpmyadmin|/hello\.world|%2e\.%2e|%2e%2e|%252e|/actuator|/hnap|/dr0v|/payment/index\.php|_vti_bin|/owa/|autodiscover|/hudson|/manager/html|/api/v1/pops|\.php($|\?)|/setup$|/config$|/admin/config|/telescope|/vendor/phpunit|/solr/|/jenkins|/docker|/k8s|/metrics|/debug/|/\.aws|/\.ds_store|/id_rsa|/backup|/dump\.sql|/db\.sqlite|/server-status|/info\.php|/phpinfo', re.I)
BOT_UA_RE = re.compile(r'bot|crawl|spider|slurp|facebookexternalhit|facebot|embedly|zenlayer|semrush|ahrefs|mj12|dotbot|petalbot|bytespider|gptbot|oai-search|chatgpt|claude|anthropic|perplexity|applebot|amazonbot|meta-external|youbot|diffbot|imagesift|cohere|googlebot|bingbot|yandex|duckduck|baidu|telegram|whatsapp|discord|linkedin|twitterbot|slack|go-http|python|curl|wget|okhttp|java/|libwww|scrapy|headless|phantom|lighthouse|pagespeed|uptime|pingdom|zgrab|masscan|nikto|sqlmap|wappalyzer', re.I)
BOT_RANGE = ('173.252.','66.249.','74.125.','157.55.','40.77.','64.233.','69.171.','31.13.')

def parse_ts(s):
    m = TS_RE.search(s)
    if not m: return None
    d, mon, y, hh, mm, ss = m.groups()
    try:
        return datetime.datetime(int(y), MON[mon], int(d), int(hh), int(mm), int(ss))
    except Exception:
        return None

def is_asset(path):
    p = path.lower()
    if p.startswith(ASSET_PREFIX): return True
    return p.split('?')[0].endswith(ASSET_EXT)

def classify_page(path):
    p = path.lower().split('?')[0]
    if p.startswith('/p/'): return 'shortlink'
    if '/order/t/' in p or p.startswith('/order/tracking'): return 'tracking'
    if 'checkout' in p: return 'checkout'
    if '/cart' in p: return 'cart'
    if 'payment' in p: return 'payment'
    if 'receipt' in p or 'confirm' in p: return 'confirm'
    if 'product' in p: return 'product'
    if p in ('/', ''): return 'home'
    if 'login' in p: return 'login'
    if 'register' in p or 'signup' in p: return 'register'
    if 'search' in p or '?q=' in path or '?s=' in path: return 'search'
    if 'profile' in p or 'account' in p: return 'profile'
    if 'order' in p: return 'order_other'
    if any(k in p for k in ('faq','about','contact','blog','story')): return 'info'
    return 'other'

def ref_host(ref):
    m = re.match(r'https?://([^/]+)', ref or '')
    return m.group(1).lower() if m else None

def ref_channel(ref):
    h = ref_host(ref)
    if not h: return 'direct'
    if 'rihan360' in h: return 'internal'
    if 'instagram' in h or 'ig.me' in h: return 'instagram'
    if 't.me' in h or 'telegram' in h: return 'telegram'
    if 'whatsapp' in h or 'wa.me' in h: return 'whatsapp'
    if 'facebook' in h or 'fbclid' in ref or 'fb.me' in h: return 'facebook'
    if 'google' in h: return 'google'
    if 'bing' in h: return 'bing'
    if 'aparat' in h: return 'aparat'
    if 'torob' in h: return 'torob'
    if 'emalls' in h: return 'emalls'
    if 'youtube' in h or 'youtu.be' in h: return 'youtube'
    if 'twitter' in h or 'x.com' in h: return 'x'
    return 'ext:' + h

def device_of(ua):
    u = ua or ''
    if 'iPhone' in u or 'iPad' in u or ('iOS' in u and 'Mac' not in u): return 'iOS'
    if 'Android' in u: return 'Android'
    if 'Windows' in u: return 'Windows'
    if 'Macintosh' in u: return 'Mac'
    if 'Linux' in u: return 'Linux'
    return 'Other'

def geo_lookup(ips):
    res = {}
    chunks = [ips[i:i+100] for i in range(0, len(ips), 100)]
    for ci, chunk in enumerate(chunks):
        try:
            req = urllib.request.Request(
                'http://ip-api.com/batch/?fields=status,country,countryCode,city,isp,org,as,hosting,proxy,mobile,query',
                data=json.dumps(chunk).encode(), headers={'Content-Type': 'application/json'})
            with urllib.request.urlopen(req, timeout=30) as r:
                for row in json.loads(r.read().decode()):
                    res[row.get('query')] = row
            print(f'geo chunk {ci+1}/{len(chunks)} ok ({len(chunk)} ips)', file=sys.stderr)
        except Exception as e:
            print(f'geo chunk {ci+1} FAILED: {e}', file=sys.stderr)
        if len(chunk) == 100 and ci < len(chunks)-1: time.sleep(62)
    return res

def main():
    by_ip = collections.defaultdict(lambda: {'n':0,'assets':0,'posts':0,'first':None,'last':None,'reqs':[],'owner':False,'bot_ua':False,'bot_path':False,'range_bot':False})
    nlines = 0
    for path, gz in specs:
        opener = gzip.open if gz else open
        try:
            fh = opener(path, 'rt', errors='replace')
        except Exception as e:
            print(f'skip {path}: {e}', file=sys.stderr); continue
        with fh:
            for line in fh:
                nlines += 1
                m = LINE_RE.match(line)
                if not m: continue
                ip, tsl, req, st, by, ref, ua = m.groups()
                ts = parse_ts(tsl)
                if ts is None: continue
                parts = req.split(' ')
                method = parts[0] if parts else '-'
                p = parts[1] if len(parts) > 1 else '-'
                r = by_ip[ip]
                r['n'] += 1
                r['first'] = ts if r['first'] is None or ts < r['first'] else r['first']
                r['last'] = ts if r['last'] is None or ts > r['last'] else r['last']
                if method == 'POST': r['posts'] += 1
                if is_asset(p): r['assets'] += 1
                elif not p.startswith('/') or method not in ('GET','POST','HEAD'):
                    r['junk'] = r.get('junk', 0) + 1  # proxy probes / malformed request lines
                else:
                    r['reqs'].append((ts, method, p, int(st), ref))
                    r.setdefault('ua', ua)
                    if OWNER_RE.search(p): r['owner'] = True
                    if PROBE_RE.search(p): r['probe'] = True
                    if BOT_UA_RE.search(ua): r['bot_ua'] = True
                    lp = p.lower()
                    if lp in ('/robots.txt','/llms.txt','/sitemap.xml') or lp.startswith('/.well-known'): r['bot_path'] = True
                if ip.startswith(BOT_RANGE): r['range_bot'] = True
    print(f'parsed {nlines} lines, {len(by_ip)} unique ips', file=sys.stderr)

    geo_needed = []
    for ip, r in by_ip.items():
        if not r['owner'] and not r['bot_ua'] and not r['bot_path'] and not r['range_bot']:
            geo_needed.append(ip)
    geo_cache_path = '/tmp/rihan_geo_cache.json'
    cache = {}
    if os.path.exists(geo_cache_path):
        try:
            cache = json.load(open(geo_cache_path))
        except Exception:
            cache = {}
    geo_needed = sorted({ip for ip in geo_needed if ip not in cache})
    geo = dict(cache)
    geo.update(geo_lookup(geo_needed))
    try:
        json.dump(geo, open(geo_cache_path, 'w'))
    except Exception:
        pass

    visitors, bots = {}, []
    for ip, r in by_ip.items():
        g = geo.get(ip) or {}
        hosting = bool(g.get('hosting')) or bool(g.get('proxy'))
        if r['owner']:
            bots.append((ip, 'owner/staff'))
        elif r.get('probe'):
            bots.append((ip, 'exploit-probe'))
        elif r['bot_ua'] or r['bot_path'] or r['range_bot'] or hosting:
            bots.append((ip, 'bot/dc'))
        elif r['assets'] == 0 and r['n'] <= 4 and r['posts'] == 0:
            bots.append((ip, 'probe-no-assets'))
        elif not r['reqs']:
            bots.append((ip, 'junk/no-pages'))
        else:
            visitors[ip] = r

    TZ = datetime.timezone(datetime.timedelta(hours=3, minutes=30))
    sessions = []
    daily = collections.defaultdict(lambda: {'views':0, 'visitors':set()})
    hourly = collections.Counter()
    funnel = collections.Counter()
    funnel_post = collections.Counter()
    channels_first = collections.Counter()
    channels_all = collections.Counter()
    devices = collections.Counter()
    status_codes = collections.Counter()
    top_paths = collections.Counter()
    top_posts = collections.Counter()
    visitor_rows = []

    for ip, r in visitors.items():
        reqs = sorted(r['reqs'], key=lambda x: x[0])
        if not reqs:
            continue
        pages = [x for x in reqs if not is_asset(x[2])]
        uag = r.get('ua') or ''
        dev = device_of(uag)
        devices[dev] += 1
        # split sessions
        sess = []
        cur = [reqs[0]]
        for prev, nxt in zip(reqs, reqs[1:]):
            if (nxt[0] - prev[0]).total_seconds() > 1800:
                sess.append(cur); cur = [nxt]
            else:
                cur.append(nxt)
        sess.append(cur)
        s_rows = []
        ip_funnel = set()
        for s in sess:
            sp = [x for x in s if not is_asset(x[2])]
            kinds = [classify_page(x[2]) for x in sp]
            posts = [x for x in s if x[1] == 'POST']
            flags = {
                'pages': len(sp),
                'kinds': sorted(set(kinds)),
                'paths': sorted({x[2].split('?')[0] for x in sp})[:50],
                'posted': bool(posts),
                'post_paths': sorted({x[2] for x in posts}),
                'start': (s[0][0] + datetime.timedelta(hours=3, minutes=30)).strftime('%Y-%m-%d %H:%M'),
                'end': (s[-1][0] + datetime.timedelta(hours=3, minutes=30)).strftime('%Y-%m-%d %H:%M'),
                'mins': round((s[-1][0] - s[0][0]).total_seconds()/60, 1),
                'channels': sorted({ref_channel(x[4]) for x in sp if x[4] and ref_channel(x[4]) not in ('direct','internal')}),
                'status': sorted({x[3] for x in s}),
            }
            for k in kinds:
                ip_funnel.add(k)
                funnel[k] += 1
            for x in posts:
                funnel_post[classify_page(x[2])] += 1
                top_posts[x[1]+' '+x[2][:80]] += 1
            if sp:
                first_kind = kinds[0]
                first_ref = next((ref_channel(x[4]) for x in sp if x[4] and ref_channel(x[4]) not in ('direct','internal')), None)
                ch = first_ref or ('share_link' if first_kind == 'shortlink' else 'direct')
                channels_first[ch] += 1
            for x in sp:
                channels_all[ref_channel(x[4])] += 1
                top_paths[x[2].split('?')[0][:100]] += 1
                status_codes[x[3]] += 1
            d = (s[0][0] + datetime.timedelta(hours=3, minutes=30)).date().isoformat()
            daily[d]['views'] += len(sp)
            daily[d]['visitors'].add(ip)
            for x in s:
                hourly[(x[0] + datetime.timedelta(hours=3, minutes=30)).hour] += 1
            s_rows.append(flags)
        for k in ('product','cart','checkout','payment','confirm','shortlink','tracking','login','register','search','home'):
            if k in ip_funnel: funnel['ip:'+k] += 1
        ch_first = None
        for s0 in s_rows:
            if s0['channels']:
                ch_first = s0['channels'][0]; break
        if ch_first is None:
            ch_first = 'share_link' if 'shortlink' in ip_funnel else 'direct'
        g = geo.get(ip) or {}
        visitor_rows.append({
            'ip': ip,
            'geo': {'country': g.get('country'), 'city': g.get('city'), 'isp': g.get('isp'), 'mobile': g.get('mobile'), 'cc': g.get('countryCode')},
            'vpn_suspect': (g.get('countryCode') != 'IR'),
            'device': dev,
            'ua': uag[:120],
            'channel_first': ch_first,
            'first': (r['first'] + datetime.timedelta(hours=3, minutes=30)).strftime('%Y-%m-%d %H:%M'),
            'last': (r['last'] + datetime.timedelta(hours=3, minutes=30)).strftime('%Y-%m-%d %H:%M'),
            'views': len(pages),
            'sessions': s_rows,
            'kinds': sorted(ip_funnel),
        })
    visitor_rows.sort(key=lambda x: x['first'])
    result = {
        'generated': datetime.datetime.now(TZ).strftime('%Y-%m-%d %H:%M'),
        'log_files': [s[0] for s in specs],
        'totals': {
            'lines': nlines,
            'unique_ips_all': len(by_ip),
            'bot_or_owner_ips': len(bots),
            'visitor_ips': len(visitors),
            'visitor_sessions': sum(len(v['sessions']) for v in visitor_rows),
            'visitor_page_views': sum(v['views'] for v in visitor_rows),
        },
        'bots': [{'ip': ip, 'why': w, 'n': by_ip[ip]['n']} for ip, w in bots],
        'daily': {d: {'views': v['views'], 'visitors': len(v['visitors'])} for d, v in sorted(daily.items())},
        'hourly_tehran': dict(sorted(hourly.items())),
        'funnel_page_kinds': dict(funnel.most_common()),
        'funnel_posts': dict(funnel_post.most_common()),
        'channels_first_entry': dict(channels_first.most_common()),
        'channels_all': dict(channels_all.most_common()),
        'devices': dict(devices),
        'status_codes': dict(status_codes.most_common()),
        'top_paths': dict(top_paths.most_common(80)),
        'top_posts': dict(top_posts.most_common(40)),
        'visitors': visitor_rows,
    }
    with open(OUT, 'w') as f:
        json.dump(result, f, ensure_ascii=False, default=str)
    t = result['totals']
    print('VISITORS:', t['visitor_ips'], 'SESSIONS:', t['visitor_sessions'], 'VIEWS:', t['visitor_page_views'], 'BOTS:', t['bot_or_owner_ips'])
    print('written', OUT)

if __name__ == '__main__':
    main()
