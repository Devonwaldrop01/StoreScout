"""Offline exhaustive relevance ceiling. Judgment rules below are EVALUATION DATA.

Never imported by the application. No acquisition, model call, DB or endpoint call.
Reads the preserved 88-row snapshot and 50 complete pre-filter ranking traces.
"""
import collections
import csv
import hashlib
import json
import math
import socket
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))


def forbidden(*args, **kwargs):
    raise AssertionError('This evaluation must not access the network')


socket.create_connection = forbidden
socket.socket.connect = forbidden
socket.socket.connect_ex = forbidden
from app.services.discovery_quality import relevance

SOURCE = ROOT / 'outputs/discovery-quality-fixed-supply'
OUT = ROOT / 'docs/quality-audit/discovery-quality/ceiling'
load = lambda p: json.loads(p.read_text(encoding='utf8'))

# Manual catalog review for the 34 original records; V2's 54 complete reviews
# are reused, not inferred from their sometimes-incorrect category fields.
LEGACY = '''
accessprive.com|Luxury designer footwear and apparel
bemodestboutique.com|Modest adult women's dresses, skirts, tops and swimwear
bengalsandbandits.com|Licensed sports-fan apparel including infant onesies; not bamboo sleepwear
blueingreensoho.com|Specialist Japanese/American denim and apparel
broadrivermercantile.com|Outdoor/hunting apparel retailer; Filson travel backpacks, no sampled hiking shelters
cheesebros.com|Wisconsin cheeses and charcuterie gifts for human consumption
dickies.com|Durable occupational workwear and scrubs, with incidental backpacks
elevateyoursole.co.uk|Comfort footwear retailer and accessories
fetchyourpetneeds.ie|Pet food/treats retailer; prior official evidence establishes freeze-dried/raw treats
freezbone.com|Dog enrichment/refillable toys and treats; freeze-dried single-protein not established
heavensentandco.com|Small-batch fashion jewelry and graphic/style apparel
hibobbie.com|Infant formula and maternal supplements; not baby topical skincare
hydrusboardtech.com|Paddleboards, dry backpack and water-sport accessories
i-blason.com|Phone/tablet cases; Smart Keyboard type is not evidence of mechanical keyboards
inspiredgo.ca|Prepared salads and healthy meal delivery
komusodesign.com|Breathing/mindfulness necklaces and wellness accessories
marcrobinsonjewelers.com|Diamond bridal/engagement rings, fine jewelry
memoky.com|Modern furniture; Coffee category comes from coffee tables, not coffee beans
mooncarstereo.com|Car audio speakers, amplifiers and installation components
nursingqueen.com|Breastfeeding/nursing adult clothes, not infant bamboo sleepwear
onedamelane.com|Bridal/demi-fine/silver jewelry specialist
peachandlily.com|Korean skincare; prior official evidence establishes lightly tinted mineral Sun Cover SPF
poptoptoys.com|Retro/classic toys, novelty games and gifts
queensupplies.com|Nail-salon supplies/pedicure lotion; no face-color or infant-formulation evidence
redbarn.com|Dog food/chews; prior evidence establishes single-meat air-dried training treats
rumpl.com|Outdoor puffy/wool blankets, mats and towels; no tents or home sheet/duvet assortment evidenced
sandmarc.com|Phone photography gear, cases and travel accessories
shopelvis.com|Licensed Elvis merchandise, music and themed apparel/gifts
shopluxelifeboutique.com|Adult fashion dresses and rompers; baby blue/babydoll are not infant products
tasteofbritain.com|British grocery/giftware including tea towels; not bed/bath linen specialist
tower28beauty.com|Sensitive-skin complexion/color cosmetics, tinted SPF and skincare
ultimatesportnutrition.us|Sports supplements/protein nutrition, not coffee roaster or pet treats
vicegolf.com|Golf balls/clubs and branded sporting apparel, not general essentials
wixez.com|Fashion watches and prescription/sunglass frames
'''

# These lists are explicit catalog adjudications, not word-based label generation.
# Label 2 includes useful partial competitors under the FROZEN protocol.
GROUPS = {
 'shelter': ('Ultralight hiking tents/shelters or genuinely hiking-specific lightweight packs', [],
             '1036emporium.com broadrivermercantile.com rumpl.com merino.tech hydrusboardtech.com theclosetinc.com'),
 'complexion': ('Tinted SPF / complexion or face-color cosmetics',
                ['peachandlily.com', 'tower28beauty.com'],
                'kbeauty.us thekimyoung.com welcometowondervalley.com queensupplies.com'),
 'baby_skin': ('Baby-appropriate sensitive/fragrance-free topical skin products; not generic adult lotion', [],
               'kbeauty.us thekimyoung.com peachandlily.com tower28beauty.com welcometowondervalley.com shoutandabout.com aubongoutboutique.com zerowastecartel.com'),
 'coffee': ('Specialty roasted coffee beans with home delivery/subscription', ['madcapcoffee.com'],
            'aubongoutboutique.com tasteofbritain.com'),
 'baby_sleep': ('Bamboo infant/child sleepwear, sleep bags or matching pajamas', [],
               'tuttifruttikidsco.com merino.tech uk.sunnylife.com bengalsandbandits.com 74manstore.com wilkinsandolander.com nursingqueen.com'),
 'dog_treats': ('Freeze-dried/raw/single-protein edible dog treats; useful training substitutes allowed by frozen labels',
                ['fetchyourpetneeds.ie', 'redbarn.com'],
                'freezbone.com thesocialdawg.com highspeedgear.com broadrivermercantile.com'),
 'quince': ('Broad adult everyday apparel/accessories or home essentials; specialist merchandise/luxury is only adjacent',
            ['thezerano.com', 'arlingtontx.clothesmentor.com', 'wilkinsandolander.com', 'shoppandcboutique.com', 'shopworthandgray.com'],
            # Populated below from an explicit manually reviewed domain list.
            '1036emporium.com 74manstore.com accessprive.com amorcustomgifts.com andyfrisella.com aprasi.com artonwheels.co aubongoutboutique.com australian-native.com.au bemodestboutique.com bengalsandbandits.com blueingreensoho.com broadrivermercantile.com butteriedish.com claymoreshop.com cougarpaws.com dc2miami.com designerrevival.com dickies.com elevateyoursole.co.uk headingprints.com heavensentandco.com highspeedgear.com hydrusboardtech.com i-blason.com jmrhousetohome.ie komusodesign.com leahmaria.dk marcrobinsonjewelers.com meadow-nest.com megafootystore.com.au memery.eu memoky.com merino.tech nursingqueen.com onedamelane.com pintrill.com profilefashion.com riverbendfairhope.com rumpl.com sandmarc.com shopcasinoquest.com shopelvis.com shopluxelifeboutique.com shoutandabout.com stagecoachgifts.biz supernovacalzature.com tasteofbritain.com theclosetinc.com thewindopal.com tuttifruttikidsco.com uk.sunnylife.com us.thesomewhereco.com vicegolf.com vie-riche.com welcometowondervalley.com wixez.com woodtonestrings.com wragal.com zerowastecartel.com'),
 'bedding': ('Consumer bed sheets, comforters or duvet bedding; personalized bedding is a useful partial comparison',
             ['amorcustomgifts.com'], 'jmrhousetohome.ie rumpl.com aubongoutboutique.com uk.sunnylife.com welcometowondervalley.com tasteofbritain.com'),
 'linen': ('Linen bed/bath assortment, not clothing linen or unrelated table linen', [],
           'amorcustomgifts.com jmrhousetohome.ie rumpl.com aubongoutboutique.com uk.sunnylife.com welcometowondervalley.com tasteofbritain.com'),
 'keyboard': ('Complete mechanical keyboards; not tablet keyboard cases, audio parts or game consoles', [],
              'i-blason.com suncoastaudiodirect.com'),
}
CASE_GROUPS = {
 'shelter': 'durstongear zpacks gossamergear',
 'complexion': 'iliabeauty tower28beauty saiehello colourpop',
 'baby_skin': 'pipettebaby tubbytodd babobotanicals',
 'coffee': 'onyxcoffeelab counterculturecoffee vervecoffee',
 'baby_sleep': 'littlesleepies kytebaby birdiebean',
 'dog_treats': 'purebites stewartpet stellaandchewys',
 'quince': 'quince', 'bedding': 'brooklinen', 'linen': 'parachutehome',
 'keyboard': 'keychron nuphy epomaker',
}
NEW_USEFUL = {
 'shoppandcboutique.com': 'Sample has adult cardigans, knit tops, jeans, jackets, pants and necklaces; types also include bags. Useful partial apparel/accessory assortment comparison on the same basis as the preserved Wilkins & Olander judgment. Price parity/home assortment are NOT established.',
 'shopworthandgray.com': 'Sample has shirts, jeans, sweaters, jackets, pants and a necklace/belts; description confirms a general womenswear/accessory boutique. Useful partial apparel comparison, not proven price parity or home/bedding equivalence. Proprietary product names weaken current token matching.',
}


def channel_members(row, trace):
    """Exact recorded EQ/GTE/OR predicates on this bounded 88-row input.

    PostgreSQL channel membership is asserted against the retained real SQL
    output. This is a consistency check, not a new retrieval treatment.
    There are <200 rows, so no LIMIT truncation; category/string inputs are ASCII.
    """
    for op, args, _ in trace['ops']:
        if op == 'eq' and row.get(args[0]) != args[1]: return False
        if op == 'gte' and (row.get(args[0]) or 0) < args[1]: return False
        if op == 'or_':
            expr = args[0]
            if trace['channel'] == 'dna':
                # JSON singleton strings may have punctuation; decode each JSON.
                values = expr.split('dna_keywords.cs.')[1:]
                ok = any(json.loads(v.rstrip(','))[0] in (row.get('dna_keywords') or []) for v in values)
            else:
                parts = [x.split('.ilike.', 1) for x in expr.split(',')]
                ok = any(pattern.strip('%').lower() in str(row.get(col) or '').lower() for col, pattern in parts)
            if not ok: return False
    return True


def metric_ceiling(counts, k):
    return sum(min(k, n) for n in counts) / (len(counts) * k)


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    rows = load(SOURCE / 'combined.json')
    assert (SOURCE/'combined.json').read_bytes() == (ROOT/'outputs/index-v2-pilot-100/benchmark/combined.json').read_bytes()
    by_domain = {r['domain']: r for r in rows}
    runs = load(SOURCE / 'combined/evidence/replay-results.json')
    cases = [r for r in runs if r['mode'] == 'description_only']
    assert len(rows) == len(by_domain) == 88 and len(cases) == 25 and len(runs) == 50
    audits = {r['domain']: r for r in load(OUT.parent / 'eligible-store-audit.json')}
    reviews = {d: r['observed_niche'] + '. ' + r['rationale'] for d, r in audits.items()}
    reviews.update(dict(line.split('|', 1) for line in LEGACY.strip().splitlines()))
    assert set(reviews) == set(by_domain)
    groups = {c: g for g, cs in CASE_GROUPS.items() for c in cs.split()}
    assert set(groups) == {c['case_id'] for c in cases}
    prior_files = [ROOT / p for p in [
      'docs/quality-audit/real-world/evidence/relevance-labels.json',
      'docs/quality-audit/index-growth/frozen/relevance-labels.json',
      'docs/quality-audit/index-growth/controlled/relevance-labels.json',
      'docs/quality-audit/index-growth/new-judgments.json',
      'outputs/index-v2-pilot-100/benchmark/new-judgments.json',
      'outputs/discovery-quality-fixed-supply/new-judgments.json']]
    prior = {}
    for f in prior_files:
        for r in load(f):
            if r['domain'] in by_domain:
                prior[(r['case_id'], r['mode'], r['domain'])] = {**r, 'file': str(f.relative_to(ROOT))}
    matrix = []
    for c in cases:
        need, useful, adjacent = GROUPS[groups[c['case_id']]]
        for d in by_domain:
            old = [prior[(c['case_id'], m, d)] for m in ['description_only', 'structured_profile'] if (c['case_id'], m, d) in prior]
            assert len({r['label'] >= 2 for r in old}) <= 1, ('usefulness disagreement', c['case_id'], d)
            if d == c['domain']:
                label, why = 0, 'The query business itself is not a competitor; retain it in supply, exclude from useful availability.'
            elif old:
                label, why = old[-1]['label'], old[-1]['rationale']
            elif d in useful:
                label, why = 2, NEW_USEFUL[d]  # All other useful pairs must already have frozen judgments.
            elif d in adjacent.split():
                label, why = 1, f'Adjacent catalog ({reviews[d]}). Specific query requirement is not established: {need}. Do not promote unknown attributes to useful.'
            else:
                label, why = 0, f'Observed catalog ({reviews[d]}) supplies no relevant product/use-case evidence for: {need}. This is a saved-evidence judgment, not a complete live-catalog absence claim.'
            matrix.append({'case_id': c['case_id'], 'business': c['business'], 'domain': d,
                           'label': label, 'classification': 'useful' if label >= 2 else 'adjacent' if label == 1 else 'irrelevant',
                           'rationale': why, 'provenance': 'preserved_adjudication' if old else 'new_catalog_review',
                           'prior_labels': old, 'catalog_evidence_ref': d})
    labels = {(r['case_id'], r['domain']): r['label'] for r in matrix}
    assert len(matrix) == 2200 and len(labels) == 2200
    evidence = [{'domain': r['domain'], 'review': reviews[r['domain']], 'saved_record': r,
                 'classification_concern': audits.get(r['domain'], {}).get('review_status', 'not_in_targeted_25')}
                for r in rows]
    per_query, misses, near, channels_checked = [], [], [], 0
    for c in cases:
        cid = c['case_id']; useful = [d for d in by_domain if labels[cid, d] >= 2]
        entry = {'case_id': cid, 'business': c['business'], 'query': c['query'],
                 'useful_count': len(useful), 'useful_domains': useful,
                 'adjacent_count': sum(labels[cid, d] == 1 for d in by_domain), 'modes': {}}
        for run in [r for r in runs if r['case_id'] == cid]:
            mode = run['mode']; ranked = {r['domain']: r for r in run['ranked']}
            candidates = set().union(*(set(t.get('domains', [])) for t in run['retrieval']))
            assert candidates == set(ranked)
            for d, trace in ranked.items():
                assert relevance(by_domain[d], run['user_match_ctx']) == trace['match'], ('score/intent drift', cid, mode, d)
            for t in run['retrieval']:
                observed = {r['domain'] for r in rows if channel_members(r, t)}
                assert observed == set(t['domains']), (cid, t['channel'], observed ^ set(t['domains']))
                channels_checked += 1
            # Preserve the actual score order; lift ONLY the result cap to inspect
            # eligible ranks 9-20. This is diagnostic, never a new product result.
            survivors = [r for r in run['ranked'] if not r['exclusions']]
            assert [r['domain'] for r in survivors[:8]] == run['returned_domains']
            survivor_rank = {r['domain']: i for i, r in enumerate(survivors, 1)}
            entry['modes'][mode] = {
              'useful_top5': sum(d in useful for d in run['returned_domains'][:5]),
              'useful_top10': sum(d in useful for d in run['returned_domains'][:10]),
              'never_candidate': [d for d in useful if d not in candidates],
              'not_returned': [d for d in useful if d not in run['returned_domains']],
              'returned_below5': [d for d in run['returned_domains'][5:] if d in useful],
              'all_survivor_useful_below5': [d for d in useful if survivor_rank.get(d, 0) > 5],
              'candidate_count': len(candidates), 'survivor_count': len(survivors),
              'useful_survivor_6_20': [r['domain'] for r in survivors[5:20] if r['domain'] in useful],
            }
            for stage, rr in [('pre_filter', run['ranked']), ('post_filter_uncapped', survivors)]:
                near.append({'case_id': cid, 'mode': mode, 'stage': stage,
                  'positions_6_20': [{'rank': i, **r, 'label': labels[cid, r['domain']]} for i, r in enumerate(rr, 1) if 6 <= i <= 20]})
            for d in useful:
                actual = run['returned_domains'].index(d) + 1 if d in run['returned_domains'] else None
                if actual and actual <= 5: continue
                trace = ranked.get(d); blockers = []
                if trace:
                    blockers = [{'domain': x['domain'], 'label': labels[cid, x['domain']],
                                 'score': x['match']['score'], 'gap': round(x['match']['score'] - trace['match']['score'], 2)}
                                for x in survivors[:5] if labels[cid, x['domain']] < 2]
                ties = [x for x in blockers if 0 <= x['gap'] <= .1]
                reason = ('never_entered_candidate_set' if not trace else 'filtered' if trace['exclusions'] else
                          'tied_or_near_tied_with_nonuseful' if ties else 'survived_scored_too_low')
                misses.append({'case_id': cid, 'mode': mode, 'domain': d, 'failure_type': reason,
                               'actual_rank': actual, 'uncapped_survivor_rank': survivor_rank.get(d),
                               'trace': trace, 'top5_nonuseful_blockers': blockers, 'near_ties_0_1_score': ties,
                               'classification_concern': audits.get(d, {}).get('review_status', 'not_in_targeted_25')})
        per_query.append(entry)
    counts = [r['useful_count'] for r in per_query]
    refs = [r for c in cases for r in c['references']]
    present_refs = sum(r['domain'] in by_domain for r in refs)
    assert len(refs) == 50 and present_refs == 2
    concerns = {d: a for d, a in audits.items() if a['review_status'] != 'supported'}
    assert len(concerns) == 25
    classification_review = []
    for d, a in concerns.items():
        pairs = [r for r in matrix if r['domain'] == d and r['label'] >= 2]
        # No useful pair => cannot attribute a missed USEFUL match to this defect.
        # Do not mistake a counterfactual category repair of irrelevant records for recall.
        classification_review.append({'domain': d, 'concern': a['review_status'], 'rationale': a['rationale'],
          'benchmark_useful_pairs': [r['case_id'] for r in pairs],
          'missed_useful_pairs': [m for m in misses if m['domain'] == d],
          'conclusion': 'No demonstrated useful benchmark pair, so no useful miss attributable to this defect.' if not pairs else 'Inspect useful-pair traces.'})
    z = 1.96; p = .54; n = 100
    center = (p + z*z/(2*n))/(1+z*z/n)
    half = z*math.sqrt(p*(1-p)/n+z*z/(4*n*n))/(1+z*z/n)
    summary = {
      'source_commit': '8bdc0ef6881107c713a28e1d6f6e3ab1f1056e4f',
      'stores': 88, 'queries': 25, 'matrix_pairs': 2200,
      'matrix_labels': dict(collections.Counter(r['classification'] for r in matrix)),
      'preserved_judgment_pairs': sum(r['provenance'] == 'preserved_adjudication' for r in matrix),
      'useful_query_store_pairs': sum(counts),
      'availability_distribution': {str(k): {'queries': counts.count(k), 'percent': counts.count(k)*4} for k in (0, 1, 2)},
      'availability_3plus': {'queries': sum(n >= 3 for n in counts), 'percent': sum(n >= 3 for n in counts)*4},
      'perfect_supply_ceiling': {'p5': metric_ceiling(counts, 5), 'p10': metric_ceiling(counts, 10),
        'searches_three_useful_top5': sum(n >= 3 for n in counts),
        'current_top8_cap_p10_ceiling': sum(min(8, n) for n in counts)/250},
      'missing_useful_slots_to_three': sum(max(0, 3-n) for n in counts),
      'known_references': {'relationships': len(refs), 'present': present_refs, 'absent': len(refs)-present_refs, 'recall_ceiling': present_refs/len(refs)},
      'misses_by_mode': {m: dict(collections.Counter(r['failure_type'] for r in misses if r['mode'] == m)) for m in ['description_only', 'structured_profile']},
      'classification_concern_stores': len(concerns),
      'classification_attributable_useful_misses': sum(bool(r['missed_useful_pairs']) for r in classification_review),
      'classification_concern_useful_pairs': sum(len(r['benchmark_useful_pairs']) for r in classification_review),
      'sql_membership_assertions_passed': channels_checked,
      'pilot_expansion_estimate': {'domains': 500, 'point_eligible': 270,
         'wilson95_yield': [center-half, center+half], 'yield_interval_times_500': [500*(center-half), 500*(center+half)],
         'caution': 'Sampling-only uncertainty; prior pilot may not represent next batch. Not a guarantee or a prediction of useful benchmark competitors.'},
      'decision': 'B — bounded 500-domain expansion, separate approval required; no execution',
    }
    summary['current'] = {}
    for mode in ['description_only', 'structured_profile']:
        mm = [q['modes'][mode] for q in per_query]
        summary['current'][mode] = {'useful_top5': sum(x['useful_top5'] for x in mm),
          'useful_top10': sum(x['useful_top10'] for x in mm),
          'p5': sum(x['useful_top5'] for x in mm)/125, 'p10': sum(x['useful_top10'] for x in mm)/250,
          'perfect_ranking_existing_survivors_p5': sum(min(5, q['useful_count'] - len(q['modes'][mode]['never_candidate']) - sum(m['failure_type']=='filtered' and m['case_id']==q['case_id'] and m['mode']==mode for m in misses)) for q in per_query)/125,
          'queries_useful_survivors_6_20': [q['case_id'] for q in per_query if q['modes'][mode]['useful_survivor_6_20']]}
    downgraded = [q['useful_count'] - (2 if q['case_id'] == 'quince' else 0) for q in per_query]
    summary['sensitivity_new_partial_labels_downgraded'] = {'p5': metric_ceiling(downgraded,5), 'p10': metric_ceiling(downgraded,10), 'three_useful_queries':sum(n>=3 for n in downgraded)}
    inputs = [SOURCE/'combined.json', SOURCE/'legacy.json', SOURCE/'v2.json', SOURCE/'clock.json',
              SOURCE/'combined/evidence/replay-results.json',
              ROOT/'outputs/index-v2-pilot-100/pilot-results-20260922.sqlite', *prior_files,
              OUT.parent/'eligible-store-audit.json', ROOT/'app/services/product_intent.py',
              ROOT/'app/services/discovery_quality.py', ROOT/'app/api/v1/competitors.py']
    summary['input_sha256'] = {p.relative_to(ROOT).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
    assert summary['input_sha256']['outputs/index-v2-pilot-100/pilot-results-20260922.sqlite'] == '6c5b00b34188892f87cba9a6a7b6ede520c4d237d547f14264236e10538c5a26'
    for name, data in [('relevance-matrix', matrix), ('catalog-evidence', evidence), ('per-query', per_query),
                       ('useful-misses', misses), ('near-misses', near), ('classification-contribution', classification_review), ('summary', summary)]:
        (OUT/f'{name}.json').write_text(json.dumps(data, indent=2, ensure_ascii=False)+'\n', encoding='utf8')
    with (OUT/'per-query.csv').open('w', newline='', encoding='utf8') as f:
        writer=csv.DictWriter(f,fieldnames=['business','useful_available','useful_domains','description_top5','description_top10','structured_top5','structured_top10','description_not_returned','structured_not_returned'])
        writer.writeheader()
        for q in per_query:
            d=q['modes']['description_only']; s=q['modes']['structured_profile']
            writer.writerow(dict(business=q['business'],useful_available=q['useful_count'],useful_domains='; '.join(q['useful_domains']),description_top5=d['useful_top5'],description_top10=d['useful_top10'],structured_top5=s['useful_top5'],structured_top10=s['useful_top10'],description_not_returned='; '.join(d['not_returned']),structured_not_returned='; '.join(s['not_returned'])))
    print(json.dumps({k:v for k,v in summary.items() if k!='input_sha256'}, indent=2))


if __name__ == '__main__':
    main()
