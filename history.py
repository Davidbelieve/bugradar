import os
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import text as _text

from database import _engine
from auth import get_current_user

router = APIRouter()


@router.get("/history")
def get_history(
    repo_id: int | None = Query(default=None),
    limit: int = Query(default=100),
    current_user=Depends(get_current_user),
):
    user_id = int(current_user["sub"])

    with _engine.connect() as conn:
        if repo_id:
            # Verify repo belongs to this user
            owned = conn.execute(
                _text("SELECT id FROM repos WHERE id=:rid AND user_id=:uid"),
                {"rid": repo_id, "uid": user_id}
            ).fetchone()
            if not owned:
                raise HTTPException(status_code=403, detail="Repo not found or not yours.")

            rows = conn.execute(_text("""
                SELECT id, repo, pr_number, files_scanned, high_risk,
                       medium_risk, low_risk, timestamp, repo_id
                FROM scan_reports
                WHERE repo_id=:rid
                ORDER BY timestamp DESC
                LIMIT :lim
            """), {"rid": repo_id, "lim": limit}).fetchall()
        else:
            rows = conn.execute(_text("""
                SELECT sh.id, sh.repo, sh.pr_number, sh.files_scanned,
                       sh.high_risk, sh.medium_risk, sh.low_risk,
                       sh.timestamp, sh.repo_id
                FROM scan_reports sh
                JOIN repos r ON r.id=sh.repo_id
                WHERE r.user_id=:uid
                ORDER BY sh.timestamp DESC
                LIMIT :lim
            """), {"uid": user_id, "lim": limit}).fetchall()

    return [
        {
            "id":            r[0],
            "repo":          r[1],
            "pr_number":     r[2],
            "files_scanned": r[3],
            "high_risk":     r[4],
            "medium_risk":   r[5],
            "low_risk":      r[6],
            "scanned_at":    str(r[7]),
            "repo_id":       r[8],
        }
        for r in rows
    ] if rows else []
