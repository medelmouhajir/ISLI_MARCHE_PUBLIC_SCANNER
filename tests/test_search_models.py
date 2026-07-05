import pytest
from pydantic import ValidationError

from app.config import settings
from app.models import SearchRequest


def test_default_search_request() -> None:
    req = SearchRequest()
    assert req.page == 1
    assert req.page_size == settings.DEFAULT_PAGE_SIZE
    assert req.max_results == settings.DEFAULT_MAX_RESULTS
    assert req.limit is None


def test_limit_normalizes_pagination() -> None:
    req = SearchRequest(page=3, page_size=50, max_results=200, limit=10)
    assert req.limit == 10
    assert req.page == 1
    assert req.page_size == 10
    assert req.max_results == 10


def test_page_size_rejected_above_max() -> None:
    with pytest.raises(ValidationError):
        SearchRequest(page_size=999)


def test_max_results_rejected_above_absolute_max() -> None:
    with pytest.raises(ValidationError):
        SearchRequest(max_results=999)


def test_limit_rejected_above_absolute_max() -> None:
    with pytest.raises(ValidationError):
        SearchRequest(limit=999)
