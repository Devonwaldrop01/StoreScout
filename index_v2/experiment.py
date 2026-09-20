"""Read-only snapshots for the frozen benchmark; never publish customer Discovery."""
from datetime import datetime,timezone
import json
from pathlib import Path
from app.services.discovery_quality import is_recent_verified,is_classification_usable
from app.services.verification_lifecycle import timestamp
from .identity import canonical,digest


def eligible_rows(rows,now):
    out={}
    for row in rows:
        if not is_recent_verified(row,now=now) or not is_classification_usable(row,now=now): continue
        key=canonical(row['domain'])
        old=out.get(key)
        stamp=lambda r:timestamp((r.get('catalog_observation') or {}).get('observed_at') or r.get('last_verified_at'))
        if old is None or stamp(row)>stamp(old): out[key]=row
    return [out[key] for key in sorted(out)]


def export(store,directory,legacy_path=None,now=None):
    now=now or datetime.now(timezone.utc)
    directory.mkdir(parents=True,exist_ok=False)
    legacy=json.loads(legacy_path.read_text(encoding='utf8')) if legacy_path else []
    v2=store.rows(eligible_only=True)
    sets={'legacy':eligible_rows(legacy,now),'v2':eligible_rows(v2,now),'combined':eligible_rows(legacy+v2,now)}
    inputs={}
    for key,rows in sets.items():
        path=directory/(key+'.json');path.write_text(json.dumps(rows,indent=2),encoding='utf8')
        inputs[key]=str(path.resolve())
    (directory/'clock.json').write_text(json.dumps({'clock':now.isoformat()}))
    (directory/'experiment.json').write_text(json.dumps({'inputs':inputs,'output_dir':str(directory.resolve()),
        'hashes':{k:digest(v) for k,v in sets.items()},'supply':{k:len(v) for k,v in sets.items()},
        'deduplication':'www/apex canonical identity; latest eligible successful observation wins',
        'ranking':'unchanged; use frozen replay and adjudicate every new placement'},indent=2))
    return sets
