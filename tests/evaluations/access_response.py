"""Decode once when adapting either transport to the common response interface."""
import httpx

SAFE_HEADERS=['content-type','server','retry-after','cf-mitigated','x-shopify-stage','x-shopify-shop-api-call-limit']

def decoded_response(status,headers,body,url):
    return httpx.Response(status,headers={k.lower():v for k,v in headers.items() if k.lower() in SAFE_HEADERS},
                          content=bytes(body),request=httpx.Request('GET',url))
