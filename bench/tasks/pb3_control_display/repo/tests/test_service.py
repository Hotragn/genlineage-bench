import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "gen"))
from acct.v1 import user_pb2, team_pb2
from app import service
class T(unittest.TestCase):
    def test_display_without_email(self):
        self.assertEqual(service.display_name(user_pb2.User(id=1, name="Ada")), "Ada")
    def test_display_with_email(self):
        self.assertEqual(service.display_name(service.make_user(1, "Ada", "a@x")), "Ada <a@x>")
