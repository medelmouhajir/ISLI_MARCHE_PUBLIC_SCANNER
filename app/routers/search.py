from fastapi import APIRouter

from app.models import SearchRequest, SearchResponse
from app.scraper.listings import search_announcements

router = APIRouter(prefix="/search", tags=["search"])


@router.post("", response_model=SearchResponse)
async def search(request: SearchRequest) -> SearchResponse:
    outcome = await search_announcements(request)
    return SearchResponse(
        total_estimated=outcome.total_estimated,
        page=request.page,
        page_size=request.page_size,
        matches_found=outcome.matches_found,
        returned_count=len(outcome.results),
        scanned_portal_pages=outcome.scanned_portal_pages,
        results=outcome.results,
        source_url=outcome.source_url,
    )
