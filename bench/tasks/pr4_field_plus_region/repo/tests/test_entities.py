import unittest
from models.entities import Product, Coupon
class T(unittest.TestCase):
    def test_max_uses(self):
        self.assertEqual(Coupon(code="X", percent_off=10).max_uses, 1)
        self.assertTrue(Coupon(code="X", percent_off=10, max_uses=5).validate())
        self.assertFalse(Coupon(code="X", percent_off=10, max_uses=0).validate())
    def test_percent(self):
        self.assertFalse(Coupon(code="X", percent_off=0).validate())
