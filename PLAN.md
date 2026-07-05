# ISLI Skill Plan — Morocco Public Procurement Scanner (v2 Performance Upgrade)

## 1. Objective

Upgrade the working v1 skill to **limit results more effectively and improve search/filter performance** while keeping the existing filter surface unchanged and staying stateless/on-demand.

## 2. Approved Scope (from user decisions)

- **Filters:** keep existing filters only (query, category, procedure, location, buyer, publication/deadline dates). No new rich/server-side filters in this upgrade.
- **Limiting:** add both a global `max_results` cap and a convenient top-N / `limit` mode.
- **Monitoring:** out of scope.
- **Storage:** remain stateless.

## 3. Current Bottlenecks

- The scraper always loads results 10 per page, even when the portal allows 500/page.
- `search_announcements()` always pre-scans `page * page_size` matches, which can load many portal pages.
- There is no hard cap: a large `max_pages_to_scan` can generate dozens of requests.
- Pagination is sequential “next” clicking, which is slow.

## 4. Proposed Upgrades

### 4.1 Set portal page size to 500

Use Playwright to select the `listePageSizeTop`/`listePageSizeBottom` dropdown value `500` on the first load. This reduces the number of portal pages needed by 50×.

### 4.2 Add `max_results` to `/search`

- New `SearchRequest.max_results` field (int, 1–500, default 100).
- The scraper stops scanning portal pages once it has collected `max_results` matches (after filters).
- `page`/`page_size` still work for pagination, but only within the first `max_results` matches.

### 4.3 Add top-N / `limit` convenience mode to `/search`

- New `SearchRequest.limit` field (int, 1–500, optional).
- When `limit` is provided, ignore `page` and `page_size` and return the first `limit` matching results.
- This is a convenience alias for `page=1, page_size=limit, max_results=limit`.

### 4.4 Add richer response metadata

`SearchResponse` will include:
- `total_estimated` — portal total.
- `matches_found` — number of matching rows scanned before pagination.
- `returned_count` — number returned.
- `scanned_portal_pages` — how many portal result pages were loaded.
- `source_url` — unchanged.

### 4.5 Smarter pagination stop

- Stop scanning when either `max_results` matches are found or `max_pages_to_scan` portal pages are loaded (whichever comes first).
- Keep the existing `max_pages_to_scan` upper bound as a safety rail.

### 4.6 Cache and rate-limit polish

- Keep the existing TTL cache.
- Lower default `REQUEST_DELAY_MS` slightly (500 ms) since fewer pages are loaded.
- Document that first search may be slow but repeated calls within TTL are fast.

## 5. API Changes

### 5.1 `POST /search`

**New request fields:**
- `max_results` (int, optional, default 100, min 1, max 500).
- `limit` (int, optional, min 1, max 500) — top-N mode; when set, overrides `page`/`page_size`/`max_results`.

**Existing fields unchanged.**

**Response new fields:**
- `matches_found` (int)
- `returned_count` (int)
- `scanned_portal_pages` (int)

### 5.2 `POST /list_recent`

- Already has `limit`; keep as is.
- Add response metadata `total_estimated` and `matches_found` (same shape as SearchResponse).

## 6. Implementation Steps

### Phase 1 — Scraper improvements
1. Add `PortalClient.fetch_search_results(url, max_pages, max_matches)` that:
   - loads the first page,
   - selects page size 500,
   - waits for reload,
   - extracts each page,
   - clicks next until `max_pages` or `max_matches` reached.
2. Return list of HTML strings + count of scanned pages.
3. Cache the final loaded pages by normalized URL.

### Phase 2 — Model and router updates
1. Add `max_results`, `limit`, and response metadata fields to `app/models.py`.
2. Update `SearchRequest` validators so `limit` takes precedence.
3. Update `/search` router to compute effective `page`/`page_size`/`max_results` from `limit`.
4. Update `/list_recent` router to return metadata.

### Phase 3 — Tests and docs
1. Update offline tests for new response fields.
2. Add a test that `limit=2` returns exactly 2 results and sets `matches_found >= 2`.
3. Update `README.md` with the new `max_results`/`limit` behavior.
4. Bump version to `1.1.0` in `isli-skill.yaml` and `CHANGELOG.md`.

## 7. Risks

- Setting page size to 500 may stress the portal; if the 500-page load times out, fall back to 100.
- ASP.NET/Prado page-size selection may need an explicit change event; implementation will verify with live portal.
- Capping by `max_results` means deep pagination beyond the cap is unavailable; this is the intended trade-off.

## 8. Out of Scope

- New filter dimensions (amount range, TPE/PME flag, announcement type, etc.).
- Persistent watchlists or scheduled monitoring.
- BDC award/result notices.
