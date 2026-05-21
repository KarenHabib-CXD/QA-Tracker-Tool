# QA Sprint Tracker 🧪

> Make your manual testing **visible, traceable and impressive** at every sprint review.

---

## What it does

| Feature | Details |
|---|---|
| 🎫 **Ticket management** | Create tickets with Jira-style IDs, assign to sprints |
| 🤖 **AI test case generation** | Auto-generate test cases from ticket descriptions (OpenAI or smart mock) |
| ▶️ **Manual execution logging** | Log Pass / Fail / Blocked / Skipped per test case |
| 🌍 **Environment matrix** | See coverage across iOS / Android / Web × Production / Staging / Integration |
| 📊 **Sprint report dashboard** | Interactive charts, per-ticket breakdown, pass rate |
| 📥 **PDF export** | Download a professional PDF report for sprint review |
| 🎤 **Talking points** | Auto-generated sprint review speech |

---

## Quick Start

### 1 — Set up Python environment

```bash
cd qa-sprint-tracker
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2 — (Optional) Add OpenAI key

Edit `.env`:
```
OPENAI_API_KEY=sk-...
```
If you skip this, the tool uses a smart built-in mock generator.

### 3 — Start the backend (Terminal 1)

```bash
bash start_backend.sh
```
API docs available at: http://127.0.0.1:8000/docs

### 4 — Start the frontend (Terminal 2)

```bash
bash start_frontend.sh
```
Open: http://localhost:8501

---

## Typical Workflow

```
Create Sprint  →  Add Tickets  →  Generate Test Cases (AI)
→  Execute Tests (multi-env)  →  View Matrix  →  Generate Report  →  Sprint Review 🎉
```

---

## Project Structure

```
qa-sprint-tracker/
├── backend/
│   ├── main.py           # FastAPI app & all endpoints
│   ├── models.py         # SQLAlchemy ORM models
│   ├── schemas.py        # Pydantic schemas
│   ├── database.py       # DB engine & session
│   └── services/
│       ├── ai_generator.py  # OpenAI / mock test case generator
│       └── pdf_report.py    # PDF report builder (ReportLab)
├── frontend/
│   └── app.py            # Streamlit UI (all pages)
├── requirements.txt
├── .env                  # OPENAI_API_KEY, DATABASE_URL
├── start_backend.sh
└── start_frontend.sh
```

---

## Sprint Review Demo Script

> *"During Sprint X, I validated **N tickets** across **M test executions** covering iOS, Android, Production, Staging and Integration environments. **X% of tests passed**, and **N bugs** were identified and logged. Full traceability is available in the QA Sprint Tracker."*

That's your moment. 🚀
