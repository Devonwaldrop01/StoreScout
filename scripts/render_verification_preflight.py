"""Read configured runtime values without secrets, network calls or writes.

Run in an approved service shell or isolated image. Does not read app_config,
test Redis connectivity, fetch merchants, arm a canary or migrate anything.
"""
import json
import platform
from pathlib import Path
import sys
from urllib.parse import urlsplit, parse_qs
from importlib.metadata import version

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.core.config import get_settings
from app.services.fetch import _USE_CURL_CFFI, IMPERSONATE


def configured_values(settings):
    from app.core.index_hold import index_writes_held
    redis = urlsplit(settings.redis_url)
    api = urlsplit(settings.api_internal_url)
    query = parse_qs(redis.query)
    return {
        "python": platform.python_version(),
        "packages": {name:version(name) for name in ['redis','celery','httpx','curl-cffi','supabase']},
        "redis": {"scheme":redis.scheme,"host":redis.hostname,"port":redis.port,
                  "database":redis.path,"configured_ssl_cert_reqs":query.get('ssl_cert_reqs'),
                  "configured_ssl_check_hostname":query.get('ssl_check_hostname'),
                  "custom_ca_configured":bool(query.get('ssl_ca_certs') or query.get('ssl_ca_data'))},
        "api_internal_route": {"scheme":api.scheme,"host":api.hostname,"port":api.port,"path":api.path},
        "internal_secret_configured":bool(settings.internal_secret and settings.internal_secret!='dev-internal-secret'),
        "curl_cffi_selected":_USE_CURL_CFFI,"configured_impersonation":IMPERSONATE,
        "configured_index_enabled":settings.shopify_index_enabled,
        "effective_deployment_hold":index_writes_held(),
        "configured_verification_batch":settings.shopify_index_verify_batch,
        "configured_domain_concurrency":settings.shopify_index_concurrency,
        "configured_canary_enabled":getattr(settings,'store_index_canary_enabled',False),
        "canary_digest_configured":bool(getattr(settings,'store_index_canary_manifest_sha256','')),
        "runtime_database_overrides":"not read by this script",
    }


if __name__=='__main__':
    print(json.dumps(configured_values(get_settings()),indent=2))
