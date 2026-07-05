import datetime

import jwt
import pytest
from fastapi import HTTPException

from app.auth import verify_internal_auth
from app.config import settings


def _make_token(secret: str, issuer: str = "isli-core", delta_minutes: int = 10) -> str:
    payload = {
        "iss": issuer,
        "exp": datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=delta_minutes),
    }
    return jwt.encode(payload, secret, algorithm=settings.JWT_ALGORITHM)


def test_verify_internal_auth_accepts_valid_token() -> None:
    token = _make_token(settings.JWT_SECRET)
    payload = verify_internal_auth(token)
    assert payload["iss"] == "isli-core"


def test_verify_internal_auth_rejects_missing_header() -> None:
    with pytest.raises(HTTPException) as exc_info:
        verify_internal_auth(None)
    assert exc_info.value.status_code == 401


def test_verify_internal_auth_rejects_bad_secret() -> None:
    token = _make_token("wrong-secret")
    with pytest.raises(HTTPException) as exc_info:
        verify_internal_auth(token)
    assert exc_info.value.status_code == 401


def test_verify_internal_auth_rejects_wrong_issuer() -> None:
    token = _make_token(settings.JWT_SECRET, issuer="other-issuer")
    with pytest.raises(HTTPException) as exc_info:
        verify_internal_auth(token)
    assert exc_info.value.status_code == 401


def test_verify_internal_auth_rejects_expired_token() -> None:
    token = _make_token(settings.JWT_SECRET, delta_minutes=-10)
    with pytest.raises(HTTPException) as exc_info:
        verify_internal_auth(token)
    assert exc_info.value.status_code == 401
