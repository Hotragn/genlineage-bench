"""Hand-written invoice queries over generated row models."""
from db.models import Invoices


def outstanding(rows):
    return [r for r in rows if not r.paid]


def revenue(rows):
    return round(sum(r.total for r in rows if r.paid), 2)
