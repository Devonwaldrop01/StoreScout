#!/usr/bin/env bash
set -euo pipefail
test "$RELEASE_SHA" = "$APPROVED_SHA"
test "$(git rev-parse HEAD)" = "$RELEASE_SHA"
test -z "$(git status --porcelain)"
EVIDENCE="$RUNNER_TEMP/index-v2-evidence"
TESTDEPS="$RUNNER_TEMP/index-v2-testdeps"
mkdir -p "$EVIDENCE" "$TESTDEPS"
IMAGE="storescout-index-v2:$RELEASE_SHA"
python3 scripts/release_image_check.py inventory "$RELEASE_SHA" "$EVIDENCE/inventory.json"
docker build --platform linux/amd64 --target index-v2 --label "org.opencontainers.image.revision=$RELEASE_SHA" -t "$IMAGE" . 2>&1 | tee "$EVIDENCE/build.log"
docker image inspect "$IMAGE" > "$EVIDENCE/image.json"
test "$(docker image inspect "$IMAGE" --format '{{ index .Config.Labels "org.opencontainers.image.revision" }}')" = "$RELEASE_SHA"
test "$(docker image inspect "$IMAGE" --format '{{.Os}}/{{.Architecture}}')" = linux/amd64
test "$(docker image inspect "$IMAGE" --format '{{json .Config.Entrypoint}}')" = null
test "$(docker image inspect "$IMAGE" --format '{{json .Config.Cmd}}')" = '["./scripts/store_index_v2.py"]'
# Render's ordinary repository build preserves the legacy final target. Verify
# its filesystem matches V2 exactly, then test Render's simple command override.
RENDER_IMAGE="storescout-index-v2-render:$RELEASE_SHA"
docker build --platform linux/amd64 --label "org.opencontainers.image.revision=$RELEASE_SHA" -t "$RENDER_IMAGE" . 2>&1 | tee "$EVIDENCE/render-build.log"
test "$(docker image inspect "$IMAGE" --format '{{json .RootFS.Layers}}')" = "$(docker image inspect "$RENDER_IMAGE" --format '{{json .RootFS.Layers}}')"
test "$(docker image inspect "$RENDER_IMAGE" --format '{{json .Config.Entrypoint}}')" = null
docker image inspect "$RENDER_IMAGE" > "$EVIDENCE/render-image.json"
docker run --rm --network none -e PYTHONDONTWRITEBYTECODE=1 -v "$EVIDENCE/inventory.json:/validation/inventory.json:ro" "$IMAGE" python scripts/release_image_check.py verify /validation/inventory.json > "$EVIDENCE/inventory-packages.json"
docker run --rm --network none "$IMAGE" python -m pip check > "$EVIDENCE/pip-check.txt"
# Test tools only; never added to the release layers, no production secrets.
docker run --rm -v "$TESTDEPS:/testdeps" "$IMAGE" python -m pip install --target /testdeps pytest==9.1.1 iniconfig==2.3.0 pluggy==1.6.0 pygments==2.21.0 packaging==26.3
docker run --rm --network none --memory 512m --memory-swap 512m -e PYTHONDONTWRITEBYTECODE=1 -e PYTHONPATH=/testdeps:/app -v "$TESTDEPS:/testdeps:ro" "$IMAGE" python -m pytest tests -q -p no:cacheprovider 2>&1 | tee "$EVIDENCE/pytest.txt"
NAME="index-v2-disabled-${GITHUB_RUN_ID:-local}"
cleanup() { docker logs "$NAME" > "$EVIDENCE/disabled.log" 2>&1 || true; docker rm -f "$NAME" >/dev/null 2>&1 || true; }
trap cleanup EXIT
docker run -d --name "$NAME" --network none --memory 512m --memory-swap 512m -e INDEX_V2_ENABLED=false -e STORE_INDEX_DEPLOYMENT_HOLD=true "$RENDER_IMAGE" ./scripts/store_index_v2.py >/dev/null
for n in $(seq 1 12); do
  sleep 5
  test "$(docker inspect "$NAME" --format '{{.State.Running}}')" = true
  test "$(docker inspect "$NAME" --format '{{.RestartCount}}')" = 0
done
docker exec "$NAME" python -c 'from pathlib import Path; p=Path("/proc/1/cmdline").read_bytes().split(b"\0"); assert b"python" in p[0] and b"-c" not in p; assert not Path("/var/data/store-index-v2.sqlite").exists(); print(p)' > "$EVIDENCE/process.txt"
docker logs "$NAME" > "$EVIDENCE/disabled.log"
grep -F 'STORE_INDEX_V2 disabled; no jobs or application initialized' "$EVIDENCE/disabled.log"
docker stop --time 10 "$NAME" >/dev/null
test "$(docker inspect "$NAME" --format '{{.State.ExitCode}}')" = 0
docker inspect "$NAME" > "$EVIDENCE/stopped.json"
docker save "$IMAGE" "$RENDER_IMAGE" | gzip -1 > "$EVIDENCE/image.tar.gz"
sha256sum "$EVIDENCE/image.tar.gz" > "$EVIDENCE/archive.sha256"
printf '%s\n' "$RELEASE_SHA" > "$EVIDENCE/release-sha.txt"
