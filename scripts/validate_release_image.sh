#!/usr/bin/env bash
set -euo pipefail
test "$(git rev-parse HEAD)" = "$RELEASE_SHA"
test -z "$(git status --porcelain)"
TASK_TMP="$RUNNER_TEMP/storescout-release"
EVIDENCE="$RUNNER_TEMP/release-evidence"
mkdir -p "$TASK_TMP" "$EVIDENCE" "$TASK_TMP/testdeps" "$TASK_TMP/tls" "$TASK_TMP/sql"
IMAGE="storescout-release:$RELEASE_SHA"
NETWORK="storescout-release-${GITHUB_RUN_ID}"
export PYTHONDONTWRITEBYTECODE=1
python3 scripts/release_image_check.py inventory "$RELEASE_SHA" "$TASK_TMP/inventory.json"
docker build --platform linux/amd64 --label "org.opencontainers.image.revision=$RELEASE_SHA" -t "$IMAGE" . 2>&1 | tee "$EVIDENCE/build.log"
docker image inspect "$IMAGE" > "$EVIDENCE/image.json"
test "$(docker image inspect "$IMAGE" --format '{{ index .Config.Labels "org.opencontainers.image.revision" }}')" = "$RELEASE_SHA"
test "$(docker image inspect "$IMAGE" --format '{{.Os}}/{{.Architecture}}')" = 'linux/amd64'
docker run --rm --network none -e PYTHONDONTWRITEBYTECODE=1 -v "$TASK_TMP/inventory.json:/validation/inventory.json:ro" "$IMAGE" python scripts/release_image_check.py verify /validation/inventory.json | tee "$EVIDENCE/inventory-packages.json"
docker run --rm --network none "$IMAGE" python -m pip check | tee "$EVIDENCE/pip-check.txt"

# Test-only packages are mounted; they never alter the release image layers.
docker run --rm -v "$TASK_TMP/testdeps:/testdeps" "$IMAGE" python -m pip install --target /testdeps pytest==9.1.1 iniconfig==2.3.0 pluggy==1.6.0 pygments==2.21.0 packaging==26.3
docker run --rm --network none -e PYTHONDONTWRITEBYTECODE=1 -e PYTHONPATH=/testdeps:/app -v "$TASK_TMP/testdeps:/testdeps:ro" "$IMAGE" python -m pytest tests -q -p no:cacheprovider 2>&1 | tee "$EVIDENCE/pytest.txt"

cp config/release-validation/package*.json "$TASK_TMP/sql/"
npm ci --prefix "$TASK_TMP/sql" --ignore-scripts --no-audit --no-fund
NODE_BIN="$(readlink -f "$(command -v node)")"
for check in verification_schema deployed_schema_compatibility; do
  docker run --rm --network none -v "$NODE_BIN:/validation/node:ro" -v "$TASK_TMP/sql:/app/outputs/phase1/sql-runtime:ro" -v "$PWD/docs/quality-audit:/app/docs/quality-audit:ro" "$IMAGE" /validation/node "tests/${check}.mjs" | tee "$EVIDENCE/${check}.json"
done

# Self-signed test CA, test-only Redis, no route out of the internal network.
openssl req -x509 -newkey rsa:2048 -nodes -days 1 -subj '/CN=redis' -addext 'subjectAltName=DNS:redis' -keyout "$TASK_TMP/tls/key.pem" -out "$TASK_TMP/tls/cert.pem" 2>/dev/null
chmod 644 "$TASK_TMP/tls/key.pem"
docker pull redis:7.4.2 > "$EVIDENCE/test-redis-pull.txt"
docker image inspect redis:7.4.2 > "$EVIDENCE/test-redis-image.json"
docker network create --internal "$NETWORK" >/dev/null
cleanup() {
  for name in release-web release-worker release-beat release-redis; do
    docker logs "$name" > "$EVIDENCE/$name.log" 2>&1 || true
    docker rm -f "$name" >/dev/null 2>&1 || true
  done
  docker network rm "$NETWORK" >/dev/null 2>&1 || true
}
trap cleanup EXIT
docker run -d --name release-redis --network "$NETWORK" --network-alias redis -v "$TASK_TMP/tls:/tls:ro" redis:7.4.2 redis-server --port 0 --tls-port 6379 --tls-cert-file /tls/cert.pem --tls-key-file /tls/key.pem --tls-ca-cert-file /tls/cert.pem --tls-auth-clients no --save '' --appendonly no >/dev/null
TEST_ENV=(--network "$NETWORK" -v "$TASK_TMP/tls/cert.pem:/tls/cert.pem:ro" -e PYTHONDONTWRITEBYTECODE=1 -e PYTHONPATH=/app -e 'REDIS_URL=rediss://redis:6379/0?ssl_cert_reqs=required&ssl_check_hostname=true&ssl_ca_certs=/tls/cert.pem' -e SUPABASE_URL=https://offline.invalid -e SUPABASE_SERVICE_ROLE_KEY=offline-test -e API_INTERNAL_URL=http://web:10000 -e INTERNAL_SECRET=offline-test -e ANTHROPIC_API_KEY= -e STORE_INDEX_CANARY_ENABLED=false)
docker run -d --name release-web --network-alias web "${TEST_ENV[@]}" "$IMAGE" uvicorn app.main:app --host 0.0.0.0 --port 10000 >/dev/null
docker run -d --name release-worker "${TEST_ENV[@]}" "$IMAGE" celery -A app.tasks.celery_app.celery worker --loglevel=info -Q default,priority --concurrency=2 >/dev/null
docker run -d --name release-beat "${TEST_ENV[@]}" "$IMAGE" celery -A app.tasks.celery_app.celery beat --loglevel=info >/dev/null
docker run --rm "${TEST_ENV[@]}" "$IMAGE" python scripts/release_runtime_check.py | tee "$EVIDENCE/runtime.json"
for name in release-web release-worker release-beat; do
  test "$(docker inspect "$name" --format '{{.State.Running}}')" = true
  docker logs "$name" > "$EVIDENCE/$name.log" 2>&1
  if grep -Ei 'Traceback|CERT_NONE|CERTIFICATE_VERIFY_FAILED|lock unavailable|duplicate key|ERROR|CRITICAL' "$EVIDENCE/$name.log"; then exit 1; fi
done
grep -F 'beat: Starting' "$EVIDENCE/release-beat.log"
# Export a reusable immutable release artifact, without test mounts or credentials.
docker save "$IMAGE" | gzip -1 > "$EVIDENCE/release-image.tar.gz"
sha256sum "$EVIDENCE/release-image.tar.gz" > "$EVIDENCE/release-image.sha256"
printf '%s\n' "$RELEASE_SHA" > "$EVIDENCE/release-sha.txt"
