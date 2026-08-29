"""
رندر متن سادهٔ چندخطی (ویرایش‌شده در پنل ادمین) به HTML امن — D-100.

قواعد نشانه‌گذاری سبک:
  - خط خالی   → جداکنندهٔ بلوک (پاراگراف جدید)
  - # متن     → تیتر بخش
  - > متن     → نقل‌قول برجسته
  - - متن     → فهرست نقطه‌ای (چند خط پشت‌سرهم)
  - ۱. متن    → فهرست شماره‌ای (ارقام فارسی یا لاتین)
  - | a | b | → جدول؛ سطر اول = سرستون (بلوک پشت‌سرهم)؛ سطر جداکنندهٔ |---| نادیده گرفته می‌شود
  - بقیه      → پاراگراف معمولی

همهٔ خط‌ها قبل از ساخت HTML escape می‌شوند؛ هیچ HTML خامی از ورودی اجرا نمی‌شود.
"""
import html
import re

_NUM_MARK = re.compile(r'^[0-9۰-۹]+[.)]\s*')
_DASH_CHARS = ('-', '•', '*')


def _clean_dash(line: str) -> str:
    return line.lstrip('-•*').strip()


def render_page_markup(text: str) -> str:
    """متن چندخطی ادمین را به HTML امن و ساختارمند تبدیل می‌کند."""
    if not text or not text.strip():
        return ''

    out = []
    for block in re.split(r'\n\s*\n', text.strip()):
        lines = [ln.strip() for ln in block.splitlines() if ln.strip()]
        if not lines:
            continue

        # تیتر بخش
        if all(ln.startswith('#') for ln in lines):
            for ln in lines:
                out.append('<h2 class="pm-heading">%s</h2>' % html.escape(ln[1:].strip()))
            continue

        # فهرست نقطه‌ای
        if all(ln[0] in _DASH_CHARS for ln in lines):
            items = ''.join(
                '<li>%s</li>' % html.escape(_clean_dash(ln)) for ln in lines
            )
            out.append('<ul class="pm-list">%s</ul>' % items)
            continue

        # فهرست شماره‌ای (۱. / 1. / ۱) ...)
        if all(_NUM_MARK.match(ln) for ln in lines):
            items = ''.join(
                '<li>%s</li>' % html.escape(_NUM_MARK.sub('', ln).strip())
                for ln in lines
            )
            out.append('<ol class="pm-olist">%s</ol>' % items)
            continue

        # نقل‌قول برجسته
        if all(ln.startswith('>') for ln in lines):
            inner = ' '.join(html.escape(ln[1:].strip()) for ln in lines)
            out.append('<blockquote class="pm-quote">%s</blockquote>' % inner)
            continue

        # جدول (D-118 GEO): همهٔ خط‌ها با | شروع شوند؛ سطر اول = سرستون
        if all(ln.startswith('|') for ln in lines):
            rows = []
            for ln in lines:
                cells = [c.strip() for c in ln.strip().strip('|').split('|')]
                # سطر جداکنندهٔ سبک مارک‌داون (|---|---|) نادیده گرفته می‌شود
                if cells and all(re.fullmatch(r':?-{2,}:?', c) for c in cells):
                    continue
                rows.append([html.escape(c) for c in cells])
            if not rows:
                continue
            head, body = rows[0], rows[1:]
            parts = ['<div class="pm-table-wrap"><table class="pm-table">']
            if any(head):
                parts.append('<thead><tr>%s</tr></thead>' % ''.join('<th>%s</th>' % c for c in head))
            parts.append('<tbody>')
            parts += ['<tr>%s</tr>' % ''.join('<td>%s</td>' % c for c in r) for r in body]
            parts.append('</tbody></table></div>')
            out.append(''.join(parts))
            continue

        # پاراگراف معمولی
        out.append('<p class="pm-p">%s</p>' % ' '.join(html.escape(ln) for ln in lines))

    return '\n'.join(out)
