"""
Hypermarket Deals Scraper
==========================
Visits each hypermarket's deals page using a real (headless) browser so
JavaScript-rendered content loads properly, extracts the page text, and
asks Claude to turn it into structured offers. Writes everything to
offers.json, which index.html reads to render the dashboard.

Setup:
    pip install playwright anthropic
    playwright install chromium
    export ANTHROPIC_API_KEY="sk-ant-..."

Run:
    python scraper.py
"""

import json
import os
from datetime import datetime, timezone
from playwright.sync_api import sync_playwright
from anthropic import Anthropic

client = Anthropic()

# -----------------------------------------------------------------------
# CONFIGURATION — each site's deals page + an optional CSS selector to
# narrow down to just the offers section (inspect each site to find these;
# see README.md for how). Leaving selector as None scrapes the whole page.
# -----------------------------------------------------------------------
SITES = [
    {
        "store": "بنده",
        "url": "https://panda.sa/en/plp?category_id=830&deals=1",
        "selector": None,
    },
    {
        "store": "كارفور",
        "url": "https://www.carrefourksa.com/mafsau/en/n/c/clp_carrefouroffers",
        "selector": None,
    },
    {
        "store": "أسواق العثيم",
        "url": "https://www.othaimmarkets.com/offers",
        "selector": None,
    },
    {
        "store": "دانوب",
        "url": "https://danube.sa/departments/promotions",
        "selector": None,
    },
    {
        "store": "لولو هايبرماركت",
        "url": "https://gcc.luluhypermarket.com/en-sa/deals",
        "selector": None,
    },
]

OUTPUT_PATH = os.path.join(os.path.dirname(__file__), "offers.json")
MAX_CHARS = 15000  # cap page text sent to Claude, to control token usage


def fetch_rendered_text(page, url: str, selector: str | None) -> str:
    """Load a JS-rendered page in a real browser and return its visible text."""
    page.goto(url, wait_until="networkidle", timeout=30000)
    # Give lazy-loaded product grids a moment to finish rendering
    page.wait_for_timeout(2000)

    if selector:
        try:
            page.wait_for_selector(selector, timeout=10000)
            text = page.locator(selector).inner_text()
        except Exception:
            text = page.locator("body").inner_text()
    else:
        text = page.locator("body").inner_text()

    return text[:MAX_CHARS]


def extract_offers_with_claude(store: str, raw_text: str) -> list[dict]:
    prompt = f"""Below is text scraped from the "{store}" hypermarket's deals/offers page in Saudi Arabia.

Extract every distinct product offer you can find. For each one, return an object with:
- product: product name, translated/written in Arabic (string)
- price: current discounted price as a number (SAR), or null if not shown
- original_price: original price as a number (SAR), or null if not shown
- discount_pct: discount percentage as an integer (compute from price/original_price if not stated directly), or null
- category: a short category in Arabic (e.g. "ألبان", "مشروبات", "وجبات خفيفة"), or null

Respond with ONLY a valid JSON array of objects — no preamble, no markdown fences, no explanation.
If no real product offers are found in the text, return [].

TEXT:
{raw_text}
"""
    response = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=3000,
        messages=[{"role": "user", "content": prompt}],
    )
    text = response.content[0].text.strip()
    text = text.replace("```json", "").replace("```", "").strip()
    try:
        parsed = json.loads(text)
        # Drop any entries missing required numeric fields
        return [
            o for o in parsed
            if o.get("product") and o.get("price") is not None and o.get("original_price") is not None
        ]
    except json.JSONDecodeError:
        print(f"  [warn] Could not parse Claude's response for {store}")
        return []


def main():
    results = {}

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page(
            user_agent="Mozilla/5.0 (compatible; PersonalDealsBot/1.0)"
        )

        for site in SITES:
            store = site["store"]
            print(f"Fetching {store}...")
            try:
                raw_text = fetch_rendered_text(page, site["url"], site["selector"])
                offers = extract_offers_with_claude(store, raw_text)
                # Fill in discount_pct if Claude left it null but we have both prices
                for o in offers:
                    if o.get("discount_pct") is None and o.get("price") and o.get("original_price"):
                        o["discount_pct"] = round(
                            (1 - o["price"] / o["original_price"]) * 100
                        )
                results[store] = offers
                print(f"  Found {len(offers)} offers.")
            except Exception as e:
                print(f"  [error] {store}: {e}")
                results[store] = []

        browser.close()

    output = {
        "updated_at": datetime.now(timezone.utc).astimezone().isoformat(),
        "stores": results,
    }

    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    total = sum(len(v) for v in results.values())
    print(f"\nSaved {total} offers across {len(results)} stores to {OUTPUT_PATH}")


if __name__ == "__main__":
    main()
