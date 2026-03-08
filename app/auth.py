from dataclasses import dataclass

import httpx
from fastapi import Header, HTTPException, status

from .config import settings


@dataclass
class CurrentUser:
    id: str
    email: str
    name: str | None = None


async def get_current_user(authorization: str | None = Header(default=None)) -> CurrentUser:
    if settings.allow_anon_chat:
        return CurrentUser(id="anon-user", email="anon@example.com", name="Anonymous")

    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Missing bearer token")

    if not settings.supabase_url or not settings.supabase_anon_key:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Supabase credentials are not configured",
        )

    token = authorization.split(" ", maxsplit=1)[1].strip()
    user_endpoint = f"{settings.supabase_url.rstrip('/')}/auth/v1/user"

    headers = {
        "apikey": settings.supabase_anon_key,
        "Authorization": f"Bearer {token}",
    }

    async with httpx.AsyncClient(timeout=15.0) as client:
        response = await client.get(user_endpoint, headers=headers)

    if response.status_code != 200:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid auth token")

    payload = response.json()
    user_metadata = payload.get("user_metadata") or {}
    return CurrentUser(
        id=str(payload.get("id")),
        email=payload.get("email") or "",
        name=user_metadata.get("name") or user_metadata.get("full_name"),
    )
