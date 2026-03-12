# Appointment System

Django + DRF + Celery Integration

Backend Engineering Take-Home Assessment

| **Framework** | **Database** |
|---------------|--------------|
| Django 6.0.3 + DRF 3.16 | PostgreSQL 16 |

| **Task Queue** | **Deployment** |
|----------------|----------------|
| Celery 5.6.2 + Redis 7 | Docker + docker-compose |


## Project Structure

```
appointment_system/ ← project root
├── manage.py
├── Dockerfile
├── docker-compose.yml
├── entrypoint.sh
├── requirements.txt
├── pytest.ini
├── queries.sql ← Task 4.2 raw SQL
├── API_DISCOVERY.md ← Task 2 findings
├── README.md
├── .env.example
├── .gitignore
│
├── appointment_app/ ← main Django app
│   ├── models.py ← BookingSystem, Provider, Customer, Service, Appointment
│   ├── serializers.py ← DRF serializers
│   ├── views.py ← BookingSystemViewSet
│   ├── urls.py ← explicit path() bindings
│   ├── client.py ← BookingSystemClient (API wrapper)
│   ├── sync.py ← DataSyncHandler (upsert logic)
│   ├── tasks.py ← Celery tasks + beat schedules
│   ├── analytics.py ← generate_booking_report()
│   ├── apps.py ← AppConfig.ready() → register_beat_schedules()
|   ├── migrations/
│   ├── 0001_initial.py ← all models + base indexes
|   |── tests/
|   |   └── test_sync.py ← 43 unit tests for DataSyncHandler
│   └── management/
│       └── commands/
│           └── generate_report.py
│
├── core/ ← envelope response infrastructure
│   ├── renderers.py ← EnvelopeRenderer
│   ├── pagination.py ← EnvelopePagination
│   └── exceptions.py ← envelope_exception_handler
|
├── utils/ 
│   ├── responses.py 
│
|
│

```

## Setup Without Docker

### Prerequisites

- Python 3.12+
- PostgreSQL 16 running locally
- Redis running locally
- Git

### Step 1 — Clone the Repository

```bash
git clone https://github.com/mahbubk/Appointment-Booking-System-Assessment.git
cd Appointment-Booking-System-Assessment/
```

### Step 2 — Create Virtual Environment

```bash
python -m venv venv

# Linux / Mac
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### Step 3 — Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4 — Configure Environment

```bash
cp .env.example .env
```

Then edit .env with your local values:

```
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DB_ENGINE=django.db.backends.postgresql
DB_NAME=appointment_db
DB_USER=devuser
DB_PASSWORD=devpass
DB_HOST=localhost
DB_PORT=5432
REDIS_HOST=localhost
REDIS_PORT=6379
CELERY_BROKER_URL=redis://localhost:6379/0
CELERY_RESULT_BACKEND=redis://localhost:6379/0
```

### Step 5 — Setup PostgreSQL

```bash
# Create database
psql -U postgres -c "CREATE DATABASE appointment_db;"
```

### Step 6 — Run Migrations

```bash
python manage.py migrate
```

### Step 7 — Setup Redis

```bash
# Install Redis
sudo apt install redis-server

# Start Redis
sudo systemctl start redis

# Verify Redis is running
redis-cli ping

# Should reply: PONG
```

### Step 8 — Run All Services (3 Terminals)

**Terminal 1 — Django Server**

```bash
python manage.py runserver
```

**Terminal 2 — Celery Worker**

```bash
celery -A appointment_system worker --loglevel=info
```

**Terminal 3 — Celery Beat**

```bash
celery -A appointment_system beat --loglevel=info \
    --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

> **Done!** API is available at http://localhost:8000/v1/

## Setup With Docker

### Prerequisites

- Docker Desktop installed (Windows / Mac / Linux)
- No need to install Python, PostgreSQL, or Redis separately — Docker handles everything

### Step 1 — Clone the Repository

```bash
git clone https://github.com/your-username/appointment_system.git
cd appointment_system
```

### Step 2 — Build and Start All Services

```bash
docker compose up --build
```

This single command starts 5 services automatically:

- **db** — PostgreSQL 16
- **redis** — Redis 7
- **web** — Django + Gunicorn on port 8000
- **celery_worker** — processes async sync tasks
- **celery_beat** — triggers scheduled 6-hour syncs

> **Note:** Migrations run automatically on first startup. No manual steps needed.

### Verify All Services Are Running

```bash
docker compose ps
```

Expected output:

```
NAME                                    STATUS
appointment_system-db-1                 running (healthy)
appointment_system-redis-1              running (healthy)
appointment_system-web-1                running (healthy)
appointment_system-celery_worker-1      running
appointment_system-celery_beat-1        running
```

### Useful Docker Commands

**Create Superuser**

```bash
docker compose exec web python manage.py createsuperuser
```

**View Logs**

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f celery_worker
docker compose logs -f web
```

**Run Tests Inside Docker**

```bash
docker compose exec web pytest -v
```

**Stop Everything**

```bash
# Stop containers (keep volumes/data)
docker compose down

# Stop and wipe all data
docker compose down -v
```

**Restart After Code Changes**

```bash
docker compose up --build
```

> **Done!** API is available at http://localhost:8000/v1/

## Celery Commands

### Start Celery Worker

```bash
celery -A appointment_system worker --loglevel=info
```

With custom concurrency:

```bash
celery -A appointment_system worker --loglevel=info --concurrency=4
```

### Start Celery Beat (Scheduler)

```bash
celery -A appointment_system beat --loglevel=info \
    --scheduler django_celery_beat.schedulers:DatabaseScheduler
```

### Inspect Running Workers

```bash
# List active workers
celery -A appointment_system inspect active

# Check registered tasks
celery -A appointment_system inspect registered

# Check task stats
celery -A appointment_system inspect stats
```

### Trigger a Task Manually

```bash
# From Django shell
python manage.py shell
>>> from appointment_app.tasks import sync_booking_system_task
>>> sync_booking_system_task.delay(booking_system_id=1)
```

### Monitor Tasks — Flower (Optional)

```bash
pip install flower
celery -A appointment_system flower --port=5555
# Open http://localhost:5555 in browser
```

## Running Tests

### Install Test Dependencies

```bash
pip install pytest pytest-django pytest-mock pytest-cov
```

### Run All Tests

```bash
pytest
```

### Run With Verbose Output (see each test name)

```bash
pytest -v
```

### Run Specific Test File

```bash
pytest tests/test_sync.py -v
```

### Run Specific Test Class

```bash
pytest tests/test_sync.py::TestSyncProviders -v
pytest tests/test_sync.py::TestSyncCustomers -v
pytest tests/test_sync.py::TestSyncServices -v
pytest tests/test_sync.py::TestSyncAppointments -v
pytest tests/test_sync.py::TestSyncAll -v
pytest tests/test_sync.py::TestEdgeCases -v
```

### Run Specific Single Test

```bash
pytest tests/test_sync.py::TestSyncProviders::test_creates_new_provider -v
```

### Run With Coverage Report

```bash
pytest --cov=appointment_app --cov-report=term-missing
```

### Run Tests Inside Docker

```bash
docker compose exec web pytest -v
docker compose exec web pytest --cov=appointment_app --cov-report=term-missing
```

### Expected Output

```
tests/test_sync.py::TestSyncProviders::test_creates_new_provider PASSED
tests/test_sync.py::TestSyncProviders::test_updates_existing_provider PASSED
tests/test_sync.py::TestSyncProviders::test_no_duplicates_on_repeated_sync PASSED
tests/test_sync.py::TestSyncProviders::test_skips_record_missing_id_continues_rest PASSED
tests/test_sync.py::TestSyncProviders::test_empty_list_returns_zero PASSED
...
43 passed in 3.42s
```

### pytest.ini Configuration

Place this file in the project root next to manage.py:

```ini
[pytest]
DJANGO_SETTINGS_MODULE = appointment_system.settings
python_files = tests/test_*.py
python_classes = Test*
python_functions = test_*
```

## API Endpoints

### Base URL

```
http://localhost:8000/api/
```

| **Method** | **Endpoint** | **Description** |
|------------|--------------|-----------------|
| **POST** | /booking-systems/connect/ | Connect a new Easy!Appointments instance |
| **GET** | /booking-systems/{id}/status/ | Get sync status of a booking system |
| **GET** | /booking-systems/{id}/providers/ | List all providers |
| **GET** | /booking-systems/{id}/customers/ | List all customers |
| **GET** | /booking-systems/{id}/services/ | List all services |
| **GET** | /booking-systems/{id}/appointments/ | List all appointments |
| **POST** | /booking-systems/{id}/sync/ | Trigger manual full sync |
| **GET** | /booking-systems/{id}/sync/status/ | Get live sync progress |

### Swagger / ReDoc Docs

- http://localhost:8000/v1/ ← interactive Swagger UI
- http://localhost:8000/redoc/ ← ReDoc documentation

### Response Envelope Format

All responses follow the envelope format:

```json
// Success (paginated)
{
    "data": [...],
    "errors": [],
    "meta": { "page": 1, "total_pages": 5, "total_count": 100 }
}

// Success (single object)
{
    "data": { ... },
    "errors": [],
    "meta": null
}

// Error
{
    "data": null,
    "errors": [{ "field": "name", "message": "This field is required." }],
    "meta": null
}
```

## Management Commands

### Generate Analytics Report — Task 4

```bash
python manage.py generate_report \
    --booking_system_id=1 \
    --start_date=2026-01-01 \
    --end_date=2026-03-07
```

Expected output:

```json
{
    "booking_system": "Test Salon",
    "period": "2026-01-01 to 2026-03-07",
    "summary": {
        "total_appointments": 143,
        "unique_customers": 15,
        "total_revenue": 8250.0,
        "avg_appointment_value": 57.69
    },
    "monthly_breakdown": [...],
    "top_providers": [...],
    "top_services": [...]
}
```

## Design Decisions

### 1. Envelope Response Format

Every API response — success or error — is wrapped in a consistent envelope:

- **data** — the payload (object, list, or null)
- **errors** — list of field-level error objects
- **meta** — pagination metadata (page, total_pages, total_count) or null

This was implemented via three core components:

- **EnvelopeRenderer** — wraps all responses at the renderer level
- **EnvelopePagination** — injects meta block for paginated list responses
- **envelope_exception_handler** — converts DRF errors into envelope format

### 2. Sync Order — providers → customers → services → appointments

Appointments have foreign keys to Provider, Customer, and Service. These three must exist in the local database before any appointment can be upserted. The sync pipeline enforces this order and stops the chain if any step fails, updating sync_status to 'error' with a descriptive message.

### 3. Upsert Strategy — update_or_create on (booking_system, external_id)

Every sync is idempotent. Records are matched on (booking_system, external_id) — the composite unique key. This means re-running sync never creates duplicates and always updates stale data.

### 4. Atomic Savepoints per Record

Each record upsert is wrapped in `transaction.atomic(savepoint=True)`. A single malformed record from the API does not abort the entire batch — it is logged and skipped, and the remaining records are processed normally.

### 5. Celery Beat with DatabaseScheduler

Periodic tasks are stored in the database via django_celery_beat rather than hardcoded in settings.py. This allows schedules to be updated at runtime without redeploying. Register a new booking system and its sync schedule is created automatically via `register_beat_schedules()` in AppConfig.ready().

### 6. Analytics — 4 DB Queries, No N+1

The `generate_booking_report()` function completes in exactly 4 database queries using ORM aggregation (Sum, Count, annotate, values). No Python loops are used for aggregation. The covering index `appt_analytics_covering_idx` enables index-only scans on large datasets.

### 7. Docker — One Image, Multiple Services

The same Dockerfile is used for web, celery_worker, and celery_beat. Each service overrides only the CMD. The entrypoint.sh waits for PostgreSQL and Redis to be healthy before starting any service, and only the web container runs migrations (RUN_MIGRATIONS=true) to prevent race conditions.

## Key Files Reference

| **File** | **Purpose** |
|----------|-------------|
| models.py | BookingSystem, Provider, Customer, Service, Appointment with indexes |
| client.py | BookingSystemClient — wraps Easy!Appointments REST API |
| sync.py | DataSyncHandler — upsert logic with atomic savepoints |
| tasks.py | Celery tasks: sync_booking_system_task, sync_providers_task, sync_appointments_task |
| apps.py | AppConfig.ready() → register_beat_schedules() |
| celery.py | Celery app bootstrap — autodiscovery of tasks |
| views.py | BookingSystemViewSet — connect, sync, list endpoints |
| serializers.py | DRF serializers for all models |
| analytics.py | generate_booking_report() — 4-query ORM analytics |
| queries.sql | Task 4.2 — raw PostgreSQL analytics query with full comments |
| 0001_initial.py | All models + base indexes with inline explanations |
| core/renderers.py | EnvelopeRenderer — wraps all responses |
| core/pagination.py | EnvelopePagination — adds meta block |
| core/exceptions.py | envelope_exception_handler — error formatting |
| tests/test_sync.py | 43 unit tests for DataSyncHandler (API mocked) |
| API_DISCOVERY.md | Task 2 — Easy!Appointments API findings |
| Dockerfile | Python 3.12-slim image for all services |
| docker-compose.yml | 5 services: db, redis, web, celery_worker, celery_beat |
| entrypoint.sh | Waits for DB+Redis, runs migrations, starts service |
| management/commands/generate_report.py | python manage.py generate_report command |



## Task Completion Overview

All required tasks and bonus objectives.

| **Task** | **File(s)** | 
|----------|-------------|
| Task 1 | models.py, client.py, sync.py | 
| Task 2 | API_DISCOVERY.md, client.py | 
| Task 3 | views.py, serializers.py, urls.py | 
| Task 4 | analytics.py, queries.sql, 0002_analytics_indexes.py |
| Task 5 | tasks.py, apps.py, celery.py | 
| Bonus — Docker | Dockerfile, docker-compose.yml, entrypoint.sh | 
| Bonus — Tests | tests/test_sync.py (43 tests) | 
| Bonus — Swagger | drf-yasg auto-generated docs through swagger |


---
