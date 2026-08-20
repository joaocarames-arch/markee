# Sources Inventory — markee

> Last updated: 2026-07-24
> Purpose: authoritative reference for all trademark data sources used by markee.

---

## 1. EUIPO REST API

### Portal & Access

| Item | Detail |
|---|---|
| Developer portal | https://dev.euipo.europa.eu/ |
| Registration | Free (no cost for API access) |
| Auth method | OAuth2 — Client Credentials grant |
| Credentials | `client_id` + `client_secret` obtained via portal registration |
| Token endpoint | Provided after app registration (standard `/token` OAuth2 path) |
| Sandbox | Available — realistic test data, read/write access |

### Available APIs

| API | Version | Purpose |
|---|---|---|
| Trademark Search | 1.1.0 | Search EUTM database with RSQL query language |
| Persons | 1.0.0 | Applicant / representative data |
| Goods And Services | 1.2.0 | TMClass / Nice classification taxonomy |
| EUTM Filing | 1.1.0 | File new EU trademarks programmatically |

### Trademark Search API (1.1.0)

**Base URL:** `https://dev.euipo.europa.eu/api/trademark-search/v1.1.0/`

**Query language:** RSQL (FIQL-based)

**RSQL operators:**
- `==`, `!=`, `<`, `<=`, `>`, `>=` — comparison
- `=in=(a,b,c)` — value in set
- `=out=(a,b,c)` — value not in set
- `=all=(a,b,c)` — all values present (for arrays like Nice classes)
- `*wildcard*` — substring match
- `and`, `or`, `(` `)` — logical grouping

**RSQL query examples:**
```
applicationDate>=2026-01-01 and wordMarkSpecification.verbalElement==*brand*
status==REGISTERED and niceClasses=all=(25,28,40)
representatives.identifier==123 and renewalStatus==RENEWAL_PERIOD_OPEN
```

**Pagination:** `?page=0&size=20` (page is 0-indexed)

**Rate limits:** ~1000 requests/minute (be respectful; no hard cap published, but EUIPO monitors abuse)

### Key Response Fields

| Field | Type | Description |
|---|---|---|
| `applicationNumber` | string | Unique EUTM application number |
| `wordMarkSpecification.verbalElement` | string | Text of the word mark (primary field for similarity) |
| `status` | string | Current status (e.g. `REGISTERED`, `APPLICATION_PUBLISHED`) |
| `renewalStatus` | string | Renewal state (`RENEWAL_PERIOD_OPEN`, etc.) |
| `applicationDate` | date | Filing date (ISO 8601) |
| `registrationDate` | date | Registration date |
| `expiryDate` | date | Expiry date (10 years from filing) |
| `oppositionPeriodEndDate` | date | End of 3-month opposition window |
| `updateDate` | datetime | Last modification (use for incremental polling) |
| `niceClasses` | int[] | Nice classification numbers |
| `applicants` | object[] | `{identifier, name, address, country}` |
| `representatives` | object[] | `{identifier, name, address, country}` |
| `oppositions` | object[] | `{oppositionNumber, status, date}` |
| `cancellations` | object[] | `{cancellationNumber, status, date}` |
| `appeals` | object[] | `{appealNumber, status, date}` |
| `markFeature` | string | `Word`, `Figurative`, `3D`, `Colour`, `Sound`, etc. |

### Implementation Notes

- EUIPO service in markee enters **mock mode** automatically when no credentials are configured — safe to develop without API keys.
- Use `updateDate` for incremental polling: `updateDate>=2026-07-23T00:00:00Z`.
- RSQL date format: `YYYY-MM-DD` (no time component in queries).

---

## 2. EUTM Download (Bulk Data)

### Overview

| Item | Detail |
|---|---|
| System name | EUTM Download |
| Access | Subscription-based (EUIPO User Area) |
| Format | XML, conforming to **TM-XML standard** |
| Content | Full EUTM register: marks, owners, representatives, oppositions, appeals, recordals |
| Update frequency | Daily |
| Portal | https://eutm.euipo.europa.eu/en/user-area |

### How to Access

1. Register at https://euipo.europa.eu/ (free).
2. Navigate to User Area → EUTM Download.
3. Subscribe to the download service (free for bulk data access).
4. Receive daily XML files via the download portal.

### TM-XML Standard

- Open standard for trademark data exchange (ST.66).
- Schema maintained by WIPO.
- Covers: application data, owner details, representative details, Nice classes, status history, opposition/cancellation/appeal records, renewal data.

### Use Cases

- **Historical backfill:** load the full EUTM register once, then use the REST API for incremental updates.
- **Full-text indexing:** XML dumps are more efficient than paginated API calls for bulk processing.
- **No rate limits:** bulk files are downloaded, not API-polled.

### Alternative: EUIPO Open Data Platform

- EUIPO also publishes datasets via an Open Data Platform.
- Includes: trademarks, designs, representatives, international registrations, applicants.
- No license required.
- URL pattern: https://euipo.europa.eu/ → Transparency Portal → Open Data.

---

## 3. INPI Portugal — BPI (Boletim da Propriedade Industrial)

### Overview

| Item | Detail |
|---|---|
| Official site | https://inpi.justica.gov.pt/ |
| Bulletin page | https://inpi.justica.gov.pt/en-gb/Industrial-Property-Bulletin |
| Format | PDF (daily, weekdays) |
| Content | Applications, grants, refusals, modifications, renewals, cancellations, transmissions |
| Language | Portuguese |
| Public API | **None** (as of 2026-07) |

### BPI as a Lifecycle Event Source

The BPI is the **authoritative source for lifecycle events** in Portugal:
- **Despachos** (decisions): grants, provisional refusals, definitive refusals.
- **Oposições** (oppositions): filed oppositions and their outcomes.
- **Renovações** (renewals): renewal grants.
- **Caducidades** (expiries): marks that have lapsed.
- **Transmissões** (assignments): ownership changes.

**Critical:** Publication date in the BPI starts the **2-month opposition window** for Portuguese trademarks.

### INPI Search Portal (Legacy)

| Item | Detail |
|---|---|
| URL | https://servicosonline.inpi.pt/pesquisas/main/marcas.jsp |
| Interface | HTML (2008-era), no API |
| Features | Text search, phonetic search (built-in, PT-optimized) |
| Status | Active but legacy |

### INPI API — Future

- **Signa.io** lists "INPI Portugal API — Coming Soon Q3 2026" at https://signa.so/offices/inpi-pt.
- No official announcement from INPI as of 2026-07.
- Until then: **TMview/EUIPO API covers INPI Portugal trademarks** (INPI is a TMview participant).

### INPI Data Access Strategy

1. **Primary (similarity + search):** EUIPO/TMview API — INPI marks are integrated.
2. **Lifecycle events:** BPI PDF parsing (pymupdf + pdfplumber).
3. **Fallback:** servicosonline.inpi.pt scraping (Playwright) for phonetic search.

### Known Issues

- `inpi.justica.gov.pt` has had intermittent availability issues.
- The search portal (`servicosonline.inpi.pt`) is the more stable endpoint for manual lookups.
- BPI PDFs are published on the English-language subdomain (`/en-gb/`).

---

## 4. TMview

### Overview

| Item | Detail |
|---|---|
| Official site | https://www.tmdn.org/tmview/ |
| Operator | EUIPN (European Union Intellectual Property Network) |
| Coverage | **54.8M+ trademarks** from participating offices worldwide |
| Cost | Free |
| Public REST API | **None** (web UI only) |

### Coverage

TMview aggregates trademark data from:
- All EU member state IP offices (including INPI Portugal)
- EUIPO (EUTM)
- WIPO (international registrations designating EU)
- Non-EU participating offices (OAPI, and others)

### API Access

**TMview itself has no public REST API.** The web search at tmdn.org is the only official interface.

However, **TMview data is accessible programmatically via the EUIPO API** — the EUIPO Trademark Search API returns results from the same database that powers TMview. This is the recommended path for programmatic access.

### Related Tools

| Tool | Description |
|---|---|
| **CESTO** | Automated similarity search tool by EUIPN — compares a mark against TMview database |
| **TMclass** | Harmonised goods & services classification (linked to TMview) |
| **DesignView** | Sister tool for registered designs |

---

## 5. WIPO Global Brand Database

| Item | Detail |
|---|---|
| URL | https://www.wipo.int/en/web/global-brand-database |
| API Catalog | https://apicatalog.wipo.int/en (171 IP office APIs) |
| Nice Classification | https://nclpub.wipo.int/ |
| Vienna Classification | https://www.wipo.int/en/web/classification-vienna |

WIPO's API catalog lists 171 APIs from IP offices worldwide. Useful for Phase 3 expansion beyond EU/PT coverage.

---

## 6. Source Priority Matrix

| Source | Type | Coverage | Access | Use in markee |
|---|---|---|---|---|
| EUIPO REST API | REST (OAuth2) | EUTM + TMview offices | Free, rate-limited | Primary: search, similarity, polling |
| EUTM Download | XML bulk (TM-XML) | EUTM full register | Free subscription | Historical backfill |
| INPI BPI (PDF) | PDF bulletin | PT lifecycle events | Free, no auth | Lifecycle events, opposition windows |
| INPI Search Portal | HTML (legacy) | PT trademarks | Free, no auth | Fallback: phonetic search |
| TMview Web | Web UI | 54.8M+ marks | Free, no auth | Manual verification only |
| WIPO API Catalog | Various | 171 offices | Varies | Phase 3 expansion |

---

## 7. markee Implementation Notes

### EUIPO Service (`app/services/euipo.py`)

- OAuth2 client credentials flow.
- Token caching with refresh.
- RSQL query builder.
- Automatic mock mode when `EUIPO_CLIENT_ID` env var is unset.
- Polling via Celery beat: `poll_euipo` task every 6h.

### BPI Parser (`app/services/bpi_parser.py`)

- Downloads daily PDF from INPI bulletin page.
- Extracts lifecycle events using pdfplumber + pymupdf.
- Maps Portuguese legal terms to event types.
- Runs via Celery beat: `parse_bpi` task daily at 9:30 Lisbon time.

### Similarity Engine (`app/services/similarity.py`)

- Textual: rapidfuzz (`fuzz.ratio()`, `partial_ratio()`, `token_sort_ratio()`).
- Phonetic: jellyfish `metaphone()` + custom PT rules (ão→ao, lh→l, nh→n, ç→c, ss→s).
- Class overlap: Jaccard similarity on Nice class sets.
- Weights: 50% textual, 30% phonetic, 20% classes.
- PostgreSQL `pg_trgm` for indexed similarity queries.

### Environment Variables

```bash
EUIPO_CLIENT_ID=           # OAuth2 client ID
EUIPO_CLIENT_SECRET=       # OAuth2 client secret
EUIPO_API_BASE_URL=https://dev.euipo.europa.eu/api
INPI_BULLETIN_URL=https://inpi.justica.gov.pt/en-gb/Industrial-Property-Bulletin
```
