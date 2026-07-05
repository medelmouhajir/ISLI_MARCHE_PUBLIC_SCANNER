from fastapi import APIRouter

from app.models import RecentRequest, RecentResponse
from app.scraper.listings import list_recent_announcements

router = APIRouter(prefix="/list_recent", tags=["recent"])


@router.post("", response_model=RecentResponse)
async def recent(request: RecentRequest) -> RecentResponse:
    category = request.category.value if request.category else None
    outcome = await list_recent_announcements(category=category, limit=request.limit)
    return RecentResponse(
        total_estimated=outcome.total_estimated,
        matches_found=outcome.matches_found,
        returned_count=len(outcome.results),
        scanned_portal_pages=outcome.scanned_portal_pages,
        results=outcome.results,
        source_url=outcome.source_url,
    )
