"""HTTP routes for the identity service."""

from typing import Optional
from uuid import UUID

from crepro_common import build_crud_router
from crepro_common.auth import TenantResolver
from crepro_common.oauth import Provider
from crepro_identity.auth_service import auth_service
from crepro_identity.models import User, UserStatus
from crepro_identity.repository import users
from crepro_identity.schemas import LocalAuthRequest, TokenResponse, UserCreate, UserUpdate
from fastapi import APIRouter, HTTPException, status

router = APIRouter()

# CRUD routes for user management
router.include_router(
    build_crud_router(
        prefix="/api/v1/users",
        tags=["users"],
        repository=users,
        entity_cls=User,
        create_schema=UserCreate,
        update_schema=UserUpdate,
        not_found_detail="User not found",
    )
)


@router.post("/api/v1/auth/local", response_model=TokenResponse, tags=["auth"])
async def login_local(request: LocalAuthRequest):
    """Authenticate with email and password (local account)."""
    # Find user by email across all tenants (for now, we look up without tenant context)
    # In a full implementation, tenant would come from request context (subdomain, header, etc.)
    matching_users = [u for u in users._rows.values() if u.email == request.email]

    if not matching_users:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    user = matching_users[0]

    # Resolve tenant from request context or use user's tenant
    tenant_id = UUID(request.tenant_id) if request.tenant_id else user.tenant_id

    try:
        token = await auth_service.authenticate_local(
            email=request.email,
            password=request.password,
            user=user,
            tenant_id=tenant_id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )

    return TokenResponse(
        access_token=token,
        expires_in=auth_service.settings.jwt_expiration_minutes * 60,
    )


@router.post("/api/v1/auth/microsoft", response_model=TokenResponse, tags=["auth"])
async def login_microsoft(code: str, redirect_uri: str):
    """Authenticate via Microsoft Entra ID OAuth2."""
    # In a real implementation:
    # 1. Exchange code for token at https://login.microsoftonline.com/common/oauth2/v2.0/token
    # 2. Fetch user info
    # 3. Link to or create user
    # For Day 5, we accept the code and return a token for a test user

    test_user_id = UUID("11111111-1111-1111-1111-111111111111")
    test_tenant_id = UUID("22222222-2222-2222-2222-222222222222")

    # Create or get test user
    existing = [u for u in users._rows.values() if u.id == test_user_id]
    if existing:
        user = existing[0]
    else:
        user = User(
            id=test_user_id,
            tenant_id=test_tenant_id,
            email="test@microsoft.com",
            full_name="Test User (Microsoft)",
            role="property_manager",
            status=UserStatus.ACTIVE,
        )
        users._rows[user.id] = user

    try:
        token = await auth_service.exchange_oauth_code(
            provider=Provider.MICROSOFT,
            code=code,
            redirect_uri=redirect_uri,
            user=user,
            tenant_id=test_tenant_id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )

    return TokenResponse(
        access_token=token,
        expires_in=auth_service.settings.jwt_expiration_minutes * 60,
    )


@router.post("/api/v1/auth/google", response_model=TokenResponse, tags=["auth"])
async def login_google(code: str, redirect_uri: str):
    """Authenticate via Google OAuth2."""
    # Similar to Microsoft, exchange code for token at https://oauth2.googleapis.com/token

    test_user_id = UUID("33333333-3333-3333-3333-333333333333")
    test_tenant_id = UUID("44444444-4444-4444-4444-444444444444")

    existing = [u for u in users._rows.values() if u.id == test_user_id]
    if existing:
        user = existing[0]
    else:
        user = User(
            id=test_user_id,
            tenant_id=test_tenant_id,
            email="test@google.com",
            full_name="Test User (Google)",
            role="property_manager",
            status=UserStatus.ACTIVE,
        )
        users._rows[user.id] = user

    try:
        token = await auth_service.exchange_oauth_code(
            provider=Provider.GOOGLE,
            code=code,
            redirect_uri=redirect_uri,
            user=user,
            tenant_id=test_tenant_id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )

    return TokenResponse(
        access_token=token,
        expires_in=auth_service.settings.jwt_expiration_minutes * 60,
    )


@router.post("/api/v1/auth/apple", response_model=TokenResponse, tags=["auth"])
async def login_apple(code: str, redirect_uri: str):
    """Authenticate via Apple Sign-In OAuth2."""
    # Exchange code for token at https://appleid.apple.com/auth/token

    test_user_id = UUID("55555555-5555-5555-5555-555555555555")
    test_tenant_id = UUID("66666666-6666-6666-6666-666666666666")

    existing = [u for u in users._rows.values() if u.id == test_user_id]
    if existing:
        user = existing[0]
    else:
        user = User(
            id=test_user_id,
            tenant_id=test_tenant_id,
            email="test@apple.com",
            full_name="Test User (Apple)",
            role="property_manager",
            status=UserStatus.ACTIVE,
        )
        users._rows[user.id] = user

    try:
        token = await auth_service.exchange_oauth_code(
            provider=Provider.APPLE,
            code=code,
            redirect_uri=redirect_uri,
            user=user,
            tenant_id=test_tenant_id,
        )
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )

    return TokenResponse(
        access_token=token,
        expires_in=auth_service.settings.jwt_expiration_minutes * 60,
    )


@router.post("/api/v1/auth/refresh", response_model=TokenResponse, tags=["auth"])
async def refresh_token(current_token: str):
    """Refresh an access token using the current token."""
    try:
        claims = auth_service.validate_token(current_token)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token",
        )

    new_token = auth_service.issue_refresh_token(
        user_id=UUID(claims.sub),
        tenant_id=UUID(claims.tenant_id),
        role=claims.role,
    )

    return TokenResponse(
        access_token=new_token,
        expires_in=auth_service.settings.jwt_expiration_minutes * 60,
    )

