import json
import os
import re

import httpx
from bs4 import BeautifulSoup
from google import genai

HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) "
        "Chrome/120.0.0.0 Safari/537.36"
    ),
    "Accept-Language": "he,en-US;q=0.9,en;q=0.8",
}


def _fetch_html(page_url: str) -> bytes:
    response = httpx.get(page_url, headers=HEADERS, follow_redirects=True, timeout=15)
    response.raise_for_status()
    return response.content  # raw bytes — let BeautifulSoup detect encoding from <meta charset>


def _extract_from_structured_data(soup: BeautifulSoup) -> str | None:
    """Try JSON-LD schema.org/Product first — most reliable."""
    for tag in soup.find_all("script", type="application/ld+json"):
        try:
            data = json.loads(tag.string or "")
        except (json.JSONDecodeError, TypeError):
            continue

        items = data if isinstance(data, list) else [data]
        for item in items:
            if item.get("@type") in ("Product", "Offer"):
                raw_offers = item.get("offers") or (item if item.get("@type") == "Offer" else None)
                if raw_offers is None:
                    continue
                offers_list = raw_offers if isinstance(raw_offers, list) else [raw_offers]
                prices = []
                for offer in offers_list:
                    price_val = offer.get("price")
                    currency = offer.get("priceCurrency", "")
                    if price_val is not None:
                        prices.append(f"{currency} {price_val}".strip())
                if prices:
                    return ", ".join(prices)

    return None


def _extract_from_meta(soup: BeautifulSoup) -> str | None:
    """Try Open Graph / standard meta price tags."""
    for prop in ("product:price:amount", "og:price:amount", "price"):
        tag = soup.find("meta", attrs={"property": prop}) or soup.find(
            "meta", attrs={"name": prop}
        )
        if tag and tag.get("content"):
            currency_tag = soup.find(
                "meta", attrs={"property": "product:price:currency"}
            ) or soup.find("meta", attrs={"property": "og:price:currency"})
            currency = currency_tag["content"] if currency_tag else ""
            return f"{currency} {tag['content']}".strip()
    return None


def _build_llm_context(soup: BeautifulSoup) -> str:
    """Build a focused text snippet for the LLM, prioritising price-bearing elements."""
    for tag in soup(["script", "style", "noscript", "svg", "img", "video", "iframe", "nav", "footer", "header"]):
        tag.decompose()

    # English and Hebrew price-related terms (מחיר=price, מבצע=sale, מחיר מוצר=product price)
    price_pattern = re.compile(r"price|cost|amount|offer|sale|discount|מחיר|מבצע", re.I)
    candidates = []

    for el in soup.find_all(True):
        class_str = " ".join(el.get("class") or [])
        id_str = el.get("id") or ""
        itemprop_str = el.get("itemprop") or ""
        el_attrs = f"{class_str} {id_str} {itemprop_str}"
        if price_pattern.search(el_attrs):
            text = el.get_text(separator=" ", strip=True)
            if text:
                candidates.append(text[:300])

    if not candidates:
        candidates = [soup.get_text(separator="\n", strip=True)[:6000]]

    context = "\n".join(dict.fromkeys(candidates))  # deduplicate, preserve order
    return context[:6000]


def _extract_via_llm(page_context: str, page_url: str) -> str | None:
    """Use Gemini to extract the price from focused page text."""
    client = genai.Client(api_key="AIzaSyAo9UcVWaUQSQIOPFqA0UZHSZiDstT3nZY")

    prompt = (
        "You are a price extraction assistant. The page may be in any language including Hebrew. "
        "Reply with ONLY the price (e.g. '$49.99' or '₪49.90'). "
        "If there are multiple prices (e.g. variants), list them all separated by ' | '. "
        "If no price is found, reply with exactly: Price not found\n\n"
        f"Extract the price from this product page at: {page_url}\n\n"
        "---\n"
        f"{page_context}\n"
        "---"
    )

    response = client.models.generate_content(
        model="gemini-2.5-flash",
        contents=prompt,
    )

    result = response.text.strip()
    return None if result.lower() == "price not found" else result


def get_price_from_url(url: str) -> str | None:
    """
    Fetch a product page and extract its price.

    Strategy:
      1. JSON-LD structured data (schema.org/Product)
      2. Open Graph / meta price tags
      3. Gemini LLM fallback on focused page text
    """
    html_bytes = _fetch_html(url)
    soup = BeautifulSoup(html_bytes, "html.parser")  # auto-detects charset from <meta>

    result = _extract_from_structured_data(soup)
    if result:
        return result

    result = _extract_from_meta(soup)
    if result:
        return result

    context = _build_llm_context(soup)
    return _extract_via_llm(context, url)


# ── Example usage ──────────────────────────────────────────────────────────────
if __name__ == "__main__":
    test_urls = [
        "https://www.candid.co.il/collections/sale/products/134134-%D7%9E%D7%A0%D7%98%D7%94-xs",
    ]

    for url in test_urls:
        print(f"\nURL: {url}")
        try:
            price = get_price_from_url(url)
            print(f"Price: {price if price else 'Not found'}")
        except Exception as e:
            print(f"Error: {e}")