from __future__ import annotations

from pathlib import Path
from datetime import datetime
from typing import Dict, Any

from jinja2 import Environment, FileSystemLoader
from playwright.sync_api import sync_playwright


def render_report_html(insights: Dict[str, Any], templates_dir: Path, is_free_report: bool = False) -> str:
    env = Environment(loader=FileSystemLoader(str(templates_dir)), autoescape=True)
    template = env.get_template("report_template.html")

    store_url = ((insights.get("store") or {}).get("base_url")
                 or insights.get("store_url")
                 or "Unknown store")

    ctx = {
        "store_url": store_url,
        "generated_at": insights.get("generated_at") or (datetime.utcnow().isoformat() + "Z"),
        "takeaways": insights.get("takeaways", []),
        "catalog": insights.get("catalog", {}),
        "pricing": insights.get("pricing", {}),
        "discounts": insights.get("discounts", {}),
        "content_signals": insights.get("content_signals", {}),
        "positioning": insights.get("positioning", {}),
        "confidence_notes": insights.get("confidence_notes", []),
        "lists": insights.get("lists", {}),
        "comparisons": insights.get("comparisons", {}),
        "launch_timeline": insights.get("launch_timeline", {}) or insights.get("launch", {}) or {},
        "vendor_analysis": insights.get("vendor_analysis", {}),
        "tag_analysis": insights.get("tag_analysis", {}),
        "is_free_report": is_free_report,
    }

    return template.render(**ctx)



def html_to_pdf(html: str, out_path: Path, brand_name: str = "StoreScout", is_free_report: bool = False) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if is_free_report:
        footer_template = """
        <div style="font-size:9px; width:100%; padding:0 18mm; color:#666;
                    display:flex; justify-content:space-between;">
          <div style="color:#a3f000;font-weight:700;">FREE SAMPLE · getstorescout.com · $9 per report</div>
          <div>Page <span class="pageNumber"></span> / <span class="totalPages"></span></div>
        </div>
        """
    else:
        footer_template = f"""
        <div style="font-size:9px; width:100%; padding:0 18mm; color:#666;
                    display:flex; justify-content:space-between;">
          <div>{brand_name}</div>
          <div>Page <span class="pageNumber"></span> / <span class="totalPages"></span></div>
        </div>
        """

    with sync_playwright() as p:
        # Chromium launch can be slow the first time on a machine. These flags are harmless and
        # can improve stability/perf in some environments.
        browser = p.chromium.launch(headless=True,
                                    args=["--no-sandbox","--disable-dev-shm-usage"])
        page = browser.new_page()

        # Don't block on external network resources (fonts/images). Our template is self-contained.
        page.set_default_timeout(30_000)
        page.set_content(html, wait_until="domcontentloaded", timeout=30_000)
        page.wait_for_timeout(100)

        page.pdf(
            path=str(out_path),
            format="A4",
            print_background=True,
            prefer_css_page_size=True,
            display_header_footer=True,
            header_template="<div></div>",
            footer_template=footer_template,
            margin={"top": "18mm", "bottom": "22mm", "left": "18mm", "right": "18mm"},
        )
        browser.close()
