#!/usr/bin/env bash
# Signal-ladder driver: natural condition, Gemma 4 E4B, 39 ladder variants (13 tasks x L0/L1/L2),
# seed 1 then seed 2. Resumable (run_grid.py skips cells with transcript.json); api_error cells are purged and retried.
# Usage: from the repository root, nohup bash scripts/ladder_driver.sh > ../logs/ladder_driver.log 2>&1 &
# Stop after the current seed: touch ../logs/ladder/STOP
set -u
BENCH="$(cd "$(dirname "$0")/.." && pwd)"; cd "$BENCH"
PY="${PY:-$BENCH/.venv/bin/python}"
LOGD="$BENCH/../logs/ladder"; mkdir -p "$LOGD"
NSHARD="${NSHARD:-2}"; MODEL="${MODEL:-g4-e4b-qat}"; TAG="${TAG:-ladder_e4b}"; SEEDS="${SEEDS:-1 2}"
for SEED in $SEEDS; do
  [ -e "$LOGD/STOP" ] && { echo "$(date -Is) STOP present"; break; }
  for attempt in 1 2 3; do
    "$PY" scripts/purge_errors.py "$BENCH/results/runs/$TAG"
    echo "$(date -Is) start seed=$SEED attempt=$attempt nshard=$NSHARD model=$MODEL"
    pids=()
    for ((k=0; k<NSHARD; k++)); do
      "$PY" scripts/run_grid.py --model "$MODEL" --tag "$TAG" --conds natural --seeds "$SEED" --split test \
        --tasks_dir bench/tasks_ladder --order task_major --shard "$k/$NSHARD" >> "$LOGD/s${SEED}_shard${k}.log" 2>&1 &
      pids+=($!); sleep 15
    done
    for p in "${pids[@]}"; do wait "$p"; done
    nerr=$("$PY" scripts/purge_errors.py "$BENCH/results/runs/$TAG" --dry | awk '{print $2}')
    echo "$(date -Is) seed=$SEED attempt=$attempt done; api_error cells: $nerr"
    [ "$nerr" = "0" ] && break; sleep 60
  done
done
echo "$(date -Is) LADDER DRIVER finished"
