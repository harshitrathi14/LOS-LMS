from datetime import date, timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock

from app.services.delinquency import apply_delinquency_state, evaluate_npa_state
from app.services.par_report import (
    LAP_PAR_HEADERS,
    blank_lap_par_row,
    build_lap_los_row,
    get_lap_par_demo_defaults,
)


def test_evaluate_npa_state_is_sticky_until_full_cure() -> None:
    npa_start = date(2026, 1, 10)

    entered = evaluate_npa_state(
        dpd=90,
        as_of_date=npa_start,
        was_npa=False,
        existing_npa_date=None,
    )
    assert entered["is_npa"] is True
    assert entered["entered_npa"] is True
    assert entered["npa_date"] == npa_start

    sticky = evaluate_npa_state(
        dpd=25,
        as_of_date=npa_start + timedelta(days=15),
        was_npa=True,
        existing_npa_date=npa_start,
    )
    assert sticky["is_npa"] is True
    assert sticky["entered_npa"] is False
    assert sticky["exited_npa"] is False
    assert sticky["npa_date"] == npa_start

    cured = evaluate_npa_state(
        dpd=0,
        as_of_date=npa_start + timedelta(days=20),
        was_npa=True,
        existing_npa_date=npa_start,
    )
    assert cured["is_npa"] is False
    assert cured["exited_npa"] is True
    assert cured["npa_date"] is None


def test_apply_delinquency_state_updates_status_and_npa_flags() -> None:
    loan = SimpleNamespace(
        dpd=0,
        status="active",
        is_npa=False,
        npa_date=None,
        npa_category=None,
        is_written_off=False,
    )

    apply_delinquency_state(loan, 95, date(2026, 1, 1))
    assert loan.status == "npa"
    assert loan.is_npa is True
    assert loan.npa_date == date(2026, 1, 1)

    apply_delinquency_state(loan, 40, date(2026, 1, 15))
    assert loan.status == "npa"
    assert loan.is_npa is True

    apply_delinquency_state(loan, 0, date(2026, 1, 20))
    assert loan.status == "active"
    assert loan.is_npa is False
    assert loan.npa_date is None


def test_lap_par_headers_are_unique_and_blank_row_covers_all() -> None:
    assert len(LAP_PAR_HEADERS) == len(set(LAP_PAR_HEADERS))

    row = blank_lap_par_row()
    assert set(row.keys()) == set(LAP_PAR_HEADERS)


def test_build_lap_los_row_without_account_populates_core_fields() -> None:
    borrower = SimpleNamespace(
        id=11,
        external_id="CUS-0011",
        first_name="Hari",
        last_name="Singh",
        date_of_birth=date(1990, 5, 8),
        phone="9999999999",
    )
    product = SimpleNamespace(name="LAP Prime", code="LAP-P",)
    application = SimpleNamespace(
        id=101,
        borrower=borrower,
        product=product,
        decision_at=None,
        approved_rate=11.25,
        requested_amount=750000,
        approved_amount=700000,
        requested_tenure_months=60,
        status="submitted",
        channel="branch",
    )

    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None

    row = build_lap_los_row(application, date(2026, 2, 6), db)

    assert set(row.keys()) == set(LAP_PAR_HEADERS)
    assert row["Customer number"] == "CUS-0011"
    assert row["Member Name"] == "Hari Singh"
    assert row["Loan Amount"] == 750000.0
    assert row["Loan Status"] == "submitted"
    assert row["Overdue Days"] == 0


def test_build_lap_los_row_with_demo_defaults_populates_demo_fields() -> None:
    borrower = SimpleNamespace(
        id=22,
        external_id=None,
        first_name="Demo",
        last_name="User",
        date_of_birth=None,
        phone=None,
    )
    product = SimpleNamespace(name="LAP Demo", code="LAP-D")
    application = SimpleNamespace(
        id=102,
        borrower=borrower,
        product=product,
        decision_at=None,
        approved_rate=None,
        requested_amount=300000,
        approved_amount=None,
        requested_tenure_months=24,
        status="submitted",
        channel=None,
    )

    db = MagicMock()
    db.query.return_value.filter.return_value.first.return_value = None

    row = build_lap_los_row(
        application,
        date(2026, 2, 6),
        db,
        use_demo_defaults=True,
    )

    demo_defaults = get_lap_par_demo_defaults()
    assert row["Spouse Name"] == demo_defaults["Spouse Name"]
    assert row["Guarantor Name"] == demo_defaults["Guarantor Name"]
    assert row["Office Name"] == demo_defaults["Office Name"]
    assert row["LTV"] == demo_defaults["LTV"]
