# Plan: Task 7 — Identity Email/Password Auth

## Context

Task 7 implements the email/password authentication foundation for the Dealio webapp. The hexagonal architecture skeleton (domain models, ORM records, port protocols) was completed in T-2, T-3, and T-4. This task fills in the `flows/` and `adapters/` directories, which are currently empty `__init__.py` stubs.

Implementing this task unlocks all authenticated operations (T-8 OIDC, T-9 tracker flows, T-12 routes).

---

## Design Target

| Service | Domain | Status | Layers Affected |
|---------|--------|--------|-----------------|
| `services/webapp` | `identity` | existing | flows (new), adapters (new), config (extend) |

---

## Critical Port/Spec Discrepancies

The task spec was written before T-3 was implemented. The **actual ports are authoritative**. Key differences:

| Spec says | Actual port | Resolution |
|-----------|-------------|------------|
| `UserRepository.get(user_id)` | `get_by_id(user_id)` | Use `get_by_id` |
| `UserRepository.exists_by_email(email)` | not in port | Use `get_by_email` + check None |
| `TokenRepository.find_valid_unused()` (returns list) | `get_by_token_hash(hash)` (direct lookup) | SHA-256 hash for deterministic lookup (see below) |
| `TokenRepository` has no `mark_used` | `mark_used(token_id, used_at)` | Call `mark_used` explicitly |
| `EmailSender.send_password_reset(to, raw_token)` | `send_password_reset(to_email, reset_link)` | Flow builds URL; pass full link |
| `TokenStore.set(...)` | `store(key, value, ttl_seconds)` | Use `store` |

### Token Hash Strategy (Key Design Decision)

`TokenRepository.get_by_token_hash(hash: str)` requires a **deterministic** hash. bcrypt is salted and non-deterministic — you cannot look up by bcrypt hash after the fact.

**Decision: Store `hashlib.sha256(raw_token.encode()).hexdigest()` as `token_hash`.**

- `RequestPasswordReset`: `token_hash = sha256(raw_token).hexdigest()` → store in DB
- `ConfirmPasswordReset`: `token_hash = sha256(submitted).hexdigest()` → look up via `get_by_token_hash`
- SHA-256 of a `secrets.token_urlsafe(32)` (32 bytes = 256 bits entropy) is cryptographically safe for this use case

---

## Files to Create / Modify

### New Files

```
services/webapp/webapp/domains/identity/
├── adapters/
│   ├── jwt_service.py               # generate_jwt, decode_jwt functions
│   ├── sqlalchemy_user_repository.py
│   ├── sqlalchemy_token_repository.py
│   ├── in_memory_token_store.py
│   └── ses_email_sender.py
└── flows/
    ├── register_user.py
    ├── login_user.py
    ├── logout_user.py               # trivial — documents stateless JWT contract
    ├── request_password_reset.py
    ├── confirm_password_reset.py
    └── change_password.py
```

### Modified Files

- `services/webapp/webapp/config.py` — add `app_base_url: str` field (needed by `RequestPasswordReset` to build the reset link URL)

---

## Implementation Details

### 7.1 — `adapters/jwt_service.py`

Two standalone functions (not a class):

```python
def generate_jwt(user_id: UserId, secret: str) -> str:
    now = datetime.now(tz=timezone.utc)
    payload = {"sub": str(user_id), "iat": now, "exp": now + timedelta(seconds=86400)}
    return jwt.encode(payload, secret, algorithm="HS256")

def decode_jwt(token: str, secret: str) -> UserId:
    """Raises JWTError on invalid/expired token."""
    payload = jwt.decode(token, secret, algorithms=["HS256"])
    return UserId(uuid.UUID(payload["sub"]))
```

Import: `from jose import jwt, JWTError`

### 7.2 — `adapters/sqlalchemy_user_repository.py`

Constructor: `__init__(self, session: AsyncSession)`

Methods:
- `get_by_id(user_id)`: `SELECT * FROM users WHERE id = :id` → `_to_domain(record)` or None
- `get_by_email(email)`: `SELECT * FROM users WHERE email = :email` → domain or None
- `save(user)`: PostgreSQL upsert via `insert(UserRecord).values(...).on_conflict_do_update(index_elements=["id"], set_={...})`

Mapping helpers:
- `_to_domain(record: UserRecord) -> User`: wraps `password_hash` string in `HashedPassword(value=record.password_hash)` if not None
- `_to_record(user: User) -> dict`: extracts `user.password_hash.value` if not None

### 7.3 — `adapters/sqlalchemy_token_repository.py`

Constructor: `__init__(self, session: AsyncSession)`

Methods:
- `get_by_token_hash(token_hash)`: `SELECT * FROM password_reset_tokens WHERE token_hash = :hash` → domain or None
- `save(token)`: `INSERT INTO password_reset_tokens ...`
- `mark_used(token_id, used_at)`: `UPDATE password_reset_tokens SET used_at = :used_at WHERE id = :id`
- `delete_by_user_id(user_id)`: `DELETE FROM password_reset_tokens WHERE user_id = :uid`

Mapping: `PasswordResetTokenRecord ↔ PasswordResetToken` (flat fields, no wrapping needed)

### 7.4 — `adapters/in_memory_token_store.py`

```python
@dataclass
class InMemoryTokenStore:
    _store: dict[str, tuple[str, datetime]] = field(default_factory=dict)

    async def store(self, key: str, value: str, ttl_seconds: int) -> None: ...
    async def get(self, key: str) -> str | None:  # returns None if expired
    async def delete(self, key: str) -> None: ...
```

TTL check on `get`: if `datetime.now(utc) >= expires_at`, delete entry and return None.

### 7.5 — `adapters/ses_email_sender.py`

Constructor: `__init__(self, boto3_ses_client, from_address: str)`

```python
async def send_password_reset(self, to_email: str, reset_link: str) -> None:
    self._client.send_email(
        Source=self._from_address,
        Destination={"ToAddresses": [to_email]},
        Message={
            "Subject": {"Data": "Reset your Dealio password"},
            "Body": {
                "Text": {"Data": f"Reset link: {reset_link}"},
                "Html": {"Data": f'<a href="{reset_link}">Reset password</a>'},
            },
        },
    )
```

Note: boto3 SES `send_email` is synchronous — wrap in `asyncio.get_event_loop().run_in_executor(None, ...)` to avoid blocking the event loop.

### 7.6 — `flows/register_user.py`

```python
@dataclass
class RegisterUser:
    user_repo: UserRepository
    jwt_secret: str

    async def execute(self, email: str, raw_password: str) -> tuple[User, str]:
        normalised = email.lower()
        existing = await self.user_repo.get_by_email(normalised)
        if existing is not None:
            raise EmailAlreadyRegisteredError(normalised)
        hashed = HashedPassword.create(raw_password, cost=14)
        now = datetime.now(tz=timezone.utc)
        user = User(id=UserId(uuid.uuid4()), email=normalised, password_hash=hashed,
                    google_sub=None, created_at=now, updated_at=now)
        await self.user_repo.save(user)
        token = generate_jwt(user.id, self.jwt_secret)
        return user, token
```

### 7.7 — `flows/login_user.py`

```python
@dataclass
class LoginUser:
    user_repo: UserRepository
    jwt_secret: str

    async def execute(self, email: str, raw_password: str) -> tuple[User, str]:
        user = await self.user_repo.get_by_email(email.lower())
        if user is None or user.password_hash is None:
            raise InvalidCredentialsError()
        if not user.password_hash.verify(raw_password):
            raise InvalidCredentialsError()
        token = generate_jwt(user.id, self.jwt_secret)
        return user, token
```

### 7.8 — `flows/logout_user.py`

```python
@dataclass
class LogoutUser:
    """Stateless JWT logout — no server-side action. Route handler expires the cookie."""
    async def execute(self) -> None:
        pass
```

### 7.9 — `flows/request_password_reset.py`

```python
@dataclass
class RequestPasswordReset:
    user_repo: UserRepository
    token_repo: TokenRepository
    email_sender: EmailSender
    app_base_url: str  # from Settings.app_base_url

    async def execute(self, email: str) -> None:
        user = await self.user_repo.get_by_email(email.lower())
        if user is None:
            return  # silent — no enumeration
        raw_token = secrets.token_urlsafe(32)
        token_hash = hashlib.sha256(raw_token.encode()).hexdigest()
        now = datetime.now(tz=timezone.utc)
        token = PasswordResetToken(
            id=PasswordResetTokenId(uuid.uuid4()),
            user_id=user.id,
            token_hash=token_hash,
            expires_at=now + timedelta(hours=1),
            used_at=None,
        )
        await self.token_repo.save(token)
        reset_link = f"{self.app_base_url}/auth/password-reset/confirm?token={raw_token}"
        await self.email_sender.send_password_reset(to_email=user.email, reset_link=reset_link)
```

### 7.10 — `flows/confirm_password_reset.py`

```python
@dataclass
class ConfirmPasswordReset:
    token_repo: TokenRepository
    user_repo: UserRepository

    async def execute(self, submitted_token: str, new_password: str) -> None:
        token_hash = hashlib.sha256(submitted_token.encode()).hexdigest()
        token = await self.token_repo.get_by_token_hash(token_hash)
        if token is None or not token.is_valid():
            raise InvalidResetTokenError()
        now = datetime.now(tz=timezone.utc)
        await self.token_repo.mark_used(token.id, now)
        user = await self.user_repo.get_by_id(token.user_id)
        user.password_hash = HashedPassword.create(new_password, cost=14)
        user.updated_at = now
        await self.user_repo.save(user)
```

### 7.11 — `flows/change_password.py`

```python
@dataclass
class ChangePassword:
    user_repo: UserRepository

    async def execute(self, user_id: UserId, current_password: str, new_password: str) -> None:
        user = await self.user_repo.get_by_id(user_id)
        if user.password_hash is None:
            raise PasswordChangeNotAllowedError()
        if not user.password_hash.verify(current_password):
            raise InvalidCredentialsError()
        now = datetime.now(tz=timezone.utc)
        user.password_hash = HashedPassword.create(new_password, cost=14)
        user.updated_at = now
        await self.user_repo.save(user)
```

### Config change — `config.py`

Add to `Settings`:
```python
app_base_url: Annotated[str, Field(description="Public base URL for building password reset links")]
```

---

## Quality Attribute Notes

- **Security**: No PII in logs — flows must NOT log emails; use `user.id` only. Enumeration prevented in `LoginUser` (same error for missing user vs wrong password) and `RequestPasswordReset` (always silent).
- **Testability**: All flows use constructor-injected dependencies (Protocol ports). Pure logic is separate from I/O.
- **Robustness**: `ConfirmPasswordReset` checks `is_valid()` before marking used. `ChangePassword` checks Google-only guard before verifying password.
- **SES blocking**: boto3 `send_email` is sync — must run in executor to avoid blocking event loop.

---

## Verification

```bash
cd services/webapp

# JWT round-trip
uv run python -c "
import uuid
from webapp.domains.identity.adapters.jwt_service import generate_jwt, decode_jwt
uid = uuid.uuid4()
token = generate_jwt(uid, secret='test-secret-32chars-minimum-ok!!')
decoded = decode_jwt(token, secret='test-secret-32chars-minimum-ok!!')
print('JWT round-trip:', decoded == uid)  # True
"

# HashedPassword (existing from T-2)
uv run python -c "
from webapp.domains.identity.models.domain.hashed_password import HashedPassword
hp = HashedPassword.create('mysecurepassword123')
print(hp.verify('mysecurepassword123'))  # True
print(hp.verify('wrongpassword'))        # False
"

# InMemoryTokenStore TTL
uv run python -c "
import asyncio
from webapp.domains.identity.adapters.in_memory_token_store import InMemoryTokenStore
async def test():
    store = InMemoryTokenStore()
    await store.store('key1', 'val1', ttl_seconds=60)
    print(await store.get('key1'))  # val1
    await store.delete('key1')
    print(await store.get('key1'))  # None
asyncio.run(test())
"

# Integration: register + login against real DB
uv run python -c "
import asyncio, uuid
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from webapp.domains.identity.flows.register_user import RegisterUser
from webapp.domains.identity.flows.login_user import LoginUser
from webapp.domains.identity.adapters.sqlalchemy_user_repository import SQLAlchemyUserRepository

DATABASE_URL = 'postgresql+asyncpg://postgres:test@localhost:5432/dealio'
engine = create_async_engine(DATABASE_URL)
async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def main():
    async with async_session() as session:
        repo = SQLAlchemyUserRepository(session)
        register = RegisterUser(user_repo=repo, jwt_secret='test-secret-32chars-minimum-ok!!')
        user, token = await register.execute('test@example.com', 'password123')
        print('Registered:', user.email, 'token:', token[:20] + '...')
        login = LoginUser(user_repo=repo, jwt_secret='test-secret-32chars-minimum-ok!!')
        user2, token2 = await login.execute('test@example.com', 'password123')
        print('Login ok:', user2.id == user.id)

asyncio.run(main())
"
```
