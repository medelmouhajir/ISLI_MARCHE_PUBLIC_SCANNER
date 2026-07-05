from datetime import date

from app.models import Category, SearchRequest
from app.scraper.details import parse_detail_html
from app.scraper.listings import _extract_total_count, _matches, _parse_list_page


def test_parse_detail_html(detail_html: str) -> None:
    detail = parse_detail_html(detail_html)
    assert detail.reference == "01/2027/dm"
    assert detail.object == "Fourniture de matériel informatique"
    assert detail.buyer == "Ministère de l'Économie"
    assert detail.category == "Fournitures"
    assert detail.procedure == "Appel d'offres ouvert | Sur offre de prix"
    assert detail.location == "RABAT"
    assert detail.deadline is not None
    assert detail.deadline.day == 19
    assert detail.published_date is None  # not present in the sample
    assert detail.estimated_amount == "100 000,00"
    assert detail.currency == "MAD"
    assert detail.reserved_tpe_pme is True
    assert detail.withdrawal_address == "Siège administratif"
    assert detail.deposit_address == "Plateforme en ligne"
    assert detail.opening_address == "RABAT"
    assert detail.contact_name == "M. Ahmed Bennani"
    assert detail.contact_email == "test@example.com"
    assert detail.contact_phone == "05 00 00 00 00"
    assert len(detail.documents) == 2
    assert "EntrepriseDownloadAvisJAL" in detail.documents[0].url


def test_extract_total_count(list_html: str) -> None:
    assert _extract_total_count(list_html) == 3


def test_parse_list_page(list_html: str) -> None:
    rows = _parse_list_page(list_html, "https://www.marchespublics.gov.ma")
    assert len(rows) == 3
    assert rows[0].refConsultation == "1005689"
    assert rows[0].orgAcronyme == "m1i"
    assert rows[0].object == "Fourniture de matériel informatique"
    assert rows[0].category == "Fournitures"
    assert rows[1].category == "Services"
    assert rows[2].category == "Travaux"


def test_matches_filters(list_html: str) -> None:
    rows = _parse_list_page(list_html, "https://www.marchespublics.gov.ma")
    req = SearchRequest(query="informatique", page=1, page_size=10)
    assert _matches(rows[0], req) is True
    assert _matches(rows[1], req) is False

    req_cat = SearchRequest(category=Category.TRAVAUX, page=1, page_size=10)
    assert _matches(rows[2], req_cat) is True
    assert _matches(rows[0], req_cat) is False
