# Plan: Task 8 — Identity Google OIDC

## Context

Implement Google OIDC login for Dealio's identity domain. Users can sign in via Google; the callback flow finds an existing user by `google_sub`, links `google_sub` on email match, or creates a new Google-only account. The domain already has scaffolding (exceptions, `OIDCClient` protocol stub, `User.google_sub` field) but the protocol signatures do not match the task spec and `UserRepository` is missing `get_by_google_sub`.

## Design Target

| Service | Domain | Status | Layers Affected |
|---------|--------|--------|-----------------|
| webapp | identity | existing | ports, adapters, flows |

**Complexity:** Medium — 3 new files + 3 file updates, no new domain concepts.

---

## Key Discrepancies Found

| Area | Current state | Required by task spec |
|------|--------------|----------------------|
| `OIDCClient.build_authorization_url` | `get_authorization_url(state: str)` (no nonce) | `build_authorization_url(state: str, nonce: str) -> str` |
| `OIDCClient.exchange_code` | `exchange_code(code: str, state: str)` | `exchange_code(code: str) -> dict` |
| `OIDCClient.verify_id_token` | does not exist | `verify_id_token(id_token: str, nonce: str) -> dict` |
| `UserRepository.get_by_google_sub` | does not exist | `get_by_google_sub(sub: str) -> User \| None` |
| `TokenStore.store/set` | method named `store(key, value, ttl_seconds)` | task doc shows `set()` — **keep `store()`** (existing impl is canonical) |

---

## Files

### Modified
1. `services/webapp/webapp/domains/identity/ports/oidc_client.py`
   - Replace all three method stubs to match task spec signatures

2. `services/webapp/webapp/domains/identity/ports/user_repository.py`
   - Add `get_by_google_sub(self, sub: str) -> User | None`

3. `services/webapp/webapp/domains/identity/adapters/sqlalchemy_user_repository.py`
   - Implement `get_by_google_sub` using `WHERE google_sub = :sub` query

### Created
4. `services/webapp/webapp/domains/identity/adapters/authlib_google_oidc_client.py`
5. `services/webapp/webapp/domains/identity/flows/initiate_google_login.py`
6. `services/webapp/webapp/domains/identity/flows/handle_google_callback.py`

---

## Implementation Details

### 1. `ports/oidc_client.py` — Updated Protocol

```python
class OIDCClient(Protocol):
    async def build_authorization_url(self, state: str, nonce: str) -> str: ...
    async def exchange_code(self, code: str) -> dict: ...
    async def verify_id_token(self, id_token: str, nonce: str) -> dict: ...
```

### 2. `ports/user_repository.py` — Add method

```python
async def get_by_google_sub(self, sub: str) -> User | None: ...
```

### 3. `adapters/sqlalchemy_user_repository.py` — Implement `get_by_google_sub`

Mirror the existing `get_by_email` pattern:
```python
async def get_by_google_sub(self, sub: str) -> User | None:
    result = await self._session.execute(
        select(UserRecord).where(UserRecord.google_sub == sub)
    )
    record = result.scalar_one_or_none()
    return _to_domain(record) if record else None
```

### 4. `adapters/authlib_google_oidc_client.py` — `AuthlibGoogleOIDCClient`

```python
DISCOVERY_URL = "https://accounts.google.com/.well-known/openid-configuration"

async def build_authorization_url(self, state: str, nonce: str) -> str:
    async with AsyncOAuth2Client(client_id=..., redirect_uri=...) as client:
        metadata = await client.load_server_metadata(DISCOVERY_URL)
        url, _ = client.create_authorization_url(
            metadata["authorization_endpoint"],
            state=state, nonce=nonce, scope="openid email profile",
        )
        return url

async def exchange_code(self, code: str) -> dict:
    async with AsyncOAuth2Client(client_id=..., client_secret=..., redirect_uri=...) as client:
        metadata = await client.load_server_metadata(DISCOVERY_URL)
        return await client.fetch_token(metadata["token_endpoint"], code=code)

async def verify_id_token(self, id_token: str, nonce: str) -> dict:
    # Fetch JWKS from Google discovery; decode with authlib.jose.JsonWebToken
    async with httpx.AsyncClient() as client:
        metadata = (await client.get(DISCOVERY_URL)).json()
        jwks_data = (await client.get(metadata["jwks_uri"])).json()
    jwt = JsonWebToken(["RS256"])
    claims = jwt.decode(id_token, jwks_data)
    claims.validate()
    if claims.get("nonce") != nonce:
        raise ValueError("nonce mismatch")
    return dict(claims)
```

> Note: `httpx` is already a project dependency (used by authlib).

### 5. `flows/initiate_google_login.py` — `InitiateGoogleLogin`

Pattern: dataclass with injected dependencies, single `async def execute()`. **Non-underscore field names** — mirrors `LoginUser` and other existing flows.

```python
@dataclass
class InitiateGoogleLogin:
    oidc_client: OIDCClient
    token_store: TokenStore

    async def execute(self) -> str:
        state = secrets.token_urlsafe(32)
        nonce = secrets.token_urlsafe(32)
        await self.token_store.store(f"oidc:{state}", nonce, ttl_seconds=300)
        return await self.oidc_client.build_authorization_url(state, nonce)
```

### 6. `flows/handle_google_callback.py` — `HandleGoogleCallback`

```python
@dataclass
class HandleGoogleCallback:
    oidc_client: OIDCClient
    user_repo: UserRepository
    token_store: TokenStore
    jwt_secret: str

    async def execute(self, code: str, state: str) -> tuple[User, str]:
        # Validate + consume state
        nonce = await self.token_store.get(f"oidc:{state}")
        if nonce is None:
            raise InvalidOIDCStateError("Unknown or expired OIDC state")
        await self.token_store.delete(f"oidc:{state}")

        # Exchange code
        try:
            token_data = await self.oidc_client.exchange_code(code)
        except Exception as exc:
            raise OIDCExchangeError("Token exchange failed") from exc

        # Verify id_token
        try:
            claims = await self.oidc_client.verify_id_token(token_data["id_token"], nonce)
        except Exception as exc:
            raise OIDCTokenVerificationError("ID token verification failed") from exc

        sub: str = claims["sub"]
        email: str = claims["email"]
        now = datetime.now(UTC)

        # Find-or-create-or-link
        user = await self.user_repo.get_by_google_sub(sub)

        if user is None:
            existing = await self.user_repo.get_by_email(email)
            if existing is not None:
                # Link google_sub to email-only account
                user = dataclasses.replace(existing, google_sub=sub, updated_at=now)
                await self.user_repo.save(user)
            else:
                # Create new Google-only account
                user = User(
                    id=UserId(uuid.uuid4()),
                    email=email,
                    password_hash=None,
                    google_sub=sub,
                    created_at=now,
                    updated_at=now,
                )
                await self.user_repo.save(user)

        jwt_token = generate_jwt(user.id, self.jwt_secret)
        return user, jwt_token
```

> `dataclasses.replace()` works if `User` is a standard dataclass (not frozen-with-slots).
> If `User` is frozen, construct a new instance explicitly with same id/email/password_hash.
> Check `User` definition during implementation; adjust accordingly.

---

## Invariants Preserved

- `google_sub` is only linked when currently `None` (email match path)
- `state` key deleted after first use (replay protection)
- Google-only users always have `password_hash = None`

---

## Verification

Run the two verification snippets from the task spec (adapted to use `store()` not `set()`):

```bash
cd services/webapp

# 1. TokenStore round-trip
uv run python -c "
import asyncio
from webapp.domains.identity.adapters.in_memory_token_store import InMemoryTokenStore
store = InMemoryTokenStore()
asyncio.run(store.store('oidc:abc123', 'nonce_value', ttl_seconds=300))
nonce = asyncio.run(store.get('oidc:abc123'))
print(nonce)   # nonce_value
asyncio.run(store.delete('oidc:abc123'))
gone = asyncio.run(store.get('oidc:abc123'))
print(gone)    # None
"

# 2. HandleGoogleCallback mock (new-user path)
uv run python -c "
import asyncio
from unittest.mock import AsyncMock
from webapp.domains.identity.flows.handle_google_callback import HandleGoogleCallback
from webapp.domains.identity.adapters.in_memory_token_store import InMemoryTokenStore

store = InMemoryTokenStore()
asyncio.run(store.store('oidc:state123', 'nonce_abc', ttl_seconds=300))

mock_oidc = AsyncMock()
mock_oidc.exchange_code.return_value = {'id_token': 'tok'}
mock_oidc.verify_id_token.return_value = {'sub': 'google-sub-1', 'email': 'newuser@gmail.com'}

mock_repo = AsyncMock()
mock_repo.get_by_google_sub.return_value = None
mock_repo.get_by_email.return_value = None
mock_repo.save.return_value = None

flow = HandleGoogleCallback(oidc_client=mock_oidc, user_repo=mock_repo, token_store=store, jwt_secret='test-secret')
user, token = asyncio.run(flow.execute(code='authcode', state='state123'))
print('email:', user.email, 'google_sub:', user.google_sub)
# Expected: newuser@gmail.com, google-sub-1
"
```
