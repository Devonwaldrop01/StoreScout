"""Validate the exact Linux image with no production network/credentials."""
import concurrent.futures
import json
import os
from pathlib import Path
import subprocess
import time

ROOT = Path(__file__).resolve().parent
OUT = Path(os.environ["RUNNER_TEMP"]) / "release-evidence" / "web-maintenance"
OUT.mkdir(parents=True, exist_ok=True)
SHA = os.environ["RELEASE_SHA"]
CMD = "./scripts/store_web_maintenance.py"
names = []
results = {"release_sha": SHA, "command": CMD, "cases": [], "passed": False}

def run(*args, timeout=120):
    p = subprocess.run(args, capture_output=True, text=True, timeout=timeout)
    assert p.returncode == 0, (args[:5], p.returncode, p.stdout[-3000:], p.stderr[-3000:])
    return p.stdout.strip()
def docker(*args, **kw):
    return run("docker", *args, **kw)
def info(name):
    return json.loads(docker("inspect", name))[0]
def logs(name):
    p = subprocess.run(["docker", "logs", name], capture_output=True, text=True)
    return p.stdout + p.stderr
def waitfor(fn, seconds=20):
    until = time.monotonic() + seconds
    while time.monotonic() < until:
        if fn():
            return
        time.sleep(.2)
    raise AssertionError("Readiness timeout")
IMAGE = info("storescout-release:" + SHA)["Id"]
results["image_id"] = IMAGE

def start(name, port, args=None, extra=()):
    names.append(name)
    docker("run", "-d", "--name", name, "--network", "none", "--read-only",
           "-e", "PORT=" + str(port), "-e", "STORE_INDEX_DEPLOYMENT_HOLD=false",
           "-e", "REDIS_URL=redis://127.0.0.1:16379/0",
           "-e", "SUPABASE_URL=http://127.0.0.1:15432",
           "-e", "SUPABASE_SERVICE_ROLE_KEY=synthetic-only",
           *extra, IMAGE, *(args if args is not None else [CMD]))
    return info(name)

def request(name, port, method, path, expected):
    code = """import http.client,json
c=http.client.HTTPConnection("127.0.0.1",PORT,timeout=3)
c.request(METHOD,PATH)
r=c.getresponse(); b=r.read().decode()
print(json.dumps({"status":r.status,"body":b,"headers":dict(r.getheaders())}))
c.close()
""".replace("PORT", str(port)).replace("METHOD", repr(method)).replace("PATH", repr(path))
    response = json.loads(docker("exec", name, "python", "-ISB", "-c", code))
    assert response["status"] == expected, response
    assert response["headers"]["X-StoreScout-Mode"] == "maintenance"
    assert response["headers"]["Cache-Control"] == "no-store"
    if method != "HEAD":
        assert "maintenance" in response["body"].lower()
        if expected == 503:
            assert json.loads(response["body"])["detail"] == "StoreScout is temporarily undergoing maintenance."
            assert response["headers"]["Content-Type"] == "application/json"
    else:
        assert not response["body"]
    return response

def stop(name, sig):
    begun = time.monotonic()
    docker("kill", "--signal", sig, name)
    code = int(docker("wait", name, timeout=10))
    assert code == 0, logs(name)
    assert "STORE_WEB_MAINTENANCE clean exit" in logs(name)
    return round(time.monotonic() - begun, 3)

try:
    cfg = info(IMAGE)
    assert cfg["Config"]["Entrypoint"] is None
    assert cfg["Config"]["WorkingDir"] == "/app"
    assert cfg["Config"]["Labels"]["org.opencontainers.image.revision"] == SHA
    assert cfg["Os"] == "linux" and cfg["Architecture"] == "amd64"
    results["image_config"] = cfg["Config"]
    assert run("git", "ls-tree", "HEAD", "scripts/store_web_maintenance.py").startswith("100755 ")
    data = Path("scripts/store_web_maintenance.py").read_bytes()
    assert data.startswith(b"#!/usr/bin/python -ISB\n") and b"\r" not in data
    # Direct CMD override is precisely the proposed Render string.
    for number, (port, sig) in enumerate(((10000, "SIGTERM"), (18765, "SIGINT"))):
        name = "web-maint-" + str(number)
        start(name, port)
        waitfor(lambda: "STORE_WEB_MAINTENANCE ready" in logs(name))
        assert info(name)["Path"] == CMD and info(name)["Args"] == []
        proof = json.loads(docker("exec", name, "python", "-ISB", "-c",
            'import pathlib,json; p=pathlib.Path("/proc/1"); s=dict(x.split(":",1) for x in (p/"status").read_text().splitlines()); print(json.dumps({"argv":(p/"cmdline").read_bytes().decode().split(chr(0))[:-1],"ppid":s["PPid"].strip(),"term":bool(int(s["SigCgt"],16)&16384),"int":bool(int(s["SigCgt"],16)&2),"tcp":pathlib.Path("/proc/1/net/tcp").read_text()}))'))
        assert proof["ppid"] == "0" and proof["term"] and proof["int"]
        assert proof["argv"] == ["/usr/bin/python", "-ISB", CMD], proof
        assert ("00000000:%04X" % port) in proof["tcp"], proof
        responses = []
        for method in ("GET", "HEAD", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"):
            for path in ("/", "/health", "/check_store", "/api/v1/internal/store-index/verify"):
                responses.append(request(name, port, method, path, 503))
        responses.append(request(name, port, "GET", "/__maintenance/ready", 200))
        responses.append(request(name, port, "POST", "/__maintenance/ready", 503))
        # TCP-only probes must not block subsequent requests.
        docker("exec", name, "python", "-ISB", "-c",
               'import socket; s=socket.create_connection(("127.0.0.1",'+str(port)+')); s.close()')
        request(name, port, "GET", "/", 503)
        if number == 0:
            begun = time.monotonic()
            while time.monotonic() - begun < 180:
                request(name, port, "GET", "/", 503)
                assert info(name)["State"]["Running"] and info(name)["RestartCount"] == 0
                time.sleep(5)
            results["sustained_seconds"] = round(time.monotonic() - begun, 3)
        assert not docker("diff", name)
        top = docker("top", name, "-eo", "pid,ppid,comm")
        # Linux comm retains the executable script basename; argv above proves
        # the interpreter and absence of a parent shell.
        assert len(top.splitlines()) == 2 and "store_web_maint" in top, top
        results["cases"].append({"port": port, "signal": sig, "proof": proof,
            "response_cases": len(responses), "restart_count": info(name)["RestartCount"],
            "shutdown_seconds": stop(name, sig)})
    # Runtime audit of the same file: fail on ANY StoreScout/Celery/Redis/DB
    # import or outbound socket operation. Audit code is test-only.
    start("web-maint-audit", 10000, ["python", "-ISB", "/validation/audit.py"],
          ("-v", str(ROOT / "audit.py") + ":/validation/audit.py:ro"))
    waitfor(lambda: "STORE_WEB_MAINTENANCE ready" in logs("web-maint-audit"))
    for path in ("/", "/api/v1/store-index", "/health"):
        request("web-maint-audit", 10000, "POST", path, 503)
    stop("web-maint-audit", "SIGTERM")
    line = next(x for x in logs("web-maint-audit").splitlines() if x.startswith("ISOLATION_AUDIT "))
    results["isolation"] = json.loads(line.removeprefix("ISOLATION_AUDIT "))
    assert results["isolation"] == {"forbidden_events": [], "forbidden_modules": []}
    for value in ("", "0", "65536", "not-a-port"):
        name = "bad-port-" + str(len(names))
        start(name, value)
        assert int(docker("wait", name, timeout=10)) != 0
        assert "STORE_WEB_MAINTENANCE ready" not in logs(name)
    # Uvicorn's graceful drain is distinct from maintenance readiness.
    # Synthetic synchronous request performs a delayed simulated commit.
    legacy = OUT / "legacy-server-packages"
    legacy.mkdir()
    # Test-only mounts reproduce the live Web server stack; never alter image.
    docker("run", "--rm", "-v", str(legacy) + ":/legacy", IMAGE, "python", "-m", "pip",
           "install", "--no-deps", "--target", "/legacy", "starlette==1.3.1", "anyio==4.14.1")
    results["synthetic_drain"] = {}
    for stack in ("release", "legacy"):
        name = "web-drain-" + stack
        extra = ["-v", str(ROOT / "fixture.py") + ":/validation/fixture.py:ro",
                 "-e", "PYTHONDONTWRITEBYTECODE=1"]
        if stack == "legacy":
            extra += ["-v", str(legacy) + ":/legacy:ro", "-e", "PYTHONPATH=/legacy"]
        start(name, 10000, ["uvicorn", "fixture:app", "--host", "0.0.0.0",
              "--port", "10000", "--app-dir", "/validation"], tuple(extra))
        waitfor(lambda: "Application startup complete" in logs(name))
        versions = json.loads(docker("exec", name, "python", "-B", "-c",
            'import importlib.metadata as m,json; print(json.dumps({n:m.version(n) for n in ("uvicorn","fastapi","starlette","anyio")}))'))
        if stack == "legacy":
            assert versions == {"uvicorn":"0.51.0","fastapi":"0.139.0","starlette":"1.3.1","anyio":"4.14.1"}, versions
        code = 'import http.client; c=http.client.HTTPConnection("127.0.0.1",10000,timeout=15); c.request("POST","/write"); r=c.getresponse(); print(r.status,r.read().decode())'
        with concurrent.futures.ThreadPoolExecutor() as pool:
            request_future = pool.submit(docker, "exec", name, "python", "-ISB", "-c", code)
            waitfor(lambda: "FIXTURE_WRITE_BEGIN" in logs(name))
            begun = time.monotonic()
            docker("kill", "--signal", "SIGTERM", name)
            assert request_future.result().startswith("200 ")
            assert int(docker("wait", name, timeout=15)) == 0
            output = logs(name)
            assert output.index("FIXTURE_WRITE_COMMIT") < output.index("Application shutdown complete")
            assert "Finished server process" in output
            results["synthetic_drain"][stack] = {"seconds":round(time.monotonic()-begun,3),
                "commit_before_shutdown":True,"exit":0,"versions":versions}
    results["passed"] = True
finally:
    for name in names:
        try:
            output = logs(name)
            (OUT / (name + ".log")).write_text(output)
            print("CONTAINER_LOG " + name + " " + output[-4000:])
            (OUT / (name + ".json")).write_text(json.dumps(info(name), indent=2))
            docker("rm", "-f", name)
        except Exception as exc:
            print("Evidence cleanup:", type(exc).__name__)
    (OUT / "results.json").write_text(json.dumps(results, indent=2))
    print("WEB_MAINTENANCE_RESULTS " + json.dumps(results), flush=True)
