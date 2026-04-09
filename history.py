from fastapi import APIRouter, Depends, HTTPException, Query
from auth import get_current_user
from sqlalchemy import text as _text
from main import _engine

router = APIRouter()

@router.get("/history")
def get_history(repo_id: int | None = Query(default=None), limit: int = Query(default=100, le=500), current_user: dict = Depends(get_current_user)):
    user_id = int(current_user["sub"])
    with _engine.connect() as conn:
        if repo_id:
            owned = conn.execute(_text("SELECT id FROM repos WHERE id=:rid AND user_id=:uid"), {"rid": repo_id, "uid": user_id}).fetchone()
            if not owned:
                raise HTTPException(status_code=403, detail="Repo not found or not yours.")
            rows = conn.execute(_text("""
                SELECT id, filename, risk_score, high_risk_functions, repo_id, scanned_at
                FROM scan_reports WHERE repo_id=:rid ORDER BY scanned_at DESC LIMIT :lim
            """), {"rid": repo_id, "lim": limit}).fetchall()
        else:
            rows = conn.execute(_text("""
                SELECT sh.id, sh.filename, sh.risk_score, sh.high_risk_functions, sh.repo_id, sh.timestamp
                FROM scan_reports sh JOIN repos r ON r.id=sh.repo_id
                WHERE r.user_id=:uid ORDER BY sh.timestamp DESC LIMIT :lim
            """), {"uid": user_id, "lim": limit}).fetchall()
    return [{"id": r[0], "filename": r[1], "risk_score": r[2], "high_risk_functions": r[3], "repo_id": r[4], "scanned_at": str(r[5]) if r[5] else None} for r in rows]
