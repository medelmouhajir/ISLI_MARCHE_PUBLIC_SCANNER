import asyncio
from contextlib import asynccontextmanager
from typing import AsyncGenerator, Optional

from cachetools import TTLCache
from playwright.async_api import async_playwright, BrowserContext

from app.config import settings

# Shared in-memory cache for static/detail pages to reduce portal load.
_html_cache: TTLCache = TTLCache(maxsize=256, ttl=settings.CACHE_TTL_SECONDS)


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

    async def fetch_html_with_next(self, url: str, next_clicks: int = 0) -> list[str]:
        """Fetch the first page plus `next_clicks` additional pages by clicking next."""
        pages: list[str] = []
        async with self._context() as context:
            page = await context.new_page()
            try:
                await page.goto(url, wait_until="networkidle", timeout=60000)
                pages.append(await page.content())

                for _ in range(next_clicks):
                    next_btn = page.locator('img[title="Aller à la page suivante"]').first
                    try:
                        if await next_btn.count() == 0 or not await next_btn.is_visible(timeout=2000):
                            break
                        await next_btn.click()
                        await page.wait_for_load_state("networkidle", timeout=60000)
                        await asyncio.sleep(self.request_delay_ms / 1000.0)
                        pages.append(await page.content())
                    except Exception:
                        break
            finally:
                await page.close()
        return pages

    async def fetch_detail_html(self, ref_consultation: str, org_acronyme: str) -> str:
        url = (
            f"{settings.PORTAL_BASE_URL}/?page=entreprise.EntrepriseDetailConsultation"
            f"&refConsultation={ref_consultation}&orgAcronyme={org_acronyme}"
        )
        return await self.fetch_html(url)
