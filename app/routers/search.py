from fastapi import APIRouter

from app.models import SearchRequest, SearchResponse
from app.scraper.listings import search_announcements

router = APIRouter(prefix="/search", tags=["search"])


@router.post("", response_model=SearchResponse)
async def search(request: SearchRequest) -> SearchResponse:
    results, total, source_url = await search_announcements(request)
    return SearchResponse(
        total_estimated=total,
        page=request.page,
        page_size=request.page_size,
        results=results,
        source_url=source_url,
    )
