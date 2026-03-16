"""Domain exceptions for the identity bounded context."""
from __future__ import annotations


class IdentityError(Exception):
    """Base exception for all identity domain errors."""


class EmailAlreadyRegisteredError(IdentityError):
    """Raised when attempting to register an email that is already in use."""


class InvalidCredentialsError(IdentityError):
    """Raised when email/password credentials do not match."""


class WeakPasswordError(IdentityError):
    """Raised when a supplied password does not meet strength requirements."""


class PasswordChangeNotAllowedError(IdentityError):
    """Raised when a password change is requested for a non-password account (e.g. OIDC-only)."""


class InvalidResetTokenError(IdentityError):
    """Raised when a password-reset token is missing, expired, or already used."""


class InvalidOIDCStateError(IdentityError):
    """Raised when the OIDC state parameter does not match the stored value."""


class OIDCExchangeError(IdentityError):
    """Raised when the OIDC authorization-code exchange fails."""


class OIDCTokenVerificationError(IdentityError):
    """Raised when the OIDC ID token cannot be verified."""
