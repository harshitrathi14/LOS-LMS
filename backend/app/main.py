from fastapi import FastAPI

from app.api.routers import (
    benchmark_rates,
    borrowers,
    documents,
    health,
    holiday_calendars,
    loan_accounts,
    loan_applications,
    loan_lifecycle,
    loan_participations,
    loan_partners,
    loan_products,
)
from app.core.config import get_settings

settings = get_settings()

app = FastAPI(title=settings.app_name, version="0.1.0")

app.include_router(health.router)
app.include_router(borrowers.router)
app.include_router(loan_products.router)
app.include_router(loan_applications.router)
app.include_router(loan_accounts.router)
app.include_router(loan_partners.router)
app.include_router(loan_participations.router)
app.include_router(documents.router)
app.include_router(holiday_calendars.router)
app.include_router(benchmark_rates.router)
app.include_router(loan_lifecycle.router)


@app.get("/")
def root() -> dict:
    return {"name": settings.app_name, "status": "running"}
