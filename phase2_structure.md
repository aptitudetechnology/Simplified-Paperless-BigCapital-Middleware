# Phase 2 Extended Directory Structure

```
paperless-bigcapital-middleware/
├── config/
│   ├── __init__.py
│   ├── settings.py              # Enhanced with conditional loading
│   ├── base_config.py           # Core Phase 1/1.1 settings
│   ├── extended_config.py       # Phase 2+ settings (only loaded if enabled)
│   └── config.ini.example
├── core/
│   ├── __init__.py
│   ├── ocr_processor.py         # Phase 1 implementation
│   ├── text_extractor.py        # Phase 1 implementation
│   ├── processor.py             # Phase 1 synchronous processing
│   ├── exceptions.py
│   └── mappers.py
├── core_extended/               # NEW: Phase 2+ enhanced core (conditional)
│   ├── __init__.py
│   ├── async_processor.py       # Async version of processor.py
│   ├── enhanced_ocr.py          # Enhanced OCR with confidence scoring
│   ├── batch_processor.py       # Batch processing capabilities
│   └── ml_extractors.py         # ML-powered extraction
├── clients/
│   ├── __init__.py
│   ├── bigcapital/              # Phase 1.1 basic client
│   │   ├── __init__.py
│   │   ├── client.py            # Basic sync client
│   │   ├── models.py
│   │   └── mappers.py
│   └── paperless/               # Phase 1.1 basic client
│       ├── __init__.py
│       ├── client.py            # Basic sync client
│       └── models.py
├── clients_extended/            # NEW: Phase 2+ enhanced clients (conditional)
│   ├── __init__.py
│   ├── bigcapital/
│   │   ├── __init__.py
│   │   ├── async_client.py      # Async client with retry/circuit breaker
│   │   ├── batch_client.py      # Batch operations
│   │   └── webhook_client.py    # Webhook support
│   └── paperless/
│       ├── __init__.py
│       ├── async_client.py      # Async client
│       └── streaming_client.py  # Streaming document retrieval
├── services/
│   ├── __init__.py
│   ├── document_service.py      # Phase 1/1.1 sync service
│   ├── invoice_service.py       # Phase 1/1.1 sync service
│   └── sync_service.py          # Phase 1/1.1 basic sync
├── services_extended/           # NEW: Phase 2+ async services (conditional)
│   ├── __init__.py
│   ├── async_document_service.py
│   ├── job_manager_service.py   # Job tracking and management
│   ├── queue_service.py         # Queue management
│   ├── notification_service.py  # Real-time notifications
│   └── workflow_service.py      # Automated workflows
├── queue/                       # NEW: Phase 2+ only (conditional loading)
│   ├── __init__.py
│   ├── celery_app.py
│   ├── redis_manager.py
│   ├── job_tracker.py
│   └── status_broadcaster.py
├── tasks/                       # NEW: Phase 2+ Celery tasks (conditional)
│   ├── __init__.py
│   ├── document_tasks.py
│   ├── sync_tasks.py
│   ├── batch_tasks.py
│   └── maintenance_tasks.py
├── database/
│   ├── __init__.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── base_models.py       # Phase 1/1.1 models
│   │   └── extended_models.py   # Phase 2+ models (conditional)
│   ├── connection.py            # Handles both sync/async based on config
│   ├── create_tables.py         # Creates tables based on enabled features
│   ├── migrations/
│   │   ├── phase1/              # Phase 1 migrations
│   │   │   ├── 001_initial.sql
│   │   │   └── 002_basic_features.sql
│   │   └── phase2/              # Phase 2+ migrations (conditional)
│   │       ├── 003_job_tracking.sql
│   │       ├── 004_queue_status.sql
│   │       └── 005_advanced_features.sql
│   └── repositories/            # NEW: Data access layer
│       ├── __init__.py
│       ├── base_repository.py   # Sync repository for Phase 1/1.1
│       └── async_repository.py  # Async repository for Phase 2+
├── api/
│   ├── __init__.py
│   ├── v1/
│   │   ├── __init__.py
│   │   ├── documents.py         # Phase 1/1.1 endpoints
│   │   ├── invoices.py          # Phase 1/1.1 endpoints
│   │   └── sync.py              # Phase 1/1.1 endpoints
│   ├── v1_extended/             # NEW: Phase 2+ endpoints (conditional)
│   │   ├── __init__.py
│   │   ├── jobs.py              # Job management
│   │   ├── queue.py             # Queue management
│   │   ├── batch.py             # Batch operations
│   │   └── monitoring.py        # System monitoring
│   ├── websocket/               # NEW: Phase 2+ real-time (conditional)
│   │   ├── __init__.py
│   │   ├── handlers.py
│   │   └── connections.py
│   └── middleware.py            # Conditional middleware loading
├── web/
│   ├── __init__.py
│   ├── app.py                   # Factory pattern with conditional features
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── core_routes.py       # Phase 1/1.1 routes
│   │   ├── document_routes.py   # Phase 1/1.1 routes
│   │   └── sync_routes.py       # Phase 1/1.1 routes
│   ├── routes_extended/         # NEW: Phase 2+ routes (conditional)
│   │   ├── __init__.py
│   │   ├── job_routes.py
│   │   ├── monitoring_routes.py
│   │   └── admin_routes.py
│   ├── templates/
│   │   ├── base/                # Base templates for all phases
│   │   │   ├── base.html
│   │   │   └── layout.html
│   │   ├── core/                # Phase 1/1.1 templates
│   │   │   ├── dashboard.html
│   │   │   ├── documents.html
│   │   │   └── upload.html
│   │   └── extended/            # Phase 2+ templates (conditional)
│   │       ├── jobs/
│   │       ├── monitoring/
│   │       └── admin/
│   └── static/
│       ├── css/
│       │   ├── core.css         # Phase 1/1.1 styles
│       │   └── extended.css     # Phase 2+ styles (conditional)
│       └── js/
│           ├── core.js          # Phase 1/1.1 JavaScript
│           └── extended.js      # Phase 2+ JavaScript (conditional)
├── utils/
│   ├── __init__.py
│   ├── logger.py                # Enhanced for conditional features
│   ├── validators.py
│   └── helpers.py
├── utils_extended/              # NEW: Phase 2+ utilities (conditional)
│   ├── __init__.py
│   ├── retry.py
│   ├── circuit_breaker.py
│   ├── rate_limiter.py
│   └── monitoring_utils.py
├── monitoring/                  # NEW: Phase 2+ only (conditional)
│   ├── __init__.py
│   ├── health_checks.py
│   ├── metrics.py
│   └── alerts.py
├── processing/
│   ├── __init__.py
│   ├── basic_pipeline.py        # Phase 1/1.1 processing
│   └── sync_processor.py        # Phase 1/1.1 processor
├── processing_extended/         # NEW: Phase 2+ processing (conditional)
│   ├── __init__.py
│   ├── async_pipeline.py
│   ├── batch_pipeline.py
│   ├── stages/
│   │   ├── __init__.py
│   │   ├── extraction.py
│   │   ├── validation.py
│   │   ├── transformation.py
│   │   └── integration.py
│   └── ml_pipeline.py
├── factory/                     # NEW: Factory pattern for conditional loading
│   ├── __init__.py
│   ├── app_factory.py           # Creates appropriate app based on config
│   ├── service_factory.py       # Creates sync/async services
│   ├── client_factory.py        # Creates basic/extended clients
│   └── processor_factory.py     # Creates appropriate processors
├── tests/
│   ├── __init__.py
│   ├── unit/
│   │   ├── core/                # Phase 1/1.1 tests
│   │   └── extended/            # Phase 2+ tests
│   ├── integration/
│   │   ├── core/                # Phase 1/1.1 integration tests
│   │   └── extended/            # Phase 2+ integration tests
│   └── fixtures/
│       ├── core/                # Phase 1/1.1 fixtures
│       └── extended/            # Phase 2+ fixtures
├── docker/
│   ├── Dockerfile               # Multi-stage with conditional builds
│   ├── Dockerfile.extended      # Extended features container
│   ├── docker-compose.base.yml  # Phase 1/1.1 services
│   └── docker-compose.extended.yml # Phase 2+ services (Redis, workers)
├── deployment/
│   ├── base/                    # Phase 1/1.1 deployment
│   └── extended/                # Phase 2+ deployment configs
├── scripts/
│   ├── run_basic.sh            # Phase 1/1.1 startup
│   ├── run_extended.sh         # Phase 2+ startup
│   ├── check_config.sh         # Validates configuration
│   └── migrate.sh              # Smart migration based on config
├── requirements/
│   ├── base.txt                # Phase 1/1.1 requirements
│   ├── extended.txt            # Phase 2+ additional requirements
│   ├── dev.txt
│   └── test.txt
└── bootstrap/                  # NEW: Conditional bootstrapping
    ├── __init__.py
    ├── phase1_bootstrap.py     # Phase 1/1.1 initialization
    ├── phase2_bootstrap.py     # Phase 2+ initialization
    └── config_validator.py     # Validates configuration compatibility
```

## Key Design Principles

### 1. **Conditional Loading Pattern**
- Core functionality in base directories (e.g., `core/`, `services/`, `clients/`)
- Extended functionality in `*_extended/` directories
- Factory pattern creates appropriate instances based on `[extended] enabled` flag

### 2. **Import Strategy**
```python
# In settings.py or app initialization
if config.get('extended', 'enabled', fallback=False):
    from services_extended import AsyncDocumentService as DocumentService
    from clients_extended.bigcapital import AsyncClient as BigCapitalClient
else:
    from services import DocumentService
    from clients.bigcapital import Client as BigCapitalClient
```

### 3. **Database Migration Strategy**
- Phase 1 migrations in `phase1/` subfolder
- Phase 2+ migrations in `phase2/` subfolder
- Migration script checks config and applies appropriate migrations

### 4. **Template/Static Asset Strategy**
- Base templates always loaded
- Extended templates/assets conditionally loaded via Jinja2 template inheritance
- CSS/JS includes based on enabled features

### 5. **Docker Strategy**
- Base Dockerfile for Phase 1/1.1
- Extended Dockerfile adds Phase 2+ dependencies
- Conditional docker-compose files

This structure ensures that:
- Phase 1/1.1 code remains untouched and stable
- Phase 2+ features are completely isolated until enabled
- No performance overhead from unused features
- Clean upgrade path when ready to enable extended features
- Easy testing of both modes