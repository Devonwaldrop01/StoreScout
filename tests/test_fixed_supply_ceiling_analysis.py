"""Ceiling arithmetic and evidence accounting, no application behavior changes."""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT/'docs/quality-audit/discovery-quality/ceiling'
load = lambda name: json.loads((DATA/f'{name}.json').read_text(encoding='utf8'))


def test_exhaustive_unique_matrix_and_known_labels_preserved():
    matrix = load('relevance-matrix')
    assert len(matrix) == 2200
    assert len({(r['case_id'], r['domain']) for r in matrix}) == 2200
    assert len({r['domain'] for r in matrix}) == 88
    for row in matrix:
        assert row['rationale']
        for old in row['prior_labels']:
            assert (old['label'] >= 2) == (row['label'] >= 2)


def test_ceiling_uses_padded_per_query_denominators_not_pooled_precision():
    summary = load('summary')
    queries = load('per-query')
    counts = [q['useful_count'] for q in queries]
    assert summary['perfect_supply_ceiling']['p5'] == sum(min(n, 5) for n in counts)/125
    assert summary['perfect_supply_ceiling']['p10'] == sum(min(n, 10) for n in counts)/250
    assert summary['perfect_supply_ceiling']['searches_three_useful_top5'] == sum(n >= 3 for n in counts)
    assert sum(summary['availability_distribution'][str(n)]['queries'] for n in (0,1,2)) + summary['availability_3plus']['queries'] == 25


def test_every_missed_useful_pair_has_exactly_one_failure_stage():
    summary = load('summary')
    misses = load('useful-misses')
    assert len({(r['case_id'], r['mode'], r['domain']) for r in misses}) == len(misses)
    for mode, current in summary['current'].items():
        mm = [r for r in misses if r['mode'] == mode]
        assert current['useful_top5'] + len(mm) == summary['useful_query_store_pairs']
        for m in mm:
            if m['failure_type'] == 'never_entered_candidate_set':
                assert m['trace'] is None
            elif m['failure_type'] == 'filtered':
                assert m['trace']['exclusions'] and m['uncapped_survivor_rank'] is None
            else:
                assert not m['trace']['exclusions'] and m['uncapped_survivor_rank'] > 5


def test_near_miss_ranks_do_not_fabricate_actual_results_9_to_20():
    for record in load('near-misses'):
        for item in record['positions_6_20']:
            assert 6 <= item['rank'] <= 20
            if record['stage'] == 'post_filter_uncapped' and item['rank'] > 8:
                assert item['returned_rank'] is None


def test_classification_contribution_is_intersection_not_confidence_guess():
    defects = load('classification-contribution')
    matrix = load('relevance-matrix')
    assert len(defects) == 25
    for defect in defects:
        actual = {r['case_id'] for r in matrix if r['domain'] == defect['domain'] and r['label'] >= 2}
        assert actual == set(defect['benchmark_useful_pairs'])
        assert {m['case_id'] for m in defect['missed_useful_pairs']} <= actual
