from __future__ import annotations

import json
import re
from decimal import Decimal, InvalidOperation

from bs4 import BeautifulSoup


def extract_price(html: str) -> Decimal | None:
    """
    Extract product price from HTML using a three-level cascade strategy.

    Extraction strategy:
    1. JSON-LD: Parse <script type="application/ld+json"> → @type: "Product" → offers.price
    2. Meta tags: property="product:price:amount", name="price", property="og:price:amount"
    3. CSS selectors: .price, [data-price], #priceblock_ourprice, .a-price-whole, .price-characteristic

    Price cleaning: strip currency symbols, remove commas, parse as Decimal.
    Returns None if extraction fails, parsing fails, or result is non-positive (≤ 0).

    Args:
        html: Raw HTML string

    Returns:
        Extracted price as Decimal, or None if not found or invalid
    """
    # Level 1: JSON-LD extraction
    price = _extract_price_from_json_ld(html)
    if price is not None:
        return price

    # Level 2: Meta tags extraction
    try:
        soup = BeautifulSoup(html, "lxml")
    except Exception:
        try:
            soup = BeautifulSoup(html, "html.parser")
        except Exception:
            return None

    price = _extract_price_from_meta_tags(soup)
    if price is not None:
        return price

    # Level 3: CSS selectors extraction
    price = _extract_price_from_selectors(soup)
    if price is not None:
        return price

    return None


def _extract_price_from_json_ld(html: str) -> Decimal | None:
    """Extract price from JSON-LD structured data."""
    try:
        # Find all JSON-LD script tags
        pattern = r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>(.*?)</script>'
        matches = re.findall(pattern, html, re.DOTALL | re.IGNORECASE)

        for match in matches:
            try:
                data = json.loads(match)
                # Handle both single object and array formats
                items = data if isinstance(data, list) else [data]

                for item in items:
                    if isinstance(item, dict) and item.get("@type") == "Product":
                        offers = item.get("offers", {})
                        if isinstance(offers, dict):
                            price_str = offers.get("price")
                        elif isinstance(offers, list) and len(offers) > 0:
                            price_str = offers[0].get("price") if isinstance(offers[0], dict) else None
                        else:
                            continue

                        if price_str:
                            return _parse_price(str(price_str))
            except (json.JSONDecodeError, KeyError, AttributeError, TypeError):
                continue

    except Exception:
        pass

    return None


def _extract_price_from_meta_tags(soup: BeautifulSoup) -> Decimal | None:
    """Extract price from meta tags."""
    selectors = [
        ('meta[property="product:price:amount"]', "content"),
        ('meta[name="price"]', "content"),
        ('meta[property="og:price:amount"]', "content"),
    ]

    for selector, attr in selectors:
        try:
            meta = soup.select_one(selector)
            if meta and meta.get(attr):
                return _parse_price(meta.get(attr))
        except Exception:
            continue

    return None


def _extract_price_from_selectors(soup: BeautifulSoup) -> Decimal | None:
    """Extract price from common CSS selectors."""
    selectors = [
        ".price",
        "[data-price]",
        "#priceblock_ourprice",
        ".a-price-whole",
        ".price-characteristic",
    ]

    for selector in selectors:
        try:
            element = soup.select_one(selector)
            if element:
                text = element.get_text(strip=True)
                price = _parse_price(text)
                if price is not None:
                    return price
        except Exception:
            continue

    return None


def _parse_price(price_str: str) -> Decimal | None:
    """
    Parse price string to Decimal.

    Cleans currency symbols, removes commas as thousands separators,
    and strips whitespace.

    Args:
        price_str: Raw price string (may contain symbols, commas, etc.)

    Returns:
        Decimal price or None if parsing fails or result is non-positive
    """
    if not price_str:
        return None

    try:
        # Strip whitespace
        cleaned = price_str.strip()

        # Remove common currency symbols
        for symbol in ["$", "£", "€", "¥", "₹"]:
            cleaned = cleaned.replace(symbol, "")

        # Remove commas (thousands separator)
        cleaned = cleaned.replace(",", "")

        # Strip whitespace again after cleaning
        cleaned = cleaned.strip()

        if not cleaned:
            return None

        # Parse as Decimal
        price = Decimal(cleaned)

        # Reject non-positive prices
        if price <= 0:
            return None

        return price

    except (InvalidOperation, ValueError, TypeError):
        return None
