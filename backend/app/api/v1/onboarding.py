"""Onboarding router — role selection, profile filling, document upload, submission."""

from typing import Literal
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db_session
from app.core.dependencies import get_current_user_id
from app.schemas.onboarding import (
    ChooseRoleRequest,
    DocumentUploadResponse,
    OnboardingProfileUpdate,
    OnboardingStatusResponse,
    OnboardingStepResponse,
)
from app.services.onboarding_service import OnboardingService

router = APIRouter(prefix="/onboarding")


@router.get("/status", response_model=OnboardingStatusResponse)
async def get_status(
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db_session),
) -> OnboardingStatusResponse:
    svc = OnboardingService(db)
    status = await svc.get_status(user_id)
    return OnboardingStatusResponse(**status)


@router.post("/choose-role", response_model=OnboardingStepResponse)
async def choose_role(
    data: ChooseRoleRequest,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db_session),
) -> OnboardingStepResponse:
    svc = OnboardingService(db)
    result = await svc.choose_role(user_id, data.role)
    return OnboardingStepResponse(**result)


@router.patch("/doctor-profile", response_model=OnboardingStepResponse)
async def update_doctor_profile(
    data: OnboardingProfileUpdate,
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db_session),
) -> OnboardingStepResponse:
    svc = OnboardingService(db)
    update_data = data.model_dump(exclude_unset=True)
    result = await svc.update_doctor_profile(user_id, update_data)
    return OnboardingStepResponse(**result)


@router.post("/documents", status_code=201, response_model=DocumentUploadResponse)
async def upload_document(
    file: UploadFile = File(...),
    document_type: Literal[
        "medical_diploma", "retraining_cert", "oncology_cert", "additional_cert"
    ] = Form(...),
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db_session),
) -> DocumentUploadResponse:
    svc = OnboardingService(db)
    doc = await svc.upload_document(user_id, document_type, file)
    return DocumentUploadResponse(
        id=doc.id,
        document_type=doc.document_type,
        original_filename=doc.original_filename,
        uploaded_at=doc.uploaded_at,
    )


@router.post("/submit", response_model=OnboardingStepResponse)
async def submit(
    user_id: UUID = Depends(get_current_user_id),
    db: AsyncSession = Depends(get_db_session),
) -> OnboardingStepResponse:
    svc = OnboardingService(db)
    result = await svc.submit(user_id)
    return OnboardingStepResponse(**result)
