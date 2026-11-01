# Day 5 Authentication Endpoints - Quick Reference

## All endpoints are in the Identity Service

### Base URL
```
http://localhost:8000  (local dev)
```

## 1. Local Authentication (Email/Password)

```bash
curl -X POST http://localhost:8000/api/v1/auth/local \
  -H "Content-Type: application/json" \
  -d '{
    "email": "user@example.com",
    "password": "password123",
    "tenant_id": "optional-uuid"
  }'
```

**Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

**JWT Claims:**
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

---

## 2. Microsoft OAuth2 (Entra ID)

```bash
curl -X POST http://localhost:8000/api/v1/auth/microsoft \
  -G \
  -d code=AUTH_CODE_FROM_MICROSOFT \
  -d redirect_uri=http://localhost:3000/callback
```

**Test User (for Day 5):**
- Email: test@microsoft.com
- User ID: 11111111-1111-1111-1111-111111111111
- Tenant ID: 22222222-2222-2222-2222-222222222222

**Response (200 OK):**
```json
{
  "access_token": "...",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

**In Production:**
1. User clicks "Sign in with Microsoft"
2. User is redirected to: `https://login.microsoftonline.com/common/oauth2/v2.0/authorize?client_id=...&redirect_uri=...&response_type=code&scope=openid%20profile%20email`
3. User signs in and grants consent
4. Microsoft redirects to your callback with `?code=...`
5. Exchange code at this endpoint to get JWT

---

## 3. Google OAuth2

```bash
curl -X POST http://localhost:8000/api/v1/auth/google \
  -G \
  -d code=AUTH_CODE_FROM_GOOGLE \
  -d redirect_uri=http://localhost:3000/callback
```

**Test User (for Day 5):**
- Email: test@google.com
- User ID: 33333333-3333-3333-3333-333333333333
- Tenant ID: 44444444-4444-4444-4444-444444444444

**In Production:**
1. User clicks "Sign in with Google"
2. User is redirected to: `https://accounts.google.com/o/oauth2/v2/auth?client_id=...&redirect_uri=...&response_type=code&scope=openid%20profile%20email`
3. User signs in and grants consent
4. Google redirects to your callback with `?code=...`
5. Exchange code at this endpoint to get JWT

---

## 4. Apple Sign-In

```bash
curl -X POST http://localhost:8000/api/v1/auth/apple \
  -G \
  -d code=AUTH_CODE_FROM_APPLE \
  -d redirect_uri=http://localhost:3000/callback
```

**Test User (for Day 5):**
- Email: test@apple.com
- User ID: 55555555-5555-5555-5555-555555555555
- Tenant ID: 66666666-6666-6666-6666-666666666666

**In Production:**
1. User clicks "Sign in with Apple"
2. User is redirected to: `https://appleid.apple.com/auth/authorize?client_id=...&redirect_uri=...&response_type=code&scope=openid%20profile%20email`
3. User signs in and grants consent
4. Apple redirects to your callback with `?code=...`
5. Exchange code at this endpoint to get JWT

---

## 5. Refresh Token

```bash
curl -X POST http://localhost:8000/api/v1/auth/refresh \
  -G \
  -d current_token=EXISTING_JWT_TOKEN
```

**Response (200 OK):**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "Bearer",
  "expires_in": 3600
}
```

**Use Case:**
- Current access token is about to expire
- Send the current token to refresh endpoint
- Get a new token with refreshed expiration
- Continue using new token for future requests

---

## Error Responses

### 401 Unauthorized
```json
{
  "detail": "Invalid email or password"
}
```

### 401 Unauthorized (Disabled User)
```json
{
  "detail": "User account is disabled, cannot authenticate"
}
```

### 401 Unauthorized (Invalid Token)
```json
{
  "detail": "Invalid token"
}
```

---

## Using the JWT in Requests

Add the token to subsequent requests:

```bash
curl -X GET http://localhost:8000/api/v1/users \
  -H "Authorization: Bearer $ACCESS_TOKEN"
```

Or with X-Tenant-ID header (for multi-tenant routing):

```bash
curl -X GET http://localhost:8000/api/v1/users \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "X-Tenant-Id: 22222222-2222-2222-2222-222222222222"
```

---

## Key Configuration

All settings in `CREPRO_*` environment variables:

```bash
# JWT Configuration
CREPRO_JWT_SECRET_KEY=your-secret-key        # Use strong secret in production
CREPRO_JWT_ALGORITHM=HS256                   # HS256 (symmetric) or RS256 (asymmetric)
CREPRO_JWT_ISSUER=crepro
CREPRO_JWT_AUDIENCE=crepro-api
CREPRO_JWT_EXPIRATION_MINUTES=60             # Access token expiry
CREPRO_JWT_REFRESH_EXPIRATION_MINUTES=10080  # Refresh token expiry (7 days)

# OpenTelemetry (for distributed tracing)
CREPRO_OPENTELEMETRY_ENABLED=false
CREPRO_JAEGER_HOST=localhost
CREPRO_JAEGER_PORT=6831
```

---

## Tenant Resolution

The system resolves tenant via this priority:

1. **Custom Domain** - Request Host header (e.g., tenant1.example.com)
2. **Subdomain** - Extract UUID from subdomain (e.g., 22222222-2222-2222-2222-222222222222.local)
3. **Header** - X-Tenant-Id header
4. **JWT Claim** - tenant_id claim from token

This allows multi-tenant routing without explicit tenant selection on every request.

---

## Testing

Run all auth tests:
```bash
cd services/identity
python -m pytest tests/test_auth.py -v
```

Results: **9 tests passing** ✓
- Local auth with valid/invalid credentials
- Microsoft/Google/Apple OAuth flows
- Token refresh
- JWT validation
- Claims verification

---

## Next Steps (Day 6+)

1. **Unit Tests**: Mock OAuth provider responses
2. **Integration Tests**: Real OAuth flows in lower environments
3. **Production Setup**: Configure real OAuth app credentials
4. **Database**: Migrate to PostgreSQL for user persistence
5. **Security**: Implement PKCE, httpOnly cookies, rate limiting
6. **MFA**: Add multi-factor authentication support
