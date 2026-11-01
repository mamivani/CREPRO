# Day 5 - Quick Start for Developers

## What Was Built

**OAuth2/OIDC Authentication** with 4 login paths, JWT tokens with tenant context, and tenant resolution.

## Running Tests

```bash
# All crepro-common auth tests (14 tests)
cd packages/crepro-common
pytest tests/test_auth.py -v

# All identity service tests (14 tests)
cd services/identity
pytest tests/ -v

# Integration test showing all 4 flows
pytest tests/test_day5_integration.py -v -s
```

**Expected Result: 28 passing tests** ✓

## Running the Service

```bash
cd services/identity
python -m uvicorn crepro_identity.main:app --reload --port 8000
```

Visit: http://localhost:8000/docs (Swagger UI)

## Testing Endpoints

### 1. Local Auth (Email/Password)
```bash
curl -X POST http://localhost:8000/api/v1/auth/local \
  -H "Content-Type: application/json" \
  -d '{
    "email": "alice@example.com",
    "password": "securepass",
    "tenant_id": "optional-uuid"
  }'
```

### 2. Microsoft OAuth
```bash
curl -X POST http://localhost:8000/api/v1/auth/microsoft \
  -G \
  -d code=TEST_CODE \
  -d redirect_uri=http://localhost:3000/callback
```

Test user created automatically:
- Email: test@microsoft.com
- Tenant: 22222222-2222-2222-2222-222222222222

### 3. Google OAuth
```bash
curl -X POST http://localhost:8000/api/v1/auth/google \
  -G \
  -d code=TEST_CODE \
  -d redirect_uri=http://localhost:3000/callback
```

Test user created automatically:
- Email: test@google.com
- Tenant: 44444444-4444-4444-4444-444444444444

### 4. Apple OAuth
```bash
curl -X POST http://localhost:8000/api/v1/auth/apple \
  -G \
  -d code=TEST_CODE \
  -d redirect_uri=http://localhost:3000/callback
```

Test user created automatically:
- Email: test@apple.com
- Tenant: 66666666-6666-6666-6666-666666666666

### 5. Refresh Token
```bash
curl -X POST http://localhost:8000/api/v1/auth/refresh \
  -G \
  -d current_token=$TOKEN
```

## Response Format

All auth endpoints return:
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

## JWT Token Structure

Decode any returned token to see:
```json
{
  "sub": "user-uuid",
  "tenant_id": "tenant-uuid",
  "role": "property_manager",
  "iss": "crepro",
  "aud": "crepro-api",
  "iat": 1701234567,
  "exp": 1701238167
}
```

## Configuration

Set environment variables to customize:
```bash
CREPRO_JWT_SECRET_KEY=your-secret
CREPRO_JWT_EXPIRATION_MINUTES=60
CREPRO_OPENTELEMETRY_ENABLED=false
```

## Key Files to Know

### Core Auth Logic
- `packages/crepro-common/src/crepro_common/auth.py` - TokenIssuer, TenantResolver
- `services/identity/src/crepro_identity/auth_service.py` - AuthService
- `services/identity/src/crepro_identity/api/__init__.py` - API endpoints

### Tests
- `packages/crepro-common/tests/test_auth.py` - Token/tenant tests
- `services/identity/tests/test_auth.py` - Endpoint tests
- `services/identity/tests/test_day5_integration.py` - Integration test

## Architecture Overview

```
User Login Flow
    ↓
[OAuth2 Provider or Email/Password]
    ↓
[Identity Service Auth Endpoint]
    ↓
[AuthService.exchange_oauth_code() or authenticate_local()]
    ↓
[TokenIssuer.issue(user_id, tenant_id, role)]
    ↓
[JWT Token with Tenant Context]
    ↓
[Return to Client]
```

## Common Operations

### Add a test user to local auth
```python
from crepro_identity.models import User, UserStatus
from crepro_identity.repository import users
from uuid import UUID

user = User(
    id=UUID("..."),
    tenant_id=UUID("..."),
    email="user@example.com",
    full_name="Test User",
    role="maintenance_technician",
    status=UserStatus.ACTIVE,
)
users._rows[user.id] = user
```

### Decode a JWT in tests
```python
from crepro_identity.auth_service import auth_service

claims = auth_service.validate_token(token)
print(f"User: {claims.sub}")
print(f"Tenant: {claims.tenant_id}")
print(f"Role: {claims.role}")
```

### Enable OpenTelemetry tracing
```bash
# Set env var
CREPRO_OPENTELEMETRY_ENABLED=true

# Make sure Jaeger is running
docker run -d -p 6831:6831/udp -p 16686:16686 jaegertracing/all-in-one

# View traces at http://localhost:16686
```

## Troubleshooting

### "User account is disabled"
User status must be ACTIVE to authenticate. Check:
```python
user.status == UserStatus.ACTIVE
```

### "Invalid email or password"
For local auth, user must exist in repository.

### "Invalid token"
Token may be expired or signed with different secret key.

### JWT claims missing
Ensure all 4 endpoints are returning tokens with all required claims: sub, tenant_id, role, iss, aud, iat, exp

## Next Steps

1. **Day 6**: Add comprehensive tests (mocked OAuth responses, contract tests)
2. **Day 7**: External ERP spike
3. **Day 8+**: Real database, production OAuth config
