import json
from urllib.parse import urlparse

def normalize_store_url(url: str) -> str:
    if not url.startswith("http"):
        url = "https://" + url
    p = urlparse(url)
    return f"{p.scheme}://{p.netloc}"

def to_float(x):
    if x is None:
        return None
    try:
        return float(x)
    except Exception:
        return None

def normalize_product(p: dict, base_url: str) -> dict:
    variants = p.get("variants", [])
    prices = [to_float(v.get("price")) for v in variants if v.get("price") is not None]
    compare_prices = [to_float(v.get("compare_at_price")) for v in variants if v.get("compare_at_price")]

    available = any(v.get("available") for v in variants)

    out = {
        "id": p.get("id"),
        "title": p.get("title"),
        "handle": p.get("handle"),
        "product_url": f"{base_url}/products/{p.get('handle')}",
        "created_at": p.get("created_at"),
        "published_at": p.get("published_at"),
        "updated_at": p.get("updated_at"),
        "vendor": p.get("vendor"),
        "tags": p.get("tags", []),
        "variants_count": len(variants),
        "available": bool(available),
        "price_min": min(prices) if prices else None,
        "price_max": max(prices) if prices else None,
        "compare_at_min": min(compare_prices) if compare_prices else None,
        "compare_at_max": max(compare_prices) if compare_prices else None,
        "images": [img.get("src") for img in p.get("images", [])[:3] if img.get("src")],
    }

    # derived helpers (useful later)
    if out["compare_at_min"] and out["price_min"]:
        out["discount_pct_min"] = round((out["compare_at_min"] - out["price_min"]) / out["compare_at_min"] * 100, 1)
    else:
        out["discount_pct_min"] = None

    return out

def main():
    # change this to the store you tested
    store_url = "https://thenordstick.com"
    base_url = normalize_store_url(store_url)

    with open("raw.json", "r", encoding="utf-8") as f:
        raw = json.load(f)

    products = raw.get("products", [])
    normalized = [normalize_product(p, base_url) for p in products]

    result = {
        "store": {"base_url": base_url, "product_count": len(normalized)},
        "products": normalized,
    }

    with open("normalized.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print(f"Normalized {len(normalized)} products → normalized.json")

if __name__ == "__main__":
    main()