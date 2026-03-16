from __future__ import annotations

import uuid
from typing import NewType

UserId = NewType("UserId", uuid.UUID)
PasswordResetTokenId = NewType("PasswordResetTokenId", uuid.UUID)
