from fastapi import APIRouter

from app.config import settings
from app.models import DetailRequest, DetailResponse
from app.scraper.client import PortalClient
from app.scraper.details import parse_detail_html

router = APIRouter(prefix="/details", tags=["details"])


@router.post("", response_model=DetailResponse)
async def details(request: DetailRequest) -> DetailResponse:
    async with PortalClient() as client:
        html = await client.fetch_detail_html(request.refConsultation, request.orgAcronyme)

    detail = parse_detail_html(html)
    detail.refConsultation = request.refConsultation
    detail.orgAcronyme = request.orgAcronyme
    detail.detail_url = (
        f"{settings.PORTAL_BASE_URL}/?page=entreprise.EntrepriseDetailConsultation"
        f"&refConsultation={request.refConsultation}&orgAcronyme={request.orgAcronyme}"
    )
    return DetailResponse(data=detail, source_url=detail.detail_url)
