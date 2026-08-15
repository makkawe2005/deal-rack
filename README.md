# Deal Rack — Saudi Hypermarket Offers Dashboard

A single page that consolidates deals from Panda, Carrefour, Othaim Markets,
Danube, and LuLu Hypermarket. Updates automatically once a day and is hosted
free on GitHub Pages so you can check it from your phone.

## How it works

```
scraper.py (Playwright + Claude)  →  offers.json  →  index.html (the page you view)
        ↑
GitHub Actions runs this daily, commits offers.json, redeploys the page
```

- **scraper.py** opens each store's deals page in a real (headless) browser
  so JavaScript-rendered content loads, then asks Claude to turn the messy
  page text into clean structured offers.
- **offers.json** is the single data file both the scraper writes to and the
  page reads from.
- **index.html** is the dashboard — store filter chips, sort by discount or
  price, styled as supermarket price-tag stickers.
- **.github/workflows/update-deals.yml** runs the whole pipeline daily and
  publishes the page — no server of your own required.

## One-time setup (about 15 minutes)

### 1. Create a GitHub repo
1. Go to github.com → New repository → name it e.g. `deal-rack`
2. Upload all the files from this folder (or `git init` + `git push` them)

### 2. Add your Claude API key as a secret
1. In your repo: **Settings → Secrets and variables → Actions → New repository secret**
2. Name: `ANTHROPIC_API_KEY`
3. Value: your key from console.anthropic.com

### 3. Turn on GitHub Pages
1. **Settings → Pages**
2. Under "Build and deployment", set Source to **GitHub Actions**

### 4. Run the workflow once manually
1. Go to the **Actions** tab → "Update deals and deploy" → **Run workflow**
2. After it finishes (~2-3 min), your site is live at:
   `https://<your-username>.github.io/<repo-name>/`
3. Bookmark that URL on your phone — that's your dashboard.

From here it re-runs automatically every day at 08:00 Saudi time and
redeploys with fresh deals.

## IMPORTANT: selectors need real tuning per site

Each site in `scraper.py`'s `SITES` list has `"selector": None`, meaning it
currently grabs the whole page's text. This works but is noisier and less
reliable than narrowing to just the offers section. To improve accuracy per
site:

1. Open the store's deals page in Chrome
2. Right-click the area listing the products → **Inspect**
3. Find a wrapping element with a distinct class/id, e.g. `<div class="product-grid">`
4. Set `"selector": "div.product-grid"` for that store in `scraper.py`

The URLs in `SITES` are my best guess at each store's current offers page —
double check each one still resolves correctly, since retailers restructure
their sites periodically.

## Legal note

Always check each site's `robots.txt` and Terms of Service before scraping.
Some retailers explicitly restrict automated access. This project is for
personal use — checking your own daily grocery deals — not redistribution
or commercial use. If a site disallows scraping, consider removing it from
`SITES` and checking that store's offers manually or via their newsletter.

## Testing locally before deploying

```bash
pip install -r requirements.txt
playwright install chromium
export ANTHROPIC_API_KEY="sk-ant-..."
python scraper.py
# then just open index.html in your browser to preview
```
