from datetime import date

from app.services.schedule import generate_amortization_schedule


def test_generate_emi_schedule() -> None:
    schedule = generate_amortization_schedule(
        principal=10000,
        annual_rate=12,
        tenure_months=12,
        start_date=date(2024, 1, 1),
        schedule_type="emi",
        repayment_frequency="monthly",
    )
    assert len(schedule) == 12
    total_principal = sum(item["principal_due"] for item in schedule)
    assert abs(total_principal - 10000) < 0.1
