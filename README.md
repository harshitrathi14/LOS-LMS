# LOS/LMS (Unified Loan Origination + Loan Management)

This repository begins the implementation of a unified LOS/LMS platform based on the provided
requirements PDFs.

## Structure
- `backend/` - FastAPI service (API-first)
- `docs/requirements-summary.md` - condensed requirements notes

## Quickstart (local)
1) Create and activate a virtual environment, then install dependencies.
2) Configure the database connection in `backend/.env`.
3) Initialize the schema and run the API.

Example commands (PowerShell):

```
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
python -m app.db.init_db
uvicorn app.main:app --reload
```

If you prefer Postgres, start the database via:

```
docker compose up -d
```

## Starter APIs
- `GET /health`
- `POST /borrowers`, `GET /borrowers`
- `POST /loan-products`, `GET /loan-products`
- `POST /loan-applications`, `GET /loan-applications`, `PATCH /loan-applications/{id}`
- `POST /loan-accounts`, `GET /loan-accounts`
- `GET /loan-accounts/{id}/schedule`
- `POST /loan-accounts/{id}/payments`
- `POST /loan-partners`, `GET /loan-partners`
- `POST /loan-participations`, `GET /loan-participations`
- `POST /documents`, `GET /documents`
