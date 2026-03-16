"""Identity auth routes — v1."""
from __future__ import annotations

import boto3
from fastapi import APIRouter, Depends, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.ext.asyncio import AsyncSession

from webapp.config import Settings
from webapp.dependencies import get_current_user, get_db_session, get_settings
from webapp.domains.identity.adapters.authlib_google_oidc_client import AuthlibGoogleOIDCClient
from webapp.domains.identity.adapters.ses_email_sender import SESEmailSender
from webapp.domains.identity.adapters.sqlalchemy_token_repository import SQLAlchemyTokenRepository
from webapp.domains.identity.adapters.sqlalchemy_user_repository import SQLAlchemyUserRepository
from webapp.domains.identity.exceptions import (
    InvalidOIDCStateError,
    OIDCExchangeError,
    OIDCTokenVerificationError,
)
from webapp.domains.identity.flows.change_password import ChangePassword
from webapp.domains.identity.flows.confirm_password_reset import ConfirmPasswordReset
from webapp.domains.identity.flows.handle_google_callback import HandleGoogleCallback
from webapp.domains.identity.flows.initiate_google_login import InitiateGoogleLogin
from webapp.domains.identity.flows.login_user import LoginUser
from webapp.domains.identity.flows.logout_user import LogoutUser
from webapp.domains.identity.flows.register_user import RegisterUser
from webapp.domains.identity.flows.request_password_reset import RequestPasswordReset
from webapp.domains.identity.models.contracts.api.auth import (
    ChangePasswordRequest,
    ConfirmPasswordResetRequest,
    LoginRequest,
    LoginResponse,
    RegisterRequest,
    RegisterResponse,
    RequestPasswordResetRequest,
)
from webapp.domains.identity.models.domain.user import User

_COOKIE_NAME = "session"
_COOKIE_MAX_AGE = 86400


def _set_session_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        _COOKIE_NAME,
        token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=_COOKIE_MAX_AGE,
        path="/",
    )


router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=201, response_model=RegisterResponse)
async def register(
    body: RegisterRequest,
    response: Response,
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> RegisterResponse:
    user, token = await RegisterUser(
        user_repo=SQLAlchemyUserRepository(session),
        jwt_secret=settings.jwt_secret,
    ).execute(body.email, body.password)
    _set_session_cookie(response, token)
    return RegisterResponse(id=str(user.id), email=user.email, created_at=user.created_at)


@router.post("/login", status_code=200, response_model=LoginResponse)
async def login(
    body: LoginRequest,
    response: Response,
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> LoginResponse:
    user, token = await LoginUser(
        user_repo=SQLAlchemyUserRepository(session),
        jwt_secret=settings.jwt_secret,
    ).execute(body.email, body.password)
    _set_session_cookie(response, token)
    return LoginResponse(id=str(user.id), email=user.email)


@router.post("/logout", status_code=204)
async def logout(
    response: Response,
    current_user: User = Depends(get_current_user),
) -> None:
    await LogoutUser().execute()
    response.delete_cookie(_COOKIE_NAME, path="/")


@router.get("/google/login", status_code=302)
async def google_login(
    request: Request,
    settings: Settings = Depends(get_settings),
) -> RedirectResponse:
    oidc_client = AuthlibGoogleOIDCClient(
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        redirect_uri=settings.google_redirect_uri,
    )
    url = await InitiateGoogleLogin(
        oidc_client=oidc_client,
        token_store=request.app.state.token_store,
    ).execute()
    return RedirectResponse(url=url, status_code=302)


@router.get("/google/callback", status_code=303)
async def google_callback(
    code: str,
    state: str,
    request: Request,
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> RedirectResponse:
    oidc_client = AuthlibGoogleOIDCClient(
        client_id=settings.google_client_id,
        client_secret=settings.google_client_secret,
        redirect_uri=settings.google_redirect_uri,
    )
    try:
        user, token = await HandleGoogleCallback(
            oidc_client=oidc_client,
            user_repo=SQLAlchemyUserRepository(session),
            token_store=request.app.state.token_store,
            jwt_secret=settings.jwt_secret,
        ).execute(code, state)
    except InvalidOIDCStateError:
        return RedirectResponse(url="/login?error=INVALID_OIDC_STATE", status_code=303)
    except OIDCExchangeError:
        return RedirectResponse(url="/login?error=OIDC_EXCHANGE_FAILED", status_code=303)
    except OIDCTokenVerificationError:
        return RedirectResponse(url="/login?error=OIDC_TOKEN_VERIFICATION_FAILED", status_code=303)

    redirect = RedirectResponse(url="/dashboard", status_code=303)
    _set_session_cookie(redirect, token)
    return redirect


@router.post("/password-reset", status_code=204)
async def request_password_reset(
    body: RequestPasswordResetRequest,
    session: AsyncSession = Depends(get_db_session),
    settings: Settings = Depends(get_settings),
) -> None:
    await RequestPasswordReset(
        user_repo=SQLAlchemyUserRepository(session),
        token_repo=SQLAlchemyTokenRepository(session),
        email_sender=SESEmailSender(
            _client=boto3.client("ses", region_name=settings.aws_region),
            _from_address=settings.ses_from_address,
        ),
        app_base_url=settings.app_base_url,
    ).execute(body.email)


@router.post("/password-reset/confirm", status_code=204)
async def confirm_password_reset(
    body: ConfirmPasswordResetRequest,
    session: AsyncSession = Depends(get_db_session),
) -> None:
    await ConfirmPasswordReset(
        token_repo=SQLAlchemyTokenRepository(session),
        user_repo=SQLAlchemyUserRepository(session),
    ).execute(body.token, body.new_password)


@router.put("/password", status_code=204)
async def change_password(
    body: ChangePasswordRequest,
    session: AsyncSession = Depends(get_db_session),
    current_user: User = Depends(get_current_user),
) -> None:
    await ChangePassword(
        user_repo=SQLAlchemyUserRepository(session),
    ).execute(current_user.id, body.current_password, body.new_password)
