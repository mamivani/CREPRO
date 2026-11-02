"""Authentication endpoints (15-day plan, Day 5): three OAuth/OIDC providers, a local
account fallback, registration, and refresh. Each path resolves the tenant the login
belongs to (custom domain > subdomain > claim), provisions or reuses a `User` scoped to
that tenant, and returns a CREPRO-issued access/refresh JWT pair carrying `tenantId`,
`userId`, and `role` claims.

Provider instances and the tenant directory client are FastAPI dependencies so tests can
override them with fakes instead of making real network calls to Microsoft/Google/Apple
or the tenant service (Day 6 mocks IdP responses the same way).
"""

from crepro_common import EntityNotFoundError, InvalidTokenError, TokenType, decode_token, issue_token_pair
from crepro_identity.config import get_identity_settings
from crepro_identity.models import LocalCredential, User, UserRole, UserStatus
from crepro_identity.oauth import (
    AppleSignInProvider,
    ExternalIdentity,
    GoogleOAuthProvider,
    MicrosoftEntraProvider,
    OAuthVerificationError,
    OIDCProvider,
)
from crepro_identity.passwords import hash_password, verify_password
from crepro_identity.repository import credentials, users
from crepro_identity.schemas import (
    LocalLoginRequest,
    LocalRegisterRequest,
    OAuthLoginRequest,
    RefreshRequest,
    TokenResponse,
)
from crepro_identity.tenant_resolution import TenantDirectoryClient, TenantResolutionError, resolve_tenant
from fastapi import APIRouter, Depends, HTTPException, Request, status

router = APIRouter(prefix="/api/v1/auth", tags=["auth"])


def get_tenant_directory() -> TenantDirectoryClient:
    return TenantDirectoryClient()


def get_microsoft_provider() -> MicrosoftEntraProvider:
    settings = get_identity_settings()
    return MicrosoftEntraProvider(
        issuer=f"https://login.microsoftonline.com/{settings.microsoft_tenant}/v2.0",
        audience=settings.microsoft_client_id,
        jwks_url=f"https://login.microsoftonline.com/{settings.microsoft_tenant}/discovery/v2.0/keys",
    )


def get_google_provider() -> GoogleOAuthProvider:
    settings = get_identity_settings()
    return GoogleOAuthProvider(
        issuer="https://accounts.google.com",
        audience=settings.google_client_id,
        jwks_url="https://www.googleapis.com/oauth2/v3/certs",
    )


def get_apple_provider() -> AppleSignInProvider:
    settings = get_identity_settings()
    return AppleSignInProvider(
        issuer="https://appleid.apple.com",
        audience=settings.apple_client_id,
        jwks_url="https://appleid.apple.com/auth/keys",
    )


def _resolve_tenant_or_400(request: Request, tenant_id, directory: TenantDirectoryClient):
    try:
        return resolve_tenant(
            host=request.headers.get("host"), claimed_tenant_id=tenant_id, directory=directory
        )
    except TenantResolutionError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc)) from exc


def _provision_oauth_user(tenant_id, identity: ExternalIdentity) -> User:
    for existing in users.list(tenant_id):
        if existing.email == identity.email:
            return existing
    return users.create(
        User(
            tenant_id=tenant_id,
            email=identity.email,
            full_name=identity.full_name,
            role=UserRole.PROPERTY_MANAGER,
            status=UserStatus.ACTIVE,
        )
    )


def _tokens_for(user: User) -> TokenResponse:
    access, refresh = issue_token_pair(tenant_id=user.tenant_id, user_id=user.id, role=user.role.value)
    return TokenResponse(access_token=access, refresh_token=refresh)


def _login_with_provider(
    provider: OIDCProvider,
    payload: OAuthLoginRequest,
    request: Request,
    directory: TenantDirectoryClient,
) -> TokenResponse:
    tenant_id = _resolve_tenant_or_400(request, payload.tenant_id, directory)
    try:
        identity = provider.verify(payload.id_token)
    except OAuthVerificationError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc)) from exc
    user = _provision_oauth_user(tenant_id, identity)
    return _tokens_for(user)


@router.post("/microsoft", response_model=TokenResponse)
def login_microsoft(
    payload: OAuthLoginRequest,
    request: Request,
    directory: TenantDirectoryClient = Depends(get_tenant_directory),
    provider: MicrosoftEntraProvider = Depends(get_microsoft_provider),
) -> TokenResponse:
    return _login_with_provider(provider, payload, request, directory)


@router.post("/google", response_model=TokenResponse)
def login_google(
    payload: OAuthLoginRequest,
    request: Request,
    directory: TenantDirectoryClient = Depends(get_tenant_directory),
    provider: GoogleOAuthProvider = Depends(get_google_provider),
) -> TokenResponse:
    return _login_with_provider(provider, payload, request, directory)


@router.post("/apple", response_model=TokenResponse)
def login_apple(
    payload: OAuthLoginRequest,
    request: Request,
    directory: TenantDirectoryClient = Depends(get_tenant_directory),
    provider: AppleSignInProvider = Depends(get_apple_provider),
) -> TokenResponse:
    return _login_with_provider(provider, payload, request, directory)


@router.post("/register", response_model=TokenResponse, status_code=status.HTTP_201_CREATED)
def register_local(
    payload: LocalRegisterRequest,
    request: Request,
    directory: TenantDirectoryClient = Depends(get_tenant_directory),
) -> TokenResponse:
    tenant_id = _resolve_tenant_or_400(request, payload.tenant_id, directory)
    if any(existing.email == payload.email for existing in users.list(tenant_id)):
        raise HTTPException(status.HTTP_409_CONFLICT, "A user with this email already exists for this tenant")
    user = users.create(
        User(
            tenant_id=tenant_id,
            email=payload.email,
            full_name=payload.full_name,
            role=payload.role,
            status=UserStatus.ACTIVE,
        )
    )
    credentials.set(
        LocalCredential(user_id=user.id, tenant_id=tenant_id, password_hash=hash_password(payload.password))
    )
    return _tokens_for(user)


@router.post("/local", response_model=TokenResponse)
def login_local(
    payload: LocalLoginRequest,
    request: Request,
    directory: TenantDirectoryClient = Depends(get_tenant_directory),
) -> TokenResponse:
    tenant_id = _resolve_tenant_or_400(request, payload.tenant_id, directory)
    user = next((existing for existing in users.list(tenant_id) if existing.email == payload.email), None)
    credential = credentials.get(user.id) if user is not None else None
    if user is None or credential is None or not verify_password(payload.password, credential.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid email or password")
    if user.status != UserStatus.ACTIVE:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "User is not active")
    return _tokens_for(user)


@router.post("/refresh", response_model=TokenResponse)
def refresh(payload: RefreshRequest) -> TokenResponse:
    try:
        claims = decode_token(payload.refresh_token, expected_type=TokenType.REFRESH)
    except InvalidTokenError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, str(exc)) from exc
    try:
        user = users.get(claims.tenant_id, claims.user_id)
    except EntityNotFoundError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "User no longer exists") from exc
    if user.status != UserStatus.ACTIVE:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "User is not active")
    return _tokens_for(user)
