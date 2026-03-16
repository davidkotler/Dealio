"""Pydantic API contracts for the identity domain."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class RegisterRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    email: EmailStr
    password: str = Field(min_length=8)


class RegisterResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    email: str
    created_at: datetime


class LoginRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    email: EmailStr
    password: str


class LoginResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    email: str


class ChangePasswordRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    current_password: str
    new_password: str = Field(min_length=8)


class RequestPasswordResetRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    email: EmailStr


class ConfirmPasswordResetRequest(BaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")

    token: str
    new_password: str = Field(min_length=8)
