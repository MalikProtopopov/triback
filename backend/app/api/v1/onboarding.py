"""Onboarding router — role selection, profile filling, document upload, submission."""

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Response, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.auth import _set_access_token_cookie
from app.core.database import get_db_session
from app.core.dependencies import get_current_user_id
from app.core.openapi import error_responses
from app.schemas.onboarding import (
    ChooseRoleRequest,
    DocumentUploadResponse,
    OnboardingProfileUpdate,
    OnboardingStatusResponse,
    OnboardingStepResponse,
)
from app.services.onboarding_service import OnboardingService

router = APIRouter(prefix="/onboarding")


@router.get(
    "/status",
    response_model=OnboardingStatusResponse,
    summary="Статус онбординга",
    responses=error_responses(401),
)
async def get_status(
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db_session),
) -> OnboardingStatusResponse:
    """Текущий шаг и состояние прохождения онбординга.

    - **401** — не авторизован
    """
    svc = OnboardingService(db)
    status = await svc.get_status(user_id)
    return OnboardingStatusResponse(**status)


@router.post(
    "/choose-role",
    response_model=OnboardingStepResponse,
    summary="Выбор роли",
    responses=error_responses(401, 403, 409, 422),
)
async def choose_role(
    data: ChooseRoleRequest,
    response: Response,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db_session),
) -> OnboardingStepResponse:
    """Устанавливает роль пользователя (doctor / user), апгрейд user→doctor, идемпотентность.

    При изменении ролей возвращается новый **access_token** (и выставляется cookie), чтобы JWT
    совпадал с БД для doctor-only API.

    - **401** — не авторизован
    - **403** — учётная запись сотрудника (онбординг портала недоступен)
    - **409** — конфликт (например даунгрейд врача)
    """
    svc = OnboardingService(db)
    result = await svc.choose_role(user_id, data.role)
    if result.get("access_token"):
        _set_access_token_cookie(response, result["access_token"])
    return OnboardingStepResponse(**result)


@router.patch(
    "/doctor-profile",
    response_model=OnboardingStepResponse,
    summary="Заполнение анкеты врача",
    responses=error_responses(401, 404, 422),
)
async def update_doctor_profile(
    data: OnboardingProfileUpdate,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db_session),
) -> OnboardingStepResponse:
    """Заполняет или обновляет поля анкеты врача на этапе онбординга.

    - **401** — не авторизован
    - **404** — профиль не создан (роль не выбрана)
    """
    svc = OnboardingService(db)
    update_data = data.model_dump(exclude_unset=True)
    result = await svc.update_doctor_profile(user_id, update_data)
    return OnboardingStepResponse(**result)


@router.post(
    "/documents",
    status_code=201,
    response_model=DocumentUploadResponse,
    summary="Загрузка документа",
    responses=error_responses(401, 404, 422),
)
async def upload_document(
    file: UploadFile = File(...),
    document_type: Literal[
        "medical_diploma", "retraining_cert", "oncology_cert", "additional_cert"
    ] = Form(...),
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db_session),
) -> DocumentUploadResponse:
    """Загружает документ (диплом, сертификат) в S3.

    - **401** — не авторизован
    - **404** — профиль не создан
    """
    svc = OnboardingService(db)
    doc = await svc.upload_document(user_id, document_type, file)
    return DocumentUploadResponse(
        id=doc.id,
        document_type=doc.document_type,
        original_filename=doc.original_filename,
        uploaded_at=doc.uploaded_at,
    )


@router.post(
    "/submit",
    response_model=OnboardingStepResponse,
    summary="Отправка на модерацию",
    responses=error_responses(401, 409),
)
async def submit(
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db_session),
) -> OnboardingStepResponse:
    """Отправляет заполненную анкету на модерацию. Повторная отправка невозможна.

    - **401** — не авторизован
    - **409** — анкета уже отправлена на модерацию
    """
    svc = OnboardingService(db)
    result = await svc.submit(user_id)
    return OnboardingStepResponse(**result)
