import os, secrets, httpx
from datetime import datetime, timedelta, timezone
from fastapi import APIRouter, HTTPException, Depends, status
from fastapi.responses import RedirectResponse
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
import jwt
from sqlalchemy import text as _text
from database import _engine

router = APIRouter()
bearer_scheme = HTTPBearer()

GITHUB_CLIENT_ID     = os.environ.get("GITHUB_CLIENT_ID", "")
GITHUB_CLIENT_SECRET = os.environ.get("GITHUB_CLIENT_SECRET", "")
JWT_SECRET           = os.environ.get("JWT_SECRET", "dev-secret")
FRONTEND_URL         = os.environ.get("FRONTEND_URL", "http://localhost:8501")
JWT_ALGORITHM        = "HS256"
JWT_TTL_HOURS        = 72

def create_jwt(user_id: int, username: str) -> str:
    payload = {
        "sub": str(user_id),
        "username": username,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_TTL_HOURS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def decode_jwt(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")

def get_current_user(credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme)) -> dict:
    return decode_jwt(credentials.credentials)

@router.get("/github")
def github_login():
    state = secrets.token_urlsafe(16)
    url = (
        f"https://github.com/login/oauth/authorize"
        f"?client_id={GITHUB_CLIENT_ID}&scope=read:user,user:email&state={state}"
    )
    return RedirectResponse(url)

@router.get("/github/callback")
async def github_callback(code: str, state: str):
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            "https://github.com/login/oauth/access_token",
            headers={"Accept": "application/json"},
            json={"client_id": GITHUB_CLIENT_ID, "client_secret": GITHUB_CLIENT_SECRET, "code": code},
        )
    token_data = token_resp.json()
    access_token = token_data.get("access_token")
    if not access_token:
        raise HTTPException(status_code=400, detail="GitHub OAuth failed")

    async with httpx.AsyncClient() as client:
        user_resp = await client.get(
            "https://api.github.com/user",
            headers={"Authorization": f"Bearer {access_token}"},
        )
    gh = user_resp.json()

    with _engine.connect() as conn:
        result = conn.execute(_text("""
            INSERT INTO users (github_id, username, email, avatar_url)
            VALUES (:gid, :uname, :email, :avatar)
            ON CONFLICT (github_id) DO UPDATE
                SET username=EXCLUDED.username, email=EXCLUDED.email, avatar_url=EXCLUDED.avatar_url
            RETURNING id, tier
        """), {"gid": gh["id"], "uname": gh["login"], "email": gh.get("email"), "avatar": gh.get("avatar_url")})
        row = result.fetchone()
        conn.commit()

    jwt_token = create_jwt(row[0], gh["login"])
    return RedirectResponse(f"{FRONTEND_URL}?token={jwt_token}&tier={row[1]}")

@router.get("/me")
def me(current_user: dict = Depends(get_current_user)):
    return current_user
