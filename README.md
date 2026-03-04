# Kapkoros Tea Factory Software Management System

A full workflow tea factory management system for **Kapkoros Tea Factory**:

- Farmer green-leaf intake and quality flagging.
- Processing batch monitoring by stage (withering, rolling, oxidation, drying, sorting).
- Quality compliance checks against international tea quality thresholds.
- Inventory lot creation and traceability linking collections -> processing -> quality -> auction sales.
- Auction sale recording and revenue tracking.

## Backend (FastAPI)

From repo root:

```bash
pip install -r backend/requirements.txt
python backend/backend/app.py
```

Server runs at `http://localhost:8000`.

## Key API endpoints

- `GET /dashboard`
- `GET /farmers`
- `POST /collections`
- `POST /processing`
- `POST /quality-assessments`
- `GET /inventory`
- `POST /auction-sales`
- `GET /traceability`

## Frontend

Open:

`backend/backend/backend/frontend/index.html`

The frontend calls the API at `http://localhost:8000`.
