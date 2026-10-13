#!/usr/bin/env python3
"""Fetch Saudi laws from Internet Archive copies of laws.boe.gov.sa (Bureau of Experts).

laws.boe.gov.sa is not reachable from the network this corpus was built on (connection
timeouts), so the latest Wayback Machine capture of each law page is used instead.

Usage: sa_fetch.py RAW_DIR
  RAW_DIR/cdx_lawdetails.txt  CDX listing (downloaded if missing)
  RAW_DIR/html/<guid>_<lang>.html  cached raw captures (+ .json with capture metadata)
"""
import json, os, re, sys, time, urllib.parse
import requests

UA = "LawCodex/1.0 (+https://github.com/LawCodex)"
CDX = ("https://web.archive.org/cdx/search/cdx?url=laws.boe.gov.sa/BoeLaws/Laws/LawDetails/"
       "&matchType=prefix&fl=original,timestamp,statuscode,length&filter=statuscode:200")
AR_DIGITS = str.maketrans('٠١٢٣٤٥٦٧٨٩', '0123456789')
GUID = r'([0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12})'

S = requests.Session()
S.headers['User-Agent'] = UA


def get(url, timeout=120):
    delay = 10
    for attempt in range(12):
        try:
            r = S.get(url, timeout=timeout)
            if r.status_code == 200:
                return r
            if r.status_code == 404:
                return None
            print('  HTTP', r.status_code, url, file=sys.stderr)
        except requests.RequestException as e:
            print('  ERR', type(e).__name__, url, file=sys.stderr)
        time.sleep(delay)
        delay = min(delay * 2, 300)
    return None


def load_cdx(raw):
    path = os.path.join(raw, 'cdx_lawdetails.txt')
    if not os.path.exists(path):
        r = get(CDX, timeout=600)
        open(path, 'w').write(r.text)
    caps = {}
    for line in open(path):
        parts = line.split()
        if len(parts) < 4:
            continue
        u, ts, st, ln = parts[:4]
        u2 = urllib.parse.unquote(u).lower().translate(AR_DIGITS)
        m = re.search(r'/boelaws/laws/lawdetails/\s*' + GUID + r'/?(\d*)/?$', u2)
        if not m:
            continue
        lang = {'': 'ar', '1': 'ar', '2': 'en'}.get(m.group(2))
        if not lang:
            continue
        caps.setdefault((m.group(1), lang), []).append((ts, int(ln) if ln.isdigit() else 0, u))
    return caps


def main():
    raw = sys.argv[1]
    os.makedirs(os.path.join(raw, 'html'), exist_ok=True)
    caps = load_cdx(raw)
    todo = sorted(caps)
    print(len(todo), 'documents/languages')
    for i, (guid, lang) in enumerate(todo):
        out = os.path.join(raw, 'html', f'{guid}_{lang}.html')
        if os.path.exists(out):
            continue
        # newest capture first; skip tiny captures (error / JS shells)
        cands = sorted(caps[(guid, lang)], key=lambda c: c[0], reverse=True)
        cands = [c for c in cands if c[1] >= 5000] or cands
        for ts, ln, u in cands[:4]:
            r = get(f'https://web.archive.org/web/{ts}id_/{u}')
            time.sleep(1.5)
            if r is None:
                continue
            html = r.content.decode('utf-8', 'replace')
            if 'divLawText' not in html:
                continue
            open(out, 'w', encoding='utf-8').write(html)
            json.dump({'guid': guid, 'lang': lang, 'timestamp': ts, 'original': u,
                       'archive_url': f'https://web.archive.org/web/{ts}/{u}'},
                      open(out[:-5] + '.json', 'w'))
            print(i, guid, lang, ts, flush=True)
            break
        else:
            print(i, guid, lang, 'NO USABLE CAPTURE', flush=True)


if __name__ == '__main__':
    main()
