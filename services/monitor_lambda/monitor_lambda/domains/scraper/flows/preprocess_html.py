"""Pure HTML preprocessing — strips noise and truncates for LLM consumption."""
from __future__ import annotations

import re

from bs4 import BeautifulSoup, Comment

_NOISE_TAGS = ["script", "style", "svg", "canvas", "header", "footer", "nav", "aside"]
_MAX_CHARS = 32_000


def preprocess_html(html: str, max_chars: int = _MAX_CHARS) -> str:
    """
    Strip noise from HTML and truncate for LLM input.

    Steps:
    1. Parse with BeautifulSoup (lxml with html.parser fallback)
    2. Remove script, style, svg, canvas, header, footer, nav, aside, and HTML comments
    3. Collapse whitespace
    4. Truncate at max_chars, scanning back to nearest '<' to avoid mid-tag cuts

    Args:
        html: Raw HTML string from the fetched page
        max_chars: Maximum character length of the output (default 32,000)

    Returns:
        Cleaned, truncated HTML string
    """
    try:
        soup = BeautifulSoup(html, "lxml")
    except Exception:
        soup = BeautifulSoup(html, "html.parser")

    for tag in soup.find_all(_NOISE_TAGS):
        tag.decompose()

    for comment in soup.find_all(string=lambda text: isinstance(text, Comment)):
        comment.extract()

    cleaned = str(soup)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    if len(cleaned) <= max_chars:
        return cleaned

    truncated = cleaned[:max_chars]
    last_open = truncated.rfind("<")
    if last_open > 0:
        truncated = truncated[:last_open]

    return truncated
