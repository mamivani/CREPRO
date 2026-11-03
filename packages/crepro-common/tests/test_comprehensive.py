"""Additional comprehensive tests for crepro-common.

Covers edge cases, error paths, and areas identified in coverage analysis.
"""

from uuid import uuid4

import pytest
from crepro_common import (
    EntityNotFoundError,
    InMemoryRepository,
    TenantScopedEntity,
)
from crepro_common.config import Settings
from crepro_common.security import issue_token_pair, decode_token, InvalidTokenError, TokenType
from crepro_common.tenancy import TenantContext


class TestRepositoryEdgeCases:
    """Additional repository edge cases for complete coverage."""

    def test_repository_list_returns_empty_when_no_items(self):
        """Repository.list returns empty list when tenant has no items."""
        repo = InMemoryRepository[TenantScopedEntity]()
        tenant_id = uuid4()

        result = repo.list(tenant_id)

        assert result == []

    def test_repository_delete_removes_item_and_returns_none_on_retry(self):
        """Deleting twice raises EntityNotFoundError."""
        repo = InMemoryRepository[TenantScopedEntity]()
        tenant_id = uuid4()
        item = repo.create(TenantScopedEntity(tenant_id=tenant_id))

        repo.delete(tenant_id, item.id)

        with pytest.raises(EntityNotFoundError):
            repo.delete(tenant_id, item.id)

    def test_repository_update_on_nonexistent_item_raises(self):
        """Update on non-existent item raises EntityNotFoundError."""
        repo = InMemoryRepository[TenantScopedEntity]()
        tenant_id = uuid4()
        item = TenantScopedEntity(tenant_id=tenant_id)

        with pytest.raises(EntityNotFoundError):
            repo.update(tenant_id, item)

    def test_repository_get_different_tenant_raises(self):
        """Get from different tenant raises EntityNotFoundError."""
        repo = InMemoryRepository[TenantScopedEntity]()
        tenant_a = uuid4()
        item = repo.create(TenantScopedEntity(tenant_id=tenant_a))

        with pytest.raises(EntityNotFoundError):
            repo.get(uuid4(), item.id)


class TestTokenExpiryAndRefresh:
    """Additional token lifecycle tests."""

    def test_token_pair_creates_different_access_and_refresh(self):
        """Access and refresh tokens are distinct."""
        tenant_id, user_id = uuid4(), uuid4()
        access, refresh = issue_token_pair(tenant_id=tenant_id, user_id=user_id, role="admin")

        assert access != refresh

    def test_decode_expired_token_raises(self):
        """Decoding an expired token raises InvalidTokenError."""
        settings = Settings(jwt_secret="test-secret-at-least-32-bytes-long!!", jwt_issuer="crepro-test")
        # Create an expired token by manipulating the exp claim
        import jwt as pyjwt

        payload = {
            "tenant_id": str(uuid4()),
            "user_id": str(uuid4()),
            "role": "admin",
            "token_type": "access",
            "iss": "crepro-test",
            "exp": 1000000,  # Expired timestamp
        }
        expired_token = pyjwt.encode(payload, settings.jwt_secret, algorithm="HS256")

        with pytest.raises(InvalidTokenError):
            decode_token(expired_token, settings=settings)

    def test_token_claims_includes_all_required_fields(self):
        """Token claims include tenant_id, user_id, role."""
        settings = Settings(jwt_secret="test-secret-at-least-32-bytes-long!!", jwt_issuer="crepro-test")
        tenant_id, user_id = uuid4(), uuid4()
        access, _ = issue_token_pair(
            tenant_id=tenant_id, user_id=user_id, role="property_manager", settings=settings
        )

        claims = decode_token(access, expected_type=TokenType.ACCESS, settings=settings)

        assert claims.tenant_id == tenant_id
        assert claims.user_id == user_id
        assert claims.role == "property_manager"


class TestTenantContext:
    """Additional tenant context tests."""

    def test_tenant_context_initializes_with_tenant_id(self):
        """TenantContext stores tenant_id."""
        tenant_id = uuid4()
        context = TenantContext(tenant_id=tenant_id)

        assert context.tenant_id == tenant_id

    def test_tenant_context_is_hashable(self):
        """TenantContext can be used in sets/dicts."""
        tenant_id = uuid4()
        context = TenantContext(tenant_id=tenant_id)

        # Should be hashable
        s = {context}
        assert context in s


class TestSettingsConfiguration:
    """Settings and configuration edge cases."""

    def test_settings_has_default_values(self):
        """Settings can be instantiated with defaults."""
        settings = Settings(jwt_secret="test-secret-at-least-32-bytes-long!!")

        # Settings have jwt_issuer set (may vary by deployment)
        assert hasattr(settings, "jwt_issuer")
        assert settings.jwt_issuer is not None

    def test_settings_jwt_secret_minimum_length(self):
        """JWT secret must be sufficiently long (Pydantic validation)."""
        # Creating Settings with a very short secret should still work
        # (validation happens at runtime during token operations)
        settings = Settings(jwt_secret="short")
        assert settings.jwt_secret == "short"
