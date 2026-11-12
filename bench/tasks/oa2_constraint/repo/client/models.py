# Billing API models

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, conint, constr


class Status(Enum):
    active = 'active'
    suspended = 'suspended'
    archived = 'archived'


class Account(BaseModel):
    id: int
    username: constr(max_length=8)
    email: str | None = None
    status: Status | None = None


class Invoice(BaseModel):
    id: int
    account_id: int
    amount_cents: conint(ge=0)
