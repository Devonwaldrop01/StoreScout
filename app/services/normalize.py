import json
import math
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
        value = float(x)
        return value if math.isfinite(value) and value >= 0 else None
    except Exception:
        return None

def normalize_product(p: dict, base_url: str) -> dict:
    variants = [v for v in (p.get("variants") or []) if isinstance(v, dict)]
    prices = [n for v in variants if (n := to_float(v.get("price"))) is not None]
    compare_prices = [n for v in variants if (n := to_float(v.get("compare_at_price"))) is not None]
    # A markdown is evidence about ONE variant. Independent minima may belong
    # to different variants and cannot establish a discount.
    discounts = []
    for variant in variants:
        price = to_float(variant.get("price"))
        compare = to_float(variant.get("compare_at_price"))
        if price is not None and compare is not None and compare > price:
            discounts.append(round((compare - price) / compare * 100, 2))

    observed_availability = [v["available"] for v in variants if isinstance(v.get("available"), bool)]
    available = True if True in observed_availability else (False if variants and len(observed_availability) == len(variants) else None)

    minimum_price = min(prices) if prices else None
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
        "available": available,
        "price_min": minimum_price,
        "price_min_variant_ids": [str(v["id"]) for v in variants if v.get("id") is not None
                                  and prices and to_float(v.get("price")) == minimum_price],
        "price_max": max(prices) if prices else None,
        "compare_at_min": min(compare_prices) if compare_prices else None,
        "compare_at_max": max(compare_prices) if compare_prices else None,
        "images": [img.get("src") for img in p.get("images", [])[:3] if img.get("src")],
    }

    # derived helpers (useful later)
    out["discount_pct_min"] = min(discounts) if discounts else None
    out["discount_pct_max"] = max(discounts) if discounts else None
    out["discount_method"] = "same_variant"
    out["priced_variants_count"] = len(prices)

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
