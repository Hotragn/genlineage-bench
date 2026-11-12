"""Render app/settings.py and app/flags.py from config/*.yaml using templates/*.j2."""
import os, yaml, jinja2
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
env = jinja2.Environment(loader=jinja2.FileSystemLoader(os.path.join(ROOT, "templates")), keep_trailing_newline=True)
ctx = {}
for name in ("settings", "features"):
    with open(os.path.join(ROOT, "config", name + ".yaml")) as f:
        ctx[name] = yaml.safe_load(f)
for tpl, out in (("settings.py.j2", "app/settings.py"), ("flags.py.j2", "app/flags.py")):
    text = env.get_template(tpl).render(**ctx)
    with open(os.path.join(ROOT, out), "w") as f:
        f.write(text)
