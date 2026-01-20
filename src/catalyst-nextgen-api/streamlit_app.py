"""
Streamlit frontend to view projects from the Catalyst NextGen API.
"""

import os
from typing import List, Dict, Any, Optional

import httpx
import streamlit as st

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost:8000/api/v1")
DEFAULT_LIMIT = 50
STATUSES = ["planning", "in_progress", "on_hold", "completed", "archived"]

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


def create_project(base_url: str, headers: Dict[str, str], payload: Dict[str, Any]) -> Dict[str, Any]:
    """Create a new project via the API."""
    url = f"{base_url.rstrip('/')}/projects"
    with httpx.Client(timeout=10.0) as client:
        resp = client.post(url, headers=headers, json=payload)
        resp.raise_for_status()
        return resp.json().get("project")


def update_project(
    base_url: str,
    headers: Dict[str, str],
    project_id: str,
    payload: Dict[str, Any],
) -> Dict[str, Any]:
    """Update an existing project via the API."""
    url = f"{base_url.rstrip('/')}/projects/{project_id}"
    with httpx.Client(timeout=10.0) as client:
        resp = client.put(url, headers=headers, json=payload)
        resp.raise_for_status()
        return resp.json().get("project")


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
    options=["", *STATUSES],
    format_func=lambda x: "All" if x == "" else x,
)

st.title("Projects")
st.caption("Fetched from Catalyst NextGen API")

st.session_state.setdefault("projects", [])

def ensure_headers() -> Optional[Dict[str, str]]:
    """Validate and build headers based on auth selection."""
    headers = build_headers(auth_mode, user_id, bearer_token)
    if not headers:
        st.error("Please provide authentication (Bearer token or X-User-Id).")
        return None
    return headers

# Fetch button
col_fetch, col_clear = st.columns([1, 1])
with col_fetch:
    if st.button("Fetch projects", type="primary"):
        headers = ensure_headers()
        if headers:
            try:
                projects = fetch_projects(base_url, headers, limit, status_filter or None)
                st.session_state["projects"] = projects
                st.success(f"Loaded {len(projects)} projects")
            except httpx.HTTPStatusError as e:
                st.error(f"API error: {e.response.status_code} - {e.response.text}")
            except Exception as e:
                st.error(f"Failed to fetch projects: {e}")

with col_clear:
    if st.button("Clear results"):
        st.session_state["projects"] = []
        st.info("Cleared project list.")

projects = st.session_state.get("projects", [])

if projects:
    st.subheader("Projects list")
    st.dataframe(projects, use_container_width=True)
else:
    st.info("No projects loaded. Fetch projects to see the list.")

st.divider()

# Create project form
st.subheader("Create project")
with st.form("create_project_form"):
    new_name = st.text_input("Name", placeholder="Project name")
    new_description = st.text_area("Description", placeholder="Optional description")
    new_status = st.selectbox("Status", STATUSES, index=0)
    submitted = st.form_submit_button("Create project", type="primary")

    if submitted:
        headers = ensure_headers()
        if headers:
            if not new_name.strip():
                st.error("Name is required.")
            else:
                payload = {
                    "name": new_name.strip(),
                    "description": new_description.strip() if new_description else None,
                    "status": new_status,
                }
                try:
                    created = create_project(base_url, headers, payload)
                    st.success(f"Created project: {created.get('name')} (id: {created.get('id')})")
                    # Refresh list
                    projects = fetch_projects(base_url, headers, limit, status_filter or None)
                    st.session_state["projects"] = projects
                except httpx.HTTPStatusError as e:
                    st.error(f"API error: {e.response.status_code} - {e.response.text}")
                except Exception as e:
                    st.error(f"Failed to create project: {e}")

st.divider()

# Edit project form
st.subheader("Edit project")
if not projects:
    st.info("Fetch projects first to edit an existing project.")
else:
    options = {f"{p.get('name', '(no name)')} ({p.get('id')})": p for p in projects}
    selected_label = st.selectbox("Select a project", list(options.keys()))
    selected_project = options[selected_label]

    with st.form("edit_project_form"):
        edit_name = st.text_input("Name", value=selected_project.get("name", ""))
        edit_description = st.text_area("Description", value=selected_project.get("description", "") or "")
        current_status = selected_project.get("status", STATUSES[0])
        status_index = STATUSES.index(current_status) if current_status in STATUSES else 0
        edit_status = st.selectbox("Status", STATUSES, index=status_index)
        update_submitted = st.form_submit_button("Save changes", type="primary")

        if update_submitted:
            headers = ensure_headers()
            if headers:
                if not edit_name.strip():
                    st.error("Name is required.")
                else:
                    payload = {
                        "name": edit_name.strip(),
                        "description": edit_description.strip() if edit_description else None,
                        "status": edit_status,
                    }
                    try:
                        updated = update_project(base_url, headers, selected_project.get("id"), payload)
                        st.success(f"Updated project: {updated.get('name')} (id: {updated.get('id')})")
                        # Refresh list
                        projects = fetch_projects(base_url, headers, limit, status_filter or None)
                        st.session_state["projects"] = projects
                    except httpx.HTTPStatusError as e:
                        st.error(f"API error: {e.response.status_code} - {e.response.text}")
                    except Exception as e:
                        st.error(f"Failed to update project: {e}")
