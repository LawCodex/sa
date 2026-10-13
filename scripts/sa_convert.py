#!/usr/bin/env python3
"""Convert cached BOE law pages (see sa_fetch.py) to LawCodex Markdown.

Usage: sa_convert.py RAW_DIR REPO_DIR
"""
import collections, datetime, glob, json, os, re, sys
from bs4 import BeautifulSoup, NavigableString, Tag

AR_DIGITS = str.maketrans('٠١٢٣٤٥٦٧٨٩', '0123456789')
TODAY = datetime.date.today().isoformat()

CATEGORIES = {
    'أنظمة أساسية': 'basic-laws',
    'أنظمة عادية': 'laws',
    'تنظيمات، وترتيبات تنظيمية': 'organizational-statutes',
    'لوائح وما في حكمها': 'regulations',
}
TYPES = {'basic-laws': 'basic_law', 'laws': 'law', 'organizational-statutes': 'organizational_statute',
         'regulations': 'regulation', 'other': 'other'}
INSTRUMENTS = [  # (regex on instrument text, slug)
    (r'مرسوم\s*ملكي', 'royal-decree'),
    (r'أمر\s*ملكي', 'royal-order'),
    (r'أمر\s*سامي', 'high-order'),
    (r'قرار\s*مجلس\s*الوزراء', 'council-of-ministers-resolution'),
    (r'قرار\s*مجلس\s*الشورى', 'shura-council-resolution'),
    (r'قرار\s*وزاري|قرار\s*وزير|قرار\s*معالي', 'ministerial-resolution'),
    (r'قرار', 'resolution'),
]
TRANSLIT = {'م': 'm', 'أ': 'a', 'ا': 'a', 'إ': 'a', 'ب': 'b', 'ت': 't', 'ج': 'j', 'د': 'd', 'ر': 'r',
            'س': 's', 'ش': 'sh', 'ص': 's', 'ع': 'a', 'ف': 'f', 'ق': 'q', 'ك': 'k', 'ل': 'l', 'ن': 'n',
            'هـ': 'h', 'ه': 'h', 'و': 'w', 'ي': 'y', 'ح': 'h', 'خ': 'kh', 'ط': 't', 'ز': 'z'}
SECTION_RANK = [('الكتاب', 0), ('القسم', 1), ('الباب', 2), ('الفصل', 3), ('الفرع', 4), ('المبحث', 5),
                ('PART', 2), ('Part', 2), ('Chapter', 3), ('CHAPTER', 3), ('Section', 4), ('SECTION', 4)]


def clean(s):
    return re.sub(r'[ \t ]+', ' ', s).strip()


def yq(s):
    return '"' + str(s).replace('\\', '\\\\').replace('"', '\\"') + '"'


def to_iso(s):
    m = re.search(r'(\d{1,2})/(\d{1,2})/(\d{4})\s*م', s.translate(AR_DIGITS))
    if m:
        try:
            return datetime.date(int(m.group(3)), int(m.group(2)), int(m.group(1))).isoformat()
        except ValueError:
            return None
    return None


def hijri(s):
    m = re.search(r'(\d{4})/(\d{1,2})/(\d{1,2})', s.translate(AR_DIGITS))
    return f'{m.group(1)}-{int(m.group(2)):02d}-{int(m.group(3)):02d}' if m else None


def inline(node):
    """Inline HTML -> Markdown-ish text (br = newline)."""
    out = []
    for c in node.children:
        if isinstance(c, NavigableString):
            if c.__class__.__name__ in ('Comment', 'Doctype'):
                continue
            out.append(re.sub(r'\s+', ' ', str(c)))
        elif isinstance(c, Tag):
            if c.name == 'br':
                out.append('\n')
            elif c.name in ('script', 'style'):
                continue
            elif c.name in ('strong', 'b'):
                t = inline(c)
                out.append(f'**{t.strip()}**' if t.strip() and '\n' not in t.strip() else t)
            elif c.name == 'table':
                out.append('\n\n' + table(c) + '\n\n')
            elif c.name in ('p', 'div', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'ul', 'ol', 'center', 'tr'):
                out.append('\n\n' + inline(c) + '\n\n')
            else:
                out.append(inline(c))
    return ''.join(out)


def table(t):
    rows = []
    for tr in t.find_all('tr'):
        cells = tr.find_all(['td', 'th'], recursive=False)
        if any(c.get('rowspan') or c.get('colspan') for c in cells):
            return str(t)
        rows.append([clean(inline(c)).replace('\n', '<br>').replace('|', '\\|') for c in cells])
    if not rows:
        return ''
    n = max(len(r) for r in rows)
    rows = [r + [''] * (n - len(r)) for r in rows]
    md = ['| ' + ' | '.join(rows[0]) + ' |', '|' + ' --- |' * n]
    md += ['| ' + ' | '.join(r) + ' |' for r in rows[1:]]
    return '\n'.join(md)


def paras(text):
    lines = [clean(l) for l in text.split('\n')]
    out, blank = [], True
    for l in lines:
        if not l:
            if not blank:
                out.append('')
            blank = True
            continue
        out.append(l)
        blank = False
    # keep each source line as its own paragraph (Markdown needs a blank line)
    res = []
    for l in out:
        if l == '':
            continue
        res.append(l)
    return '\n\n'.join(res)


def section_rank(text):
    t = text.strip()
    for k, r in SECTION_RANK:
        if t.startswith(k):
            return r
    return None


def parse_info(s):
    info = {}
    for d in s.select('.system_info > div'):
        lab = d.find('label')
        if not lab:
            continue
        k = lab.get_text(strip=True)
        if d.find('ul'):
            info[k] = [clean(li.get_text(' ', strip=True)) for li in d.find_all('li')]
        else:
            sp = d.find('span')
            info[k] = clean(sp.get_text(' ', strip=True)) if sp else ''
    return info


def instrument_slug(instr):
    t = instr.translate(AR_DIGITS)
    kind = None
    for rx, slug in INSTRUMENTS:
        if re.search(rx, t):
            kind = slug
            break
    m = re.search(r'رقم\s*\(?\s*([^\s()]+(?:\s*/\s*[^\s()]+)?)\s*\)?\s*(?:بتاريخ|وتاريخ|في|و?تاريخ)', t)
    y = re.search(r'(1[34]\d\d)\s*(?:هـ|$)', t) or re.search(r'\b(1[34]\d\d)\b', t)
    if not (kind and m and y):
        return None, None
    num = m.group(1).replace(' ', '')
    parts = []
    for ch in num:
        if ch.isdigit():
            parts.append(ch)
        elif ch in '/-':
            parts.append('-')
        elif ch in TRANSLIT:
            parts.append(TRANSLIT[ch])
    num = re.sub(r'-+', '-', ''.join(parts)).strip('-')
    if not num:
        return None, None
    return f'{y.group(1)}-{kind}-{num}', y.group(1)


def body_md(s):
    root = s.select_one('#divLawText')
    kids = root.find_all(recursive=False)
    if len(kids) == 1 and kids[0].name == 'div' and not kids[0].get('class'):
        kids = kids[0].find_all(recursive=False)
    # determine section levels
    ranks = sorted({r for k in kids if k.name in ('h2', 'h3', 'h4') and 'center' in (k.get('class') or [])
                    for r in [section_rank(k.get_text(' ', strip=True))] if r is not None})
    lvl = {r: min(3 + i, 5) for i, r in enumerate(ranks)}
    art_level = min(3 + len(ranks), 6)
    out = []
    seen_title = False
    for k in kids:
        cls = k.get('class') or []
        if k.name == 'div' and k.find('h1', class_='system_title'):
            out.append('## ' + clean(k.get_text(' ', strip=True)))
            seen_title = True
            continue
        if k.name == 'h1':
            out.append('## ' + clean(k.get_text(' ', strip=True)))
            seen_title = True
            continue
        if 'article_item' in cls:
            h = k.find(['h3', 'h4'], recursive=False)
            head = clean(h.get_text(' ', strip=True)) if h else ''
            if head:
                out.append('#' * art_level + ' ' + head.rstrip(':').strip() if art_level <= 6 else f'**{head}**')
            for c in k.find_all(recursive=False):
                ccls = c.get('class') or []
                if 'HTMLContainer' in ccls:
                    t = paras(inline(c))
                    if t:
                        out.append(t)
            pop = k.find(class_='popup-list')
            if pop:
                notes = []
                for p in pop.find_all(class_='article_item_popup'):
                    hc = p.find(class_='HTMLContainer')
                    if hc:
                        t = paras(inline(hc))
                        if t:
                            notes.append(t)
                if notes:
                    label = 'تعديلات المادة' if re.search(r'[؀-ۿ]', head) else 'Amendments'
                    block = [f'**{label}:**'] + notes
                    out.append('\n>\n'.join('> ' + x.replace('\n\n', '\n>\n> ') for x in block))
            continue
        if k.name in ('h2', 'h3', 'h4', 'h5'):
            t = clean(k.get_text(' ', strip=True))
            if not t:
                continue
            r = section_rank(t)
            if seen_title and r is not None:
                out.append('#' * lvl[r] + ' ' + t)
            else:
                out.append(f'**{t}**')
            continue
        if k.name in ('script', 'style'):
            continue
        t = paras(inline(k)) if k.name != 'table' else table(k)
        if t:
            out.append(t)
    return '\n\n'.join(out)


def convert(path):
    html = open(path, encoding='utf-8').read()
    meta = json.load(open(path[:-5] + '.json'))
    s = BeautifulSoup(html, 'lxml')
    info = parse_info(s)
    bc = [clean(b.get_text(' ', strip=True)) for b in s.select('ol.breadcrumb li, .bread_crumb li')]
    return s, info, bc, meta


def main():
    raw, repo = sys.argv[1], sys.argv[2]
    docs = {}
    for f in sorted(glob.glob(os.path.join(raw, 'html', '*_ar.html'))):
        guid = os.path.basename(f)[:-8]
        s, info, bc, meta = convert(f)
        docs[guid] = (s, info, bc, meta)
    # assign paths
    used = collections.Counter()
    plan = {}
    for guid, (s, info, bc, meta) in docs.items():
        cat = CATEGORIES.get(bc[1] if len(bc) > 1 and bc[0] == 'الوثائق النظامية' else '')
        if not cat:  # older page layout (volumes of the Saudi Laws collection): classify by title
            t = info.get('الاسم', '')
            cat = ('laws' if re.match(r'(ال)?نظام', t) else
                   'regulations' if re.match(r'(ال)?(لائحة|قواعد|ضوابط)', t) else
                   'organizational-statutes' if re.match(r'(ال)?(تنظيم|ترتيبات)', t) else 'other')
        instr = info.get('أدوات إصدار النظام') or []
        if isinstance(instr, str):
            instr = [instr]
        slug, year = (None, None)
        for i in instr:
            slug, year = instrument_slug(i)
            if slug:
                break
        if not slug:
            h = hijri(info.get('تاريخ الإصدار', '')) or ''
            year = h[:4] or 'unknown'
            slug = f'{year}-boe-{guid[:8]}'
        plan[guid] = [cat, year, slug]
        used[(cat, slug)] += 1
    for guid, p in plan.items():
        if used[(p[0], p[2])] > 1:
            p[2] = p[2] + '-' + guid[:8]
    counts = collections.Counter()
    index = []
    for guid, (s, info, bc, meta) in sorted(docs.items()):
        cat, year, slug = plan[guid]
        for lang in ('ar', 'en'):
            if lang == 'ar':
                ss, ii, bb, mm = s, info, bc, meta
            else:
                f = os.path.join(raw, 'html', f'{guid}_en.html')
                if not os.path.exists(f):
                    continue
                ss, ii, bb, mm = convert(f)
            title = ii.get('الاسم') or clean(ss.select_one('#divLawText h3').get_text(' ', strip=True))
            status_raw = ii.get('الحالة', '')
            status = 'repealed' if 'لاغ' in status_raw or 'ملغ' in status_raw else (
                'in_force' if 'ساري' in status_raw else 'unknown')
            body = body_md(ss)
            if len(body) < 40:
                print('EMPTY', guid, lang, file=sys.stderr)
                continue
            instr = ii.get('أدوات إصدار النظام') or []
            if isinstance(instr, str):
                instr = [instr]
            fm = ['---', f'title: {yq(title)}', f'identifier: {yq(guid)}',
                  f'type: {TYPES[cat]}', 'jurisdiction: sa', f'language: {lang}']
            d = to_iso(ii.get('تاريخ الإصدار', ''))
            if d:
                fm.append(f'date: {d}')
            h = hijri(ii.get('تاريخ الإصدار', ''))
            if h:
                fm.append(f'date_hijri: {yq(h)}')
            p = to_iso(ii.get('تاريخ النشر', ''))
            if p:
                fm.append(f'published: {p}')
            if instr:
                fm.append('issued_by:')
                fm += ['  - ' + yq(x) for x in instr]
            fm.append(f'status: {status}')
            if status_raw:
                fm.append(f'status_label: {yq(status_raw)}')
            if bb:
                fm.append(f'category: {yq(" > ".join(bb[1:-1]) if len(bb) > 2 else bb[-1])}')
            src = f'https://laws.boe.gov.sa/BoeLaws/Laws/LawDetails/{guid}/{1 if lang == "ar" else 2}'
            fm.append(f'source: {yq(src)}')
            fm.append(f'archived_source: {yq(mm["archive_url"])}')
            ts = mm['timestamp']
            fm.append(f'archived: {ts[:4]}-{ts[4:6]}-{ts[6:8]}')
            fm.append(f'retrieved: {TODAY}')
            if lang == 'en':
                fm.append('translation: "Official English translation published by the Bureau of Experts at the Council of Ministers"')
            fm.append('---')
            sub = cat if cat == 'basic-laws' else f'{cat}/{year}'
            out = os.path.join(repo, lang, sub, slug + '.md')
            os.makedirs(os.path.dirname(out), exist_ok=True)
            with open(out, 'w', encoding='utf-8', newline='\n') as fh:
                fh.write('\n'.join(fm) + '\n\n# ' + title + '\n\n' + body.strip() + '\n')
            counts[(lang, cat, status)] += 1
            index.append((lang, cat, year, slug, title, status))
    for k in sorted(counts):
        print(k, counts[k])
    json.dump(index, open(os.path.join(raw, 'index.json'), 'w'), ensure_ascii=False)


if __name__ == '__main__':
    main()
