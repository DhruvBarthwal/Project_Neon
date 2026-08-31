import os
import time
import uuid

import jwt
from fastapi import Header, HTTPException

JWT_SECRET = os.environ.get("JWT_SECRET")

if not JWT_SECRET:
    raise RuntimeError("Hardcoded JWT")

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
        raise HTTPException(status_code=401, detail="Invalid Token")
    
    
def get_current_agent(authorization: str = Header(...)) -> dict:
    if not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Expected 'Authorization: Bearer <token>' header")
    token = authorization.removeprefix("Bearer ").strip()
    return verify_agent_identity(token)