import secrets
from fastapi import APIRouter, HTTPException, Depends, status, Query
from pydantic import BaseModel
from auth import get_current_user
from sqlalchemy import text as _text
from database import _engine

router = APIRouter()

class RepoRegisterRequest(BaseModel):
    repo_name: str
    github_url: str

class RepoOut(BaseModel):
    id: int
    repo_name: str
    github_url: str
    api_key: str

@router.post("/register", response_model=RepoOut, status_code=201)
def register_repo(body: RepoRegisterRequest, current_user: dict = Depends(get_current_user)):
    user_id = int(current_user["sub"])
    api_key = secrets.token_hex(32)
    with _engine.connect() as conn:
        tier_row = conn.execute(_text("SELECT tier FROM users WHERE id=:uid"), {"uid": user_id}).fetchone()
        tier = tier_row[0] if tier_row else "free"
        limit_row = conn.execute(_text("SELECT max_repos FROM tier_limits WHERE tier=:t"), {"t": tier}).fetchone()
        max_repos = limit_row[0] if limit_row else 3
        count = conn.execute(_text("SELECT COUNT(*) FROM repos WHERE user_id=:uid"), {"uid": user_id}).fetchone()[0]
        if count >= max_repos:
            raise HTTPException(status_code=402, detail=f"Free tier allows {max_repos} repos. Upgrade to Pro.")
        row = conn.execute(_text("""
            INSERT INTO repos (user_id, repo_name, github_url, api_key)
            VALUES (:uid, :rname, :gurl, :akey)
            ON CONFLICT DO NOTHING
            RETURNING id, repo_name, github_url, api_key
        """), {"uid": user_id, "rname": body.repo_name, "gurl": body.github_url, "akey": api_key}).fetchone()
        conn.commit()
    if not row:
        raise HTTPException(status_code=409, detail="Repo already registered.")
    return RepoOut(id=row[0], repo_name=row[1], github_url=row[2], api_key=row[3])

@router.get("/", response_model=list[RepoOut])
def list_repos(current_user: dict = Depends(get_current_user)):
    user_id = int(current_user["sub"])
    with _engine.connect() as conn:
        rows = conn.execute(_text(
            "SELECT id, repo_name, github_url, api_key FROM repos WHERE user_id=:uid ORDER BY created_at DESC"
        ), {"uid": user_id}).fetchall()
    return [RepoOut(id=r[0], repo_name=r[1], github_url=r[2], api_key=r[3]) for r in rows]

@router.delete("/{repo_id}", status_code=204)
def delete_repo(repo_id: int, current_user: dict = Depends(get_current_user)):
    user_id = int(current_user["sub"])
    with _engine.connect() as conn:
        deleted = conn.execute(_text(
            "DELETE FROM repos WHERE id=:rid AND user_id=:uid RETURNING id"
        ), {"rid": repo_id, "uid": user_id}).fetchone()
        conn.commit()
    if not deleted:
        raise HTTPException(status_code=404, detail="Repo not found or not yours.")
