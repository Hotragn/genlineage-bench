import unittest
from orders.status import OrderStatus, TERMINAL
from orders import lifecycle

class T(unittest.TestCase):
    def test_refunded_status(self):
        self.assertEqual(OrderStatus.REFUNDED, 50)
    def test_delivered(self):
        self.assertTrue(lifecycle.is_final(OrderStatus.DELIVERED))
