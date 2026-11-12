# Database row models.
from dataclasses import dataclass
from typing import Optional


@dataclass
class Invoices:
    id: int
    total: float
    paid: bool
    customer: Optional[str] = None
    paid_at: Optional[str] = None
    note: Optional[str] = None
