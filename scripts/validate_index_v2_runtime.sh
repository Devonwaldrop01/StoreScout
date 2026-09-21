#!/usr/bin/env bash
# Exact production entrypoint, synthetic saved catalog, persistent local volume.
set -euo pipefail
IMAGE="$1"; EVIDENCE="$2"; TESTDEPS="$3"
DATA="$RUNNER_TEMP/index-v2-synthetic-data"
mkdir -p "$DATA"
NAME="index-v2-runtime-${GITHUB_RUN_ID:-local}"
cleanup_runtime() { docker logs "$NAME" > "$EVIDENCE/runtime-last.log" 2>&1 || true; docker rm -f "$NAME" >/dev/null 2>&1 || true; }
trap cleanup_runtime EXIT
docker run --rm --network none --memory 512m --memory-swap 512m -e PYTHONDONTWRITEBYTECODE=1 -e PYTHONPATH=/testdeps:/app -v "$TESTDEPS:/testdeps:ro" -v "$DATA:/var/data" "$IMAGE" python tests/evaluations/index_v2_runtime_fixture.py prepare
BATCH="$(cat "$DATA/batch")"
for phase in first restart; do
  docker run -d --name "$NAME" --network none --memory 512m --memory-swap 512m -e PYTHONDONTWRITEBYTECODE=1 -e INDEX_V2_ENABLED=true -e INDEX_V2_MANIFEST_SHA256="$BATCH" -e STORE_INDEX_DEPLOYMENT_HOLD=true -v "$DATA:/var/data" "$IMAGE" ./scripts/store_index_v2.py >/dev/null
  date -u +%FT%TZ > "$EVIDENCE/runtime-$phase-start.txt"
  if [ "$phase" = first ]; then samples=60; else samples=12; fi
  for n in $(seq 1 "$samples"); do
    sleep 5
    test "$(docker inspect "$NAME" --format '{{.State.Running}}')" = true
    test "$(docker inspect "$NAME" --format '{{.RestartCount}}')" = 0
    docker stats --no-stream --format '{{json .}}' "$NAME" >> "$EVIDENCE/runtime-$phase-stats.jsonl"
  done
  docker exec "$NAME" python -c 'from pathlib import Path; p=Path("/proc/1/cmdline").read_bytes().split(b"\0"); assert b"python" in p[0] and b"-c" not in p and any(b"store_index_v2.py" in x for x in p); print(p)' > "$EVIDENCE/runtime-$phase-process.txt"
  docker exec "$NAME" python tests/evaluations/index_v2_runtime_fixture.py check > "$EVIDENCE/runtime-$phase-state.json"
  docker logs "$NAME" > "$EVIDENCE/runtime-$phase.log"
  docker stop --time 10 "$NAME" >/dev/null
  test "$(docker inspect "$NAME" --format '{{.State.ExitCode}}')" = 0
  test "$(docker inspect "$NAME" --format '{{.State.OOMKilled}}')" = false
  docker inspect "$NAME" > "$EVIDENCE/runtime-$phase-stopped.json"
  date -u +%FT%TZ > "$EVIDENCE/runtime-$phase-end.txt"
  docker rm "$NAME" >/dev/null
done
trap - EXIT
