"""Preserve previous reports; replay into a separate offline readiness directory."""
from pathlib import Path
ROOT = Path(__file__).resolve().parents[2]
source = ROOT/'tests/evaluations/access_empty_benchmark.py'
code = source.read_text(encoding='utf8').replace('outputs/production-access/benchmark', 'outputs/production-readiness/benchmark')
exec(compile(code, str(source), 'exec'), {'__file__': str(source)})
