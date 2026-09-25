"""Bounded metadata only. No URLs, headers, body content or credentials."""
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path

ROLES={'/':'home','/cart.js':'cart','/products.json':'products','/collections.json':'collections'}


def observed(path, status, seconds, size, protection):
    if protection.get('access_state') not in ('blocked','password_protected'): return None
    return {'timestamp':datetime.now(timezone.utc).isoformat(),
            'role':ROLES.get(path,'other'), 'required':path!='/collections.json',
            'status':status,'seconds':seconds,'bytes':size,
            'retry_after_at':protection.get('retry_after_at'),
            'kind':protection['access_state']}


def validated(events):
    if not isinstance(events,list) or len(events)>8: raise ValueError('Invalid protection evidence')
    result=[]
    keys={'timestamp','role','required','status','seconds','bytes','retry_after_at','kind'}
    for e in events:
        if set(e)!=keys or e['role'] not in {*ROLES.values(),'other'} or type(e['required']) is not bool:
            raise ValueError('Invalid protection metadata')
        if e['kind'] not in ('blocked','password_protected') or type(e['status']) is not int or not 100<=e['status']<=599:
            raise ValueError('Invalid protection status')
        if type(e['bytes']) is not int or not 0<=e['bytes']<=8*1024*1024 or not isinstance(e['seconds'],(int,float)) or not math.isfinite(e['seconds']) or not 0<=e['seconds']<=90:
            raise ValueError('Invalid protection measurements')
        clean=dict(e)
        for key in ('timestamp','retry_after_at'):
            if e[key] is None and key=='retry_after_at': continue
            if not isinstance(e[key],str) or len(e[key])>40: raise ValueError('Invalid evidence timestamp')
            value=datetime.fromisoformat(e[key])
            if value.tzinfo is None: raise ValueError('Missing evidence timezone')
            clean[key]=value.astimezone(timezone.utc).isoformat()
        result.append(clean)
    return result


def journal(events):
    """Atomic bounded sidecar, supervised and durably copied to SQLite by parent."""
    target=os.environ.get('INDEX_V2_PROTECTION_JOURNAL')
    if target:
        path=Path(target); temporary=path.with_suffix('.tmp')
        raw=json.dumps(validated(events),separators=(',',':')).encode()
        with temporary.open('wb') as stream:
            stream.write(raw);stream.flush();os.fsync(stream.fileno())
        os.replace(temporary,path)


def has_protection(outcome, result):
    # Read older attempt evidence without rewriting historical rows.
    return outcome in ('blocked','password_protected') or bool(result.get('protection_events')) or any(
        r.get('status') in (401,403,429) for r in result.get('requests',[]))


def enrich(events, job, succeeded):
    return [dict(e,canonical=job['canonical'],attempt_id=job['attempt_id'],
                 verification_succeeded=succeeded,contributes_to_protection_gate=True)
            for e in validated(events)]
