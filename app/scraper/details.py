import re
from datetime import datetime
from typing import Any, Dict, List, Optional

from bs4 import BeautifulSoup, Tag

from app.config import settings
from app.models import AnnouncementDetail, DocumentLink
from app.scraper.parser import (
    clean_text,
    make_absolute_url,
    parse_portal_date,
    parse_portal_datetime,
    soup,
)


def parse_detail_html(html: str) -> AnnouncementDetail:
    bs = soup(html)

    # Parse all labelled lines in the recap consultation block.
    raw = _extract_labelled_lines(bs)

    # Extract documents from the download section
    documents: List[DocumentLink] = []
    for link in bs.find_all("a", href=True):
        href = link["href"]
        if "EntrepriseDownload" in href or "EntrepriseDemandeTelechargementDce" in href:
            text = clean_text(link.get_text()) or "Document"
            url = make_absolute_url(href, settings.PORTAL_BASE_URL)
            documents.append(DocumentLink(name=text, url=url))

    reference = _get(raw, "Référence")
    obj = _get(raw, "Objet")
    buyer = _get(raw, "Acheteur public")
    category = _get(raw, "Catégorie principale")
    procedure = _get(raw, "Procédure")
    lots = _get(raw, "Allotissement")
    location = _dedupe_repeated_tokens(_get(raw, "Lieu d'exécution"))

    estimation_key, amount_text = _find_estimation(raw)
    currency = None
    estimated_amount = None
    if amount_text:
        amount_match = re.search(r"([\d\s,]+)", amount_text.replace(" ", " "))
        if amount_match:
            estimated_amount = amount_match.group(1).strip()
        if estimation_key and ("Dhs" in estimation_key or "MAD" in estimation_key):
            currency = "MAD"

    deadline_text = _find_deadline(bs)
    published_text = _get(raw, "Publié le") or _get(raw, "Date de publication")

    reserved_text = _get(raw, "Réservé")
    reserved = "Oui" in reserved_text if reserved_text else None

    contact_block = _get(raw, "Contact Administratif")
    contact_name, contact_email, contact_phone = _split_contact(contact_block)

    detail = AnnouncementDetail(
        refConsultation="",
        orgAcronyme="",
        reference=reference,
        object=obj,
        buyer=buyer,
        category=category,
        procedure=procedure,
        location=location,
        deadline=parse_portal_datetime(deadline_text),
        published_date=parse_portal_date(published_text),
        detail_url="",
        estimated_amount=estimated_amount,
        currency=currency,
        lots=lots,
        reserved_tpe_pme=reserved,
        withdrawal_address=_get(raw, "Adresse de retrait des dossiers"),
        deposit_address=_get(raw, "Adresse de dépôt des offres"),
        opening_address=_get(raw, "Lieu d'ouverture des plis"),
        contact_name=contact_name,
        contact_email=contact_email,
        contact_phone=contact_phone,
        documents=documents,
        raw_sections=raw,
    )
    return detail


def _extract_labelled_lines(bs: BeautifulSoup) -> Dict[str, str]:
    """Extract key/value pairs from the detail page's labelled-line layout."""
    raw: Dict[str, str] = {}

    # Main labelled lines: div.line with div.intitule-240.bold label and content-bloc value.
    for line in bs.find_all("div", class_="line"):
        label_el = line.find("div", class_=re.compile(r"intitule-240"))
        if label_el is None:
            continue

        label = clean_text(label_el.get_text("\n"))
        if not label:
            continue
        label = label.rstrip(" :").strip()

        # Skip if this is a section heading without a value.
        value_els = line.find_all(["div", "span"], class_=re.compile(r"content-bloc"))
        if not value_els:
            # Some referentiel lines use a span with id containing labelReferentiel as value.
            value_els = line.find_all("span", id=re.compile(r"labelReferentiel"))

        values = []
        for vel in value_els:
            # Remove tooltip/popup duplicates.
            clone = vel.__copy__()
            for popup in clone.find_all(class_=["info-bulle", "info-suite"]):
                popup.decompose()
            for hidden in clone.find_all(style=re.compile(r"display\s*:\s*none", re.I)):
                hidden.decompose()
            val_text = clean_text(clone.get_text("\n"))
            if val_text:
                values.append(val_text)

        if values:
            raw[label] = " ".join(values)

    return raw


def _get(raw: Dict[str, Any], key: str) -> Optional[str]:
    for k, v in raw.items():
        if key.lower() in k.lower():
            return v
    return None


def _dedupe_repeated_tokens(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    tokens = value.split()
    seen = set()
    result = []
    for token in tokens:
        if token not in seen:
            seen.add(token)
            result.append(token)
    return " ".join(result) if result else None


def _find_estimation(raw: Dict[str, Any]) -> tuple[Optional[str], Optional[str]]:
    for k, v in raw.items():
        if "estimation" in k.lower():
            return k, v
    return None, None


def _find_deadline(bs: BeautifulSoup) -> Optional[str]:
    # Deadline is shown above the labelled lines, often in a dedicated span.
    span = bs.find("span", id=re.compile(r"dateHeureLimiteRemisePlis"))
    if span:
        return clean_text(span.get_text())
    # Fallback: text node search.
    marker = bs.find(string=re.compile(r"Date et heure limite de remise des plis"))
    if marker:
        for sibling in marker.parent.next_siblings:
            if getattr(sibling, "name", None) in ("p", "div", "span"):
                return clean_text(sibling.get_text())
    return None


def _split_contact(contact_block: Optional[str]) -> tuple[Optional[str], Optional[str], Optional[str]]:
    if not contact_block:
        return None, None, None

    email_match = re.search(r"\S+@\S+", contact_block)
    email = email_match.group(0) if email_match else None

    # Phone/fax: a sequence of digits, spaces, dots, or dashes with at least 8 digits.
    phone_match = re.search(r"[\d\s\.\-]{8,}", contact_block)
    phone = phone_match.group(0).strip() if phone_match else None

    name = contact_block
    if email:
        name = name.replace(email, "")
    if phone:
        name = name.replace(phone, "")
    name = clean_text(name)

    return name, email, phone
