"""Run only the digest-verified retained image; never builds or deploys an image."""
import ast
import hashlib
import json
import os
from pathlib import Path
import shlex
import subprocess
import time
from single_line import build, encode

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

SHELL_PROGRAM = "stop() { trap \"\" TERM INT; kill \"$child\" 2>/dev/null; wait \"$child\" 2>/dev/null; echo \"STORE_INDEX_MAINTENANCE_BRIDGE clean exit\"; exit 0; }; sleep infinity & child=$!; trap stop TERM INT; echo \"STORE_INDEX_MAINTENANCE_BRIDGE idle; application not imported\"; wait \"$child\"; exit 1"
RENDER_COMMAND = "/bin/sh -c '" + SHELL_PROGRAM + "'"
assert shlex.split(RENDER_COMMAND) == ["/bin/sh", "-c", SHELL_PROGRAM]
assert not any(c in RENDER_COMMAND for c in "\r\n\t\x00")
commands = {"render_command": RENDER_COMMAND, "argv": shlex.split(RENDER_COMMAND),
            "command_sha256": hashlib.sha256(RENDER_COMMAND.encode()).hexdigest()}
(EVIDENCE / "render-beat-command.txt").write_text(RENDER_COMMAND)
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
    # Render documents /bin/sh -c for shell commands. Test the exact submitted
    # text via POSIX tokenization, and through an additional outer POSIX shell.
    # The maintenance payload itself is shell + sleep, never Python/app code.
    results["shell_contract"] = {"render_command": RENDER_COMMAND,
        "argv": shlex.split(RENDER_COMMAND), "new_release_required": False}
    for transport in ("documented-argv", "outer-shell"):
        argv = (shlex.split(RENDER_COMMAND) if transport == "documented-argv"
                else ["/bin/sh", "-c", "exec " + RENDER_COMMAND])
        for value in (None, "true", "", "unknown", "false"):
            suffix = "missing" if value is None else value or "empty"
            name = "shell-" + transport + "-" + suffix
            env = {"STORE_INDEX_CANARY_ENABLED": "false",
                   "PYTHONPATH": "/must-not-be-imported"}
            if value is not None:
                env["STORE_INDEX_DEPLOYMENT_HOLD"] = value
            start(name, argv, env, extra=("--read-only",))
            for _ in range(30):
                if "application not imported" in logs(name):
                    break
                time.sleep(0.2)
            assert "application not imported" in logs(name)
            time.sleep(2)
            assert inspect(name)["State"]["Running"]
            top = docker("top", name, "-eo", "pid,comm")
            process_names = sorted(line.split()[-1] for line in top.splitlines()[1:])
            assert process_names == ["sh", "sleep"], top
            assert docker("diff", name) == mount_baseline
            assert inspect(name)["HostConfig"]["NetworkMode"] == "none"
            results["inert"][name] = {"processes": process_names,
                "network": "none", "hold": value, "app_initializations": 0}
            stop_clean(name)
            assert "clean exit" in logs(name)
            assert inspect(name)["State"]["Running"] is False
            docker("start", name)
            time.sleep(1)
            assert inspect(name)["State"]["Running"]
            stop_clean(name, "SIGINT")
            assert logs(name).count("clean exit") == 2
            assert docker("diff", name) == mount_baseline

    # The wait child must not silently disappear while the container looks live.
    # Kill ONLY the disposable test container's sleep process from inside it.
    start("shell-child-failure", shlex.split(RENDER_COMMAND),
          {"STORE_INDEX_DEPLOYMENT_HOLD": "true"}, extra=("--read-only",))
    time.sleep(1)
    child_probe = """from pathlib import Path
import os,signal
children=Path('/proc/1/task/1/children').read_text().split()
assert len(children)==1
os.kill(int(children[0]),signal.SIGTERM)
"""
    docker("exec", "shell-child-failure", "python", "-I", "-S", "-B", "-c", child_probe)
    assert int(docker("wait", "shell-child-failure", timeout=10)) == 1
    results["child_failure"] = "unexpected sleep exit terminates container with status 1"

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
    assert recorded == [], recorded  # No fake DB requests, including reads.
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
