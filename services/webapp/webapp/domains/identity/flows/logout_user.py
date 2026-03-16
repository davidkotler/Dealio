"""Flow: logout (stateless JWT — cookie expiry handled by the route layer)."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class LogoutUser:
    """Stateless JWT logout — no server-side action required.

    The route handler is responsible for expiring / clearing the auth cookie.
    This class exists to document the contract and provide a testable seam.
    """

    async def execute(self) -> None:
        pass
