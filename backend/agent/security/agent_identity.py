import jwt
import time
import os

SECRET = os.getenv("AGENT_IDENTITY_SECRET", "dev-secret-change-me")

def issue_agent_identity(departement: str, user_id: str, convo_id: str) -> str:
    payload = {
        "department" : departement,
        "user_id": user_id,
        "convo_id": convo_id,
        "iat": time.time(),
    }
    
    return jwt.encode(payload, SECRET, algorithm="HS256")

def verify_agent_identity(token: str) -> dict:
    return jwt.decode(token, SECRET, algorithms=["HS256"])
                   