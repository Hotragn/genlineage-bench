import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "gen"))
from acct.v1 import user_pb2, team_pb2
from app import service
class T(unittest.TestCase):
    def test_make_user(self):
        u = service.make_user(1, "Ada", "ada@example.com")
        self.assertEqual(service.display_name(u), "Ada <ada@example.com>")
    def test_wire_roundtrip(self):
        u = user_pb2.User(id=7, name="Lin", email="lin@example.com")
        self.assertEqual(user_pb2.User.FromString(u.SerializeToString()).email, "lin@example.com")
    def test_admins(self):
        t = team_pb2.Team(id=1, title="core", members=[service.make_user(1, "A", "a@x", user_pb2.ADMIN), service.make_user(2, "B", "b@x")])
        self.assertEqual([m.name for m in service.admins(t)], ["A"])
