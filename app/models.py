import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Numeric, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class Record:
    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())


class User(Record, Base):
    __tablename__ = "users"
    email: Mapped[str] = mapped_column(String(320), unique=True)
    name: Mapped[str] = mapped_column(String(200))
    password_hash: Mapped[str] = mapped_column(Text)


class Owned(Record):
    owner_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)


class Company(Owned, Base):
    __tablename__ = "companies"
    name: Mapped[str] = mapped_column(String(200))
    website: Mapped[str | None] = mapped_column(String(500))


class Contact(Owned, Base):
    __tablename__ = "contacts"
    name: Mapped[str] = mapped_column(String(200))
    email: Mapped[str | None] = mapped_column(String(320))
    phone: Mapped[str | None] = mapped_column(String(50))
    company_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("companies.id", ondelete="SET NULL"), index=True)


class Deal(Owned, Base):
    __tablename__ = "deals"
    __table_args__ = (CheckConstraint("value >= 0", name="ck_deal_value"), CheckConstraint("stage IN ('lead', 'qualified', 'proposal', 'won', 'lost')", name="ck_deal_stage"))
    title: Mapped[str] = mapped_column(String(200))
    value: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    currency: Mapped[str] = mapped_column(String(3), default="USD")
    stage: Mapped[str] = mapped_column(String(20), default="lead")
    contact_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("contacts.id", ondelete="SET NULL"), index=True)


class Task(Owned, Base):
    __tablename__ = "tasks"
    __table_args__ = (CheckConstraint("status IN ('todo', 'in_progress', 'done')", name="ck_task_status"),)
    title: Mapped[str] = mapped_column(String(200))
    description: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="todo")
    due_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    deal_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("deals.id", ondelete="SET NULL"), index=True)
