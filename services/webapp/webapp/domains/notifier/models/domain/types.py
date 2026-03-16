from __future__ import annotations

import uuid
from typing import NewType

NotificationId = NewType("NotificationId", uuid.UUID)
