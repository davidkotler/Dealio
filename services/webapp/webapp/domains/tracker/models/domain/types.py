from __future__ import annotations

import uuid
from typing import NewType

TrackedProductId = NewType("TrackedProductId", uuid.UUID)
