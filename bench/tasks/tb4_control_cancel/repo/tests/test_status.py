import unittest
from orders.status import OrderStatus, TERMINAL
from orders import lifecycle

class T(unittest.TestCase):
    def test_cancel(self):
        self.assertTrue(lifecycle.can_cancel(OrderStatus.PAID))
        self.assertFalse(lifecycle.can_cancel(OrderStatus.SHIPPED))
