"""Hand-written client helpers around the generated models."""
from client.models import Account, Invoice, Status


def parse_account(payload):
    return Account.model_validate(payload)


def total_cents(invoices):
    return sum(i.amount_cents for i in invoices)


def page_slices(n_items, page_size):
    """Return (start, stop) index pairs covering n_items in pages of page_size."""
    return [(s, s + page_size) for s in range(0, n_items, page_size)]


def is_billable(account):
    return account.status in (None, Status.active)
