import copy
import re
from dataclasses import dataclass
from datetime import date, datetime
from typing import List, Optional

from bs4 import Tag

from app.config import settings
from app.models import AnnouncementSummary, SearchRequest
from app.scraper.client import PortalClient
from app.scraper.parser import (
    clean_text,
    extract_detail_link_params,
    make_absolute_url,
    parse_portal_date,
    parse_portal_datetime,
    soup,
)


@dataclass(frozen=True)
class SearchOutcome:
    results: List[AnnouncementSummary]
    matches_found: int
    total_estimated: Optional[int]
    scanned_portal_pages: int
    source_url: str


async def search_announcements(request: SearchRequest) -> SearchOutcome:
    base_url = f"{settings.PORTAL_BASE_URL}/index.php?AllCons=&page=entreprise.EntrepriseAdvancedSearch"

    # Effective pagination and cap.
    if request.limit:
        page = 1
        page_size = request.limit
        max_matches = request.limit
    else:
        page = request.page
        page_size = request.page_size
        max_matches = request.max_results or settings.DEFAULT_MAX_RESULTS

    max_pages_scan = request.max_pages_to_scan or settings.DEFAULT_MAX_PAGES_SCAN

    all_matches: List[AnnouncementSummary] = []
    portal_total: Optional[int] = None
    scanned_portal_pages = 0

    async with PortalClient() as client:
        html_pages, scanned_portal_pages = await client.fetch_search_result_pages(
            base_url,
            max_pages=max_pages_scan,
            max_matches=max_matches,
            page_size=500,
        )

    for html in html_pages:
        page_total = _extract_total_count(html)
        if page_total is not None:
            portal_total = page_total
        rows = _parse_list_page(html, base_url)
        for row in rows:
            if _matches(row, request):
                all_matches.append(row)
            if len(all_matches) >= max_matches:
                break
        if len(all_matches) >= max_matches:
            break

    matches_found = len(all_matches)
    start = (page - 1) * page_size
    end = start + page_size
    paginated = all_matches[start:end]

    return SearchOutcome(
        results=paginated,
        matches_found=matches_found,
        total_estimated=portal_total,
        scanned_portal_pages=scanned_portal_pages,
        source_url=base_url,
    )


async def list_recent_announcements(
    category: Optional[str] = None,
    limit: int = 10,
) -> SearchOutcome:
    base_url = f"{settings.PORTAL_BASE_URL}/index.php?AllCons=&page=entreprise.EntrepriseAdvancedSearch"
    results: List[AnnouncementSummary] = []
    portal_total: Optional[int] = None

    async with PortalClient() as client:
        html_pages, scanned_portal_pages = await client.fetch_search_result_pages(
            base_url,
            max_pages=2,
            max_matches=limit,
            page_size=500,
        )

    for html in html_pages:
        page_total = _extract_total_count(html)
        if page_total is not None:
            portal_total = page_total
        rows = _parse_list_page(html, base_url)
        for row in rows:
            if category is None or (row.category and row.category.lower() == category.lower()):
                results.append(row)
            if len(results) >= limit:
                break
        if len(results) >= limit:
            break

    return SearchOutcome(
        results=results[:limit],
        matches_found=len(results),
        total_estimated=portal_total,
        scanned_portal_pages=scanned_portal_pages,
        source_url=base_url,
    )


def _extract_total_count(html: str) -> Optional[int]:
    bs = soup(html)
    span = bs.find("span", id=re.compile(r"nombreElement"))
    if span:
        digits = re.sub(r"\D", "", span.get_text())
        return int(digits) if digits else None
    pattern = re.compile(r"Nombre de résultats\s*:\s*([\d\s\xa0]+)")
    for text_node in bs.find_all(string=pattern):
        match = pattern.search(text_node)
        if match:
            digits = re.sub(r"\D", "", match.group(1))
            return int(digits) if digits else None
    return None


def _parse_list_page(html: str, base_url: str) -> List[AnnouncementSummary]:
    bs = soup(html)
    results: List[AnnouncementSummary] = []

    detail_anchors = bs.find_all("a", href=re.compile(r"EntrepriseDetailConsultation"))
    for anchor in detail_anchors:
        href = anchor.get("href", "")
        params = extract_detail_link_params(href)
        if not params.get("refConsultation") or not params.get("orgAcronyme"):
            continue

        row_el = anchor.find_parent("tr")
        if row_el is None:
            continue

        detail = _parse_row(row_el)
        if detail is None:
            continue

        detail.refConsultation = params["refConsultation"]
        detail.orgAcronyme = params["orgAcronyme"]
        detail.detail_url = make_absolute_url(href, settings.PORTAL_BASE_URL)
        results.append(detail)

    return results


def _parse_row(row_el: Tag) -> Optional[AnnouncementSummary]:
    ref_cell = row_el.find("td", attrs={"headers": "cons_ref"})
    intitule_cell = row_el.find("td", attrs={"headers": "cons_intitule"})
    lieu_cell = row_el.find("td", attrs={"headers": "cons_lieuExe"})
    date_cell = row_el.find("td", attrs={"headers": "cons_dateEnd"})

    if not all((ref_cell, intitule_cell, lieu_cell, date_cell)):
        return None

    category = _text_from_id(ref_cell, r"panelBlocCategorie")
    procedure = _text_from_id(ref_cell, r"panelBlocTypesProc")
    published_date = _first_date_in_cell(ref_cell)

    reference = _text_from_selector(intitule_cell, "span.ref")
    object_text = _text_after_label(intitule_cell, r"panelBlocObjet", "Objet")
    buyer = _text_after_label(intitule_cell, r"panelBlocDenomination", "Acheteur public")

    location = _text_from_id(lieu_cell, r"panelBlocLieuxExec")

    deadline = _deadline_from_cell(date_cell)

    return AnnouncementSummary(
        refConsultation="",
        orgAcronyme="",
        reference=reference,
        object=object_text,
        buyer=buyer,
        category=category,
        procedure=procedure,
        location=location,
        deadline=deadline,
        published_date=published_date,
        detail_url="",
    )


def _visible_text(el: Tag, separator: str = "\n") -> str:
    """Return text of the element with tooltip/popup and "more" indicators removed."""
    clone = copy.copy(el)
    for popup in clone.find_all(class_=["info-bulle", "info-suite"]):
        popup.decompose()
    for hidden in clone.find_all(style=re.compile(r"display\s*:\s*none", re.I)):
        hidden.decompose()
    return clean_text(clone.get_text(separator)) or ""


def _text_from_selector(cell: Tag, selector: str) -> Optional[str]:
    el = cell.select_one(selector)
    return _visible_text(el) if el else None


def _text_from_id(cell: Tag, id_pattern: str) -> Optional[str]:
    for candidate in cell.find_all(id=re.compile(id_pattern)):
        text = _visible_text(candidate)
        if text:
            return text
    return None


def _text_after_label(cell: Tag, id_pattern: str, label: str) -> Optional[str]:
    el = None
    for candidate in cell.find_all(id=re.compile(id_pattern)):
        el = candidate
        break
    if el is None:
        return None
    full_text = _visible_text(el)
    if not full_text:
        return None
    prefix = f"{label} :"
    if full_text.startswith(prefix):
        return clean_text(full_text[len(prefix):])
    for line in full_text.split("\n"):
        if line.strip().lower().startswith(label.lower()):
            parts = line.split(":", 1)
            if len(parts) == 2:
                return clean_text(parts[1])
    return full_text


def _first_date_in_cell(cell: Tag) -> Optional[date]:
    text = _visible_text(cell, " ")
    for match in re.finditer(r"\b(\d{2}/\d{2}/\d{4})\b", text):
        parsed = parse_portal_date(match.group(1))
        if parsed:
            return parsed
    return None


def _deadline_from_cell(cell: Tag) -> Optional[datetime]:
    cloture = cell.find("div", class_="cloture-line")
    if cloture:
        return parse_portal_datetime(_visible_text(cloture, " "))
    text = _visible_text(cell, " ")
    match = re.search(r"\b(\d{2}/\d{2}/\d{4}\s+\d{2}:\d{2})\b", text)
    if match:
        return parse_portal_datetime(match.group(1))
    return None


def _matches(row: AnnouncementSummary, request: SearchRequest) -> bool:
    query = (request.query or "").lower()
    if query:
        haystack = " ".join(
            str(x) for x in (row.reference, row.object, row.buyer, row.location) if x
        ).lower()
        if query not in haystack:
            return False

    if request.category and row.category != request.category.value:
        return False

    if request.procedure and (not row.procedure or request.procedure.lower() not in row.procedure.lower()):
        return False

    if request.location and (not row.location or request.location.lower() not in row.location.lower()):
        return False

    if request.buyer and (not row.buyer or request.buyer.lower() not in row.buyer.lower()):
        return False

    if request.published_after and row.published_date and row.published_date < request.published_after:
        return False

    if request.published_before and row.published_date and row.published_date > request.published_before:
        return False

    if request.deadline_after and row.deadline and row.deadline < request.deadline_after:
        return False

    if request.deadline_before and row.deadline and row.deadline > request.deadline_before:
        return False

    return True
