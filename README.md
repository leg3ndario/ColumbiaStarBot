# Richland County SC — Motivated Seller Lead Scraper (Columbia Star)

Automated daily scraper for The Columbia Star public notices. Extracts motivated-seller signals, enriches with Richland County parcel data, scores leads, and publishes a live dashboard to GitHub Pages.

---

## Source

**`https://www.thecolumbiastar.com/category/public-notices/`**

The Columbia Star is Richland County's designated legal newspaper of record. All Richland County foreclosures, judgments, probate notices, tax deeds, liens, and other legal notices are published here weekly (typically Thursdays). Full notice text is public and freely accessible.

**Two-layer fetch strategy:**
1. **WordPress REST API** (`/wp-json/wp/v2/posts?categories=...&after=...`) — fast, structured, no JS required
2. **HTML pagination fallback** — scrapes the category listing pages and fetches each article if the API fails

---

## What Gets Parsed from Each Notice

Each post can contain dozens of individual notices. The scraper splits them into blocks and extracts:

| Field | Source |
|---|---|
| Case / Doc # | `C/A No.`, `Civil Action No.`, `Case No.` |
| Doc Type | Text pattern classification (16 types) |
| Property Address | `Property Address:` label or address patterns |
| TMS / PIN | `TMS#`, `PIN#`, `APN` labels |
| Owner / Defendant | `vs.` / `against` party split |
| Plaintiff / Lender | `vs.` / `against` party split |
| Amount | Mortgage principal, judgment amount |
| Legal Description | `ALL THAT CERTAIN PIECE...` |
| Publication Date | WordPress post `date_gmt` |

---

## Lead Types (16 codes)

| Code | Label | Detected By |
|------|-------|-------------|
| NOFC | Notice of Foreclosure | Master's Sale, by virtue of decree |
| LP | Lis Pendens | Notice of Pendency of Action |
| TAXDEED | Tax Deed | Delinquent tax sale |
| JUD/CCJ | Judgment | Transcript/abstract of judgment |
| DRJUD | Domestic Judgment | Family Court context |
| LNIRS | IRS Lien | Internal Revenue / federal tax |
| LNCORPTX | Corp Tax Lien | SC Dept of Revenue lien |
| LNFED | Federal Lien | U.S. Government lien |
| LN | Lien | Notice of lien sale / storage |
| LNMECH | Mechanic Lien | Mechanic's / materialman's lien |
| LNHOA | HOA Lien | HOA foreclosure / lien sale |
| MEDLN | Medicaid Lien | Medicaid / hospital lien |
| PRO | Probate | Notice to creditors of estates |
| NOC | Notice of Commencement | Construction start notice |
| RELLP | Release Lis Pendens | Release / cancellation notice |
| CCJ | Certified Judgment | Certificate of judgment |

---

## Seller Score (0–100)

| Rule | Points |
|------|--------|
| Base | 30 |
| Per motivational flag | +10 each |
| LP + Foreclosure combo | +20 |
| Amount > $100k | +15 |
| Amount > $50k | +10 |
| New this week | +5 |
| Has address | +5 |

---

## Parcel Enrichment

Owner name → parcel lookup via:
1. **TMS/PIN#** extracted from notice text (most accurate)
2. **Owner name** (3 variants: FIRST LAST / LAST FIRST / LAST, FIRST)
3. **Property address** string match

Parcel data sources (tried in order):
1. richlandmaps.com ArcGIS REST
2. ArcGIS Online hosted FeatureServer
3. Bulk DBF ZIP download fallback

---

## File Structure

```
.
├── scraper/
│   ├── fetch.py              ← main scraper
│   └── requirements.txt
├── dashboard/
│   ├── index.html            ← live dashboard (GitHub Pages)
│   └── records.json          ← latest data
├── data/
│   ├── records.json          ← duplicate
│   └── leads_ghl_export.csv  ← GHL-ready export
└── .github/workflows/
    └── scrape.yml
```

---

## Setup

1. Fork / clone repo
2. **Settings → Pages → Source: GitHub Actions**
3. **Settings → Actions → General → Read and write permissions**
4. Run: **Actions → Scrape → Run workflow**
5. Dashboard: `https://<username>.github.io/<repo>/`

---

## Local Run

```bash
pip install -r scraper/requirements.txt
python -m playwright install chromium   # optional – only needed for JS fallback
python scraper/fetch.py
```
