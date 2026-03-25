"""Auth router — registration, login, tokens, password/email management."""

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Cookie, Depends, Request, Response
from redis.asyncio import Redis
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_db_session
from app.core.dependencies import get_current_user, get_current_user_id
from app.core.openapi import error_responses
from app.core.rate_limit import limiter
from app.core.redis import get_redis
from app.schemas.auth import (
    ChangeEmailRequest,
    ChangePasswordRequest,
    ConfirmEmailChangeRequest,
    CurrentUserResponse,
    ForgotPasswordRequest,
    LoginRequest,
    MessageResponse,
    RegisterRequest,
    ResendVerificationRequest,
    ResetPasswordRequest,
    TokenResponse,
    VerifyEmailRequest,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth")

REFRESH_COOKIE_KEY = "refresh_token"
REFRESH_COOKIE_KEY_ADMIN = "refresh_token_admin"
ACCESS_TOKEN_COOKIE_KEY = "access_token"
REFRESH_COOKIE_MAX_AGE = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600
ACCESS_TOKEN_COOKIE_MAX_AGE = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
REFRESH_COOKIE_PATH = "/api/v1/auth"
ACCESS_TOKEN_COOKIE_PATH = "/api/v1"


def _is_admin_origin(request: Request) -> bool:
    """True if Origin or Referer contains 'admin.' (admin subdomain)."""
    origin = request.headers.get("Origin") or request.headers.get("Referer") or ""
    return "admin." in origin


def _get_refresh_cookie_key(request: Request) -> str:
    return REFRESH_COOKIE_KEY_ADMIN if _is_admin_origin(request) else REFRESH_COOKIE_KEY


def _set_refresh_cookie(response: Response, token: str, key: str = REFRESH_COOKIE_KEY) -> None:
    kwargs: dict[str, Any] = {
        "httponly": True,
        "secure": True,
        "samesite": "lax",
        "max_age": REFRESH_COOKIE_MAX_AGE,
        "path": REFRESH_COOKIE_PATH,
    }
    if settings.COOKIE_DOMAIN:
        kwargs["domain"] = settings.COOKIE_DOMAIN
    response.set_cookie(key=key, value=token, **kwargs)


def _clear_refresh_cookie(response: Response, key: str = REFRESH_COOKIE_KEY) -> None:
    kwargs: dict[str, Any] = {
        "httponly": True,
        "secure": True,
        "samesite": "lax",
        "path": REFRESH_COOKIE_PATH,
    }
    if settings.COOKIE_DOMAIN:
        kwargs["domain"] = settings.COOKIE_DOMAIN
    response.delete_cookie(key=key, **kwargs)


def _set_access_token_cookie(response: Response, token: str) -> None:
    """Set access_token cookie so cross-origin API requests with credentials get auth.
    SameSite=None allows cookie to be sent from frontend on different subdomain.
    """
    kwargs: dict[str, Any] = {
        "httponly": True,
        "secure": True,
        "samesite": settings.ACCESS_TOKEN_COOKIE_SAMESITE,
        "path": ACCESS_TOKEN_COOKIE_PATH,
        "max_age": ACCESS_TOKEN_COOKIE_MAX_AGE,
    }
    if settings.COOKIE_DOMAIN:
        kwargs["domain"] = settings.COOKIE_DOMAIN
    response.set_cookie(key=ACCESS_TOKEN_COOKIE_KEY, value=token, **kwargs)


def _clear_access_token_cookie(response: Response) -> None:
    kwargs: dict[str, Any] = {
        "httponly": True,
        "secure": True,
        "samesite": settings.ACCESS_TOKEN_COOKIE_SAMESITE,
        "path": ACCESS_TOKEN_COOKIE_PATH,
    }
    if settings.COOKIE_DOMAIN:
        kwargs["domain"] = settings.COOKIE_DOMAIN
    response.delete_cookie(key=ACCESS_TOKEN_COOKIE_KEY, **kwargs)


@router.post(
    "/register",
    status_code=201,
    response_model=MessageResponse,
    summary="Регистрация нового пользователя",
    responses=error_responses(409, 422, 429),
)
@limiter.limit("5/minute")
async def register(
    request: Request,
    data: RegisterRequest,
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),
) -> MessageResponse:
    """Создаёт аккаунт и отправляет письмо подтверждения.

    - **409** — email уже зарегистрирован
    - **429** — превышен лимит 5 запросов/мин
    """
    svc = AuthService(db, redis)
    await svc.register(email=data.email, password=data.password)
    return MessageResponse(message="Проверьте email для подтверждения")


@router.post(
    "/verify-email",
    response_model=MessageResponse,
    summary="Подтверждение email",
    responses=error_responses(404, 422, 429),
)
@limiter.limit("20/minute")
async def verify_email(
    request: Request,
    data: VerifyEmailRequest,
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),
) -> MessageResponse:
    """Подтверждает email по одноразовому токену из письма.

    - **404** — токен не найден или истёк
    """
    svc = AuthService(db, redis)
    await svc.verify_email(data.token)
    return MessageResponse(message="Email подтверждён")


@router.post(
    "/resend-verification-email",
    response_model=MessageResponse,
    summary="Повторная отправка письма подтверждения",
    responses=error_responses(422, 429),
)
@limiter.limit("5/minute")
async def resend_verification_email(
    request: Request,
    data: ResendVerificationRequest,
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),
) -> MessageResponse:
    """Повторно отправляет письмо подтверждения email. Всегда 200 — не раскрывает
    статус верификации.

    - **429** — превышен лимит (3 запроса на email за 10 минут)
    """
    svc = AuthService(db, redis)
    await svc.resend_verification_email(data.email)
    return MessageResponse(
        message="Письмо с подтверждением отправлено на указанный email"
    )


@router.post(
    "/login",
    response_model=TokenResponse,
    summary="Авторизация",
    responses=error_responses(401, 422, 429),
)
@limiter.limit("10/minute")
async def login(
    request: Request,
    data: LoginRequest,
    response: Response,
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),
) -> TokenResponse:
    """Аутентифицирует пользователя, возвращает access_token.
    Refresh token устанавливается в httpOnly cookie.

    - **401** — неверный email/пароль или email не подтверждён
    - **429** — превышен лимит 10 запросов/мин
    """
    svc = AuthService(db, redis)
    tokens = await svc.login(email=data.email, password=data.password)
    cookie_key = _get_refresh_cookie_key(request)
    _set_refresh_cookie(response, tokens["refresh_token"], key=cookie_key)
    _set_access_token_cookie(response, tokens["access_token"])
    return TokenResponse(
        access_token=tokens["access_token"],
        role=tokens["role"],
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Обновление токена",
    responses=error_responses(401, 429),
)
@limiter.limit("30/minute")
async def refresh(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),
    refresh_token: str | None = Cookie(None, alias=REFRESH_COOKIE_KEY),
    refresh_token_admin: str | None = Cookie(None, alias=REFRESH_COOKIE_KEY_ADMIN),
) -> TokenResponse:
    """Обновляет пару access/refresh токенов.
    Refresh token берётся из httpOnly cookie по Origin: admin. → refresh_token_admin, иначе refresh_token.

    - **401** — refresh token отсутствует, невалиден или отозван
    """
    cookie_key = _get_refresh_cookie_key(request)
    token = refresh_token_admin if cookie_key == REFRESH_COOKIE_KEY_ADMIN else refresh_token
    if not token:
        from app.core.exceptions import UnauthorizedError

        raise UnauthorizedError("Refresh token missing")
    svc = AuthService(db, redis)
    tokens = await svc.refresh_tokens(token)
    _set_refresh_cookie(response, tokens["refresh_token"], key=cookie_key)
    _set_access_token_cookie(response, tokens["access_token"])
    return TokenResponse(
        access_token=tokens["access_token"],
        role=tokens["role"],
    )


@router.get(
    "/me",
    response_model=CurrentUserResponse,
    summary="Текущий пользователь",
    responses=error_responses(401),
)
async def get_me(
    payload: dict[str, Any] = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),
) -> CurrentUserResponse:
    """Возвращает id, email, role, is_staff и sidebar_sections для текущего пользователя.
    Используется фронтендом для построения сайдбара по ролям.
    """
    svc = AuthService(db, redis)
    return await svc.get_current_user_info(user_id=payload["sub"])


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Выход из системы",
)
async def logout(
    response: Response,
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),
    refresh_token: str | None = Cookie(None, alias=REFRESH_COOKIE_KEY),
    refresh_token_admin: str | None = Cookie(None, alias=REFRESH_COOKIE_KEY_ADMIN),
) -> MessageResponse:
    """Отзывает refresh token и очищает оба cookie (client + admin)."""
    svc = AuthService(db, redis)
    for token in (refresh_token, refresh_token_admin):
        if token:
            await svc.logout(token)
    _clear_refresh_cookie(response, key=REFRESH_COOKIE_KEY)
    _clear_refresh_cookie(response, key=REFRESH_COOKIE_KEY_ADMIN)
    _clear_access_token_cookie(response)
    return MessageResponse(message="Вы вышли из системы")


@router.post(
    "/logout-all",
    response_model=MessageResponse,
    summary="Выйти на всех устройствах",
    responses=error_responses(401),
)
async def logout_all(
    response: Response,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),
) -> MessageResponse:
    """Отзывает все refresh-сессии пользователя. Текущий access JWT остаётся валидным до exp."""
    svc = AuthService(db, redis)
    await svc.logout_all_sessions(user_id)
    _clear_refresh_cookie(response, key=REFRESH_COOKIE_KEY)
    _clear_refresh_cookie(response, key=REFRESH_COOKIE_KEY_ADMIN)
    _clear_access_token_cookie(response)
    return MessageResponse(message="Все сессии завершены")


@router.post(
    "/forgot-password",
    response_model=MessageResponse,
    summary="Запрос сброса пароля",
    responses=error_responses(422, 429),
)
@limiter.limit("5/minute")
async def forgot_password(
    request: Request,
    data: ForgotPasswordRequest,
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),
) -> MessageResponse:
    """Отправляет письмо для сброса пароля. Всегда 200 — не раскрывает,
    зарегистрирован ли email.

    - **429** — превышен лимит 5 запросов/мин
    """
    svc = AuthService(db, redis)
    await svc.forgot_password(data.email)
    return MessageResponse(message="Если email зарегистрирован, вы получите письмо для сброса пароля")


@router.post(
    "/reset-password",
    response_model=MessageResponse,
    summary="Сброс пароля по токену",
    responses=error_responses(404, 422, 429),
)
@limiter.limit("20/minute")
async def reset_password(
    request: Request,
    data: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),
) -> MessageResponse:
    """Устанавливает новый пароль, используя одноразовый токен из письма.

    - **404** — токен не найден или истёк
    """
    svc = AuthService(db, redis)
    await svc.reset_password(data.token, data.new_password)
    return MessageResponse(message="Пароль успешно изменён")


@router.post(
    "/change-password",
    response_model=MessageResponse,
    summary="Смена пароля",
    responses=error_responses(401, 422),
)
async def change_password(
    data: ChangePasswordRequest,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),
) -> MessageResponse:
    """Меняет пароль авторизованного пользователя.

    - **401** — не авторизован или текущий пароль неверен
    """
    svc = AuthService(db, redis)
    await svc.change_password(user_id, data.current_password, data.new_password)
    return MessageResponse(message="Пароль успешно изменён")


@router.post(
    "/change-email",
    response_model=MessageResponse,
    summary="Запрос смены email",
    responses=error_responses(401, 409, 422),
)
async def change_email(
    data: ChangeEmailRequest,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),
) -> MessageResponse:
    """Инициирует смену email. Отправляет письмо подтверждения на новый адрес.

    - **401** — пароль неверен
    - **409** — новый email уже занят
    """
    svc = AuthService(db, redis)
    await svc.change_email(user_id, data.new_email, data.password)
    return MessageResponse(message="Проверьте новый email для подтверждения смены")


@router.post(
    "/confirm-email-change",
    response_model=MessageResponse,
    summary="Подтверждение смены email",
    responses=error_responses(404, 422),
)
async def confirm_email_change(
    data: ConfirmEmailChangeRequest,
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),
) -> MessageResponse:
    """Подтверждает смену email по одноразовому токену.

    - **404** — токен не найден или истёк
    """
    svc = AuthService(db, redis)
    await svc.confirm_email_change(data.token)
    return MessageResponse(message="Email успешно изменён")
