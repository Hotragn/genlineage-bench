"""Regenerates orders/status.py from data/order_status.csv."""
import csv, os
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
with open(os.path.join(ROOT, "data/order_status.csv")) as f:
    rows = list(csv.DictReader(f))
lines = ["# Order status codes.", "import enum", "", "", "class OrderStatus(enum.IntEnum):"]
for r in rows:
    lines.append(f"    {r['name']} = {int(r['code'])}")
lines += ["", "", "TERMINAL = frozenset({" + ", ".join(f"OrderStatus.{r['name']}" for r in rows if r['terminal'] == 'no') + "})", ""]
with open(os.path.join(ROOT, "orders/status.py"), "w") as f:
    f.write("\n".join(lines))
