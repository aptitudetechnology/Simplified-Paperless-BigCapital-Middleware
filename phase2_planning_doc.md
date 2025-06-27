# Phase 2 Development Planning Document
## Paperless-ngx to BigCapital Middleware

### Overview
Phase 2 focuses on building the core integration capabilities, implementing robust asynchronous processing, and establishing reliable error handling mechanisms. This phase will transform the middleware from a prototype into a functional integration platform.

---

## 1. BigCapital API Integration

### Architecture Overview
- RESTful API client with authentication handling
- Rate limiting and request throttling
- Automatic token refresh mechanisms
- Comprehensive error handling

### Implementation Plan

#### 1.1 API Client Structure
```python
# bigcapital/client.py
import httpx
import asyncio
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
import logging

class BigCapitalClient:
    def __init__(self, base_url: str, client_id: str, client_secret: str):
        self.base_url = base_url.rstrip('/')
        self.client_id = client_id
        self.client_secret = client_secret
        self.access_token: Optional[str] = None
        self.token_expires_at: Optional[datetime] = None
        self.client = httpx.AsyncClient(timeout=30.0)
        self.logger = logging.getLogger(__name__)
    
    async def authenticate(self) -> bool:
        """Authenticate with BigCapital API"""
        auth_data = {
            'client_id': self.client_id,
            'client_secret': self.client_secret,
            'grant_type': 'client_credentials'
        }
        
        try:
            response = await self.client.post(
                f"{self.base_url}/api/auth/token",
                data=auth_data
            )
            response.raise_for_status()
            
            token_data = response.json()
            self.access_token = token_data['access_token']
            expires_in = token_data.get('expires_in', 3600)
            self.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in - 300)  # 5min buffer
            
            return True
        except Exception as e:
            self.logger.error(f"Authentication failed: {e}")
            return False
    
    async def _ensure_authenticated(self):
        """Ensure we have a valid token"""
        if not self.access_token or datetime.utcnow() >= self.token_expires_at:
            await self.authenticate()
    
    async def create_invoice(self, invoice_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create invoice in BigCapital"""
        await self._ensure_authenticated()
        
        headers = {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }
        
        response = await self.client.post(
            f"{self.base_url}/api/invoices",
            json=invoice_data,
            headers=headers
        )
        response.raise_for_status()
        return response.json()
```

#### 1.2 Invoice Data Mapping
```python
# bigcapital/mappers.py
from typing import Dict, Any, List
from dataclasses import dataclass
from decimal import Decimal

@dataclass
class InvoiceLineItem:
    description: str
    quantity: Decimal
    unit_price: Decimal
    total: Decimal
    tax_rate: Optional[Decimal] = None

@dataclass
class InvoiceData:
    customer_id: str
    invoice_number: str
    invoice_date: str
    due_date: str
    line_items: List[InvoiceLineItem]
    subtotal: Decimal
    tax_amount: Decimal
    total_amount: Decimal
    currency: str = 'USD'

class InvoiceMapper:
    @staticmethod
    def paperless_to_bigcapital(paperless_data: Dict[str, Any]) -> Dict[str, Any]:
        """Map Paperless-ngx document data to BigCapital invoice format"""
        return {
            "customer_id": paperless_data.get("correspondent_id"),
            "invoice_number": paperless_data.get("title", "").split("-")[-1],
            "invoice_date": paperless_data.get("created"),
            "due_date": paperless_data.get("due_date"),
            "line_items": [
                {
                    "description": item.get("description", ""),
                    "quantity": float(item.get("quantity", 1)),
                    "unit_price": float(item.get("unit_price", 0)),
                    "total": float(item.get("total", 0))
                }
                for item in paperless_data.get("line_items", [])
            ],
            "subtotal": float(paperless_data.get("subtotal", 0)),
            "tax_amount": float(paperless_data.get("tax_amount", 0)),
            "total_amount": float(paperless_data.get("total_amount", 0)),
            "currency": paperless_data.get("currency", "USD")
        }
```

---

## 2. Paperless-ngx Integration

### Implementation Plan

#### 2.1 Document Retrieval Service
```python
# paperless/client.py
import httpx
from typing import List, Dict, Any, Optional
import logging

class PaperlessClient:
    def __init__(self, base_url: str, api_token: str):
        self.base_url = base_url.rstrip('/')
        self.api_token = api_token
        self.client = httpx.AsyncClient(
            headers={'Authorization': f'Token {api_token}'},
            timeout=30.0
        )
        self.logger = logging.getLogger(__name__)
    
    async def get_documents(self, 
                          document_type: Optional[str] = None,
                          tag: Optional[str] = None,
                          limit: int = 100) -> List[Dict[str, Any]]:
        """Retrieve documents from Paperless-ngx"""
        params = {'page_size': limit}
        
        if document_type:
            params['document_type__name'] = document_type
        if tag:
            params['tags__name'] = tag
            
        try:
            response = await self.client.get(
                f"{self.base_url}/api/documents/",
                params=params
            )
            response.raise_for_status()
            return response.json()['results']
        except Exception as e:
            self.logger.error(f"Failed to retrieve documents: {e}")
            raise
    
    async def get_document_content(self, document_id: int) -> bytes:
        """Download document content"""
        response = await self.client.get(
            f"{self.base_url}/api/documents/{document_id}/download/"
        )
        response.raise_for_status()
        return response.content
    
    async def update_document_tags(self, document_id: int, tags: List[str]):
        """Update document tags to track processing status"""
        tag_data = {'tags': tags}
        response = await self.client.patch(
            f"{self.base_url}/api/documents/{document_id}/",
            json=tag_data
        )
        response.raise_for_status()
        return response.json()
```

#### 2.2 Document Processing Service
```python
# services/document_processor.py
from typing import Dict, Any, Optional
import logging
from .paperless.client import PaperlessClient
from .bigcapital.client import BigCapitalClient
from .models import ProcessingJob, ProcessingStatus

class DocumentProcessor:
    def __init__(self, paperless_client: PaperlessClient, bigcapital_client: BigCapitalClient):
        self.paperless = paperless_client
        self.bigcapital = bigcapital_client
        self.logger = logging.getLogger(__name__)
    
    async def process_invoice_document(self, document_id: int, job_id: str) -> Dict[str, Any]:
        """Process a single invoice document"""
        try:
            # Update job status
            await self.update_job_status(job_id, ProcessingStatus.PROCESSING)
            
            # Retrieve document from Paperless
            documents = await self.paperless.get_documents()
            document = next((d for d in documents if d['id'] == document_id), None)
            
            if not document:
                raise ValueError(f"Document {document_id} not found")
            
            # Extract invoice data (placeholder for OCR/parsing logic)
            invoice_data = await self.extract_invoice_data(document)
            
            # Create invoice in BigCapital
            bigcapital_invoice = await self.bigcapital.create_invoice(invoice_data)
            
            # Update document tags in Paperless
            await self.paperless.update_document_tags(
                document_id, 
                ['processed', f'bigcapital-id-{bigcapital_invoice["id"]}']
            )
            
            await self.update_job_status(job_id, ProcessingStatus.COMPLETED)
            
            return {
                'document_id': document_id,
                'bigcapital_invoice_id': bigcapital_invoice['id'],
                'status': 'success'
            }
            
        except Exception as e:
            self.logger.error(f"Processing failed for document {document_id}: {e}")
            await self.update_job_status(job_id, ProcessingStatus.FAILED, str(e))
            raise
    
    async def extract_invoice_data(self, document: Dict[str, Any]) -> Dict[str, Any]:
        """Extract structured data from document (placeholder)"""
        # This would integrate with OCR/ML services
        return {
            'customer_name': document.get('correspondent', {}).get('name', ''),
            'invoice_number': document.get('title', '').split('-')[-1],
            'total_amount': 0.0,  # Would be extracted from OCR
            'line_items': []  # Would be extracted from OCR
        }
```

---

## 3. Redis + Celery Queue System

### Implementation Plan

#### 3.1 Celery Configuration
```python
# celery_app.py
from celery import Celery
from kombu import Queue
import os

# Celery configuration
celery_app = Celery('paperless_bigcapital_middleware')

celery_app.conf.update(
    broker_url=os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
    result_backend=os.getenv('REDIS_URL', 'redis://localhost:6379/0'),
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_routes={
        'process_document': {'queue': 'document_processing'},
        'sync_invoice': {'queue': 'invoice_sync'},
        'cleanup_jobs': {'queue': 'maintenance'},
    },
    task_default_queue='default',
    task_queues=(
        Queue('document_processing', routing_key='document_processing'),
        Queue('invoice_sync', routing_key='invoice_sync'),
        Queue('maintenance', routing_key='maintenance'),
    ),
    # Retry configuration
    task_acks_late=True,
    task_reject_on_worker_lost=True,
    task_default_retry_delay=60,
    task_max_retries=3,
)

# Auto-discover tasks
celery_app.autodiscover_tasks(['tasks'])
```

#### 3.2 Celery Tasks
```python
# tasks/document_tasks.py
from celery import current_task
from celery.exceptions import Retry
from typing import Dict, Any
import asyncio
import logging

from ..celery_app import celery_app
from ..services.document_processor import DocumentProcessor
from ..models import ProcessingJob, ProcessingStatus
from ..database import get_db_session

@celery_app.task(bind=True, max_retries=3, default_retry_delay=60)
def process_document_task(self, document_id: int, config: Dict[str, Any]):
    """Celery task for processing documents"""
    job_id = self.request.id
    logger = logging.getLogger(__name__)
    
    try:
        # Update job status in database
        with get_db_session() as db:
            job = ProcessingJob(
                id=job_id,
                document_id=document_id,
                status=ProcessingStatus.QUEUED,
                config=config
            )
            db.add(job)
            db.commit()
        
        # Run async processing
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            processor = DocumentProcessor(
                paperless_client=create_paperless_client(config),
                bigcapital_client=create_bigcapital_client(config)
            )
            
            result = loop.run_until_complete(
                processor.process_invoice_document(document_id, job_id)
            )
            
            # Update job with success
            with get_db_session() as db:
                job = db.query(ProcessingJob).filter_by(id=job_id).first()
                job.status = ProcessingStatus.COMPLETED
                job.result = result
                db.commit()
            
            return result
            
        finally:
            loop.close()
            
    except Exception as exc:
        logger.error(f"Task failed: {exc}")
        
        # Update job with failure
        with get_db_session() as db:
            job = db.query(ProcessingJob).filter_by(id=job_id).first()
            if job:
                job.status = ProcessingStatus.FAILED
                job.error_message = str(exc)
                db.commit()
        
        # Retry logic
        if self.request.retries < self.max_retries:
            logger.info(f"Retrying task {job_id}, attempt {self.request.retries + 1}")
            raise self.retry(countdown=60 * (2 ** self.request.retries))
        
        raise exc

@celery_app.task
def sync_invoice_status(invoice_id: str, bigcapital_id: str):
    """Sync invoice status between systems"""
    # Implementation for status synchronization
    pass

@celery_app.task
def cleanup_old_jobs():
    """Maintenance task to clean up old processing jobs"""
    # Implementation for cleanup
    pass
```

---

## 4. Enhanced Error Handling

### Implementation Plan

#### 4.1 Custom Exception Classes
```python
# exceptions.py
class MiddlewareException(Exception):
    """Base exception for middleware operations"""
    pass

class AuthenticationError(MiddlewareException):
    """Authentication failed"""
    pass

class DocumentNotFoundError(MiddlewareException):
    """Document not found in Paperless-ngx"""
    pass

class BigCapitalAPIError(MiddlewareException):
    """BigCapital API operation failed"""
    def __init__(self, message: str, status_code: int = None, response_data: dict = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_data = response_data

class ProcessingError(MiddlewareException):
    """Document processing failed"""
    pass

class RateLimitError(MiddlewareException):
    """API rate limit exceeded"""
    def __init__(self, message: str, retry_after: int = None):
        super().__init__(message)
        self.retry_after = retry_after
```

#### 4.2 Retry Mechanisms
```python
# utils/retry.py
import asyncio
import functools
import random
from typing import Callable, Any, Union, Type
import logging

def async_retry(
    max_attempts: int = 3,
    delay: Union[int, float] = 1,
    backoff: float = 2,
    jitter: bool = True,
    exceptions: tuple = (Exception,)
):
    """Async retry decorator with exponential backoff"""
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            logger = logging.getLogger(func.__module__)
            
            for attempt in range(max_attempts):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    if attempt == max_attempts - 1:
                        logger.error(f"Final attempt failed for {func.__name__}: {e}")
                        raise
                    
                    wait_time = delay * (backoff ** attempt)
                    if jitter:
                        wait_time *= (0.5 + random.random() * 0.5)
                    
                    logger.warning(
                        f"Attempt {attempt + 1} failed for {func.__name__}: {e}. "
                        f"Retrying in {wait_time:.2f}s"
                    )
                    await asyncio.sleep(wait_time)
            
        return wrapper
    return decorator

# Usage example
@async_retry(max_attempts=3, delay=2, exceptions=(httpx.HTTPError, RateLimitError))
async def make_api_request(url: str, data: dict):
    # API request implementation
    pass
```

#### 4.3 Circuit Breaker Pattern
```python
# utils/circuit_breaker.py
import asyncio
from datetime import datetime, timedelta
from enum import Enum
from typing import Callable, Any
import logging

class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

class CircuitBreaker:
    def __init__(self, 
                 failure_threshold: int = 5,
                 recovery_timeout: int = 60,
                 expected_exception: Type[Exception] = Exception):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitState.CLOSED
        self.logger = logging.getLogger(__name__)
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        if self.state == CircuitState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitState.HALF_OPEN
                self.logger.info("Circuit breaker: Attempting reset")
            else:
                raise Exception("Circuit breaker is OPEN")
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise e
    
    def _should_attempt_reset(self) -> bool:
        return (datetime.utcnow() - self.last_failure_time) > timedelta(seconds=self.recovery_timeout)
    
    def _on_success(self):
        self.failure_count = 0
        self.state = CircuitState.CLOSED
    
    def _on_failure(self):
        self.failure_count += 1
        self.last_failure_time = datetime.utcnow()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitState.OPEN
            self.logger.warning(f"Circuit breaker opened after {self.failure_count} failures")
```

---

## 5. Processing Status Tracking

### Implementation Plan

#### 5.1 Database Models
```python
# models.py
from sqlalchemy import Column, Integer, String, DateTime, Text, JSON, Enum
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func
from enum import Enum as PyEnum

Base = declarative_base()

class ProcessingStatus(PyEnum):
    PENDING = "pending"
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    RETRYING = "retrying"

class ProcessingJob(Base):
    __tablename__ = "processing_jobs"
    
    id = Column(String, primary_key=True)  # Celery task ID
    document_id = Column(Integer, nullable=False)
    status = Column(Enum(ProcessingStatus), default=ProcessingStatus.PENDING)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now(), onupdate=func.now())
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)
    config = Column(JSON)
    result = Column(JSON)
    
    def to_dict(self):
        return {
            'id': self.id,
            'document_id': self.document_id,
            'status': self.status.value,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None,
            'started_at': self.started_at.isoformat() if self.started_at else None,
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'error_message': self.error_message,
            'retry_count': self.retry_count,
            'result': self.result
        }
```

#### 5.2 Status Tracking API
```python
# api/status.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Optional

from ..database import get_db
from ..models import ProcessingJob, ProcessingStatus

router = APIRouter(prefix="/api/status", tags=["status"])

@router.get("/jobs", response_model=List[dict])
async def get_all_jobs(
    status: Optional[ProcessingStatus] = None,
    limit: int = 100,
    db: Session = Depends(get_db)
):
    """Get all processing jobs with optional status filter"""
    query = db.query(ProcessingJob)
    
    if status:
        query = query.filter(ProcessingJob.status == status)
    
    jobs = query.order_by(ProcessingJob.created_at.desc()).limit(limit).all()
    return [job.to_dict() for job in jobs]

@router.get("/jobs/{job_id}")
async def get_job_status(job_id: str, db: Session = Depends(get_db)):
    """Get specific job status"""
    job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    return job.to_dict()

@router.post("/jobs/{job_id}/retry")
async def retry_job(job_id: str, db: Session = Depends(get_db)):
    """Retry a failed job"""
    job = db.query(ProcessingJob).filter(ProcessingJob.id == job_id).first()
    
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    
    if job.status != ProcessingStatus.FAILED:
        raise HTTPException(status_code=400, detail="Only failed jobs can be retried")
    
    # Reset job status and queue for retry
    job.status = ProcessingStatus.PENDING
    job.error_message = None
    job.retry_count += 1
    db.commit()
    
    # Re-queue the task
    from ..tasks.document_tasks import process_document_task
    process_document_task.delay(job.document_id, job.config)
    
    return {"message": "Job queued for retry", "job_id": job_id}
```

#### 5.3 Real-time Status Updates with WebSocket
```python
# api/websocket.py
from fastapi import WebSocket, WebSocketDisconnect
from typing import List
import json
import asyncio

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
    
    async def send_personal_message(self, message: str, websocket: WebSocket):
        await websocket.send_text(message)
    
    async def broadcast(self, message: str):
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                # Connection might be closed
                pass

manager = ConnectionManager()

@router.websocket("/ws/status")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        while True:
            # Keep connection alive
            await asyncio.sleep(30)
            await websocket.send_text(json.dumps({"type": "ping"}))
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# Function to broadcast status updates
async def broadcast_status_update(job_id: str, status: ProcessingStatus, data: dict = None):
    message = {
        "type": "status_update",
        "job_id": job_id,
        "status": status.value,
        "data": data or {}
    }
    await manager.broadcast(json.dumps(message))
```

---

## Development Timeline

### Week 1-2: Foundation
- Set up BigCapital API client with authentication
- Implement basic Paperless-ngx integration
- Create database models and migrations

### Week 3-4: Core Processing
- Implement document processing pipeline
- Set up Celery with Redis backend
- Basic error handling and retry mechanisms

### Week 5-6: Advanced Features
- Circuit breaker implementation
- Real-time status tracking with WebSocket
- Comprehensive error handling

### Week 7-8: Testing & Optimization
- Unit and integration tests
- Performance optimization
- Documentation and deployment guides

---

## Testing Strategy

### Unit Tests
```python
# tests/test_bigcapital_client.py
import pytest
import httpx
from unittest.mock import AsyncMock, patch

from ..bigcapital.client import BigCapitalClient

@pytest.mark.asyncio
async def test_authentication_success():
    client = BigCapitalClient("https://api.example.com", "client_id", "secret")
    
    with patch.object(client.client, 'post') as mock_post:
        mock_response = AsyncMock()
        mock_response.json.return_value = {
            'access_token': 'test_token',
            'expires_in': 3600
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        result = await client.authenticate()
        
        assert result is True
        assert client.access_token == 'test_token'
        assert client.token_expires_at is not None
```

### Integration Tests
```python
# tests/test_integration.py
import pytest
from unittest.mock import AsyncMock

from ..services.document_processor import DocumentProcessor

@pytest.mark.asyncio
async def test_end_to_end_processing():
    # Mock clients
    paperless_client = AsyncMock()
    bigcapital_client = AsyncMock()
    
    # Set up mock responses
    paperless_client.get_documents.return_value = [
        {'id': 1, 'title': 'Invoice-001', 'correspondent': {'name': 'Test Corp'}}
    ]
    bigcapital_client.create_invoice.return_value = {'id': 'bc_123'}
    
    processor = DocumentProcessor(paperless_client, bigcapital_client)
    result = await processor.process_invoice_document(1, 'job_123')
    
    assert result['status'] == 'success'
    assert result['bigcapital_invoice_id'] == 'bc_123'
```

---

## Deployment Considerations

### Docker Compose Setup
```yaml
# docker-compose.yml (additional services for Phase 2)
services:
  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"
    volumes:
      - redis_data:/data
  
  celery_worker:
    build: .
    command: celery -A celery_app worker --loglevel=info --queues=document_processing,invoice_sync
    depends_on:
      - redis
      - postgres
    environment:
      - REDIS_URL=redis://redis:6379/0
      - DATABASE_URL=postgresql://user:pass@postgres:5432/middleware
    volumes:
      - ./logs:/app/logs
  
  celery_beat:
    build: .
    command: celery -A celery_app beat --loglevel=info
    depends_on:
      - redis
      - postgres
    environment:
      - REDIS_URL=redis://redis:6379/0

volumes:
  redis_data:
```

### Monitoring and Logging
- Implement structured logging with correlation IDs
- Set up Celery monitoring with Flower
- Add health check endpoints
- Configure alerting for failed jobs

This planning document provides a comprehensive roadmap for Phase 2 development with practical code examples and implementation strategies.