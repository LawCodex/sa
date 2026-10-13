# Saudi Arabia — LawCodex (الأنظمة السعودية)

Saudi legislation as plain Markdown: Arabic texts (`ar/`), plus the official English
translations (`en/`) where the Bureau of Experts publishes one. Part of
[LawCodex](https://github.com/LawCodex): one repository per jurisdiction.

> **Source: Internet Archive copies of the official site.** The official source is the
> **Bureau of Experts at the Council of Ministers** (هيئة الخبراء بمجلس الوزراء),
> [laws.boe.gov.sa](https://laws.boe.gov.sa). That site could not be reached from the network
> this corpus was built on: every connection timed out, over both HTTP and HTTPS. Each text was
> therefore taken from the **latest Wayback Machine capture** of its official BOE page. Each
> file records the official URL (`source`), the archived copy it was built from
> (`archived_source`) and the capture date (`archived`). So a text may be older than the
> current BOE version. Check the official site before you rely on it.

- Retrieved: **2026-10-13**. Capture dates range from 2019 to 2026; most are from 2025–2026.
- Nothing is translated, summarised or edited. The English files are BOE's own translations.

## Coverage

| Directory | BOE category | Arabic files (repealed) | English files (repealed) |
| --- | --- | ---: | ---: |
| `basic-laws/` | أنظمة أساسية: Basic Laws. These are the Basic Law of Governance (النظام الأساسي للحكم, Royal Order A/90 of 1412 AH) and the Shura Council, Council of Ministers, Regions and Allegiance Council laws | 5 | 4 |
| `laws/<hijri-year>/` | أنظمة عادية: ordinary laws (statutes) | 352 (50) | 206 (25) |
| `organizational-statutes/<hijri-year>/` | تنظيمات، وترتيبات تنظيمية: statutes of public bodies and organisational arrangements | 164 (22) | 45 (6) |
| `regulations/<hijri-year>/` | لوائح وما في حكمها: regulations and similar instruments | 68 (7) | 13 (1) |
| `other/<hijri-year>/` | old captures that have no BOE category and could not be classified by title | 3 | 0 |
| **Total** | | **592** | **268** |

This is every BOE law page (`/BoeLaws/Laws/LawDetails/<id>`) that has a usable capture in the
Wayback Machine: 594 distinct documents. Two documents had no usable Arabic capture, and four
English pages had none either. A further 36 English captures are only the "N/A" placeholder
that BOE shows when no translation exists, so they were skipped.

### Not covered / known gaps

- **Completeness.** BOE publishes more documents than the Internet Archive has captured. These
  include further laws, regulations, Royal Orders, Council of Ministers resolutions and
  international agreements. This repository covers only the captured ones. The full set can be
  built by running the scripts against laws.boe.gov.sa from a network that can reach it.
- **Version.** BOE shows the text as originally issued. Amendments appear as notes attached to
  each article ("تعديلات المادة" / amendments). Those notes are kept below the article as a
  block quote, so the text is **not a consolidated version**. A capture may also predate later
  amendments.
- **Status.** `status` comes from BOE's "الحالة" field: ساري → `in_force`, لاغي → `repealed`,
  and anything else (e.g. "جاري العمل على النظام") → `unknown`. The original label is kept in
  `status_label`.
- Scanned originals, attachments (Viewer/PrintAttachment) and images are not included.

## Structure and file names

```
ar/basic-laws/<file>.md
ar/<category>/<hijri-year>/<file>.md
en/...  (same layout and file names as ar/)
```

Files are named after the first instrument that issued the text, with the Hijri year first. For
example, `1428-royal-decree-m-17.md` is Royal Decree No. M/17 of 1428 AH, and
`1423-council-of-ministers-resolution-78.md` is Council of Ministers Resolution No. 78. If no
instrument can be parsed, the file is `<year>-boe-<id prefix>.md`. If two documents share an
instrument (e.g. a law and its regulation), the BOE id prefix is added to the name. The year
directories use the Hijri year of issue, the official calendar of the Kingdom.

Front matter: `title` (official title, Arabic for `ar/`), `identifier` (BOE document GUID),
`type`, `date` (Gregorian issue date as given by BOE), `date_hijri`, `published`, `issued_by`
(issuing instruments), `status`, `status_label`, `category` (BOE classification), `source`,
`archived_source`, `archived`, `retrieved`.

Each document starts with its issuing instrument (royal decree / Council of Ministers
resolution). Then come the law's title (`##`), its parts and chapters (الباب / الفصل …) as
headings, and one heading per article.

## Licence

These are official legislative texts of the Kingdom of Saudi Arabia, published by a
government body so that the public can know the law. Article 4(1) of the Saudi Copyright Law (Royal Decree
M/41 of 1424 AH, [`ar/laws/1424/1424-royal-decree-m-41.md`](ar/laws/1424/1424-royal-decree-m-41.md))
excludes from protection "laws, judicial decisions, decisions of administrative bodies,
international agreements and all other official documents, as well as official translations of
these texts". The Arabic text is authoritative; the English translations are for reference. Nothing here is an official publication.

## Regenerating

```sh
pip install -r scripts/requirements.txt
python scripts/sa_fetch.py  /path/to/raw     # CDX listing + latest Wayback captures (cached)
python scripts/sa_convert.py /path/to/raw .  # writes ar/ and en/
```

`sa_fetch.py` requests the Wayback Machine one page at a time, about one request every 1.5 s,
and identifies itself as `LawCodex/1.0`. If laws.boe.gov.sa is reachable, the same converter
works on live pages. Point the fetcher at `https://laws.boe.gov.sa/BoeLaws/Laws/LawDetails/<id>/1`
(Arabic) and `/2` (English), and observe the site's terms and robots.txt.
