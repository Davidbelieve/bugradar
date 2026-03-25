# ============================================================
# BugRadar Dashboard — dashboard.py
# Streamlit web app connected to the live BugRadar API
# Run locally: streamlit run dashboard.py
# ============================================================

import streamlit as st
import requests
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import io

# ── Config ───────────────────────────────────────────────────
API_URL = "https://bugradar.onrender.com"   # your live API

st.set_page_config(
    page_title="BugOracle by Dav",
    page_icon="🔮",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ── Custom CSS ───────────────────────────────────────────────
st.markdown("""
<style>
    .main { padding: 1.5rem 2rem; }
    .stMetric { background: #f8f9fa; border-radius: 10px; padding: 1rem; }
    .risk-high { color: #A32D2D; font-weight: 600; }
    .risk-med  { color: #854F0B; font-weight: 600; }
    .risk-low  { color: #3B6D11; font-weight: 600; }
    .header-badge {
        background: #EAF3DE; color: #3B6D11;
        padding: 4px 12px; border-radius: 20px;
        font-size: 12px; font-weight: 500;
    }
    div[data-testid="stMetricValue"] { font-size: 2rem !important; }
</style>
""", unsafe_allow_html=True)


# ── Header ───────────────────────────────────────────────────
col_logo, col_status = st.columns([6, 1])
with col_logo:
    st.markdown("# 🔮 BugOracle by Dav")
    st.markdown("*ML-powered software defect prediction — NASA KC1 model*")
with col_status:
    try:
        r = requests.get(f"{API_URL}/", timeout=5)
        if r.status_code == 200:
            st.success("API Live")
        else:
            st.error("API Error")
    except:
        st.error("API Offline")

st.divider()


# ── Sample CSV download ───────────────────────────────────────
# Lets users download a template with the right column names
COLUMNS = [
    "module_name", "loc", "v(g)", "ev(g)", "iv(g)", "n", "v", "l",
    "d", "i", "e", "b", "t", "lOCode", "lOComment", "lOBlank",
    "lOCodeAndComment", "uniq_Op", "uniq_Opnd", "total_Op",
    "total_Opnd", "branchCount"
]

SAMPLE_DATA = pd.DataFrame([
    {
        "module_name": "storage_handler.cpp",
        "loc": 150, "v(g)": 22, "ev(g)": 10, "iv(g)": 14,
        "n": 600, "v": 1800, "l": 0.04, "d": 45, "i": 40,
        "e": 81000, "b": 0.6, "t": 4500, "lOCode": 120,
        "lOComment": 15, "lOBlank": 15, "lOCodeAndComment": 5,
        "uniq_Op": 18, "uniq_Opnd": 35, "total_Op": 280,
        "total_Opnd": 320, "branchCount": 44
    },
    {
        "module_name": "data_parser.cpp",
        "loc": 80, "v(g)": 10, "ev(g)": 5, "iv(g)": 8,
        "n": 300, "v": 900, "l": 0.06, "d": 28, "i": 32,
        "e": 25000, "b": 0.3, "t": 1400, "lOCode": 65,
        "lOComment": 8, "lOBlank": 7, "lOCodeAndComment": 2,
        "uniq_Op": 12, "uniq_Opnd": 22, "total_Op": 140,
        "total_Opnd": 160, "branchCount": 20
    },
    {
        "module_name": "auth_module.cpp",
        "loc": 30, "v(g)": 4, "ev(g)": 2, "iv(g)": 3,
        "n": 120, "v": 420, "l": 0.09, "d": 15, "i": 28,
        "e": 6300, "b": 0.1, "t": 350, "lOCode": 25,
        "lOComment": 3, "lOBlank": 2, "lOCodeAndComment": 1,
        "uniq_Op": 8, "uniq_Opnd": 12, "total_Op": 60,
        "total_Opnd": 60, "branchCount": 8
    }
])


# ── Upload section ────────────────────────────────────────────
st.markdown("### Scan your codebase")

dl_col, up_col = st.columns([1, 2])

with dl_col:
    csv_template = SAMPLE_DATA.to_csv(index=False)
    st.download_button(
        label="📥 Download CSV template",
        data=csv_template,
        file_name="bugradar_template.csv",
        mime="text/csv",
        help="Download a sample CSV with the correct column format"
    )

with up_col:
    uploaded = st.file_uploader(
        "Upload CSV of code metrics",
        type=["csv"],
        help="Must contain the 21 code complexity columns"
    )

# Use sample data if nothing uploaded
if uploaded is not None:
    try:
        df = pd.read_csv(uploaded)
        st.success(f"Loaded {len(df)} modules from your file")
    except Exception as ex:
        st.error(f"Could not read CSV: {ex}")
        df = SAMPLE_DATA.copy()
else:
    st.info("No file uploaded — showing sample data. Download the template above to try with your own codebase.")
    df = SAMPLE_DATA.copy()


# ── Run predictions ───────────────────────────────────────────
@st.cache_data(show_spinner=False)
def run_predictions(df_json: str) -> list:
    """Call the BugRadar API for each module and return results."""
    df_local = pd.read_json(io.StringIO(df_json))
    results = []

    for _, row in df_local.iterrows():
        payload = {
            "module_name": str(row.get("module_name", "unknown")),
            "loc":    float(row.get("loc", 0)),
            "v(g)":   float(row.get("v(g)", 0)),
            "ev(g)":  float(row.get("ev(g)", 0)),
            "iv(g)":  float(row.get("iv(g)", 0)),
            "n":      float(row.get("n", 0)),
            "v":      float(row.get("v", 0)),
            "l":      float(row.get("l", 0)),
            "d":      float(row.get("d", 0)),
            "i":      float(row.get("i", 0)),
            "e":      float(row.get("e", 0)),
            "b":      float(row.get("b", 0)),
            "t":      float(row.get("t", 0)),
            "lOCode":           float(row.get("lOCode", 0)),
            "lOComment":        float(row.get("lOComment", 0)),
            "lOBlank":          float(row.get("lOBlank", 0)),
            "lOCodeAndComment": float(row.get("lOCodeAndComment", 0)),
            "uniq_Op":   float(row.get("uniq_Op", 0)),
            "uniq_Opnd": float(row.get("uniq_Opnd", 0)),
            "total_Op":  float(row.get("total_Op", 0)),
            "total_Opnd": float(row.get("total_Opnd", 0)),
            "branchCount": float(row.get("branchCount", 0)),
        }
        try:
            r = requests.post(f"{API_URL}/predict", json=payload, timeout=15)
            if r.status_code == 200:
                results.append(r.json())
            else:
                results.append({
                    "module_name": payload["module_name"],
                    "risk_score": None, "verdict": "Error",
                    "confidence": "API error", "top_risk_factors": [],
                    "recommendation": "Could not reach API"
                })
        except Exception as ex:
            results.append({
                "module_name": payload["module_name"],
                "risk_score": None, "verdict": "Error",
                "confidence": str(ex), "top_risk_factors": [],
                "recommendation": "Connection failed"
            })
    return results


# Run predictions with progress bar
with st.spinner("Scanning modules via BugRadar API..."):
    results = run_predictions(df.to_json())

# Build results dataframe
results_df = pd.DataFrame([{
    "module":      r["module_name"],
    "risk_score":  r["risk_score"],
    "verdict":     r["verdict"],
    "confidence":  r["confidence"],
    "recommendation": r["recommendation"],
    "top_factor":  r["top_risk_factors"][0]["feature"] if r["top_risk_factors"] else "—"
} for r in results])

# Sort by risk score descending
results_df = results_df.sort_values("risk_score", ascending=False).reset_index(drop=True)

st.divider()


# ── Summary metrics ───────────────────────────────────────────
st.markdown("### Scan results")

total     = len(results_df)
high_risk = len(results_df[results_df["verdict"] == "High Risk"])
med_risk  = len(results_df[results_df["verdict"] == "Medium Risk"])
low_risk  = len(results_df[results_df["verdict"] == "Low Risk"])

m1, m2, m3, m4 = st.columns(4)
m1.metric("Modules scanned", total)
m2.metric("High Risk 🔴", high_risk)
m3.metric("Medium Risk 🟡", med_risk)
m4.metric("Low Risk 🟢", low_risk)


# ── Risk ranking table ────────────────────────────────────────
st.markdown("#### Risk ranking — highest risk first")

def colour_verdict(val):
    if val == "High Risk":
        return "color: #A32D2D; font-weight: 600"
    elif val == "Medium Risk":
        return "color: #854F0B; font-weight: 600"
    elif val == "Low Risk":
        return "color: #3B6D11; font-weight: 600"
    return ""

def colour_score(val):
    if val is None or val == "—":
        return ""
    try:
        fval = float(val)
    except (ValueError, TypeError):
        return ""
    if fval >= 0.6:
        return "color: #A32D2D; font-weight: 600"
    elif fval >= 0.3:
        return "color: #854F0B; font-weight: 600"
    return "color: #3B6D11; font-weight: 600"

display_df = results_df[["module", "risk_score", "verdict", "top_factor", "recommendation"]].copy()
display_df.columns = ["Module", "Risk Score", "Verdict", "Top Factor", "Recommendation"]
display_df["Risk Score"] = display_df["Risk Score"].apply(
    lambda x: f"{x:.3f}" if x is not None else "—"
)

styled = display_df.style\
    .applymap(colour_verdict, subset=["Verdict"])\
    .applymap(colour_score,   subset=["Risk Score"])\
    .set_properties(**{"font-size": "13px"})

st.dataframe(styled, use_container_width=True, hide_index=True)


# ── Charts ────────────────────────────────────────────────────
chart_col, rec_col = st.columns([1, 1])

with chart_col:
    st.markdown("#### Risk score by module")
    chart_df = results_df.copy()
    chart_df["colour"] = chart_df["risk_score"].apply(
        lambda x: "#E24B4A" if x >= 0.6 else ("#EF9F27" if x >= 0.3 else "#639922")
    )
    fig = go.Figure(go.Bar(
        x=chart_df["risk_score"],
        y=chart_df["module"],
        orientation="h",
        marker_color=chart_df["colour"],
        text=chart_df["risk_score"].apply(lambda x: f"{x:.3f}"),
        textposition="outside"
    ))
    fig.update_layout(
        height=max(200, len(chart_df) * 60),
        margin=dict(l=0, r=40, t=10, b=10),
        xaxis=dict(range=[0, 1.1], title="Risk Score"),
        yaxis=dict(title=""),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(size=12)
    )
    fig.update_xaxes(showgrid=True, gridcolor="rgba(0,0,0,0.06)")
    st.plotly_chart(fig, use_container_width=True)

with rec_col:
    st.markdown("#### Recommendations")
    for _, row in results_df.iterrows():
        if row["verdict"] == "High Risk":
            icon = "🔴"
        elif row["verdict"] == "Medium Risk":
            icon = "🟡"
        else:
            icon = "🟢"
        with st.container():
            st.markdown(f"**{icon} {row['module']}**")
            st.caption(row["recommendation"])
            st.divider()


# ── Export results ────────────────────────────────────────────
st.markdown("### Export")

export_df = results_df.copy()
export_csv = export_df.to_csv(index=False)

st.download_button(
    label="📤 Download full results as CSV",
    data=export_csv,
    file_name="bugradar_results.csv",
    mime="text/csv"
)

# ── Footer ────────────────────────────────────────────────────
st.divider()
st.caption("BugOracle by Dav · v1.0 — ML model trained on NASA KC1 dataset · AUC-ROC: 0.8257 · Random Forest")