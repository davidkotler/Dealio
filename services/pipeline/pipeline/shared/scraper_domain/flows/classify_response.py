from __future__ import annotations

from typing import Literal

import httpx


def classify_response(response: httpx.Response) -> Literal["ok", "blocked", "http_error"]:
    """
    Classify an HTTP response to detect blocking, errors, or success.

    Decision tree:
    - Status 403 or (status 200 + Cloudflare JS challenge in body) → "blocked"
    - Status 4xx or 5xx (non-403) → "http_error"
    - Status 200 → "ok"

    Args:
        response: The HTTP response to classify

    Returns:
        One of: "ok", "blocked", "http_error"
    """
    status = response.status_code

    # 403 Forbidden is a blocked response
    if status == 403:
        return "blocked"

    # Status 200 with Cloudflare challenge markers
    if status == 200:
        text_lower = response.text.lower()
        if (
            "cf-browser-verification" in text_lower
            or "cf_chl_prog" in text_lower
            or "checking your browser" in text_lower
        ):
            return "blocked"
        return "ok"

    # Any other 4xx or 5xx is an HTTP error
    if 400 <= status < 600:
        return "http_error"

    # Default to ok for unexpected status codes
    return "ok"
