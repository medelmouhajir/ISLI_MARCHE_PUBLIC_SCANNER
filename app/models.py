from datetime import date, datetime
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, field_validator


class Category(str, Enum):
    TRAVAUX = "Travaux"
    FOURNITURES = "Fournitures"
    SERVICES = "Services"


class DocumentLink(BaseModel):
    name: str
    url: Optional[str] = None
    size: Optional[str] = None


class AnnouncementSummary(BaseModel):
    refConsultation: str
    orgAcronyme: str
    reference: Optional[str] = None
    object: Optional[str] = None
    buyer: Optional[str] = None
    category: Optional[str] = None
    procedure: Optional[str] = None
    location: Optional[str] = None
    deadline: Optional[datetime] = None
    published_date: Optional[date] = None
    detail_url: str


class AnnouncementDetail(AnnouncementSummary):
    estimated_amount: Optional[str] = None
    currency: Optional[str] = None
    lots: Optional[str] = None
    reserved_tpe_pme: Optional[bool] = None
    withdrawal_address: Optional[str] = None
    deposit_address: Optional[str] = None
    opening_address: Optional[str] = None
    contact_name: Optional[str] = None
    contact_email: Optional[str] = None
    contact_phone: Optional[str] = None
    documents: List[DocumentLink] = Field(default_factory=list)
    raw_sections: Dict[str, Any] = Field(default_factory=dict)


class SearchRequest(BaseModel):
    query: Optional[str] = Field(default=None, description="Free-text keyword matched against reference, object, buyer, or location.")
    category: Optional[Category] = None
    procedure: Optional[str] = None
    location: Optional[str] = None
    buyer: Optional[str] = None
    published_after: Optional[date] = None
    published_before: Optional[date] = None
    deadline_after: Optional[datetime] = None
    deadline_before: Optional[datetime] = None
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=20, ge=1, le=100)
    max_pages_to_scan: Optional[int] = Field(default=None, ge=1, le=20)

    @field_validator("page_size")
    @classmethod
    def cap_page_size(cls, v: int) -> int:
        return min(v, 100)


class SearchResponse(BaseModel):
    total_estimated: Optional[int] = None
    page: int
    page_size: int
    results: List[AnnouncementSummary] = Field(default_factory=list)
    source_url: str


class DetailRequest(BaseModel):
    refConsultation: str
    orgAcronyme: str


class DetailResponse(BaseModel):
    data: AnnouncementDetail
    source_url: str


class RecentRequest(BaseModel):
    category: Optional[Category] = None
    limit: int = Field(default=10, ge=1, le=100)


class RecentResponse(BaseModel):
    total_estimated: Optional[int] = None
    results: List[AnnouncementSummary] = Field(default_factory=list)
    source_url: str
