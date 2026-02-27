from __future__ import annotations
from typing import Any, Dict, List, Optional
import httpx

DEFAULT_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/121.0.0.0 Safari/537.36"
    ),
    "Accept": "application/json",
}

def fetch_products_shopify(store_url: str, max_products: Optional[int] = None) -> List[Dict[str, Any]]:
    products: List[Dict[str, Any]] = []
    page = 1
    MAX_PAGES = 10

    with httpx.Client(timeout=25.0, headers=DEFAULT_HEADERS, follow_redirects=True) as client:
        while page <= MAX_PAGES:
            url = f"{store_url.rstrip('/')}/products.json?limit=250&page={page}"
            r = client.get(url)
            ct = r.headers.get("content-type", "")
            if "application/json" not in ct:
                print("NOT JSON:", ct, "status:", r.status_code, "url:", str(r.url))
                print("BODY PREVIEW:", r.text[:200])
                break
            if r.status_code in (429, 403):
                print("BLOCKED/RATELIMIT:", r.status_code, "page:", page)
                break


            if r.status_code != 200:
                break

            data = r.json()
            batch = data.get("products", [])
            if not batch:
                break

            products.extend(batch)

            if max_products is not None and len(products) >= max_products:
                products = products[:max_products]
                break

            page += 1

    return products
