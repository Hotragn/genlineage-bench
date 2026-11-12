#!/usr/bin/env bash
# Reproduce GenLineage-Bench end to end on a Linux machine with Python 3.13.
#   ./reproduce.sh validate          # rebuild + validate all 26 tasks (CPU, ~25 s)
#   ./reproduce.sh validate-real     # fetch the pinned yt-dlp files, then validate the 4 real-repository tasks (CPU, ~1 min)
#   ./reproduce.sh guard-tests       # survival-gate unit checks (CPU, ~10 s)
#   ./reproduce.sh realrepo          # lineage inference on 4 OSS repos (CPU, ~2 min; clones from GitHub)
#   ./reproduce.sh grid MODEL TAG    # agent grid against a local ollama server (GPU recommended)
#   ./reproduce.sh analyze           # metrics, paired tests and exploratory figures from results/runs
#   ./reproduce.sh figures           # the four paper figures into paper/figures (CPU, ~20 s)
#   ./reproduce.sh paper             # recompute every paper number from raw logs and verify paper/writeup.md
set -euo pipefail
cd "$(dirname "$0")"
VENV=${VENV:-.venv}
if [ ! -x "$VENV/bin/python" ]; then
  (python3 -m venv "$VENV" 2>/dev/null && "$VENV/bin/python" -m pip -q install -r genlineage/requirements.txt -r requirements-analysis.txt) || \
  (pip install -q uv && uv venv "$VENV" --python 3.13 && uv pip install -q --python "$VENV/bin/python" -r genlineage/requirements.txt -r requirements-analysis.txt)
fi
PY="$VENV/bin/python"; export PATH="$PWD/bin:$PATH" PYTHONHASHSEED=0
case "${1:-validate}" in
  validate) "$PY" bench/build.py --validate-only | tail -1 ;;
  fetch-real) "$PY" bench/fetch_real.py ;;
  validate-real) "$PY" bench/fetch_real.py && "$PY" bench/validate_real.py ;;
  guard-tests) "$PY" tests/test_lineage_guard.py ;;
  realrepo)
    export REALREPOS=${REALREPOS:-$PWD/.realrepos}; mkdir -p "$REALREPOS"
    for r in aio-libs/aiohttp psf/black Textualize/rich pygments/pygments; do n=$(basename $r); [ -d "$REALREPOS/$n" ] || git clone -q --depth 1 "https://github.com/$r" "$REALREPOS/$n"; done; [ -d "$REALREPOS/grpc" ] || (git clone -q --depth 1 --filter=blob:none --sparse https://github.com/grpc/grpc "$REALREPOS/grpc" && git -C "$REALREPOS/grpc" sparse-checkout set examples/python/helloworld examples/protos)
    "$PY" -m pip -q install multidict click wcwidth 2>/dev/null || uv pip install -q --python "$PY" multidict click wcwidth
    "$PY" realrepo/real_lineage.py aiohttp black rich pygments grpc > realrepo/res_all.json ;;
  grid) "$PY" scripts/run_grid.py --model "${2:?model}" --tag "${3:?tag}" --split test --order task_major --seeds "${4:-1}" ;;
  analyze) "$PY" scripts/analyze.py && "$PY" scripts/make_figures.py ;;
  figures) "$PY" scripts/fig_diagrams.py && "$PY" scripts/paper_figures.py && "$PY" scripts/fig_aidev.py ;;
  paper) "$PY" scripts/check_claims.py ;;
  *) echo "unknown command"; exit 2 ;;
esac
