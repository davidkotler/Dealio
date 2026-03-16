from __future__ import annotations

import ipaddress
import urllib.parse
from dataclasses import dataclass

from webapp.domains.tracker.exceptions import InvalidProductUrlError


@dataclass(frozen=True)
class ProductUrl:
    value: str

    @classmethod
    def parse(cls, raw: str) -> "ProductUrl":
        parsed = urllib.parse.urlparse(raw)
        if parsed.scheme not in ("http", "https"):
            raise InvalidProductUrlError(
                f"URL scheme must be http or https, got {parsed.scheme!r}: {raw!r}"
            )
        host = parsed.hostname or ""
        if not host or host == "localhost":
            raise InvalidProductUrlError(
                f"URL host is not allowed: {host!r}"
            )
        try:
            addr = ipaddress.ip_address(host)
            if addr.is_private or addr.is_loopback or addr.is_link_local:
                raise InvalidProductUrlError(
                    f"URL points to a private or loopback address: {host!r}"
                )
        except ValueError:
            pass  # hostname, not an IP literal — only "localhost" is rejected above
        return cls(value=raw)
