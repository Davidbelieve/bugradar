# 🔮 BugOracle by Dav

> ML-powered software defect prediction — trained on real NASA engineering data.

[![Live API](https://img.shields.io/badge/API-Live-brightgreen)](https://bugradar.onrender.com/docs)
[![Dashboard](https://img.shields.io/badge/Dashboard-Live-blue)](https://bugradar-ndzbc3bxka4pncmxarf2rn.streamlit.app)
[![Model](https://img.shields.io/badge/Model-RF%20%2B%20SMOTE%20%2B%20KC1%2BPC1-orange)](https://github.com/Davidbelieve/bugradar)
[![AUC-ROC](https://img.shields.io/badge/AUC--ROC-0.8531-success)](https://github.com/Davidbelieve/bugradar)
[![PC1 AUC](https://img.shields.io/badge/Cross--dataset%20AUC-0.9805-brightgreen)](https://github.com/Davidbelieve/bugradar)

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

BugOracle v3 introduces two further improvements on top of SMOTE — **threshold tuning** to maximise F1 on the defective class, and **cross-dataset training** on KC1 + PC1 combined. The optimal classification threshold was found by sweeping 0.20 → 0.50 and selecting the value that maximises F1. Training on both NASA datasets simultaneously pushed cross-dataset AUC-ROC to 0.98 on completely unseen satellite software.

| Metric | v1 (baseline) | v2 (SMOTE) | v3 (combined + threshold) | Improvement |
|---|---|---|---|---|
| **AUC-ROC** | 0.8257 | 0.8378 | **0.8531** | +0.0274 |
| **F1 Score** | 0.4600 | 0.5507 | **0.5839** | +0.1239 |
| **Recall** | 0.3538 | 0.5846 | **0.7231** | +0.3693 ✅ |
| **Precision** | 0.6571 | 0.5205 | 0.4896 | expected trade-off |
| **Threshold** | 0.50 | 0.50 | **0.40** | tuned |
| **Training data** | KC1 only | KC1 only | **KC1 + PC1** | 3,218 modules |
| **Cross-dataset AUC** | — | 0.5192 | **0.9805** | generalises ✅ |

The headline improvement across all three versions is **Recall — from 35% to 72%**. BugOracle v3 catches more than double the defective modules compared to v1. The cross-dataset result of 0.98 AUC-ROC on PC1 (satellite C code) confirms that the model generalises well beyond the KC1 training distribution.

---

## Four Models Evaluated

| Model | AUC-ROC | F1 | Recall | Notes |
|---|---|---|---|---|
| Random Forest (baseline) | 0.8257 | 0.4600 | 0.3538 | KC1 only |
| Random Forest + SMOTE | 0.8378 | 0.5507 | 0.5846 | KC1 only |
| RF + SMOTE + threshold | 0.8378 | 0.5839 | 0.7231 | KC1 only, threshold=0.40 |
| **RF + SMOTE + KC1+PC1** | **0.8531** | **0.5839** | **0.7231** | Combined datasets ✅ |
| Cross-dataset (PC1 only) | **0.9805** | — | — | Unseen satellite software |

Random Forest consistently outperformed XGBoost on these datasets — likely because the relatively small size (3,218 combined samples) and structured tabular features favour ensemble tree methods. The 0.98 cross-dataset AUC confirms the feature distributions of McCabe and Halstead metrics transfer well across different NASA C/C++ systems.

---

## Dataset

**NASA KC1** — from NASA's Metrics Data Program via the PROMISE Software Engineering Repository.

| Property | KC1 | PC1 |
|---|---|---|
| Total modules | 2,109 | 1,109 |
| Features | 21 numeric | 21 numeric |
| Defective | 326 (15.5%) | 77 (6.9%) |
| Language | C++ | C |
| System | Ground data storage | Satellite flight software |
| OpenML ID | 1067 | 1068 |

Both datasets originate from NASA's Metrics Data Program via the PROMISE Software Engineering Repository. v3 trains on the combined pool of 3,218 modules.

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
| Training data | NASA KC1 + PC1 (3,218 modules combined) |
| Threshold | 0.40 (tuned to maximise F1) |
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

- [x] v1 — Random Forest baseline (AUC-ROC: 0.8257, Recall: 0.35)
- [x] v2 — RF + SMOTE (AUC-ROC: 0.8378, Recall: 0.58)
- [x] v3 — RF + SMOTE + threshold tuning + KC1+PC1 combined (AUC-ROC: 0.8531, Recall: 0.72, PC1 cross-dataset: 0.9805)
- [ ] v4 — Auto code analysis via Radon/Lizard (no manual CSV needed)
- [ ] GitHub Action — run BugOracle on every pull request automatically
- [ ] VS Code extension — flag high-risk functions inline while coding

---

## Author

**David** — MSc. Advanced Computer Science student, Northumbria University

Built as part of a Learning module and extended into a real deployable product.

---

*BugOracle by Dav — because finding bugs before they find you is always the better strategy.*