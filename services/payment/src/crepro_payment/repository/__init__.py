"""Tenant-scoped in-memory stores for the payment service, ahead of a real database."""

from crepro_common import InMemoryRepository
from crepro_payment.models import PaymentRecord, SecurityDeposit

payments: InMemoryRepository[PaymentRecord] = InMemoryRepository()
security_deposits: InMemoryRepository[SecurityDeposit] = InMemoryRepository()
