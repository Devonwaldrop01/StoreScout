"""Offline image/source inventory and application dependency verification."""
import fnmatch
import hashlib
from importlib.metadata import distributions
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path.cwd()
assert hashlib.sha256((ROOT / 'config/verification-canary.json').read_bytes()).hexdigest() == '0c30c1e7cbf26ca3b0ab2e8cdb3da6f287e49da329ee4af9681ff83e18b2f103', 'approved manifest bytes changed'
assert hashlib.sha256((ROOT / 'supabase/migrations/20260905235144_verification_lifecycle.sql').read_bytes()).hexdigest() == '34b93523b69ee2991745ca77f305a82e7b879f641cc9b1c72999d93fdcb187f9', 'reviewed migration bytes changed'


def excluded(path):
    for pattern in (ROOT / '.dockerignore').read_text().splitlines():
        pattern = pattern.strip()
        if not pattern or pattern.startswith('#'):
            continue
        if '/' not in pattern:
            if any(fnmatch.fnmatch(part, pattern) for part in Path(path).parts):
                return True
        elif fnmatch.fnmatch(path, pattern) or path.startswith(pattern + '/'):
            return True
    return False


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


if sys.argv[1] == 'inventory':
    files = subprocess.check_output(['git', 'ls-files', '-z']).decode().split('\0')
    assert subprocess.check_output(['git', 'rev-parse', 'HEAD']).decode().strip() == sys.argv[2]
    payload = {'sha': sys.argv[2], 'files': {p: digest(ROOT / p) for p in files if p and not excluded(p)}}
    Path(sys.argv[3]).write_text(json.dumps(payload, indent=2))
else:
    expected = json.loads(Path(sys.argv[2]).read_text())
    files = {str(p.relative_to(ROOT)).replace('\\', '/'): digest(p) for p in ROOT.rglob('*') if p.is_file()}
    assert files == expected['files'], {'missing': sorted(expected['files'].keys()-files.keys()),
                                       'unexpected': sorted(files.keys()-expected['files'].keys()),
                                       'changed': [p for p in files.keys() & expected['files'].keys() if files[p] != expected['files'][p]]}
    from packaging.requirements import Requirement
    from packaging.utils import canonicalize_name
    constraints = {}
    for line in Path('requirements-release-constraints.txt').read_text().splitlines():
        if not line or line.startswith('#'): continue
        r = Requirement(line)
        if r.marker is None or r.marker.evaluate(): constraints[canonicalize_name(r.name)] = r.specifier
    installed = {canonicalize_name(d.metadata['Name']): d.version for d in distributions()}
    for name, version in installed.items():
        if name in {'pip', 'setuptools', 'wheel'}: continue
        assert name in constraints and version in constraints[name], (name, version, 'unreviewed dependency')
    for line in Path('requirements.txt').read_text().splitlines():
        if not line or line.startswith('#'): continue
        r = Requirement(line)
        assert installed[canonicalize_name(r.name)] in r.specifier
    print(json.dumps({'source_sha': expected['sha'], 'verified_files': len(files), 'packages': installed}, indent=2))
