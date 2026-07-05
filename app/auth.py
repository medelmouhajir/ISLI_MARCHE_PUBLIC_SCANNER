import jwt
from fastapi import Header, HTTPException, status

from app.config import settings


def verify_internal_auth(x_internal_auth: str = Header(default=None)) -> dict:
    if not x_internal_auth:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing X-Internal-Auth header",
        )
    try:
        # ISLI Core's internal tokens do not include an "iss" claim, so we only
        # verify the signature and expiry here. The issuer check is intentionally
        # omitted to match Core's token format.
        payload = jwt.decode(
            x_internal_auth,
            settings.JWT_SECRET,
            algorithms=[settings.JWT_ALGORITHM],
        )
    except jwt.PyJWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid authentication token: {exc}",
        ) from exc
    return payload
