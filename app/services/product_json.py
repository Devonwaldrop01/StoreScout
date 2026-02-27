import httpx
import json
from app.services.normalize import normalize_product
from app.services.report import render_html, html_to_pdf

STORE_URL = "https://thenordstick.com"
MAX_PRODUCTS = 250

def fetch_all_products(store_url: str):
    products = []
    page = 1

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/121.0.0.0 Safari/537.36"
        ),
        "Accept": "application/json",
    }

    with httpx.Client(timeout=20.0, headers=headers, follow_redirects=True) as client:
        while len(products) < MAX_PRODUCTS:
            url = f"{store_url}/products.json?limit=250&page={page}"
            print(f"Fetching page {page}...")

            r = client.get(url)
            if r.status_code != 200:
                print(f"Stopped - status {r.status_code}")
                break

            data = r.json()
            batch = data.get("products", [])
            if not batch:
                print("No more products.")
                break

            products.extend(batch)
            products = products[:MAX_PRODUCTS]  # enforce cap
            page += 1

    return products

def main():
    products = fetch_all_products(STORE_URL)

    normalized_list = [normalize_product(p, STORE_URL) for p in products]

    result = {
        "store": {"base_url": STORE_URL, "product_count": len(normalized_list)},
        "products": normalized_list,
    }

    with open("normalized.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    print(f"Saved {len(normalized_list)} products → normalized.json")

if __name__ == "__main__":
    main()
