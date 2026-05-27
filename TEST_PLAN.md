# Test Plan — QA Test API

## Service Under Test

- **Image**: `infralightio/test-integration-api:latest`
- **Spec**: OpenAPI 2.0 at `/swagger/index.html`
- **Auth**: HTTP Basic Authentication
- **Tenants**: `test1` / `test2` (pre-populated)

## Scope

| Area | Description | Test File |
|------|-------------|-----------|
| Authentication | Basic Auth enforcement on all endpoints | `tests/security/test_auth.py` |
| Integrations CRUD | Create, read, update, delete integrations | `tests/crud/test_integrations.py` |
| Assets CRUD | Create, read, update, delete assets | `tests/crud/test_assets.py` |
| Tenant Isolation | Cross-tenant data access prevention | `tests/security/test_tenant_isolation.py` |
| Contract Validation | Response schemas, status codes, swagger spec compliance | `tests/contract/test_contract.py` |
| Pagination | Page/limit behavior for list endpoints | `tests/pagination/test_pagination.py` |
| Input Validation | Missing fields, empty bodies, invalid references | `tests/validation/test_validation.py` |
| Load Testing | Throughput and stability under load | `tests/load/test_load.py` |

## Bugs Found

### Critical — Tenant Segregation

| # | Bug | Endpoint | Expected | Actual |
|---|-----|----------|----------|--------|
| 1 | Integration list leaks cross-tenant data | `GET /integrations` | Only own tenant's integrations | Returns all tenants' integrations |
| 2 | Integration get allows cross-tenant access | `GET /integrations/{id}` | 403/404 for other tenant's ID | 200 with full data |
| 3 | Integration delete allows cross-tenant deletion | `DELETE /integrations/{id}` | 403/404 | 200 — resource deleted |
| 4 | Asset get allows cross-tenant access | `GET /assets/{id}` | 403/404 | 200 with full data |
| 5 | Asset delete allows cross-tenant deletion | `DELETE /assets/{id}` | 403/404 | 204 — resource deleted |
| 6 | Asset update allows cross-tenant modification | `PATCH /assets` | 403/404 | 200 — data overwritten |
| 7 | Asset creation on another tenant's integration | `POST /assets` | 400/403/404 | 201 — asset created |

### Critical — Server Crash

| # | Bug | Endpoint | Expected | Actual |
|---|-----|----------|----------|--------|
| 8 | PATCH with nonexistent asset ID crashes the server | `PATCH /assets` | 404 | 500 + all POST/DELETE operations hang permanently |
| 9 | Resource leak causes server to become unresponsive after ~35 requests | All | Stable under load | Server stops accepting write requests |

### High — Broken Endpoints

| # | Bug | Endpoint | Expected | Actual |
|---|-----|----------|----------|--------|
| 10 | Update integration endpoint broken (route missing) | `PUT /integrations` | 200 with updated resource | 404 "page not found" |
| 11 | Different tenants cannot use the same integration name | `POST /integrations` | 200/201 (separate tenant scopes) | 409 conflict |
| 12 | PUT /integrations not auth-gated (route doesn't exist) | `PUT /integrations` | 401 without credentials | 404 (auth never reached) |

### Medium — Contract Violations

| # | Bug | Endpoint | Expected | Actual |
|---|-----|----------|----------|--------|
| 13 | Create integration wrong status code | `POST /integrations` | 200 (per OpenAPI spec) | 201 |
| 14 | Create asset wrong status code | `POST /assets` | 200 (per OpenAPI spec) | 201 |
| 15 | Error response schema wrong | All error responses | `{code: int, message: str}` | `{error: str}` |
| 16 | Delete nonexistent integration succeeds | `DELETE /integrations/{id}` | 404 | 200 |
| 17 | Delete nonexistent asset succeeds | `DELETE /assets/{id}` | 404 | 204 |
| 18 | Content-Type not validated | `POST /integrations` | 400/415 for text/plain | 201 — accepts anything |

### Low — Validation & Data Integrity

| # | Bug | Endpoint | Expected | Actual |
|---|-----|----------|----------|--------|
| 19 | No FK validation on asset creation | `POST /assets` | 400/404 for nonexistent integration_id | 201 — orphan asset created |
| 20 | Asset list ignores integration_id filter | `GET /assets?integrationId=x` | Only assets for that integration | Returns all assets regardless |
| 21 | Empty body returns 500 (integration) | `POST /integrations` | 400 | 500 internal server error |
| 22 | Missing 'name' returns 500 (integration) | `POST /integrations` | 400 | 500 internal server error |
| 23 | Missing 'type' silently accepted (integration) | `POST /integrations` | 400 | 201 — created with empty type |
| 24 | Empty body silently accepted (asset) | `POST /assets` | 400 | 201 — created with empty fields |
| 25 | Missing integration_id silently accepted (asset) | `POST /assets` | 400 | 201 — orphan asset created |
| 26 | Integration pagination: pages return same data | `GET /integrations?page=N&limit=M` | Different results per page | Identical results on every page |
| 27 | Asset pagination: pages return same data | `GET /assets?page=N&limit=M` | Different results per page | Identical results on every page |
| 28 | Not all integrations reachable through pagination | `GET /integrations?page=N&limit=M` | All items reachable | Some items missing |
| 29 | Not all assets reachable through pagination | `GET /assets?page=N&limit=M` | All items reachable | Some items missing |

## Known API Limitations

- The Go HTTP server has a resource leak causing it to become unresponsive after ~35 requests. The test infrastructure works around this with automatic container restarts.
- The `PATCH /assets` endpoint with nonexistent IDs crashes the server's write path (POST/DELETE operations hang while GET still works). The test suite detects this and auto-restarts.

## Test Strategy

### Fixtures & Reusability

- **`LiveResource`**: Mutable dict wrapper that survives API restarts by being refreshed with new data
- **`integration_factory` / `asset_factory`**: Create fresh test resources per test
- **`user1_client` / `user2_client`**: Session-scoped authenticated API clients
- **`user1_base_integration` / `user1_base_asset`**: Session-scoped shared resources, auto-refreshed on restart
- **`unique_name()`**: Shared helper for generating collision-free test resource names

### Infrastructure Resilience

- **Call-count restart**: API container is force-recreated every 15 requests to prevent the resource leak
- **Write-path liveness probe**: DELETE-based health check detects when the server's write path has crashed
- **curl-based HTTP client**: Uses subprocess+curl instead of Python requests to avoid connection pooling issues

### Configuration

All values externalized to `.env` — no hardcoded URLs, credentials, or thresholds. Tenant assertions use `settings.user1.username` / `client.auth[0]` instead of string literals.

### Contract Validation

- **Static**: Pydantic models validate response schema structure for every CRUD response
- **Dynamic**: Tests validate actual status codes and response fields against the live swagger spec at `/swagger/doc.json`
- Covers: create/get/list/delete status codes, response body fields, error schema, content type, null vs empty array

### Extensibility

- New endpoints: add methods to `APIClient`, add Pydantic models, add test class
- New tenants: add credentials to `.env` and `settings.py`
- New resource types: follow the factory fixture pattern
