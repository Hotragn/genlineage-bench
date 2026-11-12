# Order status codes.
import enum


class OrderStatus(enum.IntEnum):
    PENDING = 10
    PAID = 20
    SHIPPED = 30
    DELIVERED = 40
    REFUNDED = 50


TERMINAL = frozenset({OrderStatus.DELIVERED, OrderStatus.REFUNDED})
