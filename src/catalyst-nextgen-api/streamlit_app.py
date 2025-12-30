"""
Streamlit frontend to view projects from the Catalyst NextGen API.
"""

import os
from typing import List, Dict, Any, Optional

import httpx
import streamlit as st

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")
DEFAULT_LIMIT = 50

st.set_page_config(page_title="Catalyst Projects", layout="wide")


def fetch_projects(
    base_url: str,
    headers: Dict[str, str],
    limit: Optional[int] = None,
    status_filter: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Fetch projects from the API."""
    params = {}
    if limit:
        params["limit"] = limit
    if status_filter:
        params["status_filter"] = status_filter

    url = f"{base_url.rstrip('/')}/projects"
    with httpx.Client(timeout=10.0) as client:
        resp = client.get(url, headers=headers, params=params)
        resp.raise_for_status()
        data = resp.json()
        return data.get("projects", [])


def build_headers(auth_mode: str, user_id: str, bearer: str) -> Dict[str, str]:
    headers: Dict[str, str] = {}
    if auth_mode == "Bearer token" and bearer:
        headers["Authorization"] = f"Bearer {bearer.strip()}"
    elif auth_mode == "X-User-Id" and user_id:
        headers["X-User-Id"] = user_id.strip()
    return headers


# Sidebar controls
st.sidebar.header("API Settings")
base_url = st.sidebar.text_input("API base URL", value=API_BASE_URL)
auth_mode = st.sidebar.radio("Auth mode", ["Bearer token", "X-User-Id"], index=1)
user_id = st.sidebar.text_input("User ID (for X-User-Id)")
bearer_token = st.sidebar.text_area("Bearer token", height=100)
limit = st.sidebar.slider("Max results", min_value=1, max_value=100, value=DEFAULT_LIMIT)
status_filter = st.sidebar.selectbox(
    "Status filter (optional)",
    options=["", "planning", "in_progress", "on_hold", "completed", "archived"],
    format_func=lambda x: "All" if x == "" else x,
)

st.title("Projects")
st.caption("Fetched from Catalyst NextGen API")

# Fetch button
if st.button("Fetch projects", type="primary"):
    headers = build_headers(auth_mode, user_id, bearer_token)
    if not headers:
        st.error("Please provide authentication (Bearer token or X-User-Id).")
    else:
        try:
            projects = fetch_projects(base_url, headers, limit, status_filter or None)
            st.success(f"Loaded {len(projects)} projects")
            if projects:
                st.dataframe(projects, use_container_width=True)
        except httpx.HTTPStatusError as e:
            st.error(f"API error: {e.response.status_code} - {e.response.text}")
        except Exception as e:
            st.error(f"Failed to fetch projects: {e}")
else:
    st.info("Click 'Fetch projects' to load data.")
