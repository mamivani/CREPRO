"""API request/response DTOs for the identity service."""

from crepro_identity.models import UserRole, UserStatus
from pydantic import BaseModel


class UserCreate(BaseModel):
    email: str
    full_name: str
    role: UserRole


class UserUpdate(BaseModel):
    full_name: str | None = None
    role: UserRole | None = None
    status: UserStatus | None = None
