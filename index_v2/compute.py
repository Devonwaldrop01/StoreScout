"""Pure catalog/classification adapters. No legacy DB/broker/HTTP routes."""
from datetime import datetime, timezone
from app.services import verification_lifecycle as lifecycle
from app.services.store_index import build_knowledge_fields, derive_market_context
from app.services.discovery_quality import is_recent_verified, is_classification_usable


def verified_row(canonical, result):
    if lifecycle.classify_probe(result,60)!='verified_shopify': return None
    p=result.get('profile') or {}
    # Public catalog facts only: never retain contact emails, cookies or HTML.
    fields={k:p.get(k) for k in ('brand_name','language','product_count','median_price','min_price',
        'max_price','price_p25','price_p75','currency','promo_rate','collections','product_types','product_titles','tags','vendors')}
    fields.update(domain=canonical,description=p.get('meta_description'),homepage_message=p.get('meta_description'),
        **derive_market_context(p.get('product_count'),p.get('median_price')))
    fields.update(lifecycle.successful_fields(result['catalog_observation'],result['confidence'],result.get('signals')))
    fields['catalog_observation']['classification_state']='pending'
    fields['updated_at']=datetime.now(timezone.utc).isoformat()
    return fields


def classify(row):
    payload,classification=build_knowledge_fields(row,allow_paid=False)
    out={**row,**payload}
    eligible=is_recent_verified(out) and is_classification_usable(out) and (out.get('category_confidence') or 0)>=55
    reason=None if eligible else 'classification_below_55' if classification['confidence']<55 else 'catalog_not_current'
    return {'row':out,'eligible':eligible,'reason':reason}


def retry_time(job,state,retry_after=None,now=None):
    now=now or datetime.now(timezone.utc)
    fields=lifecycle.retry_fields({'domain':job['canonical'],'verification_attempts':job['attempts']-1},state,now)
    due=lifecycle.timestamp(fields['next_verification_at'])
    advised=lifecycle.timestamp(retry_after)
    return max(due,advised).timestamp() if advised else due.timestamp()
