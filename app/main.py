from __future__ import annotations

import re
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Request, Body,Query
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

RESEND_API_KEY = os.getenv("RESEND_API_KEY", "")
RESEND_FROM = os.getenv("RESEND_FROM", "")

stripe.api_key = STRIPE_SECRET_KEY
resend.api_key = RESEND_API_KEY


app = FastAPI(title="StoreScout")

# (optional) if you add static assets later
# app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

def extract_store_url_from_session(session: dict) -> str | None:
    fields = session.get("custom_fields") or []
    for f in fields:
        # f looks like: {"key": "...", "label": {...}, "type":"text", "text": {"value":"..."}}
        text = f.get("text") or {}
        value = text.get("value")
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
def check_store(store_url: str = Query(..., min_length=3)):
    """
    Server-side probe to confirm Shopify /products.json is accessible.
    Tries both apex and www variants because many stores only expose products.json on one host.
    """
    try:
        base = normalize_store_url(store_url)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    def probe(candidate_base: str):
        probe_url = f"{candidate_base}/products.json?limit=1"
        try:
            r = requests.get(
                probe_url,
                timeout=10,
                headers={"User-Agent": "StoreScoutBot/1.0 (+https://storescout)"},
            )
        except requests.RequestException:
            return {"ok": False, "reason": "Network error reaching store", "status": None}

        if r.status_code != 200:
          if r.status_code == 404:
              msg = "This domain doesn’t expose /products.json (try the non-www or www version)."
          elif r.status_code == 403:
              msg = "This store blocks automated access to /products.json (HTTP 403)."
          else:
              msg = f"/products.json returned HTTP {r.status_code}"
          return {"ok": False, "reason": msg, "status": r.status_code}


        try:
            data = r.json()
        except Exception:
            return {"ok": False, "reason": "/products.json did not return JSON (blocked or not Shopify)", "status": r.status_code}

        prods = data.get("products")
        if not isinstance(prods, list):
            return {"ok": False, "reason": "Unexpected /products.json shape (likely blocked or not Shopify)", "status": r.status_code}

        return {"ok": True, "products_sample": len(prods)}

    # Build fallback candidates: typed host + alternate www/apex
    parsed = urlparse(base)
    host = parsed.hostname or ""
    scheme = parsed.scheme or "https"

    candidates = [base]

    if host.startswith("www."):
        alt_host = host.replace("www.", "", 1)
        candidates.append(f"{scheme}://{alt_host}")
    else:
        candidates.append(f"{scheme}://www.{host}")

    # Try candidates in order; return the first that works
    attempts = []
    for c in candidates:
        result = probe(c)
        attempts.append({"base_url": c, **result})
        if result.get("ok"):
            return {"ok": True, "base_url": c, "products_sample": result.get("products_sample", 0), "attempts": attempts}

    # None worked
    return {
        "ok": False,
        "reason": attempts[0].get("reason") or "Store does not expose /products.json",
        "attempts": attempts,
    }



@app.get("/", response_class=HTMLResponse)
def home():
    idx = TEMPLATES_DIR / "index.html"
    if not idx.exists():
        raise HTTPException(status_code=500, detail="index.html not found. Put it in ./templates or next to main.py")
    return idx.read_text(encoding="utf-8")


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
def buy(store_url: str = Form(..., min_length=3)):
    # 1) Validate + normalize
    try:
        base = normalize_store_url(store_url)
    except ValueError:
        raise HTTPException(status_code=400, detail="Please enter a valid store URL")

    # 2) Enforce Shopify access BEFORE payment
    probe = check_store(base)
    if not probe.get("ok"):
        raise HTTPException(status_code=400, detail=f"Store not supported: {probe.get('reason')}")

    # 3) Create Stripe Checkout Session (NOT a payment link)
    if not STRIPE_SECRET_KEY:
        raise HTTPException(status_code=500, detail="Missing STRIPE_SECRET_KEY")

    # ✅ You must set this in .env (example: https://storescout.yourdomain.com)
    PUBLIC_BASE_URL = os.getenv("PUBLIC_BASE_URL", "").rstrip("/")
    if not PUBLIC_BASE_URL:
        raise HTTPException(status_code=500, detail="Missing PUBLIC_BASE_URL env var")

    # ✅ You must set this in .env: the Price ID for your product
    STRIPE_PRICE_ID = os.getenv("STRIPE_PRICE_ID", "")
    if not STRIPE_PRICE_ID:
        raise HTTPException(status_code=500, detail="Missing STRIPE_PRICE_ID env var")

    try:
        session = stripe.checkout.Session.create(
            mode="payment",
            line_items=[{"price": STRIPE_PRICE_ID, "quantity": 1}],
            success_url=f"{PUBLIC_BASE_URL}/success?session_id={{CHECKOUT_SESSION_ID}}",
            cancel_url=f"{PUBLIC_BASE_URL}/",
            # This is what your extract_store_url_from_session() reads ✅
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
def success(session_id: str):
    if not session_id:
        raise HTTPException(status_code=400, detail="Missing session_id")

    session = stripe.checkout.Session.retrieve(session_id)
    if session.get("payment_status") != "paid":
        return HTMLResponse("<h2>Payment not completed.</h2>", status_code=402)

    store_url = extract_store_url_from_session(session)
    if not store_url:
        return HTMLResponse("<h2>Missing store URL from checkout.</h2>", status_code=400)

    safe_store_url = store_url.replace("\\", "\\\\").replace('"', '\\"')

    return HTMLResponse(f"""
<!doctype html>
<html>
<head>
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
