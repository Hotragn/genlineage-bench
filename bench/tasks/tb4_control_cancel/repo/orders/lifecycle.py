"""Hand-written order lifecycle helpers."""
from orders.status import OrderStatus, TERMINAL


def can_cancel(status):
    """Orders can be cancelled until they ship."""
    return status < OrderStatus.PAID


def is_final(status):
    return status in TERMINAL
