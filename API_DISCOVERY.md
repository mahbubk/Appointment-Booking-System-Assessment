# API_DISCOVERY.md — Easy!Appointments v1 API

## Base URL
```
http://localhost:8888/index.php/api/v1
```

## Authentication
- **Method**: HTTP Basic Auth (username + password)
- **Header**: `Authorization: Basic base64(username:password)`
- **Verified via**: `GET /settings` — returns 200 on success, 401 on failure
- No token/session management required; every request carries credentials

## Endpoints

### Providers
| Method | Path | Description |
|--------|------|-------------|
| GET | `/providers` | List all providers |
| GET | `/providers/{id}` | Get single provider |
| POST | `/providers` | Create provider |
| PUT | `/providers/{id}` | Update provider |
| DELETE | `/providers/{id}` | Delete provider |

**Key fields returned:**
```json
{
  "id": 1,
  "firstName": "Sarah",
  "lastName": "Johnson",
  "email": "sarah@testsalon.com",
  "phone": "+1-555-0101",
  "timezone": "America/New_York",
  "services": [1, 2, 3],
  "settings": { "workingPlan": {...} }
}
```

### Customers
| Method | Path | Description |
|--------|------|-------------|
| GET | `/customers` | List all customers |
| GET | `/customers/{id}` | Get single customer |
| POST | `/customers` | Create customer |
| PUT | `/customers/{id}` | Update customer |

**Key fields returned:**
```json
{
  "id": 5,
  "firstName": "Alice",
  "lastName": "Brown",
  "email": "alice@email.com",
  "phone": "+1-555-1001",
  "address": null,
  "city": null,
  "notes": null
}
```
**Quirk**: `address`, `city`, `zip`, `notes` frequently return `null` — must coerce to `""` for NOT NULL CharField.

### Services
| Method | Path | Description |
|--------|------|-------------|
| GET | `/services` | List all services |
| GET | `/services/{id}` | Get single service |
| POST | `/services` | Create service |

**Key fields returned:**
```json
{
  "id": 3,
  "name": "Men's Haircut",
  "duration": 30,
  "price": "35.00",
  "currency": "USD",
  "attendantsNumber": 1,
  "description": null
}
```
**Quirk**: `price` is returned as a **string**, not a number. Must cast to `Decimal`/`float`.

### Appointments
| Method | Path | Description |
|--------|------|-------------|
| GET | `/appointments` | List appointments |
| GET | `/appointments/{id}` | Get single appointment |
| POST | `/appointments` | Create appointment |
| PUT | `/appointments/{id}` | Update appointment |
| DELETE | `/appointments/{id}` | Delete appointment |

**Query parameters for filtering:**
- `?start_date=2026-01-01` — filter from date (format: YYYY-MM-DD)
- `?end_date=2026-03-07` — filter to date

**Key fields returned:**
```json
{
  "id": 42,
  "start": "2026-01-10 09:00:00",
  "end": "2026-01-10 09:30:00",
  "location": "Test Salon - Main Branch",
  "notes": null,
  "status": "Booked",
  "customerId": 5,
  "providerId": 1,
  "serviceId": 3
}
```
**Quirk**: `status` defaults to `"Booked"` — no enum docs, but observed values: `Booked`, `Cancelled`.

## Pagination
- **No cursor pagination** — the API returns **all records** in a single response for providers, customers, and services.
- Appointments support `?start_date` / `?end_date` for range filtering but also return all matches at once.
- No `page` or `limit` query parameters observed.
- For large datasets, use date-range chunking on appointments.

## Rate Limiting
- **429 Too Many Requests** observed during bulk appointment creation (seed script).
- No `Retry-After` header documented — empirically, waiting **30 seconds** resolves it.
- Strategy: catch 429, sleep 30s, retry once.

## Field Naming Convention
- camelCase throughout (e.g., `firstName`, `customerId`, `serviceId`)
- Date/time format: `YYYY-MM-DD HH:MM:SS` (not ISO 8601)

## Error Responses
```json
{"code": 400, "message": "Validation error description"}
```
- 400: Validation failure
- 401: Bad credentials
- 404: Record not found
- 409: Conflict (e.g., duplicate email)
- 429: Rate limited
- 500: Server error

## Calendar Endpoints

### Get Calendar Appointments
| Method | Path | Description |
|--------|------|-------------|
| POST | `/index.php/calendar/get_calendar_appointments` | Fetch appointments for calendar view |

**Full URL:**
```
http://localhost:8888/index.php/calendar/get_calendar_appointments
```

**Note**: This endpoint lives outside the REST API path (`/api/v1`) — it is a legacy controller endpoint, not versioned.

---

## Connection Test
```bash
curl -u admin:admin123 http://localhost:8888/index.php/api/v1/settings
# 200 → authenticated; 401 → bad credentials
```