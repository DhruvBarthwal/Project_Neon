import os
import time
import uuid

import jwt
import logfire
from fastapi import Header, HTTPException
from typing import Optional

JWT_SECRET = os.environ.get("JWT_SECRET")

if not JWT_SECRET:
    raise RuntimeError("JWT_SECRET is not set — add it to your .env file.")

JWT_ALGORITHM = "HS256"
JWT_EXPIRY_SECONDS = int(os.environ.get("JWT_EXPIRY_SECONDS", 3600))

def issue_agent_identity(user_id: str, role: str = "viewer", convo_id: str | None = None) -> str:
    now = int(time.time())
    claims = {
        "sub": user_id,
        "role": role,
        "convo_id": convo_id or str(uuid.uuid4()),
        "iat": now,
        "exp": now + JWT_EXPIRY_SECONDS,
    }
    return jwt.encode(claims, JWT_SECRET, algorithm=JWT_ALGORITHM)


def verify_agent_identity(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired — request a new one from /auth/token")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


def get_current_agent(authorization: Optional[str] = Header(None)) -> dict:
    if not authorization:
        raise HTTPException(status_code=401, detail="Missing Authorization header")
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Expected 'Authorization: Bearer <token>' header")
        
    token = authorization.removeprefix("Bearer ").strip()
    claims = verify_agent_identity(token)

    logfire.info(
        "Authenticated request",
        actor=claims.get("sub"),
        role=claims.get("role"),
        convo_id=claims.get("convo_id"),
    )

    return claims