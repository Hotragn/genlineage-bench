# Database row models.
from dataclasses import dataclass
from typing import Optional


@dataclass
class Invoices:
    id: int
    customer: str
    total: float
    paid: bool
    paid_at: Optional[str] = None
    note: Optional[str] = None
