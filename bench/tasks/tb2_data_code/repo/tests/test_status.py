import unittest
from orders.status import OrderStatus, TERMINAL
from orders import lifecycle

class T(unittest.TestCase):
    def test_shipped_code(self):
        self.assertIs(OrderStatus(30), OrderStatus.SHIPPED)
        self.assertFalse(lifecycle.can_cancel(OrderStatus.SHIPPED))
    def test_paid(self):
        self.assertTrue(lifecycle.can_cancel(OrderStatus.PAID))
