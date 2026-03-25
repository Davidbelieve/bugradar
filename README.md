# 🔮 BugOracle by Dav

> ML-powered software defect prediction — trained on real NASA engineering data.

[![Live API](https://img.shields.io/badge/API-Live-brightgreen)](https://bugradar.onrender.com/docs)
[![Dashboard](https://img.shields.io/badge/Dashboard-Live-blue)](https://bugradar-ndzbc3bxka4pncmxarf2rn.streamlit.app)
[![Model](https://img.shields.io/badge/Model-Random%20Forest%20%2B%20SMOTE-orange)](https://github.com/Davidbelieve/bugradar)
[![AUC-ROC](https://img.shields.io/badge/AUC--ROC-0.8378-success)](https://github.com/Davidbelieve/bugradar)

---

## What is BugOracle?

BugOracle predicts the **probability that a software module contains defects** using static code complexity metrics. Send 21 code complexity measurements — lines of code, cyclomatic complexity, Halstead metrics — and get back an instant risk score, verdict, and actionable recommendation.

Built on NASA's KC1 dataset of 2,109 real C++ software modules, BugOracle demonstrates that machine learning can identify defect-prone code before manual review even begins.

---

## Live Product

| | URL |
|---|---|
| 🔮 **Dashboard** | https://bugradar-ndzbc3bxka4pncmxarf2rn.streamlit.app |
| ⚙️ **REST API** | https://bugradar.onrender.com/docs |
| 📁 **Source Code** | https://github.com/Davidbelieve/bugradar |

---

## How It Works

```
Your codebase metrics (CSV)
        ↓
BugOracle API (FastAPI + Random Forest)
        ↓
Risk Score (0.0 – 1.0) + Verdict + Top Risk Factors
        ↓
Prioritised review queue
```

Every module gets a **risk score**, a **verdict** (Low / Medium / High Risk), the **top 3 contributing metrics**, and a **recommendation** — all in one API call.

---

## Model Performance — v1 vs v2

BugOracle v2 introduced **SMOTE oversampling** to address class imbalance (only 15.5% of modules are defective). SMOTE generates synthetic defective examples by interpolating between existing minority class samples, giving the model 5× more positive examples to learn from.

| Metric | v1 (Baseline RF) | v2 (RF + SMOTE) | Improvement |
|---|---|---|---|
| **AUC-ROC** | 0.8257 | **0.8378** | +0.0121 |
| **F1 Score** | 0.4600 | **0.5507** | +0.0907 |
| **Recall** | 0.3538 | **0.5846** | +0.2308 ✅ |
| **Precision** | 0.6571 | 0.5205 | -0.1366 |
| Accuracy | 0.8720 | 0.8531 | -0.0189 |

The headline improvement is **Recall — from 35% to 58%**. BugOracle v2 catches nearly double the defective modules compared to v1. In practical terms, if your codebase has 100 buggy modules, v1 found 35 of them. v2 finds 58.

The slight drop in accuracy and precision is the expected precision-recall trade-off — the model flags more modules for review, some of which are false positives. This is the correct trade-off for defect prediction, where missing a real bug (false negative) is far more costly than reviewing clean code (false positive).

---

## Four Models Evaluated

| Model | AUC-ROC | F1 | Recall |
|---|---|---|---|
| Random Forest (baseline) | 0.8257 | 0.4600 | 0.3538 |
| **Random Forest + SMOTE** | **0.8378** | **0.5507** | **0.5846** |
| XGBoost (no SMOTE) | 0.8037 | 0.5000 | 0.5692 |
| XGBoost + SMOTE | 0.8147 | 0.5191 | 0.5231 |

Random Forest with SMOTE outperformed XGBoost on this dataset — likely because KC1's relatively small size (2,109 samples) and structured tabular features favour ensemble tree methods over gradient boosting.

---

## Dataset

**NASA KC1** — from NASA's Metrics Data Program via the PROMISE Software Engineering Repository.

| Property | Value |
|---|---|
| Total modules | 2,109 |
| Features | 21 numeric |
| Defective modules | 326 (15.5%) |
| Non-defective | 1,783 (84.5%) |
| Source language | C++ |
| System | Ground data storage management |
| OpenML ID | 1067 |

### Feature Groups

- **McCabe metrics** — `loc`, `v(g)`, `ev(g)`, `iv(g)`, `branchCount`
- **Halstead metrics** — `n`, `v`, `l`, `d`, `i`, `e`, `b`, `t`
- **Line counts** — `lOCode`, `lOComment`, `lOBlank`, `lOCodeAndComment`
- **Operand/operator** — `uniq_Op`, `uniq_Opnd`, `total_Op`, `total_Opnd`

---

## API Usage

### Health check
```bash
curl https://bugradar.onrender.com/
```

### Single module prediction
```bash
curl -X POST https://bugradar.onrender.com/predict \
  -H "Content-Type: application/json" \
  -d '{
    "module_name": "storage_handler.cpp",
    "loc": 150, "v(g)": 22, "ev(g)": 10, "iv(g)": 14,
    "n": 600, "v": 1800, "l": 0.04, "d": 45, "i": 40,
    "e": 81000, "b": 0.6, "t": 4500, "lOCode": 120,
    "lOComment": 15, "lOBlank": 15, "lOCodeAndComment": 5,
    "uniq_Op": 18, "uniq_Opnd": 35, "total_Op": 280,
    "total_Opnd": 320, "branchCount": 44
  }'
```

### Example response
```json
{
  "module_name": "storage_handler.cpp",
  "risk_score": 0.42,
  "verdict": "Medium Risk",
  "confidence": "This module shows some defect indicators — worth a review.",
  "top_risk_factors": [
    { "feature": "lOCode",  "importance": 0.0894, "value": 120 },
    { "feature": "v(g)",    "importance": 0.0833, "value": 22  },
    { "feature": "loc",     "importance": 0.0797, "value": 150 }
  ],
  "recommendation": "Include in next sprint review. Consider refactoring the highest-complexity sections."
}
```

### Batch prediction (up to 100 modules)
```bash
curl -X POST https://bugradar.onrender.com/predict/batch \
  -H "Content-Type: application/json" \
  -d '[{ ...module1... }, { ...module2... }]'
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| ML model | scikit-learn Random Forest + imbalanced-learn SMOTE |
| API | FastAPI + Uvicorn |
| Dashboard | Streamlit + Plotly |
| Deployment — API | Render (free tier) |
| Deployment — Dashboard | Streamlit Cloud (free tier) |
| Language | Python 3.11 |

---

## Local Setup

```bash
# Clone the repo
git clone https://github.com/Davidbelieve/bugradar.git
cd bugradar

# Create virtual environment
python -m venv venv
venv\Scripts\activate.bat        # Windows
source venv/bin/activate          # Mac/Linux

# Install dependencies
pip install -r requirements.txt

# Run the API
uvicorn main:app --reload
# → http://127.0.0.1:8000/docs

# Run the dashboard (separate terminal)
streamlit run dashboard.py
# → http://localhost:8501
```

---

## Project Structure

```
bugradar/
├── main.py              ← FastAPI REST API
├── dashboard.py         ← Streamlit dashboard
├── requirements.txt     ← Python dependencies
├── Procfile             ← Render deployment config
├── bugradar_model/
│   ├── model.pkl        ← Trained RF + SMOTE model
│   ├── scaler.pkl       ← StandardScaler (fitted on training data)
│   └── features.pkl     ← Ordered feature names from KC1
└── .gitignore
```

---

## Roadmap

- [x] v1 — Random Forest baseline (AUC-ROC: 0.8257)
- [x] v2 — RF + SMOTE (AUC-ROC: 0.8378, Recall: 0.5846)
- [ ] v3 — Threshold tuning + cross-dataset validation (CM1, PC1)
- [ ] Auto code analysis — extract metrics from .py/.cpp files via Radon/Lizard
- [ ] GitHub Action — run BugOracle on every pull request
- [ ] VS Code extension — flag high-risk functions inline

---

## Author

**David** — MSc Advanced Computer Science student, Northumbria University

Built as part of a Machine Learning module and extended into a real deployable product.

---

*BugOracle by Dav — because finding bugs before they find you is always the better strategy.*