import os, subprocess, sys
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PYBIN = os.path.dirname(os.path.realpath(sys.executable)) if os.environ.get("GL_USE_SYS_PY") else os.path.dirname(sys.executable)
ENV = dict(os.environ, PYTHONDONTWRITEBYTECODE="1", PYTHONHASHSEED="0", PYTHONWARNINGS="ignore",
           PATH=os.pathsep.join([os.path.join(ROOT, "bin"), PYBIN, os.environ.get("PATH", "")]))
if not any(os.access(os.path.join(p, "make"), os.X_OK) for p in os.environ.get("PATH", "").split(os.pathsep) if p and "genlineage" not in p):
    pass  # bin/make shim is first on PATH anyway

def sh(cmd, cwd, timeout=120):
    try:
        r = subprocess.run(cmd, shell=True, cwd=cwd, env=ENV, capture_output=True, text=True, timeout=timeout)
        return r.returncode, (r.stdout + r.stderr)
    except subprocess.TimeoutExpired:
        return 124, "TIMEOUT"

TEST_CMD = "python -m unittest discover -s tests -v"
