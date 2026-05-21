"""
QA Sprint Tracker — Streamlit Frontend
Run with:  streamlit run frontend/app.py
"""

import json
from datetime import datetime

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import requests
import streamlit as st

API = "http://127.0.0.1:8000"

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="QA Sprint Tracker",
    page_icon="🧪",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Custom CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    [data-testid="stSidebar"] { background: #1E3A5F; }
    [data-testid="stSidebar"] * { color: #ECF0F1 !important; }
    .metric-card {
        background: #F4F6F9; border-radius: 10px;
        padding: 16px 20px; text-align: center;
        border-left: 4px solid #2E86AB;
    }
    .metric-card h2 { margin: 0; font-size: 2rem; color: #1E3A5F; }
    .metric-card p  { margin: 0; color: #7F8C8D; font-size: 0.85rem; }
    .pass    { border-left-color: #27AE60 !important; }
    .fail    { border-left-color: #E74C3C !important; }
    .blocked { border-left-color: #F39C12 !important; }
    .stButton>button { border-radius: 8px; }
</style>
""", unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────────────────
STATUS_EMOJI = {"Pass": "✅", "Fail": "❌", "Blocked": "🚫"}
PRIORITY_COLOR = {"Critical": "🔴", "High": "🟠", "Medium": "🟡", "Low": "🟢"}


def api(method: str, path: str, **kwargs):
    try:
        r = getattr(requests, method)(f"{API}{path}", **kwargs)
        r.raise_for_status()
        return r.json()
    except requests.exceptions.ConnectionError:
        st.error("⚠️  Cannot reach the backend. Make sure the API server is running.")
        return None
    except Exception as e:
        st.error(f"API error: {e}")
        return None


def metric_card(label: str, value, css_class: str = ""):
    st.markdown(
        f'<div class="metric-card {css_class}"><h2>{value}</h2><p>{label}</p></div>',
        unsafe_allow_html=True,
    )


def load_sprints():
    return api("get", "/sprints/") or []


def load_tickets(sprint_id=None):
    url = "/tickets/" + (f"?sprint_id={sprint_id}" if sprint_id else "")
    return api("get", url) or []


def load_test_cases(ticket_id=None):
    url = "/test-cases/" + (f"?ticket_id={ticket_id}" if ticket_id else "")
    return api("get", url) or []


def load_executions(test_case_id=None):
    url = "/executions/" + (f"?test_case_id={test_case_id}" if test_case_id else "")
    return api("get", url) or []


# ── Sidebar nav ───────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🧪 QA Sprint Tracker")
    st.markdown("---")
    page = st.radio(
        "Navigate",
        ["🏠  Dashboard", "🗓️  Sprints", "🎫  Tickets",
         "📋  Test Cases", "▶️  Execute Tests",
         "🌍  Environment Matrix", "📊  Sprint Report"],
        label_visibility="collapsed",
    )
    st.markdown("---")
    st.caption("QA Sprint Tracker v1.0")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: DASHBOARD
# ══════════════════════════════════════════════════════════════════════════════
if page == "🏠  Dashboard":
    st.title("🧪 QA Sprint Tracker")
    st.markdown("Your quality work — made visible.")
    st.markdown("---")

    sprints   = load_sprints()
    tickets   = load_tickets()
    all_tcs   = load_test_cases()
    all_exes  = load_executions()

    c1, c2, c3, c4, c5 = st.columns(5)
    with c1: metric_card("Sprints",        len(sprints))
    with c2: metric_card("Tickets Tested", len(tickets))
    with c3: metric_card("Test Cases",     len(all_tcs))
    with c4: metric_card("Executions",     len(all_exes))
    with c5:
        bugs = sum(1 for e in all_exes if e.get("bug_id"))
        metric_card("Bugs Logged", bugs, "fail")

    st.markdown("")

    if all_exes:
        col1, col2 = st.columns(2)

        # Donut chart — overall pass/fail
        with col1:
            st.markdown("#### Overall Execution Results")
            counts = {"Pass": 0, "Fail": 0, "Blocked": 0}
            for e in all_exes:
                counts[e["status"]] = counts.get(e["status"], 0) + 1
            fig = go.Figure(go.Pie(
                labels=list(counts.keys()),
                values=list(counts.values()),
                hole=0.55,
                marker_colors=["#27AE60", "#E74C3C", "#F39C12", "#95A5A6"],
            ))
            fig.update_layout(margin=dict(t=0, b=0), height=280, showlegend=True)
            st.plotly_chart(fig, use_container_width=True)

        # Bar chart — executions per platform×environment
        with col2:
            st.markdown("#### Executions by Platform & Environment")
            df = pd.DataFrame(all_exes)
            if not df.empty:
                grp = df.groupby(["platform", "environment", "status"]).size().reset_index(name="count")
                fig2 = px.bar(
                    grp, x="platform", y="count", color="status", barmode="group",
                    facet_col="environment",
                    color_discrete_map={
                        "Pass": "#27AE60", "Fail": "#E74C3C",
                        "Blocked": "#F39C12"
                    },
                    height=280,
                )
                fig2.update_layout(margin=dict(t=20, b=0))
                st.plotly_chart(fig2, use_container_width=True)
    else:
        st.info("No executions logged yet. Start testing to see your dashboard come alive! 🚀")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: SPRINTS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🗓️  Sprints":
    st.title("🗓️ Sprints")

    with st.expander("➕  Create New Sprint", expanded=False):
        with st.form("new_sprint"):
            name       = st.text_input("Sprint Name", placeholder="e.g. Sprint 42")
            goal       = st.text_area("Sprint Goal (optional)")
            col1, col2 = st.columns(2)
            start_date = col1.date_input("Start Date")
            end_date   = col2.date_input("End Date")
            if st.form_submit_button("Create Sprint"):
                result = api("post", "/sprints/", json={
                    "name": name,
                    "goal": goal,
                    "start_date": start_date.isoformat() if start_date else None,
                    "end_date":   end_date.isoformat()   if end_date   else None,
                })
                if result:
                    st.success(f"✅ Sprint **{name}** created!")
                    st.rerun()

    sprints = load_sprints()
    if sprints:
        for s in sprints:
            col1, col2 = st.columns([5, 1])
            with col1:
                st.markdown(f"### 📅 {s['name']}")
                if s.get("goal"):
                    st.caption(f"Goal: {s['goal']}")
                st.caption(f"Created: {s['created_at'][:10]}")
            with col2:
                if st.button("🗑️", key=f"del_sprint_{s['id']}", help="Delete sprint"):
                    api("delete", f"/sprints/{s['id']}")
                    st.rerun()
            st.markdown("---")
    else:
        st.info("No sprints yet. Create your first sprint above.")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: TICKETS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🎫  Tickets":
    st.title("🎫 Tickets")

    sprints = load_sprints()
    sprint_map = {s["name"]: s["id"] for s in sprints}

    with st.expander("➕  Add New Ticket", expanded=False):
        with st.form("new_ticket"):
            col1, col2 = st.columns(2)
            external_id  = col1.text_input("Ticket ID", placeholder="JIRA-123")
            ticket_type  = col2.selectbox("Type", ["feature", "bug", "improvement"])
            title        = st.text_input("Title", placeholder="Describe the ticket briefly")
            description  = st.text_area("Description / Acceptance Criteria", height=120)
            sprint_name  = st.selectbox("Assign to Sprint", ["— None —"] + list(sprint_map.keys()))

            if st.form_submit_button("💾  Save Ticket"):
                sprint_id = sprint_map.get(sprint_name)
                result = api("post", "/tickets/", json={
                    "external_id": external_id or None,
                    "title": title,
                    "description": description,
                    "ticket_type": ticket_type,
                    "sprint_id": sprint_id,
                })
                if result:
                    st.success(f"✅ Ticket **{title}** saved!")
                    st.rerun()

    # Filter by sprint
    filter_sprint = st.selectbox("Filter by Sprint", ["All"] + list(sprint_map.keys()))
    sprint_id_filter = sprint_map.get(filter_sprint) if filter_sprint != "All" else None
    tickets = load_tickets(sprint_id_filter)

    if tickets:
        for t in tickets:
            col1, col2 = st.columns([6, 1])
            with col1:
                ref = f"`{t['external_id']}`  " if t.get("external_id") else ""
                st.markdown(f"**{ref}{t['title']}**  `{t['ticket_type']}`")
                st.caption(t["description"][:160] + ("…" if len(t["description"]) > 160 else ""))
            with col2:
                if st.button("🗑️", key=f"del_ticket_{t['id']}"):
                    api("delete", f"/tickets/{t['id']}")
                    st.rerun()
            st.markdown("---")
    else:
        st.info("No tickets found.")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: TEST CASES
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📋  Test Cases":
    st.title("📋 Test Cases")

    tickets = load_tickets()
    if not tickets:
        st.warning("Create a ticket first.")
        st.stop()

    ticket_map = {f"{t.get('external_id', '') or ''} {t['title']}".strip(): t for t in tickets}
    selected_label = st.selectbox("Select Ticket", list(ticket_map.keys()))
    ticket = ticket_map[selected_label]

    col1, col2 = st.columns([3, 1])
    with col2:
        if st.button("🤖  AI Generate Test Cases", use_container_width=True):
            with st.spinner("Generating test cases…"):
                result = api("post", f"/tickets/{ticket['id']}/generate-test-cases/")
            if result:
                st.success(f"✅ {len(result)} test cases generated!")
                st.rerun()

    with col1:
        with st.expander("➕  Add Test Case Manually"):
            with st.form("new_tc"):
                tc_title     = st.text_input("Title")
                preconditions = st.text_input("Preconditions")
                steps_raw    = st.text_area("Steps (one per line)", height=100)
                expected     = st.text_area("Expected Result", height=60)
                col_a, col_b = st.columns(2)
                priority     = col_a.selectbox("Priority", ["Critical", "High", "Medium", "Low"])
                tags         = col_b.text_input("Tags", placeholder="smoke, regression")
                if st.form_submit_button("💾  Save"):
                    steps_list = [s.strip() for s in steps_raw.strip().splitlines() if s.strip()]
                    api("post", "/test-cases/", json={
                        "ticket_id": ticket["id"],
                        "title": tc_title,
                        "preconditions": preconditions,
                        "steps": json.dumps(steps_list),
                        "expected_result": expected,
                        "priority": priority,
                        "tags": tags,
                    })
                    st.success("✅ Test case saved!")
                    st.rerun()

    tcs = load_test_cases(ticket["id"])
    if tcs:
        st.markdown(f"**{len(tcs)} test case(s)** for this ticket")
        for tc in tcs:
            priority_icon = PRIORITY_COLOR.get(tc["priority"], "⚪")
            with st.expander(f"{priority_icon} [{tc['priority']}]  {tc['title']}"):
                if tc.get("preconditions"):
                    st.markdown(f"**Preconditions:** {tc['preconditions']}")
                try:
                    steps = json.loads(tc["steps"])
                    st.markdown("**Steps:**")
                    for i, step in enumerate(steps, 1):
                        st.markdown(f"  {i}. {step}")
                except Exception:
                    st.markdown(f"**Steps:** {tc['steps']}")
                st.markdown(f"**Expected Result:** {tc['expected_result']}")
                if tc.get("tags"):
                    tags_html = " ".join(
                        f"`{tag.strip()}`" for tag in tc["tags"].split(",") if tag.strip()
                    )
                    st.markdown(f"**Tags:** {tags_html}")
                if st.button("🗑️ Delete", key=f"del_tc_{tc['id']}"):
                    api("delete", f"/test-cases/{tc['id']}")
                    st.rerun()
    else:
        st.info("No test cases yet. Generate them with AI or add manually.")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: EXECUTE TESTS
# ══════════════════════════════════════════════════════════════════════════════
elif page == "▶️  Execute Tests":
    st.title("▶️ Execute Tests")
    st.markdown("Log your manual test results across any platform and environment.")

    tickets = load_tickets()
    if not tickets:
        st.warning("No tickets available.")
        st.stop()

    ticket_map = {f"{t.get('external_id', '') or ''} {t['title']}".strip(): t for t in tickets}
    selected_label = st.selectbox("Select Ticket", list(ticket_map.keys()))
    ticket = ticket_map[selected_label]

    tcs = load_test_cases(ticket["id"])
    if not tcs:
        st.warning("No test cases for this ticket. Generate them first.")
        st.stop()

    st.markdown("---")
    st.markdown("### 📝 Log Execution")

    with st.form("log_execution"):
        tc_map = {f"[{tc['priority']}] {tc['title']}": tc for tc in tcs}
        tc_label   = st.selectbox("Test Case", list(tc_map.keys()))
        col1, col2 = st.columns(2)
        platform   = col1.selectbox("Platform", ["iOS", "Android", "Web"])
        environment = col2.selectbox("Environment", ["Production", "Staging", "Integration"])
        col3, col4 = st.columns(2)
        app_version = col3.text_input("App Version", placeholder="e.g. 3.2.1")
        os_version  = col4.text_input("OS Version",  placeholder="e.g. iOS 17.4")
        status     = st.radio("Status", ["Pass", "Fail", "Blocked"], horizontal=True)
        notes      = st.text_area("Notes / Observations", height=80)
        bug_id     = st.text_input("Bug ID (if failed)", placeholder="BUG-456")

        submitted = st.form_submit_button("✅  Log Result", use_container_width=True)
        if submitted:
            tc = tc_map[tc_label]
            result = api("post", "/executions/", json={
                "test_case_id": tc["id"],
                "status": status,
                "platform": platform,
                "environment": environment,
                "app_version": app_version or None,
                "os_version":  os_version  or None,
                "notes": notes or None,
                "bug_id": bug_id or None,
            })
            if result:
                emoji = STATUS_EMOJI.get(status, "")
                st.success(f"{emoji}  Logged: **{tc['title']}** → {status} on {platform} / {environment}")

    # Execution history for this ticket
    st.markdown("---")
    st.markdown("### 📜 Execution History (this ticket)")
    all_tc_ids = {tc["id"] for tc in tcs}
    all_exes = load_executions()
    ticket_exes = [e for e in all_exes if e["test_case_id"] in all_tc_ids]

    if ticket_exes:
        tc_id_to_title = {tc["id"]: tc["title"] for tc in tcs}
        rows = []
        for e in ticket_exes:
            rows.append({
                "Test Case":   tc_id_to_title.get(e["test_case_id"], "—"),
                "Status":      STATUS_EMOJI.get(e["status"], "") + " " + e["status"],
                "Platform":    e["platform"],
                "Environment": e["environment"],
                "App Ver.":    e.get("app_version") or "—",
                "Bug ID":      e.get("bug_id") or "—",
                "Executed":    e["executed_at"][:16].replace("T", " "),
            })
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)
    else:
        st.info("No executions logged for this ticket yet.")


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: ENVIRONMENT MATRIX
# ══════════════════════════════════════════════════════════════════════════════
elif page == "🌍  Environment Matrix":
    st.title("🌍 Environment Matrix")
    st.markdown("See at a glance which test cases passed/failed across every platform and environment.")

    tickets = load_tickets()
    if not tickets:
        st.warning("No tickets available.")
        st.stop()

    ticket_map = {f"{t.get('external_id', '') or ''} {t['title']}".strip(): t for t in tickets}
    selected_label = st.selectbox("Select Ticket", list(ticket_map.keys()))
    ticket = ticket_map[selected_label]

    matrix_data = api("get", f"/matrix/{ticket['id']}")
    if not matrix_data or not matrix_data.get("rows"):
        st.info("No executions logged yet for this ticket.")
        st.stop()

    columns = matrix_data["columns"]
    rows    = matrix_data["rows"]

    # Build a styled dataframe
    table_rows = []
    for row in rows:
        r = {
            "Test Case":  row["test_case_title"],
            "Priority":   PRIORITY_COLOR.get(row["priority"], "⚪") + " " + row["priority"],
        }
        for col in columns:
            status = row["matrix"].get(col, "—")
            r[col] = STATUS_EMOJI.get(status, "—") + " " + status if status != "—" else "—"
        table_rows.append(r)

    df = pd.DataFrame(table_rows)

    st.markdown(f"**Ticket:** {matrix_data['ticket_title']}")
    st.dataframe(df, use_container_width=True, hide_index=True)

    # Heat-map style view
    if columns:
        st.markdown("#### Coverage Heat Map")
        heat_data = []
        for row in rows:
            for col in columns:
                s = row["matrix"].get(col, "Not Run")
                heat_data.append({"Test Case": row["test_case_title"][:40], "Column": col, "Status": s})
        df_heat = pd.DataFrame(heat_data)
        status_order = ["Pass", "Fail", "Blocked", "Not Run"]
        color_map    = {
            "Pass": "#27AE60", "Fail": "#E74C3C",
            "Blocked": "#F39C12", "Not Run": "#D5D8DC"
        }
        fig = px.density_heatmap(
            df_heat, x="Column", y="Test Case", z=None,
            color_continuous_scale=None, height=max(300, len(rows) * 45)
        )
        # Use a categorical scatter as a workaround for colour-coded matrix
        fig2 = go.Figure()
        for status in status_order:
            sub = df_heat[df_heat["Status"] == status]
            if sub.empty:
                continue
            fig2.add_trace(go.Scatter(
                x=sub["Column"],
                y=sub["Test Case"],
                mode="markers+text",
                marker=dict(size=28, color=color_map[status], symbol="square"),
                text=STATUS_EMOJI.get(status, ""),
                textfont=dict(size=14),
                name=status,
            ))
        fig2.update_layout(
            height=max(300, len(rows) * 55),
            margin=dict(l=0, r=0, t=10, b=0),
            legend=dict(orientation="h", yanchor="bottom", y=1.02),
        )
        st.plotly_chart(fig2, use_container_width=True)


# ══════════════════════════════════════════════════════════════════════════════
# PAGE: SPRINT REPORT
# ══════════════════════════════════════════════════════════════════════════════
elif page == "📊  Sprint Report":

    # ── Extra CSS just for this page ─────────────────────────────────────────
    st.markdown("""
    <style>
    .report-hero {
        background: linear-gradient(135deg, #1E3A5F 0%, #2E86AB 100%);
        border-radius: 16px;
        padding: 32px 36px;
        margin-bottom: 24px;
        color: white;
    }
    .report-hero h1 { color: white; font-size: 2rem; margin: 0 0 4px 0; }
    .report-hero p  { color: rgba(255,255,255,0.75); margin: 0; font-size: 1rem; }

    .kpi-card {
        background: white;
        border-radius: 14px;
        padding: 20px 16px;
        text-align: center;
        box-shadow: 0 2px 12px rgba(0,0,0,0.07);
        border-top: 4px solid #2E86AB;
        height: 100%;
    }
    .kpi-card.green  { border-top-color: #27AE60; }
    .kpi-card.red    { border-top-color: #E74C3C; }
    .kpi-card.orange { border-top-color: #F39C12; }
    .kpi-card.purple { border-top-color: #8E44AD; }
    .kpi-card h2 { font-size: 2.2rem; margin: 0; color: #1E3A5F; font-weight: 700; }
    .kpi-card p  { font-size: 0.78rem; color: #7F8C8D; margin: 4px 0 0 0; text-transform: uppercase; letter-spacing: 0.05em; }

    .section-header {
        font-size: 1.05rem;
        font-weight: 700;
        color: #1E3A5F;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        border-left: 4px solid #2E86AB;
        padding-left: 10px;
        margin: 28px 0 14px 0;
    }

    .ticket-row {
        background: white;
        border-radius: 12px;
        padding: 16px 20px;
        margin-bottom: 10px;
        box-shadow: 0 1px 8px rgba(0,0,0,0.06);
        border-left: 5px solid #2E86AB;
        display: flex;
        align-items: center;
        justify-content: space-between;
    }
    .ticket-row.all-pass  { border-left-color: #27AE60; }
    .ticket-row.has-fail  { border-left-color: #E74C3C; }
    .ticket-row.has-block { border-left-color: #F39C12; }

    .talking-box {
        background: linear-gradient(135deg, #f0f9ff, #e8f5e9);
        border: 1px solid #2E86AB;
        border-radius: 14px;
        padding: 24px 28px;
        margin-top: 8px;
    }
    .talking-box h4 { color: #1E3A5F; margin-top: 0; }
    .talking-box p  { color: #2C3E50; font-size: 1.05rem; line-height: 1.7; margin: 0; }

    .pdf-btn > button {
        background: linear-gradient(135deg, #1E3A5F, #2E86AB) !important;
        color: white !important;
        border: none !important;
        border-radius: 10px !important;
        font-weight: 600 !important;
        padding: 10px 24px !important;
    }
    </style>
    """, unsafe_allow_html=True)

    # ── Sprint selector ───────────────────────────────────────────────────────
    sprints = load_sprints()
    if not sprints:
        st.warning("No sprints found. Create a sprint first.")
        st.stop()

    sprint_map  = {s["name"]: s["id"] for s in sprints}
    col_sel, col_pdf = st.columns([3, 1])
    sprint_name = col_sel.selectbox("", list(sprint_map.keys()), label_visibility="collapsed")
    sprint_id   = sprint_map[sprint_name]

    report = api("get", f"/reports/sprint/{sprint_id}")
    if not report:
        st.stop()

    ticket_reports = report.get("ticket_reports", [])

    # PDF download button
    with col_pdf:
        st.markdown('<div class="pdf-btn">', unsafe_allow_html=True)
        if st.button("📥  Download PDF", use_container_width=True):
            r = requests.get(f"{API}/reports/sprint/{sprint_id}/pdf")
            if r.status_code == 200:
                st.download_button(
                    "💾  Save PDF now",
                    data=r.content,
                    file_name=f"QA_Sprint_{sprint_name.replace(' ', '_')}.pdf",
                    mime="application/pdf",
                    use_container_width=True,
                )
            else:
                st.error("Could not generate PDF.")
        st.markdown('</div>', unsafe_allow_html=True)

    # ── Hero banner ───────────────────────────────────────────────────────────
    from datetime import datetime as _dt
    st.markdown(f"""
    <div class="report-hero">
        <h1>📊 {sprint_name}</h1>
        <p>QA Sprint Report &nbsp;·&nbsp; Generated {_dt.utcnow().strftime('%d %B %Y')}</p>
    </div>
    """, unsafe_allow_html=True)

    # ── KPI cards ─────────────────────────────────────────────────────────────
    pr   = report["pass_rate"]
    bugs = report["bug_count"]
    c1, c2, c3, c4, c5, c6 = st.columns(6)

    cards = [
        (c1, report["total_tickets"],    "Tickets",       ""),
        (c2, report["total_test_cases"], "Test Cases",    "purple"),
        (c3, report["total_executions"], "Executions",    ""),
        (c4, report["passed"],           "✅ Passed",     "green"),
        (c5, report["failed"],           "❌ Failed",     "red"),
        (c6, f"{pr:.1f}%",              "Pass Rate",     "green" if pr >= 80 else "orange" if pr >= 50 else "red"),
    ]
    for col, val, label, css in cards:
        with col:
            st.markdown(
                f'<div class="kpi-card {css}"><h2>{val}</h2><p>{label}</p></div>',
                unsafe_allow_html=True,
            )

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Charts row ────────────────────────────────────────────────────────────
    col1, col2 = st.columns([1, 2])

    with col1:
        st.markdown('<p class="section-header">Results Breakdown</p>', unsafe_allow_html=True)
        fig_donut = go.Figure(go.Pie(
            labels=["Passed", "Failed", "Blocked"],
            values=[report["passed"], report["failed"], report["blocked"]],
            hole=0.65,
            marker_colors=["#27AE60", "#E74C3C", "#F39C12"],
            textinfo="label+percent",
            textfont_size=11,
        ))
        fig_donut.update_layout(
            annotations=[dict(
                text=f"<b>{pr:.0f}%</b><br>Pass",
                font=dict(size=18, color="#1E3A5F"),
                showarrow=False,
            )],
            showlegend=False,
            margin=dict(t=10, b=10, l=10, r=10),
            height=300,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
        )
        st.plotly_chart(fig_donut, use_container_width=True)

    with col2:
        st.markdown('<p class="section-header">Coverage per Ticket</p>', unsafe_allow_html=True)
        if ticket_reports:
            def _two_line_label(t):
                """Split label into: line1 = ID, line2 = title (wrapped ~25 chars)"""
                ref   = t.get("external_id") or f"#{t['ticket_id']}"
                title = t["title"]
                # wrap title across two sub-lines if long
                if len(title) <= 25:
                    return f"<b>{ref}</b><br>{title}"
                else:
                    return f"<b>{ref}</b><br>{title[:25]}…"

            df_t = pd.DataFrame([{
                "Ticket":   (t.get("external_id") or f"#{t['ticket_id']}"),
                "Label":    _two_line_label(t),
                "Pass":     t["passed"],
                "Fail":     t["failed"],
                "Blocked":  t["blocked"],
            } for t in ticket_reports])

            fig_bar = go.Figure()
            for status, color in [
                ("Pass",    "#27AE60"),
                ("Fail",    "#E74C3C"),
                ("Blocked", "#F39C12"),
            ]:
                fig_bar.add_trace(go.Bar(
                    name=status,
                    y=df_t["Label"],
                    x=df_t[status],
                    orientation="h",
                    marker_color=color,
                    marker_line_width=0,
                ))

            fig_bar.update_layout(
                barmode="stack",
                # extra height per row to accommodate 2-line labels
                height=max(300, len(ticket_reports) * 72),
                margin=dict(t=50, b=10, l=180, r=20),
                legend=dict(
                    orientation="h",
                    yanchor="bottom",
                    y=1.08,          # push legend further above the chart
                    x=0,
                    traceorder="normal",
                    font=dict(family="Inter, sans-serif", size=12, color="#FFFFFF"),
                    bgcolor="rgba(0,0,0,0)",
                    itemwidth=50,
                    entrywidth=80,
                ),
                xaxis=dict(
                    title="Executions",
                    gridcolor="rgba(255,255,255,0.15)",
                    tickfont=dict(family="Inter, sans-serif", size=11, color="#CCCCCC"),
                    titlefont=dict(color="#CCCCCC"),
                    zeroline=False,
                ),
                yaxis=dict(
                    # use HTML-formatted tick text for two-line labels
                    tickfont=dict(family="Inter, sans-serif", size=11, color="#FFFFFF"),
                    automargin=False,
                    tickmode="array",
                    tickvals=df_t["Label"].tolist(),
                    ticktext=df_t["Label"].tolist(),
                    # increase row height via tick spacing
                    ticklabeloverflow="allow",
                ),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig_bar, use_container_width=True)

    # ── Progress bars per ticket ──────────────────────────────────────────────
    st.markdown('<p class="section-header">Ticket-by-Ticket Breakdown</p>', unsafe_allow_html=True)

    if ticket_reports:
        for t in ticket_reports:
            cov   = t["coverage_pct"]
            ref   = f"`{t['external_id']}`" if t.get("external_id") else ""
            plat  = " · ".join(t["platforms_tested"])    or "—"
            envs  = " · ".join(t["environments_tested"]) or "—"

            # border colour logic
            if t["failed"] > 0:
                border = "has-fail"
            elif t["blocked"] > 0:
                border = "has-block"
            else:
                border = "all-pass"

            col_info, col_stats = st.columns([3, 2])
            with col_info:
                st.markdown(f"**{ref}  {t['title']}**")
                st.caption(f"� {plat}   •   🌍 {envs}")
                st.progress(int(cov) / 100, text=f"Coverage: {cov:.0f}%")
            with col_stats:
                s1, s2, s3, s4 = st.columns(4)
                s1.metric("✅", t["passed"])
                s2.metric("❌", t["failed"])
                s3.metric("🚫", t["blocked"])
                s4.metric("Cases", t["total_cases"])
            st.markdown("<hr style='margin:8px 0; border-color:#ECF0F1'>", unsafe_allow_html=True)

    # ── Bugs logged ───────────────────────────────────────────────────────────
    if bugs > 0:
        st.markdown('<p class="section-header">🐞 Bugs Logged This Sprint</p>', unsafe_allow_html=True)
        st.markdown(
            f'<div style="background:#FEF9E7;border:1px solid #F39C12;border-radius:10px;padding:14px 20px;">'
            f'<b>{bugs} bug(s)</b> were identified and logged during this sprint. '
            f'Check execution notes for bug IDs and details.</div>',
            unsafe_allow_html=True,
        )
        st.markdown("<br>", unsafe_allow_html=True)

    # ── Sprint review talking points ──────────────────────────────────────────
    st.markdown('<p class="section-header">🎤 Sprint Review Talking Points</p>', unsafe_allow_html=True)

    platforms_all = set()
    envs_all      = set()
    for t in ticket_reports:
        platforms_all.update(t["platforms_tested"])
        envs_all.update(t["environments_tested"])

    plat_str = " & ".join(sorted(platforms_all)) or "multiple platforms"
    env_str  = ", ".join(sorted(envs_all))        or "multiple environments"

    quality = "🟢 Excellent" if pr >= 90 else "🟡 Good" if pr >= 70 else "🔴 Needs Attention"

    st.markdown(f"""
    <div class="talking-box">
        <h4>🎤 What to say at Sprint Review</h4>
        <p>
        During <b>{sprint_name}</b>, I validated <b>{report['total_tickets']} ticket(s)</b>
        with <b>{report['total_test_cases']} test cases</b> across
        <b>{report['total_executions']} total executions</b>
        covering <b>{plat_str}</b> on <b>{env_str}</b> environments.<br><br>
        <b>{pr:.1f}% of tests passed</b> — Quality status: {quality}.<br>
        {"<b>" + str(bugs) + " bug(s)</b> were identified and logged for the team." if bugs else "No bugs were logged this sprint. ✅"}<br><br>
        Full traceability — from ticket to test case to environment — is available in the QA Sprint Tracker.
        </p>
    </div>
    """, unsafe_allow_html=True)
