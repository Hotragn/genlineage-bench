"""Generate db/models.py from db/schema.sql (CREATE TABLE statements)."""
import os, re
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TYPES = {"INTEGER": "int", "TEXT": "str", "BOOLEAN": "bool", "TIMESTAMP": "str", "NUMERIC": "float"}
sql = open(os.path.join(ROOT, "db/schema.sql")).read()
out = ["# Database row models.", "from dataclasses import dataclass", "from typing import Optional", ""]
for table, body in re.findall(r"CREATE TABLE (\w+) \((.*?)\);", sql, re.S):
    cls = "".join(p.capitalize() for p in table.split("_"))
    out += ["", "@dataclass", f"class {cls}:"]
    req, opt = [], []
    for col in [c.strip() for c in body.split(",\n") if c.strip()]:
        name, typ = col.split()[:2]
        py = TYPES[typ.upper()]
        if "NOT NULL" in col.upper():
            req.append(f"    {name}: {py}")
        else:
            opt.append(f"    {name}: Optional[{py}] = None")
    out += req + opt + [""]
open(os.path.join(ROOT, "db/models.py"), "w").write("\n".join(out))
