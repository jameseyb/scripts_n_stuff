import re
import sys
import json
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0 Safari/537.36"}
SITE = "https://www.theregister.com"


def fetch(url: str) -> str:
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    resp.encoding = resp.apparent_encoding
    return resp.text


def is_article(url: str) -> bool:
    # The Register article URLs contain a date: /YYYY/MM/DD/...
    return bool(re.search(r"/(\d{4})/(\d{2})/(\d{2})/", url))


def get_articles(category_url: str) -> list:
    soup = BeautifulSoup(fetch(category_url), "html.parser")
    seen, articles = set(), []
    for a in soup.find_all("a", href=True):
        url = urljoin(category_url, a["href"])
        if is_article(url) and url not in seen:
            seen.add(url)
            articles.append(url)
    return articles


def extract(url: str) -> dict:
    soup = BeautifulSoup(fetch(url), "html.parser")

    title = soup.select_one('meta[property="og:title"]')
    title = (title["content"] if title and title.get("content") else "") or \
        (soup.h1.get_text(strip=True) if soup.h1 else "")

    # Short summary: prefer the meta description the site ships with
    summary = ""
    for sel in ['meta[name="description"]', 'meta[property="og:description"]']:
        m = soup.select_one(sel)
        if m and m.get("content"):
            summary = m["content"].strip()
            break
    if not summary:  # fallback: lead paragraph
        p = soup.find("p")
        summary = p.get_text(strip=True)[:300] if p else "No summary available."

    return {"title": title, "url": url, "summary": summary}


def main(category_url: str = "https://www.theregister.com/security",
         out: str | None = "register_security.json",
         limit: int | None = None):
    try:
        articles = get_articles(category_url)
    except requests.RequestException as e:
        print(f"Failed to load category page: {e}", file=sys.stderr)
        return 0

    print(f"Found {len(articles)} articles, fetching...\n")
    results, done = [], 0
    for url in articles:
        try:
            results.append(extract(url))
            done += 1
            print(f"  [{done}/{len(articles)}] {results[-1]['title']}")
        except requests.RequestException as e:
            print(f"  skip {url}: {e}", file=sys.stderr)
        if limit and done >= limit:
            break

    if out:
        with open(out, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        print(f"\nSaved {len(results)} articles to {out}")

    return len(results)


if __name__ == "__main__":
    main()