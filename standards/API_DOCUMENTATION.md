# API DOCUMENTATION STANDARDS
**Standard:** OpenAPI 3.1 | **Applies to:** All APIs across all projects

---

## Principle: Documentation is Code

API documentation is not optional, not an afterthought, and not maintained separately from the code. It lives alongside the code and is generated from it where possible.

---

## OpenAPI Spec Requirements

Every API must have a complete OpenAPI 3.1 specification. This spec is the source of truth for:
- What endpoints exist
- What inputs they accept
- What outputs they return
- What errors they produce
- What authentication they require

### Spec Location
```
/docs/
  openapi.yaml          ← Complete API specification
  /schemas/             ← Reusable schema components
    transaction.yaml
    user.yaml
    errors.yaml
```

### Minimum Spec Structure
```yaml
openapi: 3.1.0
info:
  title: JIP Financial Intelligence API
  version: 1.0.0
  description: |
    API for the Jhaveri Intelligence Platform.
    
    ## Authentication
    All protected endpoints require a Bearer token obtained from Supabase Auth.
    
    ## Rate Limiting
    Endpoints are rate limited to 100 requests/minute per user.
    Rate limit headers are included in all responses.
    
  contact:
    name: Nimish Jhaveri
    email: nimish@jhaveri.com

servers:
  - url: https://api.yourapp.com/api/v1
    description: Production
  - url: https://staging-api.yourapp.com/api/v1
    description: Staging
  - url: http://localhost:3000/api/v1
    description: Local development

components:
  securitySchemes:
    BearerAuth:
      type: http
      scheme: bearer
      bearerFormat: JWT
      
  schemas:
    # Reusable error schema
    Error:
      type: object
      required: [success, error]
      properties:
        success:
          type: boolean
          example: false
        error:
          type: object
          required: [code, message]
          properties:
            code:
              type: string
              example: VALIDATION_ERROR
            message:
              type: string
              example: Invalid input
            details:
              type: object
              
    # Reusable pagination meta
    PaginationMeta:
      type: object
      properties:
        page:
          type: integer
          example: 1
        perPage:
          type: integer
          example: 20
        total:
          type: integer
          example: 147

security:
  - BearerAuth: []  # Applied globally

paths:
  /transactions:
    get:
      operationId: listTransactions
      summary: List user transactions
      description: Returns a paginated list of transactions for the authenticated user.
      tags: [Transactions]
      parameters:
        - name: page
          in: query
          schema:
            type: integer
            minimum: 1
            default: 1
        - name: perPage
          in: query
          schema:
            type: integer
            minimum: 1
            maximum: 100
            default: 20
        - name: category
          in: query
          schema:
            type: string
            format: uuid
      responses:
        '200':
          description: Transactions retrieved successfully
          content:
            application/json:
              schema:
                type: object
                properties:
                  success:
                    type: boolean
                    example: true
                  data:
                    type: array
                    items:
                      $ref: '#/components/schemas/Transaction'
                  meta:
                    $ref: '#/components/schemas/PaginationMeta'
        '401':
          description: Not authenticated
          content:
            application/json:
              schema:
                $ref: '#/components/schemas/Error'
        '429':
          description: Rate limit exceeded
          headers:
            X-RateLimit-Limit:
              schema:
                type: integer
            X-RateLimit-Remaining:
              schema:
                type: integer
            X-RateLimit-Reset:
              schema:
                type: string
                format: date-time
```

---

## API Versioning Strategy

### URL Versioning (Required)
```
/api/v1/transactions    ← Current stable version
/api/v2/transactions    ← New version (when breaking changes needed)
```

### Versioning Rules
- Never make breaking changes to an existing version
- Breaking changes = new version
- Old versions supported for minimum 6 months after new version release
- Deprecation notice in response headers before removal:
  ```
  Deprecation: Sat, 1 Jan 2026 00:00:00 GMT
  Sunset: Mon, 1 Jun 2026 00:00:00 GMT
  Link: </api/v2/transactions>; rel="successor-version"
  ```

### What Counts as a Breaking Change
- Removing an endpoint
- Removing a required or optional field from response
- Changing a field's type
- Changing authentication requirements
- Changing error response structure

### What is NOT a Breaking Change
- Adding new optional fields to responses
- Adding new optional query parameters
- Adding new endpoints
- Improving error messages (same code, better message)

---

## Changelog Requirement

Every API change is logged in `/docs/CHANGELOG.md`:

```markdown
## [1.2.0] — 2025-03-15

### Added
- `GET /transactions/:id/attachments` — List transaction attachments
- `category` filter parameter on `GET /transactions`

### Changed
- `amount` field now returns as string to preserve decimal precision (non-breaking: was already string-compatible)

### Deprecated
- `GET /transactions?type=` — Use `category` parameter instead. Removed in v2.

### Fixed
- `POST /transactions` now correctly returns 409 for duplicate idempotency keys
```

---

## Endpoint Documentation Checklist

Every endpoint must document:
- [ ] Purpose (1 sentence)
- [ ] Authentication requirement
- [ ] All query/path parameters with types, constraints, defaults
- [ ] Request body schema (if applicable)
- [ ] All possible response codes (not just 200)
- [ ] Response body schema for success
- [ ] Error codes that can be returned
- [ ] Rate limit information
- [ ] At least one example request and response

---

## TypeScript SDK Generation

From the OpenAPI spec, generate typed clients:
```bash
# Generate TypeScript client from spec
npx openapi-typescript docs/openapi.yaml -o src/types/api.ts

# This generates types for all API operations
# Frontend uses these types directly — no manual type writing
```
