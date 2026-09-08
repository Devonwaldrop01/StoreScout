"""One TLS policy for the broker and direct index coordination clients."""
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit


def secure_redis_url(url: str) -> str:
    parts = urlsplit(url)
    if parts.scheme != "rediss":
        return url
    # URL parameters override redis-py kwargs. Replace even legacy CERT_NONE
    # instead of allowing it to disable validation or fail string parsing.
    query = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True)
             if k not in {"ssl_cert_reqs", "ssl_check_hostname"}]
    query.extend([("ssl_cert_reqs", "required"), ("ssl_check_hostname", "true")])
    return urlunsplit(parts._replace(query=urlencode(query)))


def coordination_redis():
    import redis
    from app.core.config import get_settings
    return redis.from_url(secure_redis_url(get_settings().redis_url),
                          socket_connect_timeout=2, socket_timeout=2,
                          retry_on_timeout=False)
