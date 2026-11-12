# Code generated from db/schema.sql by tools/sqlgen.py; DO NOT EDIT.
from dataclasses import dataclass
from typing import Optional


@dataclass
class Invoices:
    id: int
    customer: str
    total: float
    paid: int
    paid_at: Optional[str] = None
    note: Optional[str] = None
