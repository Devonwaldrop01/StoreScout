"""Replay preserved captures into separate deployment-preflight outputs."""
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
source=ROOT/'tests/evaluations/access_empty_benchmark.py'
code=source.read_text(encoding='utf8').replace('outputs/production-access/benchmark','outputs/deployment-preflight/benchmark')
exec(compile(code,str(source),'exec'),{'__file__':str(source)})
