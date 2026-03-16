"""Auth router — registration, login, tokens, password/email management."""

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
    ResetPasswordRequest,
    TokenResponse,
    VerifyEmailRequest,
)
from app.services.auth_service import AuthService

router = APIRouter(prefix="/auth")

REFRESH_COOKIE_KEY = "refresh_token"
REFRESH_COOKIE_MAX_AGE = settings.REFRESH_TOKEN_EXPIRE_DAYS * 24 * 3600
REFRESH_COOKIE_PATH = "/api/v1/auth"


def _set_refresh_cookie(response: Response, token: str) -> None:
    response.set_cookie(
        key=REFRESH_COOKIE_KEY,
        value=token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=REFRESH_COOKIE_MAX_AGE,
        path=REFRESH_COOKIE_PATH,
    )


def _clear_refresh_cookie(response: Response) -> None:
    response.delete_cookie(
        key=REFRESH_COOKIE_KEY,
        httponly=True,
        secure=True,
        samesite="lax",
        path=REFRESH_COOKIE_PATH,
    )


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
    redis: Redis = Depends(get_redis),  # type: ignore[type-arg]
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
    responses=error_responses(404, 422),
)
async def verify_email(
    data: VerifyEmailRequest,
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),  # type: ignore[type-arg]
) -> MessageResponse:
    """Подтверждает email по одноразовому токену из письма.

    - **404** — токен не найден или истёк
    """
    svc = AuthService(db, redis)
    await svc.verify_email(data.token)
    return MessageResponse(message="Email подтверждён")


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
    redis: Redis = Depends(get_redis),  # type: ignore[type-arg]
) -> TokenResponse:
    """Аутентифицирует пользователя, возвращает access_token.
    Refresh token устанавливается в httpOnly cookie.

    - **401** — неверный email/пароль или email не подтверждён
    - **429** — превышен лимит 10 запросов/мин
    """
    svc = AuthService(db, redis)
    tokens = await svc.login(email=data.email, password=data.password)
    _set_refresh_cookie(response, tokens["refresh_token"])
    return TokenResponse(
        access_token=tokens["access_token"],
        role=tokens["role"],
    )


@router.post(
    "/refresh",
    response_model=TokenResponse,
    summary="Обновление токена",
    responses=error_responses(401),
)
async def refresh(
    response: Response,
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),  # type: ignore[type-arg]
    refresh_token: str | None = Cookie(None),
) -> TokenResponse:
    """Обновляет пару access/refresh токенов.
    Refresh token берётся из httpOnly cookie `refresh_token`.

    - **401** — refresh token отсутствует, невалиден или отозван
    """
    if not refresh_token:
        from app.core.exceptions import UnauthorizedError

        raise UnauthorizedError("Refresh token missing")
    svc = AuthService(db, redis)
    tokens = await svc.refresh_tokens(refresh_token)
    _set_refresh_cookie(response, tokens["refresh_token"])
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
    payload: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),  # type: ignore[type-arg]
) -> CurrentUserResponse:
    """Возвращает id, email, role, is_staff и sidebar_sections для текущего пользователя.
    Используется фронтендом для построения сайдбара по ролям.
    """
    svc = AuthService(db, redis)
    return await svc.get_current_user_info(
        user_id=payload["sub"],
        role=payload.get("role", "user"),
    )


@router.post(
    "/logout",
    response_model=MessageResponse,
    summary="Выход из системы",
)
async def logout(
    response: Response,
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),  # type: ignore[type-arg]
    refresh_token: str | None = Cookie(None),
) -> MessageResponse:
    """Отзывает refresh token и очищает cookie."""
    if refresh_token:
        svc = AuthService(db, redis)
        await svc.logout(refresh_token)
    _clear_refresh_cookie(response)
    return MessageResponse(message="Вы вышли из системы")


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
    redis: Redis = Depends(get_redis),  # type: ignore[type-arg]
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
    responses=error_responses(404, 422),
)
async def reset_password(
    data: ResetPasswordRequest,
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),  # type: ignore[type-arg]
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
    user_id=Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),  # type: ignore[type-arg]
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
    user_id=Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db_session),
    redis: Redis = Depends(get_redis),  # type: ignore[type-arg]
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
    redis: Redis = Depends(get_redis),  # type: ignore[type-arg]
) -> MessageResponse:
    """Подтверждает смену email по одноразовому токену.

    - **404** — токен не найден или истёк
    """
    svc = AuthService(db, redis)
    await svc.confirm_email_change(data.token)
    return MessageResponse(message="Email успешно изменён")
