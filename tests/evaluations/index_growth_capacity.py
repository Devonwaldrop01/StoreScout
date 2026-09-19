"""Transparent capacity scenarios, NOT measured production performance."""
import json, math
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
out=ROOT/'docs/quality-audit/index-growth'
models={
 'adverse_sample':{'verify':24/248,'classify':20/36,'extra_verification_attempts':1},
 'planning_assumption':{'verify':.4,'classify':.6,'extra_verification_attempts':.5},
 'favorable_sample':{'verify':36/49,'classify':20/36,'extra_verification_attempts':.25},
}
def estimate(n,m):
    attempts=math.ceil(n*(1+m['extra_verification_attempts']))
    verified=n*m['verify']; usable=verified*m['classify']
    # Budget one retry for each low-confidence classification, credit no retry
    # yield until measured. Long-term retry accumulation is outside this model.
    classifications=math.ceil(verified*(2-m['classify']))
    return {'unique_domains':n,'verification_attempt_budget':attempts,
      'extra_attempt_budget':attempts-n,'expected_verified_first_pass':round(verified),
      'expected_new_usable_first_pass':round(usable),'classification_attempt_budget':classifications,
      'dispatch_capacity_days_at_100pct':round(max(attempts/9600,classifications/7200),2),
      'dispatch_capacity_days_at_50pct':round(max(attempts/4800,classifications/3600),2),
      'merchant_logical_requests_range':[attempts,4*attempts],
      'illustrative_paid_AI_usd':round(classifications*.0056,2)}
result={'warning':'Scenario assumptions, not confidence intervals or completion promises. New merchant I/O not performed. Retries add load but no credited yield.',
 'capacity':{'verification_slots_daily':9600,'classification_slots_daily':7200,
 'batch':100,'merchant_concurrency':3,'celery_process_concurrency':2,'utilization_range':[.5,1]},
 'cost_assumption':'Optional paid path: 2,000 combined input tokens + maximum 720 combined output tokens per classification/DNA pair, $1/$5 per million; $0.0056. Inputs/latency unmeasured; retries/longer inputs can cost more. Free path $0.',
 'pricing_source':'https://platform.claude.com/docs/en/about-claude/pricing',
 'models':{},'targets':{}}
for name,m in models.items():
    result['models'][name]={'assumptions':m,'runs':[estimate(n,m) for n in [1000,5000,10000,25000,37877]]}
    result['targets'][name]=[]
    for target in [1000,5000,10000,25000]:
        n=math.ceil((target-34)/(m['verify']*m['classify']))
        result['targets'][name].append({'target_usable':target,**estimate(n,m),
            'fits_current_37877_backlog':n<=37877})
(out/'capacity-scenarios.json').write_text(json.dumps(result,indent=2),encoding='utf8')
print('Planning assumption:')
for r in result['models']['planning_assumption']['runs']: print(r)
print('Targets:')
for r in result['targets']['planning_assumption']: print(r)
