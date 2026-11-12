import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "gen"))
from acct.v1 import user_pb2, team_pb2
from app import service
class T(unittest.TestCase):
    def test_auditor_role(self):
        self.assertEqual(user_pb2.AUDITOR, 3)
        u = service.make_user(3, "Kim", "kim@example.com", user_pb2.AUDITOR)
        self.assertEqual(user_pb2.User.FromString(u.SerializeToString()).role, 3)
        self.assertEqual(user_pb2.Role.Name(3), "AUDITOR")
    def test_admin_role(self):
        self.assertEqual(user_pb2.ADMIN, 2)
