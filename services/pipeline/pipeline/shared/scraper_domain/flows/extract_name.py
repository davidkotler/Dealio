from __future__ import annotations

from bs4 import BeautifulSoup


def extract_name(html: str) -> str | None:
    """
    Extract product name from HTML using a cascade strategy.

    Extraction strategy (in order of precedence):
    1. <meta property="og:title"> content attribute
    2. <title> tag text (strip whitespace)
    3. First <h1> tag text (strip whitespace)

    Returns None if all strategies fail or result is empty after stripping.

    Args:
        html: Raw HTML string

    Returns:
        Extracted product name, or None if not found
    """
    try:
        soup = BeautifulSoup(html, "lxml")
    except Exception:
        try:
            soup = BeautifulSoup(html, "html.parser")
        except Exception:
            return None

    # Level 1: og:title meta tag
    og_title = soup.select_one('meta[property="og:title"]')
    if og_title and og_title.get("content"):
        name = og_title.get("content").strip()
        if name:
            return name

    # Level 2: title tag
    title_tag = soup.select_one("title")
    if title_tag:
        name = title_tag.get_text(strip=True)
        if name:
            return name

    # Level 3: first h1 tag
    h1_tag = soup.select_one("h1")
    if h1_tag:
        name = h1_tag.get_text(strip=True)
        if name:
            return name

    return None
