"""Package already completed offline measurements; never calls external services."""
import hashlib
import json
from collections import Counter
from datetime import datetime
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from app.services.discovery_quality import is_recent_verified, is_classification_usable

OUT = ROOT / 'outputs/bounded-cycle'
DEST = ROOT / 'docs/quality-audit/phase1/bounded-cycle'
DEST.mkdir(parents=True, exist_ok=True)
load = lambda p: json.loads(p.read_text(encoding='utf8'))
save = lambda name, data: (DEST/name).write_text(json.dumps(data, indent=2), encoding='utf8')
clock = datetime.fromisoformat(load(OUT/'clock.json')['clock'])
after = load(OUT/'benchmark-comparison.json')
before = {v: load(ROOT/f'outputs/controlled-validation/{p}/evidence/benchmark-metrics.json')
          for v,p in [('frozen','before'),('controlled','after')]}
classification = load(OUT/'classification-results.json')
rows = load(OUT/'index-after.json')
eligible = lambda r: is_recent_verified(r,now=clock) and is_classification_usable(r,now=clock)
usable = [r for r in rows if eligible(r)]
provisional = [r for r in usable if (r.get('catalog_observation') or {}).get('classification_state')=='provisional']
assert len(usable)==365 and len(provisional)==3
source = ROOT/'docs/quality-audit/real-world/evidence'
protected = load(ROOT/'docs/quality-audit/phase1/controlled-validation/measurements.json')
for name, digest in protected['protected_hashes'].items():
    assert hashlib.sha256((source/name).read_bytes()).hexdigest()==digest
panel = next((ROOT/'docs/quality-audit').rglob('reference-panel.json'))
assert hashlib.sha256(panel.read_bytes()).hexdigest()==protected['reference_panel_sha256']

entries = []
regressions = []
for variant in after:
    old = {(c['case_id'],c['mode']): c for c in before[variant]['cases']}
    for case in after[variant]['cases']:
        prior = old[(case['case_id'],case['mode'])]
        ranks = {r['domain']:r['rank'] for r in prior['labels']}
        for label in case['labels']:
            old_rank = ranks.get(label['domain'])
            if old_rank is None or (label['rank']<=5 and old_rank>5):
                assert label.get('rationale')
                entries.append({'variant':variant,'old_rank':old_rank,
                    'entry_type':'new top-ten result' if old_rank is None else 'crossed into top five',**label})
        if any(case['metrics'][m] < prior['metrics'][m] for m in ['precision_at_5','precision_at_10']):
            regressions.append({'variant':variant,'case_id':case['case_id'],'business':case['business'],
                'mode':case['mode'],'niche':case['niche'],'before':prior['metrics'],'after':case['metrics']})
save('entry-adjudications.json',entries)
save('new-identity-adjudications.json',load(OUT/'adjudications.json'))
save('case-metrics.json',{'before':before,'after':after,'regressions':regressions})
compact_class = [{k:r[k] for k in ('domain','before','replacement','transition_state','transition_usable','after_usable')}
    | {'retained_category':r['after_row'].get('category'),
       'provisional_until':r['after_row']['catalog_observation'].get('classification_valid_until')}
    for r in classification]
save('classification-results.json',compact_class)
measurement = {'clock':clock.isoformat(),'classification_threshold':55,
    'replacement_pass_before':9,'replacement_pass_after':19,'successful_raw_catalogs':24,
    'usable_sample_after':22,'provisional_sample_after':3,'usable_supply_before':352,
    'usable_supply_after':len(usable),'nonprovisional_usable_supply_after':len(usable)-len(provisional),
    'fresh_readable_verified_before':377,'fresh_readable_verified_after':sum(is_recent_verified(r,now=clock) for r in rows),
    'paid_ai_calls':0,'new_raw_catalog_fetches':0,'tests_passed':260,
    'entry_reviews':dict(Counter(r['variant'] for r in entries)),
    'summaries':{v:{'before':before[v]['summary'],'after':after[v]['summary']} for v in after},
    'protected_hashes':protected['protected_hashes'],'reference_panel_sha256':protected['reference_panel_sha256']}
save('measurements.json',measurement)

lines = ['# Bounded classification and product-intent cycle', '',
    'Completed locally on 2026-09-06. **Discovery remains Weak. Recommend a bounded production-like access validation next; do not begin broad acquisition.**', '',
    'This cycle reapplies classification to the same 24 byte-backed successful catalogs and preserves the other 224 controlled outcomes. It does not collect a new sample. Both comparisons use the prior controlled cutoff, `'+clock.isoformat()+'`. The original 25-business panel, reference relationships, baseline, label definitions and missing-rank denominators are unchanged. All 25 businesses run in both modes; core tables retain the original 24-plus-one-control split.', '',
    '## Classification diagnosis and fix', '',
    'The dominant demonstrated problem was the free heuristic, not a calibrated threshold defect. It missed common product nouns (wallets, denim, stationery, tools, phone cases and compression garments), counted generic words inside more specific phrases, and let collection/tag/homepage noise outweigh repeated product evidence. Broad taxonomy boundaries also confused accessories with jewelry and baby apparel with general fashion. The observed catalogs contained enough product information to fix ten failures without paid AI. Two-title inputs still receive the existing sparse-evidence cap of 54; the eligibility floor remains 55.', '',
    'The vocabulary and specificity changes apply only when actual product types or titles are supplied. Text-only business-query classification is preserved, with benchmark assertions checking the original inferred category for every case. No merchant names or benchmark labels enter application rules. The confidence formula itself is unchanged; these are heuristic scores, not calibrated probabilities or independently measured classification accuracy.', '',
    'Residual failures include mixed boutique inputs, entomology/specimen products outside the useful vocabulary, brand-specific device terminology, and misleading mixed digital/health catalogs. Weak input, vocabulary gaps and category design remain distinct limitations. Paid prompt/model quality and latency were not measured; this result does not establish that a paid model is necessary or sufficient.', '',
    '| Classification/supply measure | Before | After |',
    '|---|---:|---:|',
    '| Successful classification completions | 24/24 | 24/24 |',
    '| Replacement confidence at least 55 | 9/24 (37.5%) | 19/24 (79.2%) |',
    '| Verified sample usable after classification | 9/24 (37.5%) | 22/24 (91.7%) |',
    '| Usable provisionally while awaiting replacement | 0 | 3 |',
    '| Full controlled classified usable supply | 352 | 365 |',
    '| Full controlled fresh readable verified supply | 377 | 377 |',
    '| Paid AI calls in this cycle | 0 | 0 |', '',
    'Of the 365 usable rows, 362 are nonprovisional (including unchanged legacy rows), and three are explicitly provisional. The frozen unchanged index has 384 usable classified rows at this clock; it does not gain supply in this cycle. Failed rechecks from the previous sample remain represented, so the controlled total remains below that frozen index.', '',
    'A first versioned signature no longer automatically erases an otherwise useful legacy classification. A fresh, sufficiently confident old classification can remain provisional until a passing replacement is stored, for at most seven days and never beyond its original verification expiry. Strong contradictory new product evidence prevents this carry. Reverification does not extend the provisional expiry. Weak replacement attempts leave classification pending for retry after one day; signature-conditional updates protect against superseded observations. Provisional metadata uses the existing catalog observation JSONB field.', '',
    'The three retained classifications are kitchenworldsupplies.com (Books & Media), thephotostick.com (Electronics & Gadgets), and pepticool.com (Health & Personal Care). Their attempted replacement scores are 21, 0 and 49, respectively. The retained values are explicitly stale/provisional, not claimed as new successful classifications. No comparable earlier versioned signatures exist for these 24 successes, so actual temporal catalog-change frequency is still unmeasured.', '',
    '## Retrieval and matching changes', '',
    'Recognized query intents now require matching product-family evidence in observed catalogs. General checks separate complete keyboards from keyboard covers, cosmetic product uses from apparel/artwork colors, and sleepwear from unrelated apparel/bags. Child-specific queries require child-audience evidence; coffee tables and sticker sheets do not establish coffee or bedding. Unknown intents and metadata-only legacy records retain prior behavior. No ranking weights or source-order policy were changed.', '',
    'The failing JSONB array overlap query was replaced with an OR of JSONB containment predicates. The existing JSONB GIN index can support this operator. Validation exercised actual PostgreSQL JSONB retrieval locally plus the Supabase client HTTP query encoding, without contacting production. See [Supabase containment documentation](https://supabase.com/docs/reference/python/contains). No schema or infrastructure change was required for this cycle.', '',
    '## Frozen and controlled benchmark', '',
    'P@5 and P@10 include empty ranks; useful/wrong rates use actual returned results. The endpoint returns at most eight suggestions, so P@10 is still divided by ten. Improvements in returned-result fractions must therefore be read alongside precision, coverage and errors.', '']
percent = lambda n: f'{100*n:.1f}%'
metrics = [('precision_at_5','Precision@5'),('precision_at_10','Precision@10'),
    ('useful_result_rate','Useful-result rate'),('obviously_wrong_rate','Obviously-wrong-result rate'),
    ('known_reference_recall','Known-competitor recall'),('unknown_rate','Unknown-result rate')]
for variant in ['frozen','controlled']:
    lines += ['### '+variant.title(), '', '| Metric | Description before | Description after | Structured before | Structured after |','|---|---:|---:|---:|---:|']
    series = [before[variant]['summary']['description_only']['core24'],after[variant]['summary']['description_only']['core24'],
        before[variant]['summary']['structured_profile']['core24'],after[variant]['summary']['structured_profile']['core24']]
    for key,title in metrics:
        lines.append('| '+title+' | '+' | '.join(percent(x[key]) for x in series)+' |')
    for key,title in [('three_useful_searches','Searches with at least 3 useful top-five results'),('returned','Returned results'),('useful','Useful results'),('wrong','Wrong results'),('errors','Endpoint errors')]:
        lines.append('| '+title+' | '+' | '.join(str(x[key])+('/24' if key=='three_useful_searches' else '') for x in series)+' |')
    lines.append('')
lines += ['## Regressions and unresolved quality risks', '',
    'Quince is the precision regression in the controlled comparison: description P@10 drops from 60% to 50%; structured P@5 from 60% to 40% and P@10 from 50% to 20%. Its broad clothing/home query loses useful results under the narrower matching/retrieval combination. This cycle does not claim perfect recall preservation. Full per-case regressions for both states are in `case-metrics.json`.', '',
    'Five core searches in each mode now have no eligible suggestions: Durston, Zpacks, Pipette, Tubby Todd and Babo Botanicals. The existing empty-result path responds with HTTP 500. The former Little Sleepies error is resolved, but total errors rise from one description / zero structured to five in each. These five searches already had zero useful results; rejecting their irrelevant results improves the wrong-result fraction without creating useful coverage. Returning an ordinary empty state remains an application follow-up.', '',
    'Infant skincare and mechanical keyboards still have zero useful precision. Product-family matching does not yet establish every niche constraint: ultralight function, materials, formulation, audience and actual substitution can remain wrong or merely adjacent. Missing stored product evidence can also evade these checks. Structured unknown-result rates exceed the original 5% limit. Known-reference recall remains 2/48 (4.2%) in both states/modes. These results fall well short of Acceptable.', '',
    '### Controlled niche Precision@5', '', '| Niche | Description before | Description after | Structured before | Structured after |','|---|---:|---:|---:|---:|']
for niche in before['controlled']['summary']['description_only']['core_by_niche']:
    vals=[obj['summary'][mode]['core_by_niche'][niche]['precision_at_5'] for mode in ['description_only','structured_profile'] for obj in [before['controlled'],after['controlled']]]
    lines.append('| '+niche.replace('_',' ')+' | '+' | '.join(percent(v) for v in vals)+' |')
lines += ['', '## Adjudication and validation', '',
    f"Every returned placement has an identity-associated label and rationale. There are {len(load(OUT/'adjudications.json'))} newly adjudicated variant/case/mode placements, representing 35 unique case/mode/domain identities across 19 merchants. Existing judgments are reused by identity, never by rank. The entry ledger also explicitly records every existing result crossing into the top five ({dict(Counter(r['variant'] for r in entries))} total entry reviews by state). Unknown identities remain unknown. This is a single analyst review, not an independent blinded panel.", '',
    '**260 tests passed**, with nine existing warnings; whitespace validation passed. Added regressions cover product-intent contradictions, valid product synonyms, sparse classifier inputs, unchanged text-query categories, provisional carry/expiry, contradictory replacement, successful replacement, and actual Supabase JSONB filter encoding. All 24 raw catalog signatures reproduced. Both local PostgreSQL retrieval captures contain the full requested channels; benchmark assertions reject missing channels or query-category drift. Original snapshot, health sample, labels and reference-panel hashes match the previous validation.', '',
    'Application files changed in this cycle: `app/services/store_index.py`, `app/services/discovery_quality.py`, new `app/services/product_intent.py`, `app/tasks/store_index.py`, and `app/api/v1/competitors.py`. Tests: `tests/test_bounded_cycle.py`. Local evaluation tools: `tests/evaluations/bounded_cycle_state.py`, `bounded_cycle_retrieval.mjs`, `bounded_cycle_benchmark.py`, `bounded_cycle_adjudication.py`, and this report packager. Earlier Phase 1 changes remain in the working tree and are not new changes attributed to this cycle.', '',
    'Offline reproduction order: run `bounded_cycle_state.py`; run `bounded_cycle_retrieval.mjs` with Node; run `bounded_cycle_benchmark.py frozen` and then `bounded_cycle_benchmark.py controlled`; run `bounded_cycle_adjudication.py`; run `bounded_cycle_report.py`. Use the existing virtual environment and retained raw artifacts. Do not rerun the old controlled report under new application code as though it were the historical before state.', '',
    '## Recommendation and stop point', '',
    '**Choose production-like access validation next**, bounded to the existing sample and using a safe non-production write target. The previous run was 85.1% blocked across all 248 stores and used the HTTPX fallback; classification now passes 79.2% of the 24 accessible catalogs, but that small, access-selected sample cannot establish broad pipeline capacity. A transport/scheduling validation should measure sustainable successful catalog access while respecting blocks and cooldowns. It requires a separate authorized next cycle, not broad acquisition.', '',
    'Retrieval/filtering remains the next product-quality follow-up, particularly broad-store recall, empty-result behavior and functional niche evidence. A paid classification experiment is optional for the five unresolved free replacements, with an explicit budget and accuracy/latency measurement; it is not justified as a prerequisite by current latency evidence. Acquisition remains deferred until access and usable yield are established. Ranking has not been tuned or isolated as the dominant cause.', '',
    'Stopped after this cycle. No deploy, push, merge, production Supabase write, paid AI or broad acquisition was performed. Durable measurements and all case/entry judgments are beside this report; raw catalogs, reconstructed local index and detailed retrieval captures remain under `outputs/`.', '']
(DEST/'RESULTS.md').write_text('\n'.join(lines),encoding='utf8')
print(json.dumps({'report':str(DEST/'RESULTS.md'),'entry_reviews':measurement['entry_reviews'],'regressions':len(regressions)}))
