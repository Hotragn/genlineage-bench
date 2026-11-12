"""Hand-written service helpers on top of the generated protobuf messages."""
import os, sys
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "gen"))
from acct.v1 import user_pb2, team_pb2


def make_user(uid, name, email, role=user_pb2.MEMBER):
    return user_pb2.User(id=uid, name=name, email=email, role=role)


def display_name(user):
    """Return 'Name <email>' or just 'Name' when the email is empty."""
    return f"{user.name} <{user.email}>"


def admins(team):
    return [m for m in team.members if m.role == user_pb2.ADMIN]
