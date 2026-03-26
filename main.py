# ============================================================
# BugRadar API — main.py
# ML-powered software defect prediction
# Run locally: uvicorn main:app --reload
# ============================================================

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, validator
from typing import Optional
import joblib
import numpy as np
import os

# ── Load model artefacts ─────────────────────────────────────
# All three files must sit in the same folder as main.py
MODEL_PATH     = "bugradar_model/model.pkl"
SCALER_PATH    = "bugradar_model/scaler.pkl"
FEATURES_PATH  = "bugradar_model/features.pkl"
THRESHOLD_PATH = "bugradar_model/threshold.pkl"

for path in [MODEL_PATH, SCALER_PATH, FEATURES_PATH, THRESHOLD_PATH]:
    if not os.path.exists(path):
        raise FileNotFoundError(f"❌ Missing file: {path}")

model     = joblib.load(MODEL_PATH)
scaler    = joblib.load(SCALER_PATH)
features  = joblib.load(FEATURES_PATH)
threshold = joblib.load(THRESHOLD_PATH)

print(f"✅ Model loaded — {len(features)} features expected")
print(f"✅ Threshold loaded — {threshold:.2f} (v3 optimised)")

# ── FastAPI app setup ────────────────────────────────────────
app = FastAPI(
    title="BugRadar API",
    description="ML-powered software defect prediction using NASA KC1 model. "
                "Send 21 code complexity metrics, receive a defect risk score.",
    version="1.0.0",
    docs_url="/docs",      # Swagger UI at /docs
    redoc_url="/redoc"     # Alternative docs at /redoc
)

# Allow all origins for now — tighten this when deploying to production
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Input schema ─────────────────────────────────────────────
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


# ── Output schema ────────────────────────────────────────────
class PredictionResult(BaseModel):
    module_name:   str
    risk_score:    float   # probability of defect: 0.0 → 1.0
    verdict:       str     # "Low Risk" / "Medium Risk" / "High Risk"
    confidence:    str     # human-readable confidence level
    top_risk_factors: list # top 3 features driving the prediction
    recommendation: str


# ── Helper: risk label from probability ──────────────────────
def get_verdict(prob: float) -> tuple[str, str]:
    if prob < 0.30:
        return "Low Risk",    "The model is confident this module is likely clean."
    elif prob < 0.60:
        return "Medium Risk", "This module shows some defect indicators — worth a review."
    else:
        return "High Risk",   "Strong defect signals detected — prioritise this module for review."


# ── Helper: top contributing features ────────────────────────
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


# ── Routes ───────────────────────────────────────────────────

@app.get("/", tags=["Health"])
def root():
    """Health check — confirms the API is running."""
    return {
        "status":    "✅ BugOracle by Dav API is live",
        "version":   "3.0.0",
        "model":     "Random Forest — KC1 + PC1 combined (AUC-ROC: 0.8531)",
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
        # Build feature map dynamically — avoids any manual naming mismatches
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

        # Print feature names for debugging — remove after confirming it works
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
    Returns results sorted by risk_score descending — highest risk first.
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