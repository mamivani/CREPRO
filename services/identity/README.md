# Identity Service

**Purpose:** OAuth2/OIDC authentication and JWT token issuance with multi-tenant support.

**Status:** ✅ Day 5-6 Complete

---

## Features

- **OAuth2/OIDC Providers:** Microsoft Entra ID, Google, Apple
- **Local Account Fallback:** For testing and development
- **JWT Tokens:** Access token + refresh token with tenant context
- **Tenant Resolution:** Custom domain → subdomain → JWT claim hierarchy
- **Token Validation:** Signature verification and expiry checking
- **Health Checks:** Service readiness and dependency status

---

## Endpoints

### POST `/api/v1/auth/{provider}`

Initiate OAuth flow for the specified provider.

**Providers:** `microsoft`, `google`, `apple`, `local`

**Request:**
```json
{
  "redirect_uri": "http://localhost:3000/callback"
}
```

**Response (Redirect for OAuth, Token for Local):**
```json
{
  "authorization_url": "https://login.microsoftonline.com/...",
  "state": "random-state-for-csrf"
}
```

For local auth:
```json
{
  "access_token": "eyJ0eXAi...",
  "refresh_token": "eyJ0eXAi...",
  "expires_in": 3600
}
```

---

### POST `/api/v1/auth/callback`

Handle OAuth provider callback (called by your frontend).

**Request:**
```json
{
  "provider": "microsoft",
  "code": "auth-code-from-provider",
  "state": "state-from-authorization-url"
}
```

**Response:**
```json
{
  "access_token": "eyJ0eXAi...",
  "refresh_token": "eyJ0eXAi...",
  "expires_in": 3600,
  "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "user@example.com"
}
```

---

### POST `/api/v1/auth/refresh`

Refresh an expired access token.

**Request:**
```json
{
  "refresh_token": "eyJ0eXAi..."
}
```

**Response:**
```json
{
  "access_token": "eyJ0eXAi...",
  "expires_in": 3600
}
```

---

### GET `/health`

Service health check.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2026-11-08T11:36:00Z"
}
```

---

## Configuration

### Environment Variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `MICROSOFT_CLIENT_ID` | Yes (if Entra enabled) | Azure Entra app client ID |
| `MICROSOFT_CLIENT_SECRET` | Yes (if Entra enabled) | Azure Entra app client secret |
| `MICROSOFT_TENANT_ID` | Yes (if Entra enabled) | Azure tenant ID |
| `GOOGLE_CLIENT_ID` | Yes (if Google enabled) | Google OAuth app client ID |
| `GOOGLE_CLIENT_SECRET` | Yes (if Google enabled) | Google OAuth app client secret |
| `APPLE_TEAM_ID` | Yes (if Apple enabled) | Apple Developer team ID |
| `APPLE_KEY_ID` | Yes (if Apple enabled) | Apple Developer key ID |
| `APPLE_PRIVATE_KEY` | Yes (if Apple enabled) | Apple private key (PEM format) |
| `JWT_SECRET` | Yes | Secret key for signing JWTs (min 32 chars) |
| `JWT_ALGORITHM` | No | Algorithm (default: HS256) |
| `JWT_EXPIRY_SECONDS` | No | Access token lifetime (default: 3600) |
| `REFRESH_EXPIRY_SECONDS` | No | Refresh token lifetime (default: 604800 = 7 days) |

---

## JWT Token Structure

```json
{
  "typ": "JWT",
  "alg": "HS256"
}
{
  "sub": "user@example.com",
  "tenant_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": "550e8400-e29b-41d4-a716-446655440001",
  "role": "admin",
  "iat": 1699427760,
  "exp": 1699431360,
  "token_type": "access"
}
```

**Claims:**
- `sub` (subject): User's email or username
- `tenant_id`: UUID of the tenant this user belongs to
- `user_id`: UUID of the user
- `role`: User's role (admin, manager, viewer)
- `iat` (issued at): Token creation timestamp
- `exp` (expiration): Token expiry timestamp
- `token_type`: "access" or "refresh"

---

## Testing

### Unit Tests
```bash
cd services/identity
pytest tests/ -v
```

**Coverage:** 90% (domain logic, token generation, provider mocking)

### Integration Tests
```bash
pytest tests/test_endpoints.py -v
```

**Coverage:** All OAuth flows (Microsoft, Google, Apple, Local) + callback handling

### Contract Tests
```bash
pytest tests/test_contract.py -v
```

**Coverage:** OpenAPI schema compliance, response format validation

---

## Troubleshooting

### Token Expiry
**Problem:** "token expired" error even after recent login

**Solution:**
1. Check server clock is correct (`date`)
2. Verify `JWT_EXPIRY_SECONDS` is reasonable (default 3600 = 1 hour)
3. Use refresh endpoint to get new access token

```bash
curl -X POST http://localhost:8000/api/v1/auth/refresh \
  -H "Content-Type: application/json" \
  -d '{"refresh_token": "..."}'
```

### OAuth Provider Failure
**Problem:** "Provider authentication failed"

**Solution:**
1. Verify OAuth app credentials are registered in your identity provider
   - **Microsoft Entra:** Check Client ID and Secret in Azure Portal
   - **Google:** Check Client ID/Secret in Google Cloud Console
   - **Apple:** Check Team ID, Key ID, and private key in Apple Developer
2. Check redirect URI matches between app configuration and request
3. Verify network connectivity to provider

### Tenant Resolution Issue
**Problem:** User authenticated but no tenant_id in JWT

**Solution:**
1. Check domain/subdomain routing logic (see architecture.md)
2. Ensure user claim includes tenant info from provider
3. Verify fallback tenant assignment if domain routing fails

---

## Local Development

### Start Service Locally
```bash
docker compose up -d identity

# Or for development with live reload
cd services/identity
python -m uvicorn src.main:app --reload --port 8000
```

### Test with Local Account
```bash
curl -X POST http://localhost:8000/api/v1/auth/local \
  -H "Content-Type: application/json" \
  -d '{"username": "testuser", "password": "testpass"}' | jq .
```

### Use Token in Other Requests
```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/local \
  -d '{"username": "testuser"}' | jq -r '.access_token')

curl -H "Authorization: Bearer $TOKEN" http://localhost:8001/api/v1/properties
```

---

## Architecture

See [architecture.md](./architecture.md) for:
- Provider flow diagrams
- Tenant resolution algorithm
- Token lifecycle
- Security considerations (CSRF, token storage)

---

## Deployment

See [deployment.md](./deployment.md) for:
- Azure app registration steps
- Environment variable setup
- Container image building and pushing
- Terraform integration

---

## Runbook

See [runbook.md](./runbook.md) for:
- Incident response procedures
- Provider credential rotation
- JWT secret rotation
- Debugging authentication failures
- Performance tuning

---

## Related Services

- **Property Service**: Consumes `tenant_id` from JWT header
- **All Services**: Require Authorization header with JWT token
- **ERP Adapter**: Uses tenant_id to scope ERP sync operations

---

**Last Updated:** 2026-11-08 (Day 15)
