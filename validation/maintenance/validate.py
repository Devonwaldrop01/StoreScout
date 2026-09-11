"""Run only the digest-verified retained image; never builds or deploys an image."""
import ast
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import time

SHA = "667dea6e3eb35c53116e349758d4606e08a5adb0"
IMAGE = "sha256:b55cac6642281d6d755b43144dab4639e2fcc18accee69ae1fb1b8240ac9ca6a"
ROOT = Path(__file__).resolve().parent
TEMP = Path(os.environ["RUNNER_TEMP"])
EVIDENCE = TEMP / "maintenance-evidence"
RETAINED = TEMP / "retained-release"
NET = "maintenance-validation-" + os.environ["GITHUB_RUN_ID"]
names = []
results = {"image_id": IMAGE, "release_sha": SHA, "inert": {}, "restored": {}, "shutdown": {}}

def run(*args, timeout=120):
    p = subprocess.run(list(args), text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout)
    if p.returncode:
        raise AssertionError({"command": list(args)[:5], "exit": p.returncode,
                              "stdout": p.stdout[-3000:], "stderr": p.stderr[-3000:]})
    return p.stdout.strip()

def docker(*args, **kw):
    return run("docker", *args, **kw)

def inspect(name):
    return json.loads(docker("inspect", name))[0]

def logs(name):
    p = subprocess.run(["docker", "logs", name], capture_output=True, text=True)
    return p.stdout + p.stderr

def start(name, argv, env, network="none", extra=()):
    args = ["run", "-d", "--name", name, "--network", network,
            "--mount", f"type=bind,src={ROOT},dst=/validation,readonly"]
    for k, v in env.items():
        args += ["-e", k + "=" + v]
    docker(*args, *extra, IMAGE, *argv)
    names.append(name)
    info = inspect(name)
    assert info["Image"] == IMAGE
    assert info["Config"]["Cmd"] == argv
    assert not any("TOKEN=" in x or "RENDER_API" in x for x in info["Config"]["Env"])
    return info

def stop_clean(name, signal="SIGTERM", bound=30):
    begun = time.monotonic()
    docker("kill", "--signal", signal, name)
    code = int(docker("wait", name, timeout=bound))
    elapsed = round(time.monotonic() - begun, 3)
    assert code == 0 and elapsed < bound, (name, code, elapsed)
    assert not inspect(name)["State"]["OOMKilled"]
    results["shutdown"][name + "-" + signal] = {"signal": signal, "exit_code": code, "seconds": elapsed}

commands = {}
for mode in ("web", "idle"):
    source = (ROOT / (mode + ".py")).read_text()
    imports = []
    for n in ast.walk(ast.parse(source)):
        if isinstance(n, ast.Import):
            imports.extend(a.name for a in n.names)
        elif isinstance(n, ast.ImportFrom):
            imports.append(n.module)
    assert set(imports) <= {"os", "signal", "threading", "http.server"}
    argv = ["python", "-I", "-S", "-B", "-u", "-c", source]
    command = shlex.join(argv)
    assert shlex.split(command) == argv
    commands[mode] = {"argv": argv, "linux_command": command,
                      "source_sha256": hashlib.sha256(source.encode()).hexdigest(), "imports": imports}
normal = {
    "web": ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "10000"],
    "worker": ["celery", "-A", "app.tasks.celery_app.celery", "worker", "--loglevel=info", "-Q", "default,priority", "--concurrency=2"],
    "beat": ["celery", "-A", "app.tasks.celery_app.celery", "beat", "--loglevel=info"],
}
commands["restored"] = normal
(EVIDENCE / "commands.json").write_text(json.dumps(commands, indent=2))

try:
    docker("load", "-i", str(RETAINED / "release-image.tar.gz"), timeout=300)
    image = json.loads(docker("image", "inspect", IMAGE))[0]
    assert image["Id"] == IMAGE and image["Os"] == "linux" and image["Architecture"] == "amd64"
    assert image["Config"]["Labels"]["org.opencontainers.image.revision"] == SHA
    (EVIDENCE / "image.json").write_text(json.dumps(image, indent=2))
    # Generate expected inventory from a detached checkout of the RELEASE, not
    # the validation branch, and compare using code already in the retained image.
    checkout = TEMP / "approved-source"
    run("git", "worktree", "add", "--detach", str(checkout), SHA)
    inventory = TEMP / "approved-inventory.json"
    p = subprocess.run(["python3", "scripts/release_image_check.py", "inventory", SHA, str(inventory)], cwd=checkout)
    assert p.returncode == 0
    out = docker("run", "--rm", "--network", "none", "-e", "PYTHONDONTWRITEBYTECODE=1",
                 "-v", f"{inventory}:/validation/inventory.json:ro", IMAGE,
                 "python", "scripts/release_image_check.py", "verify", "/validation/inventory.json")
    current_inventory = json.loads(out)
    original_inventory = json.loads((RETAINED / "inventory-packages.json").read_text())
    assert current_inventory == original_inventory
    (EVIDENCE / "inventory-packages.json").write_text(out)
    (EVIDENCE / "pip-check.txt").write_text(docker("run", "--rm", "--network", "none", IMAGE, "python", "-m", "pip", "check"))

    # Docker can add the bind-mount target itself to the writable layer even
    # when the process has a read-only root. Measure that with an inert control.
    start("inert-control", ["python", "-I", "-S", "-B", "-c", "pass"],
          {"PORT": "10000"}, extra=("--read-only",))
    assert int(docker("wait", "inert-control")) == 0
    mount_baseline = docker("diff", "inert-control")
    results["docker_mount_baseline"] = mount_baseline
    assert all(l in ("A /validation",) for l in mount_baseline.splitlines()), mount_baseline
    for role in ("beat", "worker", "web"):
        name = "inert-" + role
        argv = commands["web" if role == "web" else "idle"]["argv"]
        start(name, argv, {"PORT": "10000"}, extra=("--read-only",))
        for _ in range(30):
            if "application not imported" in logs(name):
                break
            time.sleep(0.2)
        assert "application not imported" in logs(name)
        assert inspect(name)["State"]["Running"]
        top = docker("top", name, "-eo", "pid,comm")
        assert len(top.splitlines()) == 2, top  # Only PID 1, no worker children.
        if role == "web":
            check = """import http.client,json,socket
with socket.create_connection(('127.0.0.1',10000),timeout=2): pass
for method,path in [('GET','/'),('HEAD','/'),('POST','/api/v1/internal/store-index/verify'),('GET','/.env'),('GET','/../Dockerfile'),('PATCH','/'),('DELETE','/'),('OPTIONS','/')]:
 c=http.client.HTTPConnection('127.0.0.1',10000,timeout=2);c.request(method,path);r=c.getresponse();b=r.read();assert r.status==503 and r.getheader('Retry-After')=='60';assert b==(b'' if method=='HEAD' else b'StoreScout maintenance. Please retry later.\\n');c.close()
print('8 maintenance responses passed')"""
            results["inert"][role] = docker("exec", name, "python", "-I", "-S", "-B", "-c", check)
        else:
            results["inert"][role] = "one idle process, no network, no application startup"
        assert docker("diff", name) == mount_baseline, docker("diff", name)
        stop_clean(name)
        assert "clean exit" in logs(name)
        # Restart the same command, then exercise SIGINT as a second clean path.
        docker("start", name)
        time.sleep(1)
        stop_clean(name, "SIGINT")
        assert docker("diff", name) == mount_baseline, docker("diff", name)

    tls = TEMP / "maintenance-tls"
    tls.mkdir(exist_ok=True)
    run("openssl", "req", "-x509", "-newkey", "rsa:2048", "-nodes", "-days", "1", "-subj", "/CN=redis",
        "-addext", "subjectAltName=DNS:redis", "-keyout", str(tls / "key.pem"), "-out", str(tls / "cert.pem"))
    (tls / "key.pem").chmod(0o644)
    redis_info = json.loads((RETAINED / "test-redis-image.json").read_text())[0]
    redis_ref = redis_info["RepoDigests"][0]
    docker("pull", redis_ref, timeout=180)
    results["test_redis_digest"] = redis_ref
    docker("network", "create", "--internal", NET)
    assert inspect(NET)["Internal"]
    docker("run", "-d", "--name", "test-redis", "--network", NET, "--network-alias", "redis",
           "-v", f"{tls}:/tls:ro", redis_ref, "redis-server", "--port", "0", "--tls-port", "6379",
           "--tls-cert-file", "/tls/cert.pem", "--tls-key-file", "/tls/key.pem",
           "--tls-ca-cert-file", "/tls/cert.pem", "--tls-auth-clients", "no", "--save", "", "--appendonly", "no")
    names.append("test-redis")
    start("dbsink", ["python", "-I", "-S", "-B", "-u", "/validation/sink.py"], {}, NET)
    env = {"PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": "/app", "PORT": "10000",
           "REDIS_URL": "rediss://redis:6379/0?ssl_cert_reqs=required&ssl_check_hostname=true&ssl_ca_certs=/tls/cert.pem",
           "SUPABASE_URL": "http://dbsink:8080", "SUPABASE_SERVICE_ROLE_KEY": "offline-test",
           "API_INTERNAL_URL": "http://web:10000", "INTERNAL_SECRET": "offline-test",
           "ANTHROPIC_API_KEY": "", "STORE_INDEX_CANARY_ENABLED": "false", "STORE_INDEX_DEPLOYMENT_HOLD": "true"}
    for role in ("web", "worker", "beat"):
        start("normal-" + role, normal[role], env, NET,
              extra=("--network-alias", role, "-v", f"{tls / 'cert.pem'}:/tls/cert.pem:ro"))
    output = docker("exec", "normal-web", "python", "/validation/runtime_check.py", timeout=90)
    checks = json.loads(output.splitlines()[-1])
    results["restored"] = checks
    for _ in range(40):
        log = logs("normal-worker")
        if all(f"[{task_id}] succeeded" in log for task_id in checks["delivery_ids"]):
            break
        time.sleep(0.25)
    for task_id in checks["delivery_ids"]:
        lines = [l for l in logs("normal-worker").splitlines() if f"[{task_id}] succeeded" in l]
        assert len(lines) == 1 and "deployment_hold" in lines[0], (task_id, lines)
    for role in ("web", "worker", "beat"):
        assert inspect("normal-" + role)["State"]["Running"]
    assert "beat: Starting" in logs("normal-beat")
    # Stop publishing first; then graceful worker shutdown; web last.
    for role in ("beat", "worker", "web"):
        stop_clean("normal-" + role)
    requests = docker("exec", "dbsink", "python", "-I", "-S", "-B", "-c",
                      "from pathlib import Path;p=Path('/tmp/requests.jsonl');print(p.read_text() if p.exists() else '')")
    recorded = [json.loads(l) for l in requests.splitlines() if l]
    protected = ("shopify_store_index", "discovery_queue", "discovery_cursors", "store_index_runs", "competitor_edges")
    assert not [r for r in recorded if r["method"] != "GET" and any(t in r["path"] for t in protected)], recorded
    results["fake_db_requests"] = recorded
    for role in ("web", "worker", "beat"):
        log = logs("normal-" + role)
        assert not any(x in log for x in ("CERT_NONE", "CERTIFICATE_VERIFY_FAILED", "single-flight lock unavailable", "duplicate key")), log
        diff = docker("diff", "normal-" + role)
        assert not any(l.endswith((".py", ".sql", "verification-canary.json")) for l in diff.splitlines()), diff
        (EVIDENCE / ("normal-" + role + "-diff.txt")).write_text(diff)
    assert json.loads(docker("image", "inspect", IMAGE))[0]["Id"] == IMAGE
    results["passed"] = True
finally:
    for name in names:
        (EVIDENCE / (name + ".log")).write_text(logs(name))
        try:
            (EVIDENCE / (name + "-diff.txt")).write_text(docker("diff", name))
            (EVIDENCE / (name + "-inspect.json")).write_text(json.dumps(inspect(name), indent=2))
        except Exception:
            pass
        subprocess.run(["docker", "rm", "-f", name], capture_output=True)
    subprocess.run(["docker", "network", "rm", NET], capture_output=True)
    (EVIDENCE / "results.json").write_text(json.dumps(results, indent=2))
    print(json.dumps(results, indent=2))
