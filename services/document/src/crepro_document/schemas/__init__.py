"""API request/response DTOs for the document service."""

from datetime import date
from uuid import UUID

from crepro_document.models import DocumentCategory, DocumentOwnerType
from pydantic import BaseModel


class DocumentCreate(BaseModel):
    owner_type: DocumentOwnerType
    owner_id: UUID
    category: DocumentCategory = DocumentCategory.OTHER
    file_name: str
    content_type: str = "application/octet-stream"
    storage_path: str
    uploaded_by: str | None = None


class DocumentUpdate(BaseModel):
    category: DocumentCategory | None = None


class InsurancePolicyCreate(BaseModel):
    property_id: UUID
    provider_name: str
    policy_type: str | None = None
    policy_number: str
    premium_amount: float = 0
    currency: str = "USD"
    effective_date: date
    expiration_date: date
    description: str | None = None
    document_id: UUID | None = None


class InsurancePolicyUpdate(BaseModel):
    premium_amount: float | None = None
    expiration_date: date | None = None
    document_id: UUID | None = None
