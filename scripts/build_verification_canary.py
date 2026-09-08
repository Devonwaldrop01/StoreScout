"""Build a review-only manifest from the frozen audit; never connects anywhere."""
import hashlib
import json
from pathlib import Path
import re
import sys
from datetime import datetime, timedelta, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from app.services.verification_canary import validate_manifest
from app.services.verification_lifecycle import due_at


def build(snapshot, clock):
    selected = []
    exclusions = {"vimeo.com": "Non-retail video platform; unsuitable for a storefront safety canary."}
    for status, count in [("discovered", 4), ("candidate", 4), ("failed", 2), ("verified", 2)]:
        eligible = [r for r in snapshot if r["status"] == status and r.get("updated_at")
                    and due_at(r) <= clock and not re.search(r"block|challenge|password|429|non.shopify|dead", str(r.get("failure_reason") or ""), re.I)
                    and not r["domain"].endswith(".myshopify.com") and r["domain"] not in exclusions]
        eligible.sort(key=lambda r: hashlib.sha256((r["domain"]+"storescout-canary-v1").encode()).hexdigest())
        if len(eligible) < count:
            raise ValueError(f"insufficient eligible {status} rows")
        selected.extend({"domain":r["domain"], "expected_updated_at":r["updated_at"],
                         "sample_status":status, "category":r.get("category")} for r in eligible[:count])
    # Sentinels span two raw-supply lanes and one historical renewal.
    order = [0,4,10,1,5,8,2,6,11,3,7,9]
    return validate_manifest({"version":1,"live_rows_confirmed":False,
        "created_at":clock.isoformat(),"expires_at":(clock+timedelta(days=2)).isoformat(),
        "selection":"Deterministic stratified safety sample from preserved audit, with documented manual exclusion; current live row preconditions still require confirmation.",
        "review_exclusions":exclusions,
        "stores":[selected[i] for i in order]})


if __name__ == "__main__":
    source = ROOT/'docs/quality-audit/real-world/evidence/index-snapshot.json'
    target = ROOT/'config/verification-canary.json'
    if target.exists():
        raise SystemExit("Refusing to overwrite an existing review manifest.")
    raw = source.read_bytes()
    manifest = build(json.loads(raw), datetime.now(timezone.utc))
    manifest["source_snapshot_sha256"] = hashlib.sha256(raw).hexdigest()
    target.parent.mkdir(exist_ok=True)
    target.write_text(json.dumps(manifest,indent=2)+'\n',encoding='utf8')
    print(target)
    print('DRAFT ONLY: live preflight false; endpoint disabled; no ledger armed.')
    print('sha256:',hashlib.sha256(target.read_bytes()).hexdigest())
    for entry in manifest['stores']: print(entry['sample_status'],entry['domain'])
