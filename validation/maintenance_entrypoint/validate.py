"""Exact release image tests using only disposable, isolated resources."""
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parent
EVIDENCE = Path(os.environ["RUNNER_TEMP"]) / "release-evidence" / "entrypoint"
EVIDENCE.mkdir(parents=True, exist_ok=True)
SHA = os.environ["RELEASE_SHA"]
COMMAND = "./scripts/store_index_maintenance_bridge.sh"
MARKER = "STORE_INDEX_MAINTENANCE_BRIDGE idle; application not imported"
NET = "entrypoint-" + os.environ["GITHUB_RUN_ID"]
names = []
results = {"release_sha": SHA, "render_command": COMMAND, "inert": {}, "shutdown": {}}

def run(*args, timeout=120):
    p = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    assert p.returncode == 0, (args[:5], p.returncode, p.stdout[-3000:], p.stderr[-3000:])
    return p.stdout.strip()

def docker(*args, **kw):
    return run("docker", *args, **kw)

def inspect(name):
    return json.loads(docker("inspect", name))[0]

def logs(name):
    p = subprocess.run(["docker", "logs", name], capture_output=True, text=True)
    return p.stdout + p.stderr

IMAGE = inspect("storescout-release:" + SHA)["Id"]
results["image_id"] = IMAGE

def start(name, argv, env=None, network="none", extra=()):
    args = ["run", "-d", "--name", name, "--network", network]
    for key, value in (env or {}).items():
        args += ["-e", key + "=" + value]
    docker(*args, *extra, IMAGE, *argv)
    names.append(name)
    info = inspect(name)
    assert info["Image"] == IMAGE
    expected_cmd = argv or (None if "--entrypoint" in extra else normal["beat"])
    assert info["Config"]["Cmd"] == expected_cmd
    return info

def running(name):
    info = inspect(name)
    assert info["State"]["Running"] and info["RestartCount"] == 0, info["State"]

def idle(name):
    running(name)
    lines = logs(name).splitlines()
    assert lines == [MARKER], lines
    top = docker("top", name, "-eo", "pid,comm")
    processes = [line.split()[-1] for line in top.splitlines()[1:]]
    assert len(processes) == 2 and "sleep" in processes, top
    assert all(p in ("sh", "sleep", "store_index_mai") for p in processes), top
    assert not docker("diff", name), docker("diff", name)
    return processes

def stop(name, signal="SIGTERM", marker=True):
    begun = time.monotonic()
    docker("kill", "--signal", signal, name)
    code = int(docker("wait", name, timeout=20))
    assert code == 0 and not inspect(name)["State"]["OOMKilled"], (name, code)
    if marker:
        assert "STORE_INDEX_MAINTENANCE_BRIDGE clean exit" in logs(name)
    results["shutdown"][name + signal] = {"exit": code, "seconds": round(time.monotonic()-begun, 3)}

normal = {
    "web": ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "10000"],
    "worker": ["celery", "-A", "app.tasks.celery_app.celery", "worker", "--loglevel=info",
               "-Q", "default,priority", "--concurrency=2"],
    "beat": ["celery", "-A", "app.tasks.celery_app.celery", "beat", "--loglevel=info"],
}
try:
    image = inspect(IMAGE)
    assert image["Config"]["Entrypoint"] is None
    assert image["Config"]["Cmd"] == normal["beat"]
    assert image["Config"]["WorkingDir"] == "/app"
    assert image["Config"]["Labels"]["org.opencontainers.image.revision"] == SHA
    assert image["Os"] == "linux" and image["Architecture"] == "amd64"
    results["image_config"] = image["Config"]
    (EVIDENCE / "image.json").write_text(json.dumps(image, indent=2))
    # Git executable mode and LF are part of the release; no chmod/runtime patch.
    tree = run("git", "ls-tree", "HEAD", "scripts/store_index_maintenance_bridge.sh")
    assert tree.startswith("100755 "), tree
    data = Path("scripts/store_index_maintenance_bridge.sh").read_bytes()
    assert data.startswith(b"#!/bin/sh\n") and b"\r" not in data
    docker("run", "--rm", "--network", "none", IMAGE, "/bin/sh", "-n", COMMAND)
    docker("run", "--rm", "--network", "none", IMAGE, "test", "-x", COMMAND)

    # Reproduce the observed error by preserving quotes in the -c argument.
    # This proves a sufficient mechanism, not Render's undisclosed exact argv.
    old_body = 'stop() { trap "" TERM INT; kill "$child" 2>/dev/null; wait "$child" 2>/dev/null; echo "STORE_INDEX_MAINTENANCE_BRIDGE clean exit"; exit 0; }; sleep infinity & child=$!; trap stop TERM INT; echo "STORE_INDEX_MAINTENANCE_BRIDGE idle; application not imported"; wait "$child"; exit 1'
    start("quoted-body-repro", ["/bin/sh", "-c", "'" + old_body + "'"])
    assert int(docker("wait", "quoted-body-repro")) == 127
    error = logs("quoted-body-repro").strip()
    assert error == "/bin/sh: 1: " + old_body + ": not found", error
    results["old_failure_reproduced"] = {"exit": 127, "error": error,
        "actual_render_argv_proven": False}

    # One path has identical tokenization with whitespace splitting and POSIX
    # parsing; also exercise an outer shell and explicit entrypoint invocation.
    modes = {
        "cmd": ([COMMAND], ()),
        "shell": (["/bin/sh", "-c", "exec " + COMMAND], ()),
        "entrypoint": ([], ("--entrypoint", COMMAND)),
    }
    for mode, (argv, extra) in modes.items():
        for value in (None, "true", "", "unknown", "false"):
            suffix = "missing" if value is None else value or "empty"
            name = "bridge-" + mode + "-" + suffix
            env = {"STORE_INDEX_CANARY_ENABLED": "false", "PYTHONPATH": "/never-import",
                   "SUPABASE_URL": "http://dbsink:8080", "SUPABASE_SERVICE_ROLE_KEY": "offline-test",
                   "REDIS_URL": "redis://redis:6379/0"}
            if value is not None:
                env["STORE_INDEX_DEPLOYMENT_HOLD"] = value
            info = start(name, argv, env, extra=("--read-only", *extra))
            assert info["HostConfig"]["NetworkMode"] == "none"
            time.sleep(1)
            processes = idle(name)
            results["inert"][name] = {"processes": processes, "hold": value,
                "network": "none", "filesystem_changes": 0, "application_initializations": 0}
            stop(name)
            docker("start", name)
            time.sleep(0.5)
            running(name)
            stop(name, "SIGINT")
            assert logs(name).splitlines().count(MARKER) == 2

    # A non-exec outer shell is a negative control, not a supported launch
    # interface: it owns PID 1 and does not forward TERM to the script.
    start("bridge-nonexec-negative", ["/bin/sh", "-c", COMMAND],
          extra=("--read-only",))
    time.sleep(1)
    top = docker("top", "bridge-nonexec-negative", "-eo", "pid,comm")
    processes = [line.split()[-1] for line in top.splitlines()[1:]]
    assert sorted(processes) == sorted(["sh", "store_index_mai", "sleep"]), top
    docker("kill", "--signal", "SIGTERM", "bridge-nonexec-negative")
    time.sleep(2)
    running("bridge-nonexec-negative")
    assert logs("bridge-nonexec-negative").splitlines() == [MARKER]
    docker("kill", "--signal", "SIGKILL", "bridge-nonexec-negative")
    assert int(docker("wait", "bridge-nonexec-negative")) == 137
    results["nonexec_wrapper_negative_control"] = {
        "rejected": True, "reason": "extra PID 1 shell does not forward TERM",
        "production_gate": "direct executable or exec-equivalent invocation required"}

    start("bridge-sustained", [COMMAND], {"STORE_INDEX_DEPLOYMENT_HOLD": "true",
          "STORE_INDEX_CANARY_ENABLED": "false"}, extra=("--read-only",))
    begun = time.monotonic()
    for _ in range(36):
        time.sleep(5)
        idle("bridge-sustained")
    results["sustained_seconds"] = round(time.monotonic()-begun, 3)
    stop("bridge-sustained")

    start("bridge-child-death", [COMMAND], extra=("--read-only",))
    time.sleep(1)
    idle("bridge-child-death")
    p = subprocess.run(["docker", "exec", "bridge-child-death", "/bin/sh", "-c",
         "kill -TERM $(cat /proc/1/task/1/children)"], capture_output=True, text=True, timeout=10)
    assert p.returncode in (0, 137), (p.returncode, p.stderr)
    assert int(docker("wait", "bridge-child-death", timeout=10)) == 1
    assert "unexpected child exit" in logs("bridge-child-death")
    results["unexpected_child_exit"] = 1

    # The fake DB and TLS Redis are only reachable over an internal test network.
    tls = Path(os.environ["RUNNER_TEMP"]) / "storescout-release" / "tls"
    redis_ref = json.loads((EVIDENCE.parent / "test-redis-image.json").read_text())[0]["RepoDigests"][0]
    docker("network", "create", "--internal", NET)
    assert inspect(NET)["Internal"]
    docker("run", "-d", "--name", "test-redis", "--network", NET, "--network-alias", "redis",
           "-v", f"{tls}:/tls:ro", redis_ref, "redis-server", "--port", "0", "--tls-port", "6379",
           "--tls-cert-file", "/tls/cert.pem", "--tls-key-file", "/tls/key.pem",
           "--tls-ca-cert-file", "/tls/cert.pem", "--tls-auth-clients", "no", "--save", "", "--appendonly", "no")
    names.append("test-redis")
    mount = ("-v", f"{ROOT}:/validation:ro")
    start("dbsink", ["python", "-I", "-S", "-B", "-u", "/validation/sink.py"],
          network=NET, extra=mount)
    env = {"PYTHONDONTWRITEBYTECODE": "1", "PYTHONPATH": "/app", "PORT": "10000",
           "REDIS_URL": "rediss://redis:6379/0?ssl_cert_reqs=required&ssl_check_hostname=true&ssl_ca_certs=/tls/cert.pem",
           "SUPABASE_URL": "http://dbsink:8080", "SUPABASE_SERVICE_ROLE_KEY": "offline-test",
           "API_INTERNAL_URL": "http://web:10000", "INTERNAL_SECRET": "offline-test",
           "ANTHROPIC_API_KEY": "", "STORE_INDEX_CANARY_ENABLED": "false", "STORE_INDEX_DEPLOYMENT_HOLD": "true"}
    start("bridge-with-fakes", [COMMAND], env, NET,
          extra=("--read-only", "-v", f"{tls / 'cert.pem'}:/tls/cert.pem:ro"))
    time.sleep(5)
    running("bridge-with-fakes")
    assert logs("bridge-with-fakes").splitlines() == [MARKER]
    clients = docker("exec", "test-redis", "redis-cli", "--tls", "--cacert", "/tls/cert.pem",
                     "-h", "redis", "CLIENT", "LIST")
    assert len(clients.splitlines()) == 1, clients  # Only the inspection client.
    results["maintenance_redis_clients"] = 0
    stop("bridge-with-fakes")
    for role in ("web", "worker", "beat"):
        start("normal-" + role, [] if role == "beat" else normal[role], env, NET,
              extra=(*mount, "--network-alias", role, "-v", f"{tls / 'cert.pem'}:/tls/cert.pem:ro"))
    output = docker("exec", "normal-web", "python", "/validation/runtime_check.py", timeout=90)
    checks = json.loads(output.splitlines()[-1])
    for _ in range(40):
        if all(f"[{tid}] succeeded" in logs("normal-worker") for tid in checks["delivery_ids"]):
            break
        time.sleep(0.25)
    for tid in checks["delivery_ids"]:
        lines = [line for line in logs("normal-worker").splitlines() if f"[{tid}] succeeded" in line]
        assert len(lines) == 1 and "deployment_hold" in lines[0], (tid, lines)
    results["restored"] = checks
    assert "beat: Starting" in logs("normal-beat")
    for role in ("beat", "worker", "web"):
        running("normal-" + role)
        stop("normal-" + role, marker=False)
    requests = docker("exec", "dbsink", "python", "-I", "-S", "-B", "-c",
                      "from pathlib import Path;p=Path('/tmp/requests.jsonl');print(p.read_text() if p.exists() else '')")
    assert requests == "", requests
    results["fake_db_requests"] = 0
    for role in normal:
        assert not any(token in logs("normal-" + role) for token in
                       ("CERT_NONE", "CERTIFICATE_VERIFY_FAILED", "single-flight lock unavailable", "duplicate key"))
    results["passed"] = True
finally:
    for name in names:
        (EVIDENCE / (name + ".log")).write_text(logs(name))
        try:
            (EVIDENCE / (name + ".json")).write_text(json.dumps(inspect(name), indent=2))
        except Exception:
            pass
        subprocess.run(["docker", "rm", "-f", name], capture_output=True)
    subprocess.run(["docker", "network", "rm", NET], capture_output=True)
    (EVIDENCE / "results.json").write_text(json.dumps(results, indent=2))
    print(json.dumps(results, indent=2))
