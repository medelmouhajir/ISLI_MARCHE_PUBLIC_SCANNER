# ISLI Skill Plan — Morocco Public Procurement Scanner

## 1. Objective & Scope

Build an ISLI Universal Skill Runtime (USR) v2.0 skill that lets ISLI AI agents **search and retrieve project announcements (open consultations)** from the Moroccan public procurement portal `https://www.marchespublics.gov.ma`.

**v1 scope (approved):**
- Open consultations / tender announcements only (not BDC award notices).
- On-demand search and detail retrieval (no monitoring/alerts/scheduler).
- Stateless container — no persistent storage required.
- Read-only — no bid submission, login, or cart actions.

## 2. Portal Analysis

- No public REST API; the site is a form-driven ASP.NET-style PHP portal with JavaScript postbacks.
- The "all consultations" list is reachable directly via:
  `https://www.marchespublics.gov.ma/index.php?AllCons=&page=entreprise.EntrepriseAdvancedSearch`
- Pagination links are JS postbacks (`javascript:;//ctl0_...`), not query-string page numbers.
- Search filters are rendered dynamically; direct `GET` parameter coverage is limited and undocumented.
- Detail page URL pattern:
  `?page=entreprise.EntrepriseDetailConsultation&refConsultation=<id>&orgAcronyme=<code>`
- Result columns include: procedure, category, publication date, reference, object, buyer, lots, location, deadline.
- Detail page fields include: reference, object, buyer, procedure, category, deadline, location, estimated amount, contact info, and downloadable documents.

## 3. Architecture Decisions

| Decision | Choice | Rationale |
|---|---|---|
| Runtime standard | ISLI USR v2.0 Dockerized HTTP microservice | Required by the ISLI skills registry for new third-party skills. |
| Language / framework | Python 3.12 + FastAPI | Fast to build, excellent async support, big scraping ecosystem. |
| Browser automation | Playwright + Chromium | Required for JS postback pagination and advanced filters. Direct `requests` alone cannot paginate or submit the search form reliably. |
| HTML parsing | BeautifulSoup 4 (lxml) | Lightweight parsing of list and detail pages. |
| Auth | `PyJWT` verifying `X-Internal-Auth` with `JWT_SECRET` | Required USR security contract. |
| Caching | In-memory TTL cache (`cachetools` or `fastapi-cache`) | Avoids re-scraping the same pages within a short window; respects the portal. |
| Rate limiting | Per-request delays + max concurrency | Polite scraping; configurable via env vars. |

## 4. Proposed Project Structure

```
.
├── isli-skill.yaml          # USR v2.0 manifest
├── Dockerfile               # Multi-stage build with Playwright deps
├── docker-compose.yml       # Local dev/testing
├── README.md                # Usage, limits, contribution notes
├── requirements.txt
├── app/
│   ├── main.py              # FastAPI app, health, manifest, middleware
│   ├── config.py            # Pydantic Settings (JWT_SECRET, CACHE_TTL, etc.)
│   ├── auth.py              # JWT verification
│   ├── models.py            # Pydantic request/response models
│   ├── scraper/
│   │   ├── __init__.py
│   │   ├── client.py        # Playwright session management
│   │   ├── listings.py      # Search / list announcements
│   │   ├── details.py       # Detail page scraping
│   │   └── parser.py        # Shared BeautifulSoup helpers
│   └── routers/
│       ├── search.py        # POST /search
│       ├── details.py       # POST /details
│       └── recent.py        # POST /list_recent
└── tests/
    ├── conftest.py
    ├── test_health.py
    ├── test_auth.py
    └── fixtures/
        └── sample_*.html    # Saved portal HTML for offline unit tests
```

## 5. Exposed Tools / Endpoints

All tool endpoints accept JSON and return JSON. Core also provides `GET /health` and `GET /.well-known/isli-manifest`.

### 5.1 `POST /search`

Search open consultations with filters and pagination.

**Parameters:**
- `query` (string, optional) — free-text keyword matched against reference/object/buyer/location after scraping.
- `category` (enum, optional) — `Travaux`, `Fournitures`, `Services`.
- `procedure` (string, optional) — e.g., `Appel d'offres ouvert`.
- `location` (string, optional) — place of execution.
- `buyer` (string, optional) — public buyer name (autocomplete/list not supported in v1; partial text match).
- `published_after` / `published_before` (ISO date, optional).
- `deadline_after` / `deadline_before` (ISO datetime, optional).
- `page` (int, default 1) — result page number.
- `page_size` (int, default 20, max 100) — v1 caps this to avoid overloading the portal.
- `max_pages_to_scan` (int, optional, default 5) — how many portal pages to scan when filtering is required.

**Response:**
- `total_estimated` (int) — portal's reported total.
- `page` (int)
- `page_size` (int)
- `results` (array of announcement summaries)
- `source_url` (string)

**Result item fields:**
- `refConsultation`, `orgAcronyme`
- `reference`, `object`, `buyer`
- `category`, `procedure`
- `location`, `deadline`, `published_date`
- `detail_url`

**Implementation notes:**
- If only `category` is given, use the portal's known `domaineActivite`/category path if discoverable; otherwise load the "all" list and filter client-side.
- For free-text or combined filters, Playwright scans result pages and filters rows until `page_size` results for the requested `page` are satisfied or `max_pages_to_scan` is reached.

### 5.2 `POST /details`

Retrieve full details for one announcement.

**Parameters:**
- `refConsultation` (string, required)
- `orgAcronyme` (string, required)

**Response fields:**
- All summary fields.
- `estimated_amount` / `currency`
- `lots`
- `reserved_tpe_pme` (bool)
- `withdrawal_address`, `deposit_address`, `opening_address`
- `contact_name`, `contact_email`, `contact_phone`
- `documents` (array of `{name, url, size}`)
- `raw_sections` (key/value map for fields not explicitly modeled)

### 5.3 `POST /list_recent`

Return the latest open consultations with minimal filters.

**Parameters:**
- `category` (enum, optional)
- `limit` (int, default 10, max 100)

**Response:** same shape as `/search`.

## 6. Data Models

Use Pydantic v2. Models live in `app/models.py`.

Key models:
- `SearchRequest`, `SearchResponse`, `AnnouncementSummary`
- `DetailRequest`, `DetailResponse`, `AnnouncementDetail`
- `DocumentLink`, `PortalError`

## 7. Authentication & Security

- All `POST` endpoints require an `X-Internal-Auth` header containing a JWT signed with the `JWT_SECRET` injected by ISLI Core.
- Middleware validates the token, issuer, and expiry. Invalid tokens return HTTP 401.
- The skill does not store credentials or user data.

## 8. Caching & Polite Scraping

- Cache page HTML for a configurable TTL (default 5 minutes) keyed by full URL + query params.
- Add a small fixed delay (default 750 ms) between portal requests.
- Limit concurrent Playwright contexts to 1 per request; close context after each request to avoid resource leaks.
- User-Agent string identifies the skill and provides a contact URL.

## 9. Implementation Phases

### Phase 0 — Repo & Tooling
1. Initialize repo in the local project directory.
2. Add `.gitignore`, `README.md`, `requirements.txt`.
3. Add `Dockerfile` and `docker-compose.yml` with Playwright Chromium.

### Phase 1 — Core Scraper
1. Implement Playwright client wrapper (context per request, error handling, retries).
2. Implement list-page parser for `AllCons` result table.
3. Implement detail-page parser.
4. Build client-side filtering helpers.

### Phase 2 — FastAPI App & USR Contract
1. Implement `config.py`, `auth.py`, `models.py`.
2. Implement routers for `/search`, `/details`, `/list_recent`.
3. Implement `GET /health` and `GET /.well-known/isli-manifest`.
4. Wire JWT middleware and exception handlers.

### Phase 3 — Manifest & Registry
1. Write `isli-skill.yaml` with the three tools and their JSON Schemas.
2. Validate the manifest against USR v2.0 expectations.
3. Prepare the registry PR entry for `index.json`.

### Phase 4 — Tests & Hardening
1. Unit tests using saved HTML fixtures.
2. JWT middleware tests.
3. Integration test: run the container locally and hit all endpoints with sample requests.
4. Test against the live portal with a small `limit` to verify selectors.

### Phase 5 — Documentation & Handoff
1. Document each tool, example requests, and known limitations.
2. Add a `CHANGELOG.md`.
3. Summarize what needs to be done to add BDC / monitoring in v2.

## 10. Testing Plan

- **Offline unit tests:** saved copies of list page and detail page HTML; verify parser outputs.
- **JWT tests:** valid/invalid/expired tokens.
- **Local container test:** `docker-compose up`, then `curl` the health and manifest endpoints.
- **Live smoke test:** run `/list_recent` with `limit=3` against the real portal.
- **Validation:** ensure `isli-skill.yaml` is syntactically valid YAML and the declared endpoints match the implemented routes.

## 11. Risks & Limitations

| Risk | Mitigation |
|---|---|
| Portal HTML changes break selectors. | Keep selectors in one module (`parser.py`), add monitoring-like tests, document fallback behavior. |
| Playwright increases image size and memory. | Use multi-stage Dockerfile; only install Chromium; allow headless mode to be forced. |
| Search form uses JS postbacks — full-text search may be slow or limited. | Cap `max_pages_to_scan` in v1; document that keyword search is client-side post-filter. |
| Portal rate limiting or blocking. | Respect delays, cache aggressively, surface `PortalRateLimitError` to the caller. |
| No official API means legal/TOS uncertainty. | Scrape only public pages, identify via User-Agent, honor any `robots.txt` if present. |

## 12. Out-of-Scope for v1 (Future Enhancements)

- BDC award/result notices (`/bdc/entreprise/consultation/resultat`).
- Monitoring / alerting / scheduled scans.
- Authenticated actions (bid submission, document upload, Q&A).
- Advanced buyer autocomplete or activity-domain tree selection.

## 13. Registry Submission

After the skill repo is ready, open a PR against `medelmouhajir/isli-skills-registry` adding an entry to `index.json`:

```json
{
  "id": "marche-publics-maroc",
  "name": "Maroc Marchés Publics Scanner",
  "description": "Search and retrieve open public procurement announcements from marchespublics.gov.ma",
  "author": "<author>",
  "git_url": "https://github.com/<owner>/<repo>.git",
  "tags": ["procurement", "morocco", "web", "scraper"]
}
```

## 14. Open Questions Before Implementation

None — the two scope questions (monitoring vs. on-demand, consultations vs. award notices) were answered as **on-demand only, open consultations only**.
