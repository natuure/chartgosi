import base64
import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from typing import Any

from fastapi import Depends, Header, HTTPException, status
import jwt
from jwt import InvalidTokenError, PyJWKClient, PyJWKClientError
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db.database import get_session

DEV_USER_ID = "00000000-0000-0000-0000-000000000001"
DEV_USER_EMAIL = "dev@chartgosi.local"


@dataclass(frozen=True)
class CurrentUser:
    id: str
    email: str
    nickname: str


async def get_current_user(
    authorization: str | None = Header(default=None),
    session: AsyncSession = Depends(get_session),
) -> CurrentUser:
    user = await resolve_current_user(authorization, session, required=True)
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return user


async def get_optional_current_user(
    authorization: str | None = Header(default=None),
    session: AsyncSession = Depends(get_session),
) -> CurrentUser | None:
    return await resolve_current_user(authorization, session, required=False)


async def resolve_current_user(
    authorization: str | None,
    session: AsyncSession,
    required: bool,
) -> CurrentUser | None:
    token = bearer_token_from_header(authorization)
    if token:
        payload = verify_supabase_jwt(token)
        user = current_user_from_payload(payload)
        await upsert_user(session, user)
        return user

    if settings.allow_dev_auth_fallback:
        user = CurrentUser(id=DEV_USER_ID, email=DEV_USER_EMAIL, nickname="개발 사용자")
        await upsert_user(session, user)
        return user

    if required:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required")
    return None


def bearer_token_from_header(authorization: str | None) -> str | None:
    if not authorization:
        return None
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid authorization header")
    return token.strip()


def verify_supabase_jwt(token: str) -> dict[str, Any]:
    parts = token.split(".")
    if len(parts) != 3:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token")

    header_raw, payload_raw, _signature_raw = parts
    header = json.loads(base64url_decode(header_raw))
    algorithm = header.get("alg")

    if algorithm == "HS256":
        return verify_supabase_hs256_jwt(token, header_raw, payload_raw)

    if algorithm in {"RS256", "ES256"}:
        return verify_supabase_jwks_jwt(token, algorithm)

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Unsupported token algorithm: {algorithm}")


def verify_supabase_hs256_jwt(token: str, header_raw: str, payload_raw: str) -> dict[str, Any]:
    if not settings.supabase_jwt_secret:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Supabase JWT secret is not configured")

    _header_raw, _payload_raw, signature_raw = token.split(".")
    signing_input = f"{header_raw}.{payload_raw}".encode("utf-8")
    expected = hmac.new(settings.supabase_jwt_secret.encode("utf-8"), signing_input, hashlib.sha256).digest()
    actual = base64url_decode(signature_raw)
    if not hmac.compare_digest(expected, actual):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token signature")

    payload = json.loads(base64url_decode(payload_raw))
    exp = payload.get("exp")
    if isinstance(exp, int) and exp < int(time.time()):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired")
    if not payload.get("sub"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token subject is missing")
    return payload


def verify_supabase_jwks_jwt(token: str, algorithm: str) -> dict[str, Any]:
    if not settings.supabase_jwks_url or not settings.supabase_issuer:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="SUPABASE_URL is not configured for JWKS token verification",
        )

    try:
        signing_key = PyJWKClient(settings.supabase_jwks_url).get_signing_key_from_jwt(token)
        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=[algorithm],
            audience="authenticated",
            issuer=settings.supabase_issuer,
        )
    except PyJWKClientError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Unable to load Supabase JWKS: {exc}") from exc
    except InvalidTokenError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=f"Invalid token: {exc}") from exc

    if not payload.get("sub"):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token subject is missing")
    return payload


def base64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(value + padding)


def current_user_from_payload(payload: dict[str, Any]) -> CurrentUser:
    user_id = str(payload["sub"])
    email = str(payload.get("email") or f"{user_id}@supabase.local")
    metadata = payload.get("user_metadata") or {}
    nickname = metadata.get("nickname") or metadata.get("name") or email.split("@")[0] or "차트고시 사용자"
    return CurrentUser(id=user_id, email=email, nickname=str(nickname)[:80])


async def upsert_user(session: AsyncSession, user: CurrentUser) -> None:
    await session.execute(
        text(
            """
            INSERT INTO users (id, email, nickname)
            VALUES (CAST(:id AS uuid), :email, :nickname)
            ON CONFLICT (id) DO UPDATE
            SET
              email = EXCLUDED.email,
              nickname = COALESCE(NULLIF(users.nickname, ''), EXCLUDED.nickname),
              updated_at = now()
            """
        ),
        {"id": user.id, "email": user.email, "nickname": user.nickname},
    )
    await session.commit()
