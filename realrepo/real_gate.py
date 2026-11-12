"""Survival gate (component G) on real repositories: an edit to a generated output should be rejected
(regeneration reverts it); an edit to a hand-written file should be admitted. Uses genlineage.lineage.edit_survives."""
import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from genlineage.lineage import edit_survives
ROOT = os.environ.get("REALREPOS", os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".realrepos")); PY = sys.executable
CASES = [
 ("pygments", f"{PY} scripts/gen_mapfiles.py", "pygments/lexers/_mapping.py", "'PythonLexer'", "'PythonLexerX'", False),
 ("pygments", f"{PY} scripts/gen_mapfiles.py", "README.rst", "Pygments", "Pygments!", True),
 ("black", f"PYTHONPATH=src {PY} scripts/generate_schema.py --outfile src/black/resources/black.schema.json", "src/black/resources/black.schema.json", '"integer"', '"number"', False),
 ("grpc", f"cd examples/python/helloworld && {PY} -m grpc_tools.protoc -I../../protos --python_out=. --pyi_out=. --grpc_python_out=. ../../protos/helloworld.proto", "examples/python/helloworld/helloworld_pb2_grpc.py", "SayHello", "SayHelo", False),
 ("grpc", f"cd examples/python/helloworld && {PY} -m grpc_tools.protoc -I../../protos --python_out=. --pyi_out=. --grpc_python_out=. ../../protos/helloworld.proto", "examples/python/helloworld/greeter_server.py", "Hello", "Hi", True),
]
out = []
for repo, cmd, rel, a, b, expect in CASES:
    r = os.path.join(ROOT, repo); old = open(os.path.join(r, rel)).read(); assert a in old, (repo, rel, a)
    ok, detail = edit_survives(r, cmd, rel, old.replace(a, b, 1), old)
    out.append(dict(repo=repo, file=rel, edit=f"{a} -> {b}", survives=ok, expected=expect, detail=detail[:160])); print(out[-1], flush=True)
json.dump(out, open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "res_gate.json"), "w"), indent=1)
print(sum(o["survives"] == o["expected"] for o in out), "/", len(out), "as expected")
