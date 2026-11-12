#!/usr/bin/env bash
# Real-repo driver: Gemma 4 E4B (local ollama, CPU), 4 real-repo tasks (bench/tasks_real) x
# natural,hint,headerguard,gate, one seed at a time (default 1 2 3), ONE shard. Lineage commands are SUPPLIED
# (--lin_commands task) and the inferred lineage is cached in results/lin_cache_real. Resumable; api_error cells are
# purged and retried (up to 3 attempts per seed).
# Usage: from the repository root, nohup bash scripts/real_driver.sh > ../logs/real/driver.log 2>&1 &
# Stop after the current seed: touch ../logs/real/STOP
set -u
BENCH="$(cd "$(dirname "$0")/.." && pwd)"; cd "$BENCH"
PY="${PY:-$BENCH/.venv/bin/python}"
LOGD="$BENCH/../logs/real"; mkdir -p "$LOGD"
MODEL="${MODEL:-g4-e4b-qat}"; TAG="${TAG:-real_e4b}"; SEEDS="${SEEDS:-1 2 3}"; CONDS="${CONDS:-natural,hint,headerguard,gate}"
for SEED in $SEEDS; do
  [ -e "$LOGD/STOP" ] && { echo "$(date -Is) STOP present"; break; }
  for attempt in 1 2 3; do
    "$PY" scripts/purge_errors.py "$BENCH/results/runs/$TAG"
    echo "$(date -Is) start seed=$SEED attempt=$attempt model=$MODEL conds=$CONDS"
    "$PY" scripts/run_grid.py --model "$MODEL" --tag "$TAG" --conds "$CONDS" --seeds "$SEED" --split real \
      --tasks_dir bench/tasks_real --order task_major --lin_commands task --lin_cache results/lin_cache_real >> "$LOGD/s${SEED}.log" 2>&1
    nerr=$("$PY" scripts/purge_errors.py "$BENCH/results/runs/$TAG" --dry | awk '{print $2}')
    echo "$(date -Is) seed=$SEED attempt=$attempt done; api_error cells: $nerr"
    [ "$nerr" = "0" ] && break; sleep 60
  done
done
echo "$(date -Is) REAL DRIVER finished"
