import os
from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"

os.environ.setdefault("JWT_SECRET", "a-test-secret-that-is-long-enough-for-hs256-signing")
os.environ.setdefault("JWT_ISSUER", "isli-core")


@pytest.fixture
def detail_html() -> str:
    return (FIXTURES_DIR / "detail_sample.html").read_text(encoding="utf-8")


@pytest.fixture
def list_html() -> str:
    return (FIXTURES_DIR / "list_sample.html").read_text(encoding="utf-8")
