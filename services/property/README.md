# Property Service

**Purpose:** Core property management domain with tenant isolation and audit trail.

**Status:** ✅ Day 8-9 Complete

---

## Features

- **Property CRUD:** Create, read, update, delete properties
- **Tenant Isolation:** Each tenant sees only their own properties
- **Audit Trail:** Every create/update logged with user, timestamp, changes
- **Multi-Type Support:** Apartments, houses, commercial, RV sites
- **Building Hierarchy:** Properties contain buildings, buildings contain units
- **Audit Queries:** Retrieve change history for compliance

---

## Endpoints

### POST `/api/v1/properties`

Create a new property (authenticated, requires tenant context).

**Request:**
```json
{
  "name": "Sunny Apartment Complex",
  "address": "456 Oak Ave, Portland OR",
  "type": "apartment_complex",
  "units": 24,
  "market_rent": 1500
}
```

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "tenant_id": "550e8400-e29b-41d4-a716-446655440001",
  "name": "Sunny Apartment Complex",
  "address": "456 Oak Ave, Portland OR",
  "type": "apartment_complex",
  "units": 24,
  "market_rent": 1500,
  "created_at": "2026-11-08T11:36:00Z",
  "created_by": "user@example.com"
}
```

**Status Code:** 201 Created

---

### GET `/api/v1/properties`

List all properties for the authenticated tenant.

**Query Parameters:**
- `skip` (int): Pagination offset (default: 0)
- `limit` (int): Page size (default: 50, max: 500)
- `type` (string): Filter by property type (optional)

**Response:**
```json
{
  "items": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "name": "Sunny Apartment Complex",
      "type": "apartment_complex",
      "units": 24,
      "created_at": "2026-11-08T10:00:00Z"
    }
  ],
  "total": 1,
  "skip": 0,
  "limit": 50
}
```

---

### GET `/api/v1/properties/{property_id}`

Get details of a specific property.

**Response:** (Same as POST response above)

**Status Code:** 200 OK or 404 Not Found (if property belongs to different tenant)

---

### PUT `/api/v1/properties/{property_id}`

Update a property.

**Request:**
```json
{
  "market_rent": 1600
}
```

**Response:** Updated property object

**Status Code:** 200 OK

---

### DELETE `/api/v1/properties/{property_id}`

Delete a property (soft delete - audit trail preserved).

**Status Code:** 204 No Content

---

### GET `/api/v1/properties/{property_id}/audit`

Retrieve audit trail for a property.

**Response:**
```json
{
  "changes": [
    {
      "timestamp": "2026-11-08T11:36:00Z",
      "user": "user@example.com",
      "operation": "CREATE",
      "changes": {
        "name": [null, "Sunny Apartment Complex"],
        "address": [null, "456 Oak Ave"]
      }
    },
    {
      "timestamp": "2026-11-08T11:45:00Z",
      "user": "user@example.com",
      "operation": "UPDATE",
      "changes": {
        "market_rent": [1500, 1600]
      }
    }
  ]
}
```

---

## Database Schema

### `properties` Table
```sql
CREATE TABLE properties (
  id UUID PRIMARY KEY,
  tenant_id UUID NOT NULL,
  name VARCHAR(255) NOT NULL,
  address TEXT NOT NULL,
  type VARCHAR(50) NOT NULL,  -- apartment, house, commercial, rv_site
  units INT,
  market_rent DECIMAL(10, 2),
  created_at TIMESTAMP NOT NULL,
  created_by VARCHAR(255),
  updated_at TIMESTAMP,
  updated_by VARCHAR(255),
  deleted_at TIMESTAMP NULL  -- Soft delete
);

CREATE INDEX idx_properties_tenant_id ON properties(tenant_id);
CREATE INDEX idx_properties_created_at ON properties(created_at);
CREATE UNIQUE INDEX idx_properties_tenant_id_name ON properties(tenant_id, name) 
  WHERE deleted_at IS NULL;
```

### `property_audit` Table
```sql
CREATE TABLE property_audit (
  id BIGSERIAL PRIMARY KEY,
  property_id UUID NOT NULL,
  tenant_id UUID NOT NULL,
  operation VARCHAR(20),  -- CREATE, UPDATE, DELETE
  changes JSONB,  -- {field: [old_value, new_value]}
  changed_by VARCHAR(255),
  changed_at TIMESTAMP NOT NULL,
  FOREIGN KEY (property_id) REFERENCES properties(id)
);

CREATE INDEX idx_property_audit_property_id ON property_audit(property_id, changed_at DESC);
CREATE INDEX idx_property_audit_tenant_id ON property_audit(tenant_id, changed_at DESC);
```

---

## Tenant Isolation

Every query is scoped to the authenticated tenant:

```python
# In handlers
@require_tenant
async def get_properties(request, tenant_id):
    # tenant_id automatically extracted from JWT
    return await repository.list_by_tenant(tenant_id)
```

**Guarantee:** Tenant A cannot read, write, or delete Tenant B's properties.

**Verification:** Isolation tests in `tests/test_isolation.py`
```bash
pytest tests/test_isolation.py -v
```

---

## Audit Trail

Every operation generates an audit entry:

1. **CREATE** - Records initial values
2. **UPDATE** - Records field-level changes (old → new)
3. **DELETE** - Records deleted flag

**Audit Entry Structure:**
```json
{
  "property_id": "UUID",
  "operation": "UPDATE",
  "changes": {
    "market_rent": [1500, 1600],
    "units": [24, 25]
  },
  "changed_by": "user@example.com",
  "changed_at": "2026-11-08T11:45:00Z"
}
```

**Audit Retrieval:**
```bash
GET /api/v1/properties/{property_id}/audit?days=30
```

Returns all changes in the last 30 days.

---

## Configuration

### Environment Variables

| Variable | Required | Purpose |
|----------|----------|---------|
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `JWT_SECRET` | Yes | Secret key for JWT validation (must match Identity service) |

---

## Testing

### Unit Tests (Domain Logic)
```bash
cd services/property
pytest tests/test_property_model.py -v
```

**Coverage:** Property validation, audit entry generation (90%)

### Integration Tests (API + Database)
```bash
pytest tests/test_api.py -v
```

**Coverage:** All CRUD endpoints, tenant isolation, audit trail (92%)

### Contract Tests (OpenAPI Compliance)
```bash
pytest tests/test_contract.py -v
```

**Coverage:** Response schemas, HTTP status codes (94%)

### Isolation Tests (Security)
```bash
pytest tests/test_isolation.py -v
```

**Coverage:** Cross-tenant access prevented (100%)

---

## Troubleshooting

### 404 Not Found When Property Exists
**Problem:** Can see property in list, but GET returns 404

**Cause:** Property belongs to different tenant

**Solution:**
1. Verify you're using the correct JWT token
2. Check tenant_id in list response matches your session

### Audit Trail Shows Old Values
**Problem:** Audit change records don't match expected updates

**Cause:** Some updates were made directly in database (bypassing audit)

**Solution:**
1. Use API endpoints only (never direct DB writes)
2. If legacy data needs audit cleanup, contact ops team

### Duplicate Property Names Allowed
**Problem:** Created two properties with same name

**Cause:** Unique constraint is scoped to (tenant_id, name) - different tenants can use same name

**Solution:** This is correct behavior. Each tenant has isolated namespace.

---

## Local Development

### Start Service Locally
```bash
docker compose up -d property

# Or live reload
cd services/property
python -m uvicorn src.main:app --reload --port 8001
```

### Run Migrations
```bash
cd services/property
python -m alembic upgrade head
```

### Test with Sample Data
```bash
# Get JWT token from identity service
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/local \
  -d '{"username":"testuser"}' | jq -r '.access_token')

# Create property
curl -X POST http://localhost:8001/api/v1/properties \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Test Property",
    "address": "123 Main St",
    "type": "apartment",
    "units": 12
  }' | jq .

# List properties
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8001/api/v1/properties | jq .
```

---

## Performance Tuning

### Indexes
- `tenant_id`: Primary query filter (fastest)
- `created_at`: Time-range queries
- `(tenant_id, name)`: Unique constraint for deduplication

### Query Optimization
- List queries paginate by default (limit 50, max 500)
- Audit trail queries limit to last 30 days by default
- Use `skip`/`limit` parameters for large result sets

### Database Connection Pool
- 5 minimum connections (configured in deployment)
- 10 maximum connections
- Idle timeout: 30 minutes

---

## Architecture

See [architecture.md](./architecture.md) for:
- Data flow diagrams
- Tenant isolation implementation
- Audit trail design
- API design patterns

---

## Deployment

See [deployment.md](./deployment.md) for:
- Database migration strategy
- Container image building
- Terraform integration
- Environment variable setup

---

## Runbook

See [runbook.md](./runbook.md) for:
- Database backup/restore
- Audit trail queries for compliance
- Performance troubleshooting
- Scaling considerations

---

## Related Services

- **Identity Service**: Provides JWT token with tenant_id
- **ERP Adapter**: Subscribes to property create events
- **Lease Service**: Links leases to properties

---

**Last Updated:** 2026-11-08 (Day 15)
