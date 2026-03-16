from __future__ import annotations

import uuid
from typing import NewType

# Local copy — no shared lib at MVP
TrackedProductId = NewType("TrackedProductId", uuid.UUID)
