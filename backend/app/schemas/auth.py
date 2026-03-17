"""Pydantic schemas for authentication endpoints."""

from pydantic import BaseModel, ConfigDict, EmailStr, Field, model_validator


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    re_password: str = Field(min_length=8)

    @model_validator(mode="after")
    def passwords_match(self) -> "RegisterRequest":
        if self.password != self.re_password:
            raise ValueError("Passwords do not match")
        return self


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    role: str  # admin | manager | accountant | doctor | user

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
            "token_type": "bearer",
            "role": "doctor",
        }
    })


class CurrentUserResponse(BaseModel):
    id: str
    email: str
    role: str
    is_staff: bool
    sidebar_sections: list[str]


class VerifyEmailRequest(BaseModel):
    token: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class ResendVerificationRequest(BaseModel):
    email: EmailStr


class ResetPasswordRequest(BaseModel):
    token: str
    new_password: str = Field(min_length=8)


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str = Field(min_length=8)


class ChangeEmailRequest(BaseModel):
    new_email: EmailStr
    password: str


class ConfirmEmailChangeRequest(BaseModel):
    token: str


class MessageResponse(BaseModel):
    message: str
