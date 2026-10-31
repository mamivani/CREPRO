"""Domain entities for the document service: file attachments and insurance policies."""

from datetime import date
from enum import StrEnum
from uuid import UUID

from crepro_common import TenantScopedEntity


class DocumentOwnerType(StrEnum):
    PROPERTY = "property"
    UNIT = "unit"
    LEASE = "lease"
    RESIDENT = "resident"
    MAINTENANCE_REQUEST = "maintenance_request"
    INSURANCE_POLICY = "insurance_policy"


class DocumentCategory(StrEnum):
    PHOTO = "photo"
    LEASE_AGREEMENT = "lease_agreement"
    INSURANCE_CERTIFICATE = "insurance_certificate"
    INSPECTION_REPORT = "inspection_report"
    IDENTIFICATION = "identification"
    OTHER = "other"


class Document(TenantScopedEntity):
    """A stored file attached to another entity, such as a lease agreement or inspection photo."""

    owner_type: DocumentOwnerType
    owner_id: UUID
    category: DocumentCategory = DocumentCategory.OTHER
    file_name: str
    content_type: str = "application/octet-stream"
    storage_path: str
    uploaded_by: str | None = None


class InsurancePolicy(TenantScopedEntity):
    """An insurance policy covering a property, e.g. building or liability coverage."""

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
