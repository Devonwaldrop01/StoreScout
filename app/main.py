from __future__ import annotations

import re
from pathlib import Path

from jinja2 import Environment, FileSystemLoader
from fastapi import FastAPI, Form, HTTPException, Request, Body, Query
from fastapi.responses import HTMLResponse, FileResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
import os
from typing import Optional, Dict, Any
from urllib.parse import urlparse
import requests
from dotenv import load_dotenv


load_dotenv()  # This must be called before os.getenv

import base64
import stripe
import resend
# Support both layouts:
# 1) flat files in the project root (fetch.py, normalize.py, analyze.py, report.py)
# 2) package layout (app/services/*.py)
try:
    from fetch import fetch_products_shopify  # type: ignore
    from normalize import normalize_product  # type: ignore
    from analyze import analyze_products  # type: ignore
    from report import render_report_html, html_to_pdf  # type: ignore
except Exception:
    from app.services.fetch import fetch_products_shopify  # type: ignore
    from app.services.normalize import normalize_product  # type: ignore
    from app.services.analyze import analyze_products  # type: ignore
    from app.services.report import render_report_html, html_to_pdf  # type: ignore
import time
from fastapi.responses import FileResponse


BASE_DIR = Path(__file__).resolve().parent

# Try both:
# - ./templates (recommended)
# - project root (when user keeps html files next to main.py)
TEMPLATES_DIR = (BASE_DIR / "templates") if (BASE_DIR / "templates").exists() else BASE_DIR

# Keep outputs next to project unless a parent outputs/ exists
OUTPUTS_DIR = (BASE_DIR / "outputs")

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY", "")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET", "")
STRIPE_PAYMENT_LINK_URL = os.getenv("STRIPE_PAYMENT_LINK_URL", "")
DEV_SKIP_PAYMENT = os.getenv("DEV_SKIP_PAYMENT", "false").lower() == "true"

RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
RESEND_FROM = os.getenv("RESEND_FROM", "")

stripe.api_key = STRIPE_SECRET_KEY
resend.api_key = RESEND_API_KEY


app = FastAPI(title="StoreScout")

from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Mount new v1 API routers
from app.api.v1.competitors import router as competitors_router
from app.api.v1.alerts import router as alerts_router
from app.api.v1.user import router as user_router
from app.api.v1.webhooks import router as webhooks_router
from app.api.v1.internal import router as internal_router
from app.api.v1.billing import router as billing_router

app.include_router(competitors_router, prefix="/api/v1")
app.include_router(alerts_router, prefix="/api/v1")
app.include_router(user_router, prefix="/api/v1")
app.include_router(webhooks_router, prefix="/api/v1")
app.include_router(internal_router, prefix="/api/v1")
app.include_router(billing_router, prefix="/api/v1")

def extract_store_url_from_session(session: dict) -> str | None:
    fields = session.custom_fields or []
    for f in fields:
        # f looks like: {"key": "...", "label": {...}, "type":"text", "text": {"value":"..."}}
        text = f.text or {}
        value = text.value
        if value:
            return value.strip()
    return None

def send_report_email(to_email: str, store_url: str, pdf_path: str):
    if not (RESEND_API_KEY and RESEND_FROM):
        # Don't crash if env not set yet
        return

    with open(pdf_path, "rb") as f:
        b64 = base64.b64encode(f.read()).decode("utf-8")

    params: resend.Emails.SendParams = {
        "from": RESEND_FROM,
        "to": [to_email],
        "subject": f"Your StoreScout report: {store_url}",
        "html": f"""
        <p>Attached is your StoreScout report for <strong>{store_url}</strong>.</p>
        <p>If you have questions, reply to this email.</p>
        """,
        "attachments": [{"filename": "storescout-report.pdf", "content": b64}],
    }
    resend.Emails.send(params)

def normalize_store_url(url: str) -> str:
    url = url.strip()
    if not url.startswith("http"):
        url = "https://" + url
    # basic safety (keeps it simple for v1)
    if not re.match(r"^https?://", url):
        raise ValueError("Invalid URL scheme.")
    return url.rstrip("/")

@app.get("/check_store")
def check_store_endpoint(store_url: str = Query(..., min_length=3)):
    """Probe whether a URL is an accessible Shopify store using curl_cffi (Chrome TLS fingerprint)."""
    try:
        base = normalize_store_url(store_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        from app.services.fetch import check_store as _check_store
    except ImportError:
        from fetch import check_store as _check_store  # type: ignore

    return _check_store(base)



@app.get("/", response_class=HTMLResponse)
def home():
    idx = TEMPLATES_DIR / "index.html"
    if not idx.exists():
        raise HTTPException(status_code=500, detail="index.html not found. Put it in ./templates or next to main.py")
    return idx.read_text(encoding="utf-8")

@app.get("/shopify-competitor-analysis-tool")
def competitortool():
    competitortool_path = TEMPLATES_DIR / "shopify-analysis.html"
    return HTMLResponse(competitortool_path.read_text(encoding="utf-8"))

@app.get("/faq", response_class=HTMLResponse)
def faq():
    faq_path = TEMPLATES_DIR / "faq.html"
    return HTMLResponse(faq_path.read_text(encoding="utf-8"))

@app.get("/sample-report", response_class=HTMLResponse)
def sample_report():
    sample_report_path = TEMPLATES_DIR / "sample-report.html"
    return HTMLResponse(sample_report_path.read_text(encoding="utf-8"))

@app.get("/free-report")
def free_report():
    """Serve the free Allbirds sample PDF. Generates once and caches."""
    static_dir = BASE_DIR / "static"
    pdf_path = static_dir / "free-report.pdf"

    if pdf_path.exists():
        return FileResponse(
            path=str(pdf_path),
            media_type="application/pdf",
            filename="allbirds-storescout-report.pdf",
        )

    try:
        store_url = "https://www.allbirds.com"
        raw_products = fetch_products_shopify(store_url)
        normalized = [normalize_product(p, store_url) for p in raw_products]
        insights = analyze_products(normalized)
        insights["store_url"] = store_url

        html = render_report_html(insights, TEMPLATES_DIR, is_free_report=True)
        static_dir.mkdir(exist_ok=True)
        html_to_pdf(html, pdf_path, is_free_report=True)

        return FileResponse(
            path=str(pdf_path),
            media_type="application/pdf",
            filename="allbirds-storescout-report.pdf",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Could not generate free report: {str(e)}")

@app.get("/blog", response_class=HTMLResponse)
def blog():
    blog_path = TEMPLATES_DIR / "blog.html"
    return HTMLResponse(blog_path.read_text(encoding="utf-8"))

@app.get("/blog/fenty-pricing-strategy", response_class=HTMLResponse)
def fenty_pricing_strategy():
    article_path = TEMPLATES_DIR / "fenty-pricing-strategy.html"
    return HTMLResponse(article_path.read_text(encoding="utf-8"))

@app.get("/blog/gymshark-pricing-strategy", response_class=HTMLResponse)
def fenty_pricing_strategy():
    article_path = TEMPLATES_DIR / "gymshark-pricing-strategy.html"
    return HTMLResponse(article_path.read_text(encoding="utf-8"))

@app.get("/blog/how-to-analyze-shopify-competitors", response_class=HTMLResponse)
def fenty_pricing_strategy():
    article_path = TEMPLATES_DIR / "how-to-analyze-shopify-competitors.html"
    return HTMLResponse(article_path.read_text(encoding="utf-8"))

@app.get("/landing", response_class=HTMLResponse)
def landing_page():
    article_path = TEMPLATES_DIR / "index.html"
    return HTMLResponse(article_path.read_text(encoding="utf-8"))
    


@app.get("/preview", response_class=HTMLResponse)
def preview(store_url: str = Query(..., min_length=3)):
    try:
        base = normalize_store_url(store_url)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid store URL")

    try:
        raw_products = fetch_products_shopify(base, max_products=500)
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Could not fetch store: {e}")

    if not raw_products:
        raise HTTPException(status_code=400, detail="No products found. Store may not be Shopify or blocks /products.json.")

    normalized = [normalize_product(p, base) for p in raw_products]
    ins = analyze_products(normalized)

    from urllib.parse import urlparse
    from datetime import datetime, timezone
    hostname = urlparse(base).hostname or base

    catalog   = ins.get("catalog", {})
    pricing   = ins.get("pricing", {})
    discounts = ins.get("discounts", {})
    launch    = ins.get("launch_timeline", {}) or {}
    tag_ana   = ins.get("tag_analysis", {}) or {}
    vend_ana  = ins.get("vendor_analysis", {}) or {}

    total_products = catalog.get("total_products", len(normalized))
    promo_rate     = round(discounts.get("discounted_pct") or 0)
    median_price   = round(pricing.get("median") or 0)
    new_30d        = (launch.get("launch_counts") or {}).get("30d", {}).get("count", 0) if isinstance((launch.get("launch_counts") or {}).get("30d"), dict) else (launch.get("launch_counts") or {}).get("30d", 0)
    entry_price    = round(pricing.get("min") or 0)
    price_max      = round(pricing.get("max") or 0)
    p25            = round(pricing.get("p25") or 0)
    p75            = round(pricing.get("p75") or 0)
    median_discount = round(discounts.get("median_discount_pct") or 0)
    vendor_count   = catalog.get("vendor_count", 0)
    top_vendor_pct = 0
    top_vendors = vend_ana.get("top_vendors") or []
    if top_vendors:
        top_vendor_pct = round(top_vendors[0].get("pct") or 0)
    tag_unique     = tag_ana.get("total_unique", 0)
    top_tag_pct    = 0
    top_tags = tag_ana.get("top_tags") or []
    if top_tags:
        top_tag_pct = round(top_tags[0].get("pct") or 0)

    # Build newest products list (up to 4) with days_ago
    now = datetime.now(timezone.utc)
    from app.services.analyze import parse_dt
    dated = []
    for p in normalized:
        dt = parse_dt(p.get("created_at"))
        if dt:
            dated.append({"title": p.get("title", "Product"), "dt": dt})
    dated.sort(key=lambda x: x["dt"], reverse=True)
    newest_products = [
        {"title": d["title"], "days_ago": max(0, (now - d["dt"]).days)}
        for d in dated[:4]
    ]

    env = Environment(loader=FileSystemLoader(str(TEMPLATES_DIR)), autoescape=True)
    template = env.get_template("preview.html")
    html = template.render(
        hostname=hostname,
        store_url=base,
        product_count=len(normalized),
        total_products=total_products,
        promo_rate=promo_rate,
        median_price=median_price,
        new_30d=new_30d,
        entry_price=entry_price,
        price_max=price_max,
        p25=p25,
        p75=p75,
        median_discount=median_discount,
        vendor_count=vendor_count,
        top_vendor_pct=top_vendor_pct,
        tag_unique=tag_unique,
        top_tag_pct=top_tag_pct,
        newest_products=newest_products,
    )
    return HTMLResponse(html)


@app.post("/generate")
def generate(
    store_url: Optional[str] = Form(None),
    payload: Optional[Dict[str, Any]] = Body(None)
):
    if not store_url and payload:
        store_url = payload.get("store_url")

    if not store_url:
        raise HTTPException(status_code=422, detail="store_url is required")
    t0 = time.time(); store_url = normalize_store_url(store_url); print("START generate")

    # 1) fetch raw products
    t = time.time(); raw_products = fetch_products_shopify(store_url, max_products=None); print("FETCH seconds:", round(time.time()-t,2), "products:", len(raw_products))

    if not raw_products:
        # Most common reasons: not Shopify, /products.json disabled, or blocked/rate-limited.
        raise HTTPException(
            status_code=400,
            detail="No product data returned from /products.json. The store may not be Shopify, may block this endpoint, or may be rate-limiting requests.",
        )
    

    # 2) normalize
    t = time.time(); normalized = [normalize_product(p, store_url) for p in raw_products]; print("NORMALIZE seconds:", round(time.time()-t,2), "products:", len(normalized))

    # 3) analyze + takeaways
    t = time.time(); insights = analyze_products(normalized); print("ANALYZE seconds:", round(time.time()-t,2))
    insights["store"] = {"base_url": store_url, "product_count": len(normalized)}

    # keep confidence notes, but avoid duplicates if analyze.py already added them
    extra_notes = [
        "Data source: public Shopify /products.json endpoint.",
        "Safety cap: up to 10 pages × 250 products (max ~2,500 products).",
        "Discounts are counted only when compare_at_min > price_min.",
        "This report does not infer traffic, conversion rate, or revenue.",
    ]
    notes = insights.setdefault("confidence_notes", [])
    for n in extra_notes:
        if n not in notes:
            notes.append(n)

    # 4) render HTML -> PDF
    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    safe_name = re.sub(r"[^a-zA-Z0-9]+", "-", store_url.replace("https://", "").replace("http://", "")).strip("-")
    pdf_path = OUTPUTS_DIR / f"{safe_name}-report.pdf"

    t = time.time(); html = render_report_html(insights, TEMPLATES_DIR); print("HTML seconds:", round(time.time()-t,2))
    t = time.time(); html_to_pdf(html, pdf_path, brand_name="StoreScout"); print("PDF seconds:", round(time.time()-t,2), pdf_path)

    return FileResponse(
        path=str(pdf_path),
        media_type="application/pdf",
        filename="storescout_report.pdf",
    )

@app.post("/buy")
def buy(request: Request, store_url: str = Form(..., min_length=3)):
    # 1) Validate + normalize
    try:
        base = normalize_store_url(store_url)
    except ValueError:
        raise HTTPException(status_code=400, detail="Please enter a valid store URL")

    # 2) Enforce Shopify access BEFORE payment
    probe = check_store(base)
    if not probe.get("ok"):
        raise HTTPException(status_code=400, detail=f"Store not supported: {probe.get('reason')}")

    # 3) DEV BYPASS: localhost only
    host = request.url.hostname
    is_local = host in ["localhost", "127.0.0.1"]

    if is_local and DEV_SKIP_PAYMENT:
        print("DEV MODE: skipping Stripe payment")
        return JSONResponse({
            "url": f"/success?dev_store_url={base}"
        })

    # 4) Normal Stripe Checkout flow
    if not STRIPE_SECRET_KEY:
        raise HTTPException(status_code=500, detail="Missing STRIPE_SECRET_KEY")

    PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")
    if not PUBLIC_BASE_URL:
        raise HTTPException(status_code=500, detail="Missing PUBLIC_BASE_URL env var")

    STRIPE_PRICE_ID = os.getenv("STRIPE_PRICE_ID", "")
    if not STRIPE_PRICE_ID:
        raise HTTPException(status_code=500, detail="Missing STRIPE_PRICE_ID env var")

    try:
        session = stripe.checkout.Session.create(
            mode="payment",
            line_items=[{"price": STRIPE_PRICE_ID, "quantity": 1}],
            success_url=f"{PUBLIC_BASE_URL}/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{PUBLIC_BASE_URL}/",
            custom_fields=[
                {
                    "key": "store_url",
                    "label": {"type": "custom", "custom": "Store URL"},
                    "type": "text",
                    "text": {"default_value": base},
                }
            ],
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Stripe session error: {e}")

    return JSONResponse({"url": session.url})



from fastapi.responses import HTMLResponse
from fastapi import HTTPException
import stripe

@app.get("/success")
def success(session_id: str = None, dev_store_url: str = None):
    if dev_store_url:
      store_url = normalize_store_url(dev_store_url)
    else:
        if not session_id:
            raise HTTPException(status_code=400, detail="Missing session_id")

        session = stripe.checkout.Session.retrieve(session_id)
        if session.payment_status != "paid":
            return HTMLResponse("<h2>Payment not completed.</h2>", status_code=402)

        store_url = extract_store_url_from_session(session)
        if not store_url:
            return HTMLResponse("<h2>Missing store URL from checkout.</h2>", status_code=400)

    safe_store_url = store_url.replace("\\", "\\\\").replace('"', '\\"')

    return HTMLResponse(f"""
<!doctype html>
<html>
<head>
    <!-- Meta Pixel Code -->
  <script>
  !function(f,b,e,v,n,t,s)
  {{if(f.fbq)return;n=f.fbq=function(){{n.callMethod?
  n.callMethod.apply(n,arguments):n.queue.push(arguments)}};
  if(!f._fbq)f._fbq=n;n.push=n;n.loaded=!0;n.version='2.0';
  n.queue=[];t=b.createElement(e);t.async=!0;
  t.src=v;s=b.getElementsByTagName(e)[0];
  s.parentNode.insertBefore(t,s)}}(window, document,'script',
  'https://connect.facebook.net/en_US/fbevents.js');
  fbq('init', '898113633245460');
  fbq('track', 'PageView');
  </script>
  <noscript><img height="1" width="1" style="display:none"
  src="https://www.facebook.com/tr?id=898113633245460&ev=PageView&noscript=1"
  /></noscript>
  <!-- End Meta Pixel Code --> 
  <meta charset="utf-8"/>
  <title>StoreScout - Success</title>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <style>
    :root {{
      --bg: #0b1220;
      --card: rgba(255,255,255,0.05);
      --card2: rgba(255,255,255,0.04);
      --border: rgba(255,255,255,0.10);
      --border2: rgba(255,255,255,0.08);
      --text: #e5e7eb;
      --muted: rgba(229,231,235,0.72);
      --muted2: rgba(229,231,235,0.60);
      --blue: #3b82f6;
      --blue2: #2563eb;
      --green: #22c55e;
      --red: #ef4444;
      --shadow: 0 24px 70px rgba(0,0,0,0.60);
      --radius: 16px;
    }}

    * {{
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }}

    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background: radial-gradient(1200px 800px at 20% 0%, rgba(59,130,246,0.18), transparent 55%),
                  radial-gradient(1200px 800px at 80% 0%, rgba(34,197,94,0.12), transparent 55%),
                  var(--bg);
      color: var(--text);
      min-height: 100vh;
      padding: 28px 18px;
    }}

    .wrap {{
      max-width: 880px;
      margin: 0 auto;
    }}

    .card {{
      background: linear-gradient(180deg, var(--card), var(--card2));
      border: 1px solid var(--border);
      border-radius: var(--radius);
      box-shadow: var(--shadow);
      padding: 18px;
    }}

    .top {{
      display: flex;
      align-items: flex-start;
      justify-content: space-between;
      gap: 12px;
      flex-wrap: wrap;
    }}

    .title {{
      display: flex;
      gap: 10px;
      align-items: center;
    }}

    .badge {{
      width: 36px;
      height: 36px;
      border-radius: 10px;
      background: rgba(34,197,94,0.12);
      border: 1px solid rgba(34,197,94,0.25);
      display: flex;
      align-items: center;
      justify-content: center;
      font-size: 18px;
    }}

    h1 {{
      font-size: 18px;
      line-height: 1.2;
      letter-spacing: -0.02em;
    }}

    .muted {{
      color: var(--muted);
      margin-top: 6px;
      font-size: 13px;
      line-height: 1.4;
    }}

    code {{
      background: rgba(255,255,255,0.08);
      border: 1px solid var(--border2);
      padding: 2px 8px;
      border-radius: 999px;
      font-size: 12px;
    }}

    .actions {{
      display: flex;
      gap: 10px;
      align-items: center;
      margin-top: 14px;
      flex-wrap: wrap;
    }}

    .btn {{
      appearance: none;
      border: 1px solid rgba(255,255,255,0.14);
      background: rgba(255,255,255,0.07);
      color: var(--text);
      border-radius: 12px;
      padding: 10px 14px;
      font-weight: 600;
      font-size: 13px;
      cursor: pointer;
      transition: transform 0.05s ease, background 0.2s ease, border-color 0.2s ease, opacity 0.2s ease;
      user-select: none;
    }}

    .btn:hover {{
      background: rgba(255,255,255,0.10);
      border-color: rgba(255,255,255,0.20);
    }}

    .btn:active {{
      transform: translateY(1px);
    }}

    .btn-primary {{
      background: linear-gradient(180deg, rgba(59,130,246,0.95), rgba(37,99,235,0.95));
      border-color: rgba(59,130,246,0.35);
    }}

    .btn-primary:hover {{
      background: linear-gradient(180deg, rgba(59,130,246,1), rgba(37,99,235,1));
      border-color: rgba(59,130,246,0.55);
    }}

    .btn[disabled] {{
      opacity: 0.55;
      cursor: not-allowed;
    }}

    .status-line {{
      margin-top: 10px;
      font-size: 13px;
      color: var(--muted2);
    }}

    .status-ok {{ color: rgba(34,197,94,0.95); }}
    .status-err {{ color: rgba(239,68,68,0.95); }}

    /* Overlay (your exact structure, production-ready styles) */
    .overlay {{
      position: fixed;
      inset: 0;
      display: none;
      align-items: center;
      justify-content: center;
      background: rgba(0,0,0,0.55);
      z-index: 9999;
      padding: 18px;
    }}
    .overlay.show {{ display: flex; }}

    .overlay-card {{
      width: min(560px, 92vw);
      background: #0f172a;
      border: 1px solid rgba(255,255,255,0.10);
      border-radius: 16px;
      padding: 18px 18px 14px 18px;
      box-shadow: 0 20px 60px rgba(0,0,0,0.55);
      color: #e5e7eb;
    }}

    .overlay-content {{
      display: flex;
      gap: 14px;
      align-items: center;
    }}

    .overlay-spinner {{
      width: 44px;
      height: 44px;
      border-radius: 999px;
      border: 4px solid rgba(255,255,255,0.18);
      border-top-color: var(--blue);
      animation: spin 0.9s linear infinite;
      flex: 0 0 auto;
    }}

    @keyframes spin {{
      to {{ transform: rotate(360deg); }}
    }}
    @keyframes fadeIn {{
      from {{ opacity: 0; }}
      to {{ opacity: 1; }}
    }}
    body {{
  animation: fadeIn 260ms ease-out both;
    }}
    @keyframes popIn {{
    from {{ opacity: 0; transform: translateY(8px); }}
    to   {{ opacity: 1; transform: translateY(0); }}
    }}
    .card {{
    animation: popIn 320ms cubic-bezier(.2,.9,.2,1) both;
    }}



    .overlay-text h3 {{
      margin: 0;
      font-size: 16px;
      font-weight: 700;
      color: #f9fafb;
    }}
    .overlay-text p {{
      margin: 3px 0 0 0;
      font-size: 13px;
      color: rgba(255,255,255,0.72);
    }}

    .progress-info {{
      margin-top: 12px;
      padding-top: 10px;
      border-top: 1px solid rgba(255,255,255,0.10);
      font-size: 12px;
      color: rgba(255,255,255,0.78);
      line-height: 1.35;
    }}
  </style>
</head>

<body>
  <div class="wrap">
    <div class="card">
      <div class="top">
        <div>
          <div class="title">
            <div class="badge">✅</div>
            <div>
              <h1>Payment received</h1>
              <div class="muted">
                Generating your StoreScout report for <code id="storeCode"></code>
              </div>
            </div>
          </div>
        </div>

        <div class="actions">
          <button id="backBtn" class="btn btn-primary" disabled>Back to Home</button>
          <button id="retryBtn" class="btn" style="display:none;">Retry</button>
        </div>
      </div>

      <div id="statusLine" class="status-line">Starting generation…</div>
    </div>
  </div>

  <!-- EXACT OVERLAY STRUCTURE YOU PROVIDED -->
  <div id="overlay" class="overlay show">
    <div class="overlay-card">
      <div class="overlay-content">
        <div class="overlay-spinner"></div>
        <div class="overlay-text">
          <h3>Generating Report</h3>
          <p>Analyzing competitor data...</p>
        </div>
      </div>
      <div class="progress-info">
        <strong>Elapsed:</strong> <span id="elapsed">0</span>s
        <br>
        <span id="hint">Fetching product catalog</span>
      </div>
    </div>
  </div>

  <script>
    (function() {{
      const storeUrl = "{safe_store_url}";
      const overlay = document.getElementById('overlay');
      const elapsedEl = document.getElementById('elapsed');
      const hintEl = document.getElementById('hint');
      const storeCode = document.getElementById('storeCode');
      const statusLine = document.getElementById('statusLine');
      const backBtn = document.getElementById('backBtn');
      const retryBtn = document.getElementById('retryBtn');

      storeCode.textContent = storeUrl;

      let timer = null;

      function startTimer() {{
        const start = Date.now();
        if (timer) clearInterval(timer);
        timer = setInterval(() => {{
          const secs = Math.floor((Date.now() - start) / 1000);
          elapsedEl.textContent = String(secs);

          if (secs < 5) {{
            hintEl.textContent = 'Fetching product catalog';
          }} else if (secs < 15) {{
            hintEl.textContent = 'Analyzing pricing data';
          }} else if (secs < 30) {{
            hintEl.textContent = 'Generating insights';
          }} else if (secs < 60) {{
            hintEl.textContent = 'Creating PDF (large store)';
          }} else {{
            hintEl.textContent = 'Still processing...';
          }}
        }}, 250);
      }}

      function stopTimer() {{
        if (timer) clearInterval(timer);
        timer = null;
      }}

      function setStatus(msg, kind) {{
        statusLine.textContent = msg;
        statusLine.className = 'status-line' + (kind ? (' status-' + kind) : '');
      }}

      function downloadBlob(blob) {{
        const hostname = (new URL(storeUrl)).hostname.replace(/^www\\./, "");
        const date = new Date().toISOString().slice(0,10);
        const filename = `storescout_${{hostname}}_${{date}}.pdf`;

        const dlUrl = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = dlUrl;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(dlUrl);
      }}

      async function generateOnce() {{
        overlay.classList.add('show');
        elapsedEl.textContent = '0';
        hintEl.textContent = 'Fetching product catalog';
        startTimer();

        try {{
          setStatus('Generating your report…', null);
          backBtn.disabled = true;
          retryBtn.style.display = 'none';

          const fd = new FormData();
          fd.append('store_url', storeUrl);

          const res = await fetch('/generate', {{ method: 'POST', body: fd }});

          if (!res.ok) {{
            let detail = 'Report generation failed. Please verify the store URL.';
            try {{
              const j = await res.json();
              if (j && j.detail) detail = (typeof j.detail === 'string') ? j.detail : JSON.stringify(j.detail);
            }} catch (_) {{}}

            hintEl.textContent = detail;
            setStatus(detail, 'err');
            retryBtn.style.display = 'inline-block';
            return;
          }}

          const blob = await res.blob();
          downloadBlob(blob);

          hintEl.textContent = 'Download started.';
          setStatus('✓ Report generated. You can return home now.', 'ok');
          backBtn.disabled = false;

        }} catch (err) {{
          console.error(err);
          hintEl.textContent = 'Network error. Please try again.';
          setStatus('Network error while generating the report.', 'err');
          retryBtn.style.display = 'inline-block';
        }} finally {{
          stopTimer();
          // Keep the overlay visible until success/error message is set, then hide it.
          // Small delay so the user sees "Download started."
          setTimeout(() => {{
            overlay.classList.remove('show');
          }}, 350);
        }}
      }}

      backBtn.addEventListener('click', () => {{
        window.location.href = '/';
      }});

      retryBtn.addEventListener('click', () => {{
        generateOnce();
      }});

      generateOnce();
    }})();
  </script>
</body>
</html>
""")



@app.get("/sitemap.xml")
async def sitemap():
    return FileResponse("sitemap.xml")


@app.get("/robots.txt")
async def robots():
    return FileResponse("robots.txt")


@app.post("/stripe/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig = request.headers.get("stripe-signature")
    if not sig:
        raise HTTPException(status_code=400, detail="Missing Stripe-Signature header")

    try:
        event = stripe.Webhook.construct_event(
            payload=payload,
            sig_header=sig,
            secret=STRIPE_WEBHOOK_SECRET,
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Webhook signature verification failed: {e}")

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]

        email = (session.get("customer_details") or {}).get("email")
        store_url = extract_store_url_from_session(session)

        if email and store_url:
            # Generate PDF using your existing pipeline
            # If your /generate already creates a PDF on disk, reuse that path.
            # If /generate only streams it, tell me and I’ll show the small refactor.
            safe_name = re.sub(r"[^a-zA-Z0-9]+", "-", store_url.replace("https://", "").replace("http://", "")).strip("-")
            pdf_path = OUTPUTS_DIR / f"{safe_name}-report.pdf"  # <-- you might need to expose this helper

            send_report_email(email, store_url, pdf_path)

    return {"ok": True}