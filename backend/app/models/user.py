"""
User and permission models.

User: System users (employees, approvers, etc.)
RolePermission: Role-based access control
"""

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class User(Base):
    """
    System user for authentication and authorization.
    """
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    employee_id: Mapped[str | None] = mapped_column(String(50), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200))

    # Role: admin, manager, underwriter, collection_officer, customer_service
    role: Mapped[str] = mapped_column(String(50), index=True)
    department: Mapped[str | None] = mapped_column(String(100))
    branch_code: Mapped[str | None] = mapped_column(String(20))

    # Approval limits
    approval_limit: Mapped[float | None] = mapped_column()  # Max loan amount can approve
    can_approve_restructure: Mapped[bool] = mapped_column(Boolean, default=False)
    can_approve_writeoff: Mapped[bool] = mapped_column(Boolean, default=False)

    # Status
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    last_login: Mapped[DateTime | None] = mapped_column(DateTime)

    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())
    updated_at: Mapped[DateTime | None] = mapped_column(DateTime, onupdate=func.now())

    # Relationships
    permissions: Mapped[list["RolePermission"]] = relationship(
        "RolePermission",
        back_populates="user",
        cascade="all, delete-orphan"
    )


class RolePermission(Base):
    """
    Permission assigned to a role or specific user.
    """
    __tablename__ = "role_permissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=True,
        index=True
    )
    role: Mapped[str | None] = mapped_column(String(50), index=True)  # For role-based permissions

    # Permission details
    permission: Mapped[str] = mapped_column(String(100), index=True)
    resource: Mapped[str | None] = mapped_column(String(100))  # loan_application, loan_account, etc.
    action: Mapped[str | None] = mapped_column(String(50))  # create, read, update, delete, approve

    # Constraints
    max_amount: Mapped[float | None] = mapped_column()  # Max amount for this permission
    product_ids: Mapped[str | None] = mapped_column(Text)  # Comma-separated product IDs

    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[DateTime] = mapped_column(DateTime, server_default=func.now())

    # Relationships
    user: Mapped["User"] = relationship("User", back_populates="permissions")
