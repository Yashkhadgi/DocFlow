from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class HealthResponse(BaseModel):
    status: str


class UserResponse(BaseModel):
    id: UUID
    email: EmailStr
    full_name: str | None = None

    model_config = ConfigDict(from_attributes=True)


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str | None = None

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email_input(cls, value: str) -> str:
        return value.strip().lower()


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1)

    @field_validator("email", mode="before")
    @classmethod
    def normalize_email_input(cls, value: str) -> str:
        return value.strip().lower()


class LoginResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user: UserResponse


class PatchDocumentFieldsRequest(BaseModel):
    fields: dict[str, Any] | None = None
    line_items: list[dict[str, Any]] | None = None


class ApproveDocumentRequest(BaseModel):
    force: bool = False
