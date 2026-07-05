import re
from datetime import date, datetime
from typing import Optional

from bs4 import BeautifulSoup


def parse_portal_datetime(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    value = value.strip()
    for fmt in ("%d/%m/%Y %H:%M", "%d/%m/%Y"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    return None


def parse_portal_date(value: Optional[str]) -> Optional[date]:
    dt = parse_portal_datetime(value)
    if dt is None:
        return None
    return dt.date()


def clean_text(value: Optional[str]) -> Optional[str]:
    if not value:
        return None
    text = value.replace("\r", " ").replace("\n", " ")
    text = re.sub(r"\s+", " ", text).strip()
    return text if text else None


def extract_detail_link_params(href: str) -> dict:
    ref = re.search(r"refConsultation=([^&]+)", href)
    org = re.search(r"orgAcronyme=([^&]+)", href)
    return {
        "refConsultation": ref.group(1) if ref else None,
        "orgAcronyme": org.group(1) if org else None,
    }


def make_absolute_url(href: str, base_url: str) -> str:
    if href.startswith("http://") or href.startswith("https://"):
        return href
    if href.startswith("/?"):
        return base_url + href
    if href.startswith("index.php"):
        return base_url + "/" + href
    return base_url + "/" + href.lstrip("/")


def soup(html: str) -> BeautifulSoup:
    return BeautifulSoup(html, "lxml")
