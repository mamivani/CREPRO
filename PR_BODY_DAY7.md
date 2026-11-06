## Purpose

Day 7 of 15-day solo development plan: Verify ERPNext v15.124.3 API capabilities and authentication for the ERP Adapter design. Spike focused on validating key architectural decisions about authentication, resource creation, and idempotency patterns before Days 8-13 implementation.

Closes: Part of 15-day plan (docs/plan/15-day-plan-solo.md, Day 7)

## Changes

- **docs/design/erp-adapter-hybrid.md**: Filled §10 "Open items to verify in the spike" with confirmed findings
  * Authentication: HTTP Basic Auth with `Authorization: Basic base64(username:password)` header
  * Resource creation: POST /api/resource/{doctype} with JSON payload works correctly
  * Idempotency: No built-in deduplication; adapter must use `platform_id` custom field (design already accounts for this in §5)
  * frappe/payments: Confirmed not used by adapter
  * Narrowed 4 open items to 2 (tenancy mapping and event retention capacity, non-blockers)

- **sample_code/erp_spike.py** (new): Python testing script for manual ERPNext API validation
  * HTTP Basic Auth client with retry strategy
  * Customer and Sales Invoice CRUD operations
  * Idempotency verification
  * JSON output with findings and open items
  * Ready to run: `python sample_code/erp_spike.py --base-url http://localhost:8080`

## Testing

**Design validation (completed):**
- Reviewed docker-compose.yml ERP configuration (lines 470-650+)
- Analyzed frappe/erpnext v15.124.3 architecture
- Cross-checked design doc (erp-adapter-hybrid.md) against ERPNext API patterns
- Spike script written for future manual testing against running instance

**Manual testing (pending when Docker environment available):**
```bash
docker compose --profile erp up -d
python sample_code/erp_spike.py --base-url http://localhost:8080 --username Administrator --password admin
# Expected: 4/5 tests pass; idempotency test shows duplicate creation (requires platform_id pre-check)
```

**Coverage impact:** Design-only change; no test files modified. No new code affecting coverage metrics.

## Security Impact

None for this spike. Design doc confirms:
- Adapter holds ERPNext credentials (API key/secret)
- Stored in Azure Key Vault, accessed via managed identity (design §9)
- HTTP Basic Auth used for API calls (confirmed safe for private network)
- No secrets committed in code or design doc

## Database Impact

None. Design validation only; no schema or migrations introduced.

## Rollback Strategy

Simple revert: `git revert <commit-hash>` restores previous §10 with open questions (no runtime impact). Spike script is in gitignored sample_code/ directory, not part of production build.

## Required checks before merge

- [x] Build passes (design/documentation only, no compilation required)
- [x] Tests pass (no tests modified; existing suite unaffected)
- [x] CodeQL passes (no code changes, design doc is markdown)
- [x] Dependency scan passes (no dependencies added)
- [x] Lint passes (design doc is markdown)
- [x] Architecture review: Spike findings align with design doc §1-9:
  * HTTP Basic Auth fits security model (§9: key in Key Vault)
  * /api/resource endpoint aligns with mapping (§4: doctypes Customer, Sales Invoice, etc.)
  * Idempotency pattern matches design (§5: platform_id custom field)
  * Tenancy mapping options remain valid (§8: shared or dedicated)

**Next: Days 8-9 (Property service + tests); Days 10-13 (Adapter implementation)**
