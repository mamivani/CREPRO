"""Tenant-scoped in-memory stores for the document service, ahead of a real database."""

from crepro_common import InMemoryRepository
from crepro_document.models import Document, InsurancePolicy

documents: InMemoryRepository[Document] = InMemoryRepository()
insurance_policies: InMemoryRepository[InsurancePolicy] = InMemoryRepository()
