"""Tests for JWT token generation and validation."""

import pytest
from datetime import UTC, datetime, timedelta
from uuid import UUID

from crepro_common.auth import TokenClaims, TokenIssuer, TenantResolver
from jose import JWTError


class TestTokenIssuer:
    """Test JWT token issuance and validation."""

    def test_issue_token_returns_valid_jwt(self):
        """Test that issue() returns a valid JWT string."""
        issuer = TokenIssuer(secret_key="test-secret")
        user_id = UUID("11111111-1111-1111-1111-111111111111")
        tenant_id = UUID("22222222-2222-2222-2222-222222222222")

        token = issuer.issue(user_id=user_id, tenant_id=tenant_id, role="admin")

        assert isinstance(token, str)
        assert token.count(".") == 2  # JWT has 3 parts separated by 2 dots

    def test_validate_token_returns_claims(self):
        """Test that validate() returns TokenClaims."""
        issuer = TokenIssuer(secret_key="test-secret")
        user_id = UUID("11111111-1111-1111-1111-111111111111")
        tenant_id = UUID("22222222-2222-2222-2222-222222222222")

        token = issuer.issue(user_id=user_id, tenant_id=tenant_id, role="admin")
        claims = issuer.validate(token)

        assert isinstance(claims, TokenClaims)
        assert claims.sub == str(user_id)
        assert claims.tenant_id == str(tenant_id)
        assert claims.role == "admin"

    def test_validate_token_with_invalid_token_raises_error(self):
        """Test that validate() raises JWTError for invalid tokens."""
        issuer = TokenIssuer(secret_key="test-secret")

        with pytest.raises(JWTError):
            issuer.validate("invalid.token.here")

    def test_validate_token_with_wrong_secret_raises_error(self):
        """Test that validate() raises error with wrong secret key."""
        issuer1 = TokenIssuer(secret_key="secret1")
        issuer2 = TokenIssuer(secret_key="secret2")

        user_id = UUID("11111111-1111-1111-1111-111111111111")
        tenant_id = UUID("22222222-2222-2222-2222-222222222222")

        token = issuer1.issue(user_id=user_id, tenant_id=tenant_id, role="admin")

        with pytest.raises(JWTError):
            issuer2.validate(token)

    def test_token_expiration(self):
        """Test that token includes expiration time."""
        issuer = TokenIssuer(secret_key="test-secret", expiration_minutes=60)
        user_id = UUID("11111111-1111-1111-1111-111111111111")
        tenant_id = UUID("22222222-2222-2222-2222-222222222222")

        token = issuer.issue(user_id=user_id, tenant_id=tenant_id, role="admin")
        claims = issuer.validate(token)

        now = int(datetime.now(UTC).timestamp())
        # Should expire in approximately 60 minutes (within 5 minute tolerance)
        assert claims.exp > now
        assert claims.exp <= now + 65 * 60

    def test_custom_expiration(self):
        """Test token with custom expiration time."""
        issuer = TokenIssuer(secret_key="test-secret")
        user_id = UUID("11111111-1111-1111-1111-111111111111")
        tenant_id = UUID("22222222-2222-2222-2222-222222222222")

        custom_expiry = timedelta(hours=2)
        token = issuer.issue(
            user_id=user_id,
            tenant_id=tenant_id,
            role="admin",
            expires_in=custom_expiry,
        )
        claims = issuer.validate(token)

        now = int(datetime.now(UTC).timestamp())
        # Should expire in approximately 2 hours (within 5 minute tolerance)
        assert claims.exp > now
        assert claims.exp <= now + 125 * 60

    def test_token_claims_match_input(self):
        """Test that token claims match the input parameters."""
        issuer = TokenIssuer(
            secret_key="test-secret",
            issuer="test-issuer",
            audience="test-audience",
        )
        user_id = UUID("11111111-1111-1111-1111-111111111111")
        tenant_id = UUID("22222222-2222-2222-2222-222222222222")

        token = issuer.issue(user_id=user_id, tenant_id=tenant_id, role="maintenance_tech")
        claims = issuer.validate(token)

        assert claims.sub == str(user_id)
        assert claims.tenant_id == str(tenant_id)
        assert claims.role == "maintenance_tech"
        assert claims.iss == "test-issuer"
        assert claims.aud == "test-audience"


class TestTenantResolver:
    """Test tenant resolution logic."""

    def test_resolve_from_subdomain(self):
        """Test resolving tenant from host subdomain."""
        tenant_id = UUID("11111111-1111-1111-1111-111111111111")
        host = f"{tenant_id}.local"

        resolved = TenantResolver.resolve_from_host(host)

        assert resolved == tenant_id

    def test_resolve_from_header(self):
        """Test resolving tenant from X-Tenant-ID header."""
        tenant_id = UUID("22222222-2222-2222-2222-222222222222")

        resolved = TenantResolver.resolve_from_header(str(tenant_id))

        assert resolved == tenant_id

    def test_resolve_from_claim(self):
        """Test resolving tenant from JWT claim."""
        tenant_id = UUID("33333333-3333-3333-3333-333333333333")

        resolved = TenantResolver.resolve(tenant_id_claim=str(tenant_id))

        assert resolved == tenant_id

    def test_resolve_priority_host_over_header(self):
        """Test that host takes priority over header."""
        host_tenant = UUID("11111111-1111-1111-1111-111111111111")
        header_tenant = UUID("22222222-2222-2222-2222-222222222222")
        host = f"{host_tenant}.local"

        resolved = TenantResolver.resolve(
            host=host,
            tenant_id_header=str(header_tenant),
        )

        assert resolved == host_tenant

    def test_resolve_priority_header_over_claim(self):
        """Test that header takes priority over claim."""
        header_tenant = UUID("22222222-2222-2222-2222-222222222222")
        claim_tenant = UUID("33333333-3333-3333-3333-333333333333")

        resolved = TenantResolver.resolve(
            tenant_id_header=str(header_tenant),
            tenant_id_claim=str(claim_tenant),
        )

        assert resolved == header_tenant

    def test_resolve_returns_none_when_no_tenant_found(self):
        """Test that resolve() returns None when no tenant is found."""
        resolved = TenantResolver.resolve()

        assert resolved is None

    def test_resolve_with_invalid_host_subdomain(self):
        """Test that invalid UUID subdomain is ignored."""
        resolved = TenantResolver.resolve_from_host("notauuid.local")

        assert resolved is None
