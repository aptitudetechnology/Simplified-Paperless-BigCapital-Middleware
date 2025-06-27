# Phase 2 Directory Structure Evolution

## New Directory Structure

```
paperless-bigcapital-middleware/
├── config/
│   ├── __init__.py
│   ├── settings.py              # Enhanced with queue/redis config
│   ├── celery_config.py         # NEW: Celery configuration
│   └── config.ini.example       # Updated with new settings
├── core/
│   ├── __init__.py
│   ├── ocr_processor.py         # Enhanced with async support
│   ├── text_extractor.py        # Enhanced with better parsing
│   ├── processor.py             # Refactored for async processing
│   ├── exceptions.py            # MOVED from utils/ + enhanced
│   └── mappers.py               # NEW: Data mapping logic
├── clients/                     # RENAMED from core/ partial
│   ├── __init__.py
│   ├── bigcapital/              # NEW: Structured BigCapital client
│   │   ├── __init__.py
│   │   ├── client.py            # Async BigCapital API client
│   │   ├── models.py            # BigCapital data models
│   │   └── mappers.py           # BigCapital-specific mappers
│   └── paperless/               # NEW: Enhanced Paperless client
│       ├── __init__.py
│       ├── client.py            # Async Paperless API client
│       └── models.py            # Paperless data models
├── tasks/                       # NEW: Celery tasks
│   ├── __init__.py
│   ├── document_tasks.py        # Document processing tasks
│   ├── sync_tasks.py            # Data synchronization tasks
│   └── maintenance_tasks.py     # Cleanup and maintenance
├── services/                    # NEW: Business logic layer
│   ├── __init__.py
│   ├── document_processor.py    # Main async document processing
│   ├── invoice_service.py       # Invoice-specific operations
│   ├── sync_service.py          # Data synchronization logic
│   └── notification_service.py  # Status notifications
├── queue/                       # NEW: Queue management
│   ├── __init__.py
│   ├── celery_app.py           # Celery application setup
│   ├── connection_manager.py    # WebSocket connection management
│   └── status_broadcaster.py   # Real-time status broadcasting
├── database/
│   ├── __init__.py
│   ├── models.py               # Enhanced with job tracking models
│   ├── connection.py           # Enhanced with async support
│   ├── create_tables.py        # Updated for new models
│   ├── check_db.py            # Enhanced health checks
│   └── migrations/            # New migration files
│       ├── 001_initial.sql
│       ├── 002_processing_jobs.sql  # NEW: Job tracking
│       ├── 003_queue_status.sql     # NEW: Queue status
│       └── filehash.sql
├── api/                        # NEW: Structured API layer
│   ├── __init__.py
│   ├── v1/                     # Versioned API
│   │   ├── __init__.py
│   │   ├── documents.py        # Document endpoints
│   │   ├── jobs.py             # Job management endpoints
│   │   ├── status.py           # Status tracking endpoints
│   │   └── config.py           # Configuration endpoints
│   ├── websocket.py            # WebSocket handlers
│   └── middleware.py           # API middleware (auth, CORS, etc.)
├── web/
│   ├── __init__.py
│   ├── app.py                 # Enhanced Flask app with async routes
│   ├── legacy_routes.py       # Maintained for compatibility
│   ├── routes/                # Enhanced routing
│   │   ├── __init__.py
│   │   ├── api_routes.py      # Updated API routes
│   │   ├── web_routes.py      # Enhanced web routes
│   │   ├── job_routes.py      # NEW: Job management routes
│   │   └── utils.py           # Enhanced utilities
│   ├── templates/             # Enhanced templates
│   │   ├── base.html          # Updated with real-time features
│   │   ├── dashboard.html     # Real-time job monitoring
│   │   ├── jobs/              # NEW: Job management templates
│   │   │   ├── list.html
│   │   │   ├── detail.html
│   │   │   └── monitor.html   # Real-time monitoring
│   │   ├── upload.html        # Enhanced with queue status
│   │   ├── documents.html     # Enhanced with processing status
│   │   ├── document_detail.html
│   │   ├── config.html        # Enhanced configuration
│   │   ├── 404.html
│   │   └── errors/
│   │       ├── 404.html
│   │       └── 500.html
│   └── static/                # Enhanced static assets
│       ├── css/
│       │   ├── style.css      # Enhanced styles
│       │   └── dashboard.css  # NEW: Dashboard styles
│       └── js/
│           ├── dashboard.js   # NEW: Real-time dashboard
│           ├── websocket.js   # NEW: WebSocket client
│           └── job-monitor.js # NEW: Job monitoring
├── utils/                     # Restructured utilities
│   ├── __init__.py
│   ├── logger.py              # Enhanced structured logging
│   ├── retry.py               # NEW: Retry mechanisms
│   ├── circuit_breaker.py     # NEW: Circuit breaker pattern
│   ├── rate_limiter.py        # NEW: Rate limiting utilities
│   └── validators.py          # NEW: Input validation
├── monitoring/                # NEW: Monitoring and health checks
│   ├── __init__.py
│   ├── health_checks.py       # System health monitoring
│   ├── metrics.py             # Application metrics
│   └── alerts.py              # Alerting logic
├── processing/                # Restructured processing
│   ├── __init__.py
│   ├── pipeline.py            # NEW: Processing pipeline
│   ├── stages/                # NEW: Processing stages
│   │   ├── __init__.py
│   │   ├── extraction.py      # Data extraction stage
│   │   ├── validation.py      # Data validation stage
│   │   ├── transformation.py  # Data transformation stage
│   │   └── integration.py     # External system integration
│   └── exceptions.py          # MOVED to core/
├── tests/
│   ├── __init__.py
│   ├── unit/                  # NEW: Organized unit tests
│   │   ├── __init__.py
│   │   ├── test_clients.py    # Client tests
│   │   ├── test_services.py   # Service layer tests
│   │   ├── test_tasks.py      # Celery task tests
│   │   └── test_utils.py      # Utility tests
│   ├── integration/           # NEW: Integration tests
│   │   ├── __init__.py
│   │   ├── test_api.py        # API integration tests
│   │   ├── test_queue.py      # Queue system tests
│   │   └── test_workflow.py   # End-to-end workflow tests
│   ├── fixtures/              # NEW: Test fixtures
│   │   ├── __init__.py
│   │   ├── documents.py       # Document test data
│   │   └── responses.py       # API response mocks
│   ├── test_core.py           # Maintained legacy tests
│   ├── test_ocr.py           # Enhanced OCR tests
│   ├── test_database.py      # Enhanced database tests
│   └── test_web.py           # Enhanced web tests
├── docker/
│   ├── Dockerfile            # Enhanced multi-stage build
│   ├── Dockerfile.worker     # NEW: Celery worker container
│   ├── docker-compose.yml    # Enhanced with Redis, workers
│   └── docker-compose.dev.yml # NEW: Development environment
├── deployment/               # NEW: Deployment configurations
│   ├── systemd/              # Systemd service files
│   │   ├── middleware.service
│   │   └── celery-worker.service
│   ├── nginx/                # Nginx configuration
│   │   └── middleware.conf
│   └── supervisor/           # Supervisor process management
│       └── middleware.conf
├── scripts/
│   ├── init.sh               # Enhanced initialization
│   ├── run.sh                # Enhanced startup
│   ├── worker.sh             # NEW: Celery worker startup
│   ├── beat.sh               # NEW: Celery beat startup
│   ├── migrate.sh            # NEW: Database migration
│   └── health-check.sh       # NEW: Health check script
├── docs/                     # NEW: Enhanced documentation
│   ├── api/                  # API documentation
│   ├── deployment/           # Deployment guides
│   ├── development/          # Development setup
│   └── architecture/         # System architecture docs
├── logs/                     # Enhanced logging structure
│   ├── app/                  # Application logs
│   ├── celery/               # Celery worker logs
│   └── nginx/                # Nginx logs (if applicable)
├── requirements/             # NEW: Organized requirements
│   ├── base.txt              # Core requirements
│   ├── dev.txt               # Development requirements
│   ├── prod.txt              # Production requirements
│   └── test.txt              # Testing requirements
├── requirements.txt          # Main requirements (imports from requirements/)
├── celery_app.py            # NEW: Celery application entry point
├── config.ini.example       # Enhanced configuration
├── .env.example             # Enhanced environment variables
├── .gitignore               # Updated for new structure
├── Makefile                 # Enhanced build commands
└── README.md                # Updated documentation
```

## Key Changes Summary

### 1. **New Core Directories**
- **`clients/`** - Structured external API clients (BigCapital, Paperless)
- **`tasks/`** - Celery task definitions
- **`services/`** - Business logic layer (async-first)
- **`queue/`** - Queue management and WebSocket handling
- **`api/`** - Structured API layer with versioning
- **`monitoring/`** - Health checks and metrics
- **`deployment/`** - Deployment configurations

### 2. **Enhanced Existing Directories**
- **`config/`** - Added Celery configuration
- **`database/`** - New models for job tracking
- **`web/`** - Real-time features, enhanced templates
- **`utils/`** - Advanced patterns (retry, circuit breaker)
- **`tests/`** - Organized into unit/integration structure

### 3. **Restructured Components**
- **Processing pipeline** - More modular with distinct stages
- **Exception handling** - Moved to core for better organization
- **Requirements** - Split into multiple files for different environments

### 4. **New Files & Features**
- **WebSocket support** for real-time updates
- **Celery workers** for background processing
- **Health monitoring** and metrics collection
- **Advanced error handling** patterns
- **Kubernetes/Docker** deployment configs

### 5. **Migration Path**
The structure maintains backward compatibility by keeping existing files and gradually enhancing them. Key migration steps:

1. **Phase 2.1**: Add new directories and async clients
2. **Phase 2.2**: Implement Celery tasks and queue system
3. **Phase 2.3**: Add real-time features and monitoring
4. **Phase 2.4**: Enhance testing and deployment

This evolution supports the Phase 2 goals while maintaining the existing functionality and providing a clear upgrade path.