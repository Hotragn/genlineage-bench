import unittest
from orders.status import OrderStatus, TERMINAL
from orders import lifecycle

class T(unittest.TestCase):
    def test_terminal(self):
        self.assertTrue(lifecycle.is_final(OrderStatus.DELIVERED))
        self.assertTrue(lifecycle.is_final(OrderStatus.REFUNDED))
        self.assertFalse(lifecycle.is_final(OrderStatus.PENDING))
