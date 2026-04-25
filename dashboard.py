import os
import streamlit as st
import pandas as pd
import requests

API_URL = os.environ.get("BUGORACLE_API_URL", "https://bugradar.onrender.com")

st.set_page_config(page_title="BugOracle", page_icon="🔍", layout="wide")

params = st.query_params
if "token" in params and "token" not in st.session_state:
    st.session_state["token"] = params["token"]
    st.session_state["tier"] = params.get("tier", "free")
    st.query_params.clear()

token = st.session_state.get("token")
tier = st.session_state.get("tier", "free")

def api_get(path):
    if not token:
        return None
    try:
        r = requests.get(f"{API_URL}{path}", headers={"Authorization": f"Bearer {token}"}, timeout=10)
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"API error: {e}")
        return None

def api_post(path, payload):
    if not token:
        return None
    try:
        r = requests.post(f"{API_URL}{path}", json=payload, headers={"Authorization": f"Bearer {token}"}, timeout=10)
        if r.status_code == 402:
            st.warning(r.json().get("detail", "Upgrade to Pro for more."))
            return None
        r.raise_for_status()
        return r.json()
    except Exception as e:
        st.error(f"API error: {e}")
        return None

def api_delete(path):
    if not token:
        return False
    try:
        r = requests.delete(f"{API_URL}{path}", headers={"Authorization": f"Bearer {token}"}, timeout=10)
        return r.status_code == 204
    except Exception:
        return False

if not token:
    st.title("🔍 BugOracle")
    st.write("AI-powered defect prediction for engineering teams.")
    st.markdown("---")
    st.link_button("Sign in with GitHub", f"{API_URL}/auth/github", type="primary")
    st.stop()

me = api_get("/auth/me")
username = me.get("username", "unknown") if me else "unknown"

with st.sidebar:
    st.write(f"**{username}**")
    if tier == "pro":
        st.success("✨ Pro tier")
    else:
        st.info("🆓 Free tier (3 repos / 100 scans/month)")
    st.markdown("---")
    if st.button("Sign out"):
        for k in ["token", "tier"]:
            st.session_state.pop(k, None)
        st.rerun()

st.title("🔍 BugOracle Dashboard")

tab_scans, tab_repos = st.tabs(["📊 Scan history", "🗂 Repos"])

with tab_repos:
    st.subheader("Your repos")
    repos = api_get("/repos/") or []
    if repos:
        for repo in repos:
            col1, col2, col3 = st.columns([3, 4, 1])
            col1.write(f"**{repo['repo_name']}**")
            col2.code(repo["api_key"], language=None)
            if col3.button("Remove", key=f"del_{repo['id']}"):
                if api_delete(f"/repos/{repo['id']}"):
                    st.success("Removed.")
                    st.rerun()
    else:
        st.write("No repos yet. Register one below.")
    st.markdown("---")
    st.subheader("Register a new repo")
    with st.form("register_repo"):
        repo_name = st.text_input("Repo name (owner/repo)", placeholder="Davidbelieve/bugradar")
        github_url = st.text_input("GitHub URL", placeholder="https://github.com/Davidbelieve/bugradar")
        submitted = st.form_submit_button("Register")
    if submitted and repo_name and github_url:
        result = api_post("/repos/register", {"repo_name": repo_name, "github_url": github_url})
        if result:
            st.success("Repo registered!")
            st.info(f"Add this to your GitHub Actions secrets:\n\n**Name:** BUGORACLE_API_KEY\n\n**Value:** {result['api_key']}")
            st.rerun()

with tab_scans:
    repos = api_get("/repos/") or []
    if not repos:
        st.info("Register a repo first to see scan history.")
        st.stop()
    repo_names = {r["id"]: r["repo_name"] for r in repos}
    selected_id = st.selectbox("Select repo", options=list(repo_names.keys()), format_func=lambda i: repo_names[i])
    history = api_get(f"/history?repo_id={selected_id}") or []
    if not history:
        st.write("No scans yet for this repo.")
    else:
        df = pd.DataFrame(history)
        if "scanned_at" in df.columns:
            df["scanned_at"] = pd.to_datetime(df["scanned_at"])
        col1, col2, col3 = st.columns(3)
        col1.metric("Total scans", len(df))
        if "risk_score" in df.columns:
            col2.metric("Avg risk score", f"{df['risk_score'].mean():.1f}")
            col3.metric("High risk (>=80)", int((df["risk_score"] >= 80).sum()))
        st.dataframe(df, use_container_width=True)
