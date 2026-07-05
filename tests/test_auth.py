import datetime

import jwt
import pytest
from fastapi import HTTPException

from app.auth import verify_internal_auth
from app.config import settings


def _make_token(
    secret: str,
    issuer: str | None = "isli-core",
    delta_minutes: int = 10,
    core_style: bool = False,
) -> str:
    exp = datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(minutes=delta_minutes)
    if core_style:
        # Matches the token format ISLI Core actually sends: no iss claim.
        payload = {"sub": "agent-42", "scopes": ["skill"], "iat": datetime.datetime.now(datetime.timezone.utc), "exp": exp, "type": "internal"}
    else:
        payload = {"exp": exp}
        if issuer:
            payload["iss"] = issuer
    return jwt.encode(payload, secret, algorithm=settings.JWT_ALGORITHM)


def test_verify_internal_auth_accepts_valid_token() -> None:
    token = _make_token(settings.JWT_SECRET)
    payload = verify_internal_auth(token)
    assert payload.get("iss") == "isli-core"


def test_verify_internal_auth_accepts_core_style_token() -> None:
    token = _make_token(settings.JWT_SECRET, core_style=True)
    payload = verify_internal_auth(token)
    assert payload["sub"] == "agent-42"
    assert payload["type"] == "internal"


def test_verify_internal_auth_accepts_token_without_issuer() -> None:
    token = _make_token(settings.JWT_SECRET, issuer=None)
    payload = verify_internal_auth(token)
    assert "iss" not in payload


def test_verify_internal_auth_rejects_missing_header() -> None:
    with pytest.raises(HTTPException) as exc_info:
        verify_internal_auth(None)
    assert exc_info.value.status_code == 401


def test_verify_internal_auth_rejects_bad_secret() -> None:
    token = _make_token("wrong-secret")
    with pytest.raises(HTTPException) as exc_info:
        verify_internal_auth(token)
    assert exc_info.value.status_code == 401


def test_verify_internal_auth_rejects_expired_token() -> None:
    token = _make_token(settings.JWT_SECRET, delta_minutes=-10)
    with pytest.raises(HTTPException) as exc_info:
        verify_internal_auth(token)
    assert exc_info.value.status_code == 401
