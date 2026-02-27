# StoreScout
StoreScout is a lightweight competitor analysis tool that generates clean, actionable reports from Shopify stores.

Give it a store URL → it fetches public product data → normalizes it → produces a structured report you can use to understand pricing, product focus, and store strategy.

No accounts. No dashboards. Just results.

⸻

What StoreScout Does (v0)
	•	Fetches products from public Shopify storefront endpoints
	•	Handles pagination automatically
	•	Normalizes raw product data into a clean schema
	•	Prepares data for PDF competitor reports

This project is focused on speed, clarity, and usefulness — not hype.

Current Pipeline

Fetch → Normalize → Analyze → Report (PDF)

1. Fetch
	•	Uses Shopify public endpoints (/products.json)
	•	No API keys required
	•	Supports pagination with safety caps

2. Normalize
	•	Converts prices to numbers
	•	Computes min/max price per product
	•	Extracts availability and discount signals
	•	Limits images to essential assets
	•	Outputs a consistent internal JSON format

3. Analyze (WIP)
	•	Pricing strategy summary
	•	Discount usage
	•	Product freshness (new vs older products)
	•	Product prioritization signals

4. Report (Planned)
	•	HTML → PDF competitor report
	•	Shareable and printable
	•	Focused on decision-making, not raw dumps

⸻

Tech Stack
	•	Python
	•	httpx (HTTP requests)
	•	Playwright (fallback scraping + PDF generation)
	•	FastAPI (planned API layer)

⸻

Project Structure (early)

storescout/
├── scraper/
│   ├── fetch_products.py
│   ├── normalize_products.py
│   └── analyze_products.py
├── reports/
│   └── templates/
├── data/
│   ├── raw/
│   └── normalized/
├── main.py
└── README.md
Why This Exists

Most competitor research is:
	•	manual
	•	slow
	•	inconsistent

StoreScout compresses hours of research into minutes by extracting what stores are actually doing, not just what they look like.

⸻

What This Is NOT
	•	Not an ad spy tool
	•	Not revenue estimation
	•	Not an AI guessing engine
	•	Not a Shopify Admin API client

Everything is based on publicly accessible storefront data.

⸻

Status

🚧 In active development
Current focus: reliable scraping + clean data

Features will only be added if they directly improve decision-making.

⸻

Disclaimer

StoreScout only accesses publicly available data exposed by Shopify storefronts.
Users are responsible for complying with applicable laws and platform terms.
