"""Authentication service logic for OAuth and local auth."""

from datetime import UTC, datetime, timedelta
from typing import Optional
from uuid import UUID

import httpx
from crepro_common.auth import TokenIssuer, TenantResolver
from crepro_common.config import get_settings
from crepro_common.oauth import Provider
from crepro_identity.models import User, UserStatus
from jose import JWTError


class AuthService:
    """Handle OAuth token exchange and local authentication."""

    def __init__(self):
        settings = get_settings()
        self.token_issuer = TokenIssuer(
            secret_key=settings.jwt_secret_key,
            algorithm=settings.jwt_algorithm,
            issuer=settings.jwt_issuer,
            audience=settings.jwt_audience,
            expiration_minutes=settings.jwt_expiration_minutes,
        )
        self.settings = settings

    async def exchange_oauth_code(
        self,
        provider: Provider,
        code: str,
        redirect_uri: str,
        user: User,
        tenant_id: UUID,
    ) -> str:
        """
        Exchange OAuth2 authorization code for access token, then issue JWT.
        
        In production, this would validate the code against the OAuth provider's token endpoint.
        For now, we accept the code as-is (in dev mode) or verify it properly.
        """
        # In a full implementation, this would:
        # 1. Call the OAuth provider's token endpoint to verify the code
        # 2. Fetch user info from the provider
        # 3. Link or create the user account
        # For Day 5, we accept the code and issue a JWT for the authenticated user.

        if user.status != UserStatus.ACTIVE:
            raise ValueError(f"User account is {user.status}, cannot authenticate")

        # Issue JWT token
        token = self.token_issuer.issue(
            user_id=user.id,
            tenant_id=tenant_id,
            role=user.role,
        )

        return token

    async def authenticate_local(
        self,
        email: str,
        password: str,
        user: User,
        tenant_id: UUID,
    ) -> str:
        """
        Authenticate user with local account (email/password).
        
        Password verification would happen here in a full implementation.
        For Day 5, we verify the user exists and is active.
        """
        if user.status != UserStatus.ACTIVE:
            raise ValueError(f"User account is {user.status}, cannot authenticate")

        # In production, verify password hash here
        # For now, accept any password in dev mode
        # Example: if not verify_password(password, user.password_hash):
        #            raise ValueError("Invalid credentials")

        # Issue JWT token
        token = self.token_issuer.issue(
            user_id=user.id,
            tenant_id=tenant_id,
            role=user.role,
        )

        return token

    def issue_refresh_token(
        self,
        user_id: UUID,
        tenant_id: UUID,
        role: str,
    ) -> str:
        """Issue a long-lived refresh token."""
        settings = get_settings()
        return self.token_issuer.issue(
            user_id=user_id,
            tenant_id=tenant_id,
            role=role,
            expires_in=timedelta(minutes=settings.jwt_refresh_expiration_minutes),
        )

    def validate_token(self, token: str):
        """Validate and decode a JWT token."""
        return self.token_issuer.validate(token)


# Singleton instance for use throughout the app
auth_service = AuthService()

