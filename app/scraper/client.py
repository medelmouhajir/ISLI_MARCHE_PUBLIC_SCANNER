import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional
from urllib.parse import urlencode, urlparse, parse_qs, urlunparse

from cachetools import TTLCache
from playwright.async_api import async_playwright, BrowserContext

from app.config import settings

# Shared in-memory cache for static/detail pages to reduce portal load.
_html_cache: TTLCache = TTLCache(maxsize=256, ttl=settings.CACHE_TTL_SECONDS)

# Default large page size supported by the portal's result page selector.
_PORTAL_PAGE_SIZE = 500


def _cache_key(url: str, page_size: int, max_matches: Optional[int]) -> str:
    """Include effective page size and match cap in the cache key.

    Different max_matches values may stop scanning at different portal pages,
    so they must not share a cached result.
    """
    parsed = urlparse(url)
    qs = parse_qs(parsed.query, keep_blank_values=True)
    qs["__skill_page_size"] = [str(page_size)]
    qs["__skill_max_matches"] = [str(max_matches or 0)]
    return urlunparse(parsed._replace(query=urlencode(qs, doseq=True)))


class PortalClient:
    """Lightweight Playwright wrapper for the Moroccan public procurement portal."""

    def __init__(
        self,
        request_delay_ms: Optional[int] = None,
        max_concurrent_pages: Optional[int] = None,
    ):
        self.request_delay_ms = request_delay_ms or settings.REQUEST_DELAY_MS
        self._semaphore = asyncio.Semaphore(max_concurrent_pages or settings.MAX_CONCURRENT_PAGES)
        self._playwright = None
        self._browser = None

    async def __aenter__(self):
        self._playwright = await async_playwright().start()
        self._browser = await self._playwright.chromium.launch(headless=True)
        return self

    async def __aexit__(self, exc_type, exc, tb):
        if self._browser:
            await self._browser.close()
        if self._playwright:
            await self._playwright.stop()

    @asynccontextmanager
    async def _context(self) -> AsyncGenerator[BrowserContext, None]:
        async with self._semaphore:
            # Keep Playwright's default browser user agent; the portal's WAF rejects
            # non-browser or custom user agents.
            context = await self._browser.new_context(
                viewport={"width": 1280, "height": 800},
                locale="fr-FR",
                timezone_id="Africa/Casablanca",
                extra_http_headers={
                    "Accept-Language": "fr-FR,fr;q=0.9",
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Upgrade-Insecure-Requests": "1",
                },
            )
            try:
                yield context
            finally:
                await context.close()

    async def fetch_html(self, url: str) -> str:
        cached = _html_cache.get(url)
        if cached:
            return cached

        async with self._context() as context:
            page = await context.new_page()
            try:
                await page.goto(url, wait_until="networkidle", timeout=60000)
                html = await page.content()
                _html_cache[url] = html
                await asyncio.sleep(self.request_delay_ms / 1000.0)
                return html
            finally:
                await page.close()

    async def fetch_search_result_pages(
        self,
        url: str,
        max_pages: int,
        max_matches: Optional[int] = None,
        page_size: int = _PORTAL_PAGE_SIZE,
    ) -> tuple[list[str], int]:
        """Fetch portal search pages, selecting `page_size` per page.

        Returns (list of HTML strings, scanned_portal_pages).
        Stops early when `max_matches` rows have been seen OR `max_pages` reached.
        """
        cache_key = _cache_key(url, page_size, max_matches)
        cached = _html_cache.get(cache_key)
        if cached:
            # Cached results are already at the requested page size and cap.
            return cached

        pages: list[str] = []
        async with self._context() as context:
            page = await context.new_page()
            try:
                await page.goto(url, wait_until="networkidle", timeout=60000)

                # Select larger page size on first load if available.
                if page_size != 10:
                    try:
                        await self._set_page_size(page, page_size)
                    except Exception:
                        # Fall back to whatever size the portal gave us.
                        pass

                html = await page.content()
                pages.append(html)
                total_rows_on_page = html.count("EntrepriseDetailConsultation")

                scanned = 1
                while scanned < max_pages and (
                    max_matches is None or total_rows_on_page < max_matches
                ):
                    next_btn = page.locator('img[title="Aller à la page suivante"]').first
                    try:
                        if await next_btn.count() == 0 or not await next_btn.is_visible(timeout=2000):
                            break
                        await next_btn.click()
                        await page.wait_for_load_state("networkidle", timeout=60000)
                        await asyncio.sleep(self.request_delay_ms / 1000.0)
                        html = await page.content()
                        pages.append(html)
                        total_rows_on_page += html.count("EntrepriseDetailConsultation")
                        scanned += 1
                    except Exception:
                        break

                result = (pages, scanned)
                _html_cache[cache_key] = result
                return result
            finally:
                await page.close()

    async def _set_page_size(self, page, page_size: int) -> None:
        """Use the portal's page-size dropdown (Prado WebForms) to request more rows."""
        selectors = [
            "#ctl0_CONTENU_PAGE_resultSearch_listePageSizeTop",
            "#ctl0_CONTENU_PAGE_resultSearch_listePageSizeBottom",
            "select[name*='listePageSize']",
        ]
        select_el = None
        for selector in selectors:
            try:
                if await page.locator(selector).count() > 0:
                    select_el = page.locator(selector).first
                    break
            except Exception:
                continue
        if select_el is None:
            return

        # Prado requires the change event; select_option alone may not trigger postback.
        await select_el.select_option(str(page_size))
        await select_el.dispatch_event("change")
        await page.wait_for_load_state("networkidle", timeout=60000)
        await asyncio.sleep(self.request_delay_ms / 1000.0)

    async def fetch_detail_html(self, ref_consultation: str, org_acronyme: str) -> str:
        url = (
            f"{settings.PORTAL_BASE_URL}/?page=entreprise.EntrepriseDetailConsultation"
            f"&refConsultation={ref_consultation}&orgAcronyme={org_acronyme}"
        )
        return await self.fetch_html(url)
