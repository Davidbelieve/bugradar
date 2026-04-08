# ============================================================
# BugRadar API â€” main.py
# ML-powered software defect prediction
# Run locally: uvicorn main:app --reload
# ============================================================

from fastapi import FastAPI, HTTPException, UploadFile, File
from radon.complexity import cc_visit, cc_rank
from radon.metrics import h_visit
from radon.raw import analyze
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
from typing import Optional
import joblib
import numpy as np
import os

# â”€â”€ Load model artefacts â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# All three files must sit in the same folder as main.py
MODEL_PATH     = "bugradar_model/model.pkl"
SCALER_PATH    = "bugradar_model/scaler.pkl"
FEATURES_PATH  = "bugradar_model/features.pkl"
THRESHOLD_PATH = "bugradar_model/threshold.pkl"

for path in [MODEL_PATH, SCALER_PATH, FEATURES_PATH, THRESHOLD_PATH]:
    if not os.path.exists(path):
        raise FileNotFoundError(f"âŒ Missing file: {path}")

model     = joblib.load(MODEL_PATH)
scaler    = joblib.load(SCALER_PATH)
features  = joblib.load(FEATURES_PATH)
threshold = joblib.load(THRESHOLD_PATH)

print(f"âœ… Model loaded â€” {len(features)} features expected")
print(f"âœ… Threshold loaded â€” {threshold:.2f} (v3 optimised)")

# â”€â”€ FastAPI app setup â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
app = FastAPI(
    title="BugRadar API",
    description="ML-powered software defect prediction using NASA KC1 model. "
                "Send 21 code complexity metrics, receive a defect risk score.",
    version="1.0.0",
    docs_url="/docs",      # Swagger UI at /docs
    redoc_url="/redoc"     # Alternative docs at /redoc
)

# Allow all origins for now â€” tighten this when deploying to production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# â”€â”€ Input schema â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
# Pydantic validates every incoming field automatically.
# All 21 features match the NASA KC1 column names exactly.
class CodeMetrics(BaseModel):
    model_config = {"populate_by_name": True}

    loc:              float = Field(..., description="McCabe line count of code")
    v_g:              float = Field(..., description="McCabe cyclomatic complexity", alias="v(g)")
    ev_g:             float = Field(..., description="McCabe essential complexity", alias="ev(g)")
    iv_g:             float = Field(..., description="McCabe design complexity", alias="iv(g)")
    n:                float = Field(..., description="Halstead total operators + operands")
    v:                float = Field(..., description="Halstead volume")
    l:                float = Field(..., description="Halstead program length")
    d:                float = Field(..., description="Halstead difficulty")
    i:                float = Field(..., description="Halstead intelligence")
    e:                float = Field(..., description="Halstead effort")
    b:                float = Field(..., description="Halstead bugs estimate")
    t:                float = Field(..., description="Halstead time estimator")
    lOCode:           float = Field(..., description="Lines of code")
    lOComment:        float = Field(..., description="Lines of comments")
    lOBlank:          float = Field(..., description="Blank lines")
    lOCodeAndComment: float = Field(..., description="Lines with code and comments")
    uniq_Op:          float = Field(..., description="Unique operators")
    uniq_Opnd:        float = Field(..., description="Unique operands")
    total_Op:         float = Field(..., description="Total operators")
    total_Opnd:       float = Field(..., description="Total operands")
    branchCount:      float = Field(..., description="Flow graph branch count")
    module_name:      Optional[str] = Field(None, description="Optional module name")


# â”€â”€ Output schema â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
class PredictionResult(BaseModel):
    module_name:   str
    risk_score:    float   # probability of defect: 0.0 â†’ 1.0
    verdict:       str     # "Low Risk" / "Medium Risk" / "High Risk"
    confidence:    str     # human-readable confidence level
    top_risk_factors: list # top 3 features driving the prediction
    recommendation: str

    class FunctionResult(BaseModel):
     function_name:    str
    line_number:      int
    risk_score:       float
    verdict:          str
    complexity:       int
    rank:             str
    top_risk_factors: list
    recommendation:   str

class ScanReport(BaseModel):
    repo:          str
    pr_number:     int
    files_scanned: int
    high_risk:     int
    medium_risk:   int
    low_risk:      int
    timestamp:     str


class PythonFileResult(BaseModel):
    filename:         str
    total_functions:  int
    high_risk:        int
    medium_risk:      int
    low_risk:         int
    functions:        list

# â”€â”€ Helper: risk label from probability â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def get_verdict(prob: float) -> tuple[str, str]:
    if prob < 0.30:
        return "Low Risk",    "The model is confident this module is likely clean."
    elif prob < 0.60:
        return "Medium Risk", "This module shows some defect indicators â€” worth a review."
    else:
        return "High Risk",   "Strong defect signals detected â€” prioritise this module for review."

# â”€â”€ Radon metric extractor â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def extract_radon_metrics(source_code: str, func_name: str) -> dict:
    raw     = analyze(source_code)
    hal     = h_visit(source_code)
    h       = hal[0] if hal else None
    blocks  = cc_visit(source_code)
    func_cc = next((b for b in blocks if b.name == func_name), None)
    v_g     = func_cc.complexity if func_cc else 1
    rank    = cc_rank(v_g)

    # Halstead attributes use h1/h2/N1/N2 naming convention
    n   = (h.N1 + h.N2)          if h else 0
    vol = h.volume                if h else 0
    dif = h.difficulty            if h else 0
    eff = h.effort                if h else 0

    return {
        "loc":               raw.loc,
        "v(g)":              v_g,
        "ev(g)":             max(1, v_g - (raw.lloc // 10)),
        "iv(g)":             max(1, v_g // 2),
        "n":                 n,
        "v":                 vol,
        "l":                 (eff / vol) if vol > 0 else 0,
        "d":                 dif,
        "i":                 (vol / dif) if dif > 0 else 0,
        "e":                 eff,
        "b":                 h.bugs       if h else 0,
        "t":                 h.time       if h else 0,
        "lOCode":            raw.lloc,
        "lOComment":         raw.comments,
        "lOBlank":           raw.blank,
        "locCodeAndComment": raw.multi,
        "uniq_Op":           h.h1         if h else 0,
        "uniq_Opnd":         h.h2         if h else 0,
        "total_Op":          h.N1         if h else 0,
        "total_Opnd":        h.N2         if h else 0,
        "branchCount":       max(0, v_g * 2 - 1),
        "_rank":             rank,
        "_cc":               v_g
    }


# â”€â”€ Helper: top contributing features â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
def get_top_factors(input_array: np.ndarray) -> list:
    importances  = model.feature_importances_   # Random Forest built-in
    scaled_input = scaler.transform(input_array)

    # Weight each feature value by its importance score
    contributions = np.abs(scaled_input[0]) * importances
    top_indices   = contributions.argsort()[::-1][:3]   # top 3

    return [
        {
            "feature":    features[i],
            "importance": round(float(importances[i]), 4),
            "value":      round(float(input_array[0][i]), 4)
        }
        for i in top_indices
    ]


# â”€â”€ Routes â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

@app.get("/", tags=["Health"])
def root():
    """Health check â€” confirms the API is running."""
    return {
        "status":    "âœ… BugOracle by Dav API is live",
        "version":   "3.0.0",
        "model":     "Random Forest â€” KC1 + PC1 combined (AUC-ROC: 0.8531)",
        "threshold": threshold,
        "docs":      "/docs"
    }


@app.get("/features", tags=["Info"])
def list_features():
    """Returns the 21 expected input features in the correct order."""
    return {
        "total_features": len(features),
        "features": [{"index": i+1, "name": f} for i, f in enumerate(features)]
    }


@app.post("/predict", response_model=PredictionResult, tags=["Prediction"])
def predict(metrics: CodeMetrics):
    """
    Accepts 21 code complexity metrics and returns a defect risk score.

    - **risk_score**: probability of defect (0.0 = clean, 1.0 = certain defect)
    - **verdict**: Low / Medium / High Risk
    - **top_risk_factors**: the 3 metrics contributing most to the prediction
    """
    try:
        # Build feature vector in the same order the model was trained on
        # Build feature map dynamically â€” avoids any manual naming mismatches
        metrics_dict = {
            "loc":              metrics.loc,
            "v(g)":             metrics.v_g,
            "ev(g)":            metrics.ev_g,
            "iv(g)":            metrics.iv_g,
            "n":                metrics.n,
            "v":                metrics.v,
            "l":                metrics.l,
            "d":                metrics.d,
            "i":                metrics.i,
            "e":                metrics.e,
            "b":                metrics.b,
            "t":                metrics.t,
            "lOCode":           metrics.lOCode,
            "lOComment":        metrics.lOComment,
            "lOBlank":          metrics.lOBlank,
            "lOCodeAndComment": metrics.lOCodeAndComment,
            "uniq_Op":          metrics.uniq_Op,
            "uniq_Opnd":        metrics.uniq_Opnd,
            "total_Op":         metrics.total_Op,
            "total_Opnd":       metrics.total_Opnd,
            "branchCount":      metrics.branchCount,
        }

        # Print feature names for debugging â€” remove after confirming it works
        print(f"Expected features: {features}")
        print(f"Provided keys:     {list(metrics_dict.keys())}")

        feature_map = metrics_dict

        # Arrange values in the exact training order
        input_values = np.array([[feature_map[f] for f in features]])

        # Scale using the same scaler fitted on training data
        input_scaled = scaler.transform(input_values)

        # Use optimised v3 threshold instead of default 0.5
        # threshold=0.40 was tuned to maximise F1 on KC1 test set
        risk_score    = float(model.predict_proba(input_scaled)[0][1])
        y_pred        = int(risk_score >= threshold)
        verdict, confidence = get_verdict(risk_score)
        top_factors   = get_top_factors(input_values)

        # Dynamic recommendation based on risk level
        if verdict == "High Risk":
            rec = "Schedule immediate code review. Focus on reducing cyclomatic complexity and splitting large functions."
        elif verdict == "Medium Risk":
            rec = "Include in next sprint review. Consider refactoring the highest-complexity sections."
        else:
            rec = "No immediate action required. Standard review process applies."

        return PredictionResult(
            module_name       = metrics.module_name or "unnamed_module",
            risk_score        = round(risk_score, 4),
            verdict           = verdict,
            confidence        = confidence,
            top_risk_factors  = top_factors,
            recommendation    = rec
        )

    except Exception as ex:
        raise HTTPException(status_code=500, detail=f"Prediction error: {str(ex)}")


@app.post("/predict/batch", tags=["Prediction"])
def predict_batch(modules: list[CodeMetrics]):
    """
    Predict defect risk for multiple modules at once.
    Returns results sorted by risk_score descending â€” highest risk first.
    """
    if len(modules) > 100:
        raise HTTPException(status_code=400, detail="Batch limit is 100 modules per request.")

    results = [predict(m) for m in modules]
    results.sort(key=lambda r: r.risk_score, reverse=True)
    return {
        "total_modules":   len(results),
        "high_risk":       sum(1 for r in results if r.verdict == "High Risk"),
        "medium_risk":     sum(1 for r in results if r.verdict == "Medium Risk"),
        "low_risk":        sum(1 for r in results if r.verdict == "Low Risk"),
        "results":         results
    }

@app.post("/predict/python", tags=["Prediction"])
async def predict_python_file(file: UploadFile = File(...)):
    """
    Upload a .py file â€” BugOracle extracts complexity metrics
    per function using Radon and returns defect risk scores.
    """
    if not file.filename.endswith('.py'):
        raise HTTPException(status_code=400,
            detail="Only .py files are supported.")

    raw_bytes   = await file.read()
    source_code = raw_bytes.decode('utf-8', errors='replace')
    source_code = source_code.replace('\r\n', '\n').replace('\r', '\n')

    if len(source_code.strip()) == 0:
        raise HTTPException(status_code=400, detail="File is empty.")

    import tempfile, os
    with tempfile.NamedTemporaryFile(
        mode='w', suffix='.py', delete=False, encoding='utf-8'
    ) as tmp:
        tmp.write(source_code)
        tmp_path = tmp.name

    try:
        with open(tmp_path, 'r', encoding='utf-8') as f:
            disk_code = f.read()
        blocks = cc_visit(disk_code)
    except Exception as ex:
        raise HTTPException(status_code=422,
            detail=f"Could not parse Python file: {str(ex)}")
    finally:
        os.unlink(tmp_path)

    if not blocks:
        raise HTTPException(status_code=422,
            detail="No functions found in file.")

    results = []
    errors  = []
    for block in blocks:
        try:
            metrics = extract_radon_metrics(source_code, block.name)
            rank    = metrics.pop('_rank')
            cc_val  = metrics.pop('_cc')
            input_values = np.array([[metrics[f] for f in features]])
            input_scaled = scaler.transform(input_values)
            risk_score   = float(model.predict_proba(input_scaled)[0][1])
            verdict, confidence = get_verdict(risk_score)
            top_factors  = get_top_factors(input_values)
            if verdict == "High Risk":
                rec = f"Refactor {block.name} immediately â€” complexity={cc_val} (rank {rank})."
            elif verdict == "Medium Risk":
                rec = f"Review {block.name} next sprint. Consider splitting into smaller functions."
            else:
                rec = f"{block.name} looks clean. Standard review applies."
            results.append({
                "function_name":    block.name,
                "line_number":      getattr(block, 'lineno', 1),
                "risk_score":       round(risk_score, 4),
                "verdict":          verdict,
                "complexity":       cc_val,
                "rank":             rank,
                "top_risk_factors": top_factors,
                "recommendation":   rec
            })
        except Exception as ex:
            errors.append(f"{block.name}: {str(ex)}")

    results.sort(key=lambda r: r["risk_score"], reverse=True)

    return {
        "filename":        file.filename,
        "total_functions": len(results),
        "high_risk":       sum(1 for r in results if r["verdict"] == "High Risk"),
        "medium_risk":     sum(1 for r in results if r["verdict"] == "Medium Risk"),
        "low_risk":        sum(1 for r in results if r["verdict"] == "Low Risk"),
        "functions":       results,
            }
import os as _os
from sqlalchemy import create_engine as _ce, text as _text

_DB_URL = _os.environ.get("DATABASE_URL", "")
if _DB_URL:
    _engine = _ce(_DB_URL)
    with _engine.connect() as _c:
        _c.execute(_text("CREATE TABLE IF NOT EXISTS scan_reports (id SERIAL PRIMARY KEY, repo TEXT, pr_number INTEGER, files_scanned INTEGER, high_risk INTEGER, medium_risk INTEGER, low_risk INTEGER, timestamp TEXT)"))
        _c.commit()
else:
    _engine = None

@app.post("/scan-report")
def receive_scan_report(report: ScanReport):
    if _engine:
        with _engine.connect() as conn:
            d = report.dict()
            conn.execute(_text("INSERT INTO scan_reports (repo, pr_number, files_scanned, high_risk, medium_risk, low_risk, timestamp) VALUES (:repo, :pr_number, :files_scanned, :high_risk, :medium_risk, :low_risk, :timestamp)"), d)
            conn.commit()
        return {"status": "saved"}
    return {"status": "no database"}

@app.get("/scan-history")
def get_scan_history():
    if _engine:
        with _engine.connect() as conn:
            rows = conn.execute(_text("SELECT repo, pr_number, files_scanned, high_risk, medium_risk, low_risk, timestamp FROM scan_reports ORDER BY id DESC LIMIT 100")).fetchall()
        return {"scans": [dict(r._mapping) for r in rows]}
    return {"scans": []}

# ─────────────────────────────────────────────
# TEMPORARY — delete this after running once
# Visit: https://bugradar.onrender.com/run-migration
# ─────────────────────────────────────────────@app.get("/run-migration")
def run_migration():
    if not _engine:
        return {"status": "error", "detail": "No database connection"}
    
    migration_sql = """
CREATE TABLE IF NOT EXISTS users (
    id            SERIAL PRIMARY KEY,
    github_id     BIGINT UNIQUE NOT NULL,
    username      VARCHAR(255) NOT NULL,
    email         VARCHAR(255),
    avatar_url    TEXT,
    tier          VARCHAR(20) NOT NULL DEFAULT 'free',
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS repos (
    id            SERIAL PRIMARY KEY,
    user_id       INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    repo_name     VARCHAR(255) NOT NULL,
    github_url    TEXT NOT NULL,
    api_key       VARCHAR(64) UNIQUE NOT NULL,
    created_at    TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_repos_user_id ON repos(user_id);
CREATE INDEX IF NOT EXISTS idx_repos_api_key ON repos(api_key);

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'scan_reports' AND column_name = 'user_id'
    ) THEN
        ALTER TABLE scan_reports ADD COLUMN user_id INTEGER REFERENCES users(id) ON DELETE SET NULL;
    END IF;
    IF NOT EXISTS (
        SELECT 1 FROM information_schema.columns
        WHERE table_name = 'scan_reports' AND column_name = 'repo_id'
    ) THEN
        ALTER TABLE scan_reports ADD COLUMN repo_id INTEGER REFERENCES repos(id) ON DELETE SET NULL;
    END IF;
END $$;

CREATE TABLE IF NOT EXISTS tier_limits (
    tier              VARCHAR(20) PRIMARY KEY,
    max_repos         INTEGER NOT NULL,
    max_scans_monthly INTEGER NOT NULL
);

INSERT INTO tier_limits VALUES ('free', 3, 100) ON CONFLICT (tier) DO NOTHING;
INSERT INTO tier_limits VALUES ('pro', 999999, 999999) ON CONFLICT (tier) DO NOTHING;
"""
    try:
        with _engine.connect() as _c:
            _c.execute(_text(migration_sql))
            _c.commit()
        return {"status": "migration complete", "tables": ["users", "repos", "tier_limits", "scan_reports (altered)"]}
    except Exception as e:
        return {"status": "error", "detail": str(e)}
# test trigger for BugOracle
def unused_function():
    x = 1
    y = x + 1

