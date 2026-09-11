"""Only GitHub artifact reads; the token never enters a test container."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import zipfile

SHA = "667dea6e3eb35c53116e349758d4606e08a5adb0"
DIGEST = "c04ea9ba6e3d0d84e802a663e39bb9c7e2fa43e0de2d9318b910ade5881138ea"
root = Path(os.environ["RUNNER_TEMP"])
evidence = root / "maintenance-evidence"
evidence.mkdir(exist_ok=True)
artifact_path = "repos/Devonwaldrop01/StoreScout/actions/artifacts/10052581360"
metadata = json.loads(subprocess.check_output(["gh", "api", artifact_path]))
assert metadata["id"] == 10052581360 and not metadata["expired"]
assert metadata["workflow_run"]["head_sha"] == SHA
assert metadata["workflow_run"]["id"] == 34217785184
assert metadata["digest"] == "sha256:" + DIGEST
archive = root / "retained-release.zip"
with archive.open("wb") as f:
    subprocess.run(["gh", "api", artifact_path + "/zip"], stdout=f, check=True)
assert hashlib.file_digest(archive.open("rb"), "sha256").hexdigest() == DIGEST
assert archive.stat().st_size == 1122932457
target = root / "retained-release"
target.mkdir(exist_ok=True)
with zipfile.ZipFile(archive) as z:
    for n in z.namelist():
        assert (target / n).resolve().is_relative_to(target.resolve()), n
    z.extractall(target)
assert (target / "release-sha.txt").read_text().strip() == SHA
image_archive = target / "release-image.tar.gz"
expected = (target / "release-image.sha256").read_text().split()[0]
actual = hashlib.file_digest(image_archive.open("rb"), "sha256").hexdigest()
assert actual == expected
(evidence / "provenance.json").write_text(json.dumps({"artifact": metadata,
    "zip_sha256": DIGEST, "image_archive_sha256": actual}, indent=2))
print(json.dumps({"verified_artifact": metadata["id"], "release_sha": SHA,
                  "zip_sha256": DIGEST, "image_archive_sha256": actual}))
