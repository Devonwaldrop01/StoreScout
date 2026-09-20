"""One www/apex processing identity; retain original host evidence separately."""
import hashlib
import ipaddress
import json
import re
from urllib.parse import urlsplit


def hostname(value):
    value = str(value).strip()
    parsed = urlsplit(value if '://' in value else 'https://' + value)
    if parsed.scheme not in ('http', 'https') or parsed.username or parsed.password or parsed.port:
        raise ValueError('Only ordinary domain hostnames are permitted')
    host = (parsed.hostname or '').rstrip('.').encode('idna').decode().lower()
    if len(host)>253 or '.' not in host or not re.fullmatch(r'[a-z0-9-]+(?:\.[a-z0-9-]+)+',host):
        raise ValueError('Invalid hostname')
    if any(len(x)>63 or x.startswith('-') or x.endswith('-') for x in host.split('.')):
        raise ValueError('Invalid hostname label')
    try: ipaddress.ip_address(host)
    except ValueError: pass
    else: raise ValueError('IP addresses are not store identities')
    return host


def canonical(value):
    host = hostname(value)
    return host[4:] if host.startswith('www.') else host


def encoded(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True)


def digest(value):
    return hashlib.sha256(encoded(value).encode()).hexdigest()


def prepare(rows, *, batch_size, expires_at, source_sha256, target_eligible=1000):
    """Deterministic bounded membership. No random/live discovery during execution."""
    if not 1 <= batch_size <= 4500: raise ValueError('Bounded seed cap is 4500 identities')
    grouped = {}
    for row in rows:
        h = hostname(row['domain']); key = canonical(h)
        if row.get('distinct_storefront_evidence'):
            raise ValueError('Conflicting storefront identity needs separate review, not an automatic split')
        grouped.setdefault(key, []).append({'hostname':h,'source':row.get('source') or 'legacy-resolved-export',
            'source_ref':str(row.get('id') or row['domain']), 'updated_at':row.get('updated_at')})
    entries=[]
    for key in sorted(grouped, key=lambda k: digest({'seed':'index-v2-1k','domain':k}))[:batch_size]:
        evidence = sorted({encoded(x):x for x in grouped[key]}.values(),key=encoded)
        hosts=sorted({x['hostname'] for x in evidence})
        entries.append({'canonical':key,'fetch_host':key if key in hosts else hosts[0],'provenance':evidence})
    return {'version':1,'enabled':False,'source_sha256':source_sha256,'expires_at':expires_at,
        'target_eligible':target_eligible,'concurrency':1,'attempt_cap':min(6750,3*len(entries)),
        'per_domain_attempt_cap':3,'request_cap':min(54000,24*len(entries)),
        'attempt_request_cap':8,'lease_seconds':180,'child_seconds':90,
        'memory_ceiling_mib':400,'min_start_gap_seconds':10,'entries':entries}


def validate(manifest):
    if manifest.get('version')!=1 or manifest.get('enabled') is not False:
        raise ValueError('Manifest must remain disabled; execution needs separate environment authorization')
    entries=manifest['entries']
    if not 1<=len(entries)<=4500 or len({e['canonical'] for e in entries})!=len(entries):
        raise ValueError('Manifest membership invalid')
    for e in entries:
        if canonical(e['canonical'])!=e['canonical'] or canonical(e['fetch_host'])!=e['canonical']:
            raise ValueError('Noncanonical processing identity')
        if not e['provenance'] or any(canonical(p['hostname'])!=e['canonical'] for p in e['provenance']):
            raise ValueError('Missing/mismatched hostname provenance')
    expected={'concurrency':1,'attempt_request_cap':8,'lease_seconds':180,'child_seconds':90,
              'memory_ceiling_mib':400,'per_domain_attempt_cap':3,'min_start_gap_seconds':10}
    if any(manifest.get(k)!=v for k,v in expected.items()): raise ValueError('Unreviewed execution limits')
    if not 1<=manifest['attempt_cap']<=min(6750,3*len(entries)): raise ValueError('Attempt cap invalid')
    if not 8<=manifest['request_cap']<=min(54000,24*len(entries)): raise ValueError('Request cap invalid')
    if not 1<=manifest['target_eligible']<=25000: raise ValueError('Target invalid')
    from datetime import datetime
    if datetime.fromisoformat(manifest['expires_at']).tzinfo is None: raise ValueError('Expiry needs timezone')
    if not re.fullmatch('[a-f0-9]{64}',manifest['source_sha256']): raise ValueError('Source hash required')
    return manifest
