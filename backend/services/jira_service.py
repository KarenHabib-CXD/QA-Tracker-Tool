"""
Jira API Service
Fetches sprints, tickets and user profile from Jira Cloud.
Credentials are passed per-request (email + API token) — no shared secrets.
"""

import os
import logging
import warnings
from base64 import b64encode
from typing import Optional
import httpx
from dotenv import load_dotenv

load_dotenv()

# Suppress SSL warnings caused by Sonnen's corporate proxy (self-signed cert)
warnings.filterwarnings("ignore", message=".*Unverified HTTPS.*")

log = logging.getLogger("jira_service")
logging.basicConfig(level=logging.DEBUG, format="%(levelname)s  [%(name)s]  %(message)s")

JIRA_BASE_URL  = os.getenv("JIRA_BASE_URL",   "https://sonnen.atlassian.net")
JIRA_BOARD_ID  = os.getenv("JIRA_BOARD_ID",   "174")
JIRA_PROJECT   = os.getenv("JIRA_PROJECT_KEY","APD")


def _headers(email: str, token: str) -> dict:
    creds = b64encode(f"{email}:{token}".encode()).decode()
    return {
        "Authorization": f"Basic {creds}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }


def _get(url: str, email: str, token: str, params: dict = None) -> dict | list | None:
    log.debug("GET %s | params=%s | email=%s | token_len=%d", url, params, email, len(token) if token else 0)
    try:
        # verify=False needed because Sonnen uses a corporate SSL proxy
        # (self-signed certificate in chain — Zscaler / similar)
        with httpx.Client(timeout=15, verify=False) as client:
            r = client.get(url, headers=_headers(email, token), params=params or {})
            log.debug("Response: status=%d | body_preview=%s", r.status_code, r.text[:300])
            if r.status_code == 401:
                log.error("401 Unauthorized — email=%s | token_prefix=%s", email, token[:6] if token else "EMPTY")
                return {"error": "Invalid Jira credentials"}
            if r.status_code == 403:
                log.error("403 Forbidden — not enough permissions for %s", url)
                return {"error": "No permission to access this resource"}
            r.raise_for_status()
            return r.json()
    except httpx.TimeoutException:
        log.error("Timeout calling %s", url)
        return {"error": "Jira request timed out"}
    except Exception as e:
        log.error("Exception calling %s: %s", url, e)
        return {"error": str(e)}


# ── Auth ──────────────────────────────────────────────────────────────────────

def verify_jira_user(email: str, token: str) -> dict:
    """Verify credentials and return user profile."""
    log.info("verify_jira_user called | email=%s | token_len=%d", email, len(token) if token else 0)
    url  = f"{JIRA_BASE_URL}/rest/api/3/myself"
    data = _get(url, email, token)
    if not data or "error" in data:
        err = data.get("error", "Unknown error") if data else "No response"
        log.error("verify_jira_user FAILED: %s", err)
        return {"ok": False, "error": err}
    log.info("verify_jira_user SUCCESS: %s (%s)", data.get("displayName"), data.get("emailAddress"))
    return {
        "ok":          True,
        "account_id":  data.get("accountId"),
        "display_name":data.get("displayName"),
        "email":       data.get("emailAddress"),
        "avatar":      data.get("avatarUrls", {}).get("48x48", ""),
    }


# ── Sprints ───────────────────────────────────────────────────────────────────

def fetch_sprints(email: str, token: str, state: str = "active,future,closed") -> list:
    """Fetch sprints from the configured Jira board."""
    url    = f"{JIRA_BASE_URL}/rest/agile/1.0/board/{JIRA_BOARD_ID}/sprint"
    result = []
    start  = 0

    while True:
        data = _get(url, email, token, params={"state": state, "startAt": start, "maxResults": 50})
        if not data or "error" in data:
            break
        values = data.get("values", [])
        for s in values:
            result.append({
                "jira_id":    s["id"],
                "name":       s["name"],
                "state":      s["state"],              # active / future / closed
                "start_date": s.get("startDate", ""),
                "end_date":   s.get("endDate", ""),
                "goal":       s.get("goal", ""),
            })
        if data.get("isLast", True):
            break
        start += len(values)

    # Sort: active first, then future, then closed
    order = {"active": 0, "future": 1, "closed": 2}
    result.sort(key=lambda x: (order.get(x["state"], 9), x["name"]))
    return result


# ── Tickets ───────────────────────────────────────────────────────────────────

def fetch_tickets_for_sprint(email: str, token: str, jira_sprint_id: int) -> list:
    """Fetch all issues in a given sprint."""
    url    = f"{JIRA_BASE_URL}/rest/agile/1.0/board/{JIRA_BOARD_ID}/sprint/{jira_sprint_id}/issue"
    result = []
    start  = 0

    while True:
        data = _get(url, email, token, params={
            "startAt":   start,
            "maxResults": 100,
            "fields":    "summary,description,issuetype,priority,status,assignee",
        })
        if not data or "error" in data:
            break
        issues = data.get("issues", [])
        for issue in issues:
            f = issue.get("fields", {})
            # Extract plain text from Atlassian Document Format description
            desc = _extract_adf_text(f.get("description"))
            result.append({
                "jira_key":    issue["key"],                        # e.g. APD-123
                "jira_id":     issue["id"],
                "title":       f.get("summary", ""),
                "description": desc,
                "issue_type":  f.get("issuetype", {}).get("name", "Story").lower(),
                "priority":    f.get("priority", {}).get("name", "Medium"),
                "status":      f.get("status",   {}).get("name", ""),
                "assignee":    f.get("assignee", {}).get("displayName", "Unassigned") if f.get("assignee") else "Unassigned",
                "url":         f"{JIRA_BASE_URL}/browse/{issue['key']}",
            })
        total = data.get("total", 0)
        start += len(issues)
        if start >= total:
            break

    return result


def fetch_single_ticket(email: str, token: str, ticket_key: str) -> dict:
    """Fetch a single Jira issue by key (e.g. APD-123)."""
    url  = f"{JIRA_BASE_URL}/rest/api/3/issue/{ticket_key}"
    data = _get(url, email, token, params={"fields": "summary,description,issuetype,priority,status,assignee"})
    if not data or "error" in data:
        return data or {"error": "Not found"}
    f = data.get("fields", {})
    return {
        "jira_key":    data["key"],
        "jira_id":     data["id"],
        "title":       f.get("summary", ""),
        "description": _extract_adf_text(f.get("description")),
        "issue_type":  f.get("issuetype", {}).get("name", "Story").lower(),
        "priority":    f.get("priority", {}).get("name", "Medium"),
        "status":      f.get("status",   {}).get("name", ""),
        "assignee":    f.get("assignee", {}).get("displayName", "Unassigned") if f.get("assignee") else "Unassigned",
        "url":         f"{JIRA_BASE_URL}/browse/{data['key']}",
    }


# ── Helpers ───────────────────────────────────────────────────────────────────

def _extract_adf_text(adf: Optional[dict]) -> str:
    """Recursively extract plain text from Atlassian Document Format."""
    if not adf:
        return ""
    if isinstance(adf, str):
        return adf
    text_parts = []
    if adf.get("type") == "text":
        text_parts.append(adf.get("text", ""))
    for child in adf.get("content", []):
        text_parts.append(_extract_adf_text(child))
    return " ".join(p for p in text_parts if p).strip()
