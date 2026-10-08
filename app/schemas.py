from datetime import datetime
from decimal import Decimal
from typing import Literal
from uuid import UUID

from pydantic import AwareDatetime, BaseModel, ConfigDict, EmailStr, Field


class Input(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class Register(Input):
    email: EmailStr
    name: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=10, max_length=128)


class Login(Input):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    email: EmailStr
    name: str


class CompanyIn(Input):
    name: str = Field(min_length=1, max_length=200)
    website: str | None = Field(default=None, max_length=500)


class ContactIn(Input):
    name: str = Field(min_length=1, max_length=200)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, max_length=50)
    company_id: UUID | None = None


class DealIn(Input):
    title: str = Field(min_length=1, max_length=200)
    value: Decimal = Field(default=Decimal("0"), ge=0, max_digits=14, decimal_places=2)
    currency: str = Field(default="USD", pattern=r"^[A-Z]{3}$")
    stage: Literal["lead", "qualified", "proposal", "won", "lost"] = "lead"
    contact_id: UUID | None = None


class TaskIn(Input):
    title: str = Field(min_length=1, max_length=200)
    description: str | None = Field(default=None, max_length=10000)
    status: Literal["todo", "in_progress", "done"] = "todo"
    due_at: AwareDatetime | None = None
    deal_id: UUID | None = None


class RecordOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: UUID
    created_at: datetime
    updated_at: datetime


class CompanyOut(CompanyIn, RecordOut):
    pass


class ContactOut(ContactIn, RecordOut):
    pass


class DealOut(DealIn, RecordOut):
    pass


class TaskOut(TaskIn, RecordOut):
    pass
