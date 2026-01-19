from app.db.base import Base
from app.db.session import engine
from app.models import (
    borrower,
    document,
    loan_account,
    loan_application,
    loan_participation,
    loan_partner,
    loan_product,
    payment,
    payment_allocation,
    repayment_schedule,
)


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    init_db()
