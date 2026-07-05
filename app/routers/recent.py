from fastapi import APIRouter

from app.models import RecentRequest, RecentResponse
from app.scraper.listings import list_recent_announcements

router = APIRouter(prefix="/list_recent", tags=["recent"])


@router.post("", response_model=RecentResponse)
async def recent(request: RecentRequest) -> RecentResponse:
    category = request.category.value if request.category else None
    results, total, source_url = await list_recent_announcements(
        category=category, limit=request.limit
    )
    return RecentResponse(
        total_estimated=total,
        results=results,
        source_url=source_url,
    )
