# System Architecture Document
## Feature Flag Promotion Dashboard - POC

**Version:** 1.0  
**Date:** May 30, 2026  
**Status:** Draft

---

## Overview

This document describes the system architecture for the Feature Flag Promotion Dashboard POC. The system provides a market-aware interface for comparing and promoting feature flags across environments, with GrowthBook as the source of truth.

---

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (React)                        │
│  - Market/Environment Selection                             │
│  - Flag Inventory View                                      │
│  - Comparison UI                                            │
│  - Promotion Confirmation                                   │
└──────────────────────┬──────────────────────────────────────┘
                       │ HTTP/REST API
┌──────────────────────▼──────────────────────────────────────┐
│                  Backend (FastAPI)                          │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  API Layer (Routers)                                  │  │
│  │  - /markets, /flags, /compare, /promote               │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  Business Logic Layer                                │  │
│  │  - Comparison Engine                                 │  │
│  │  - Promotion Engine                                  │  │
│  └──────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────┐  │
│  │  GrowthBook Client                                  │  │
│  │  - Read flags/values by environment                 │  │
│  │  - Create/update flags in environments              │  │
│  └──────────────────────────────────────────────────────┘  │
└──────┬──────────────────────┬───────────────────────────────┘
       │                      │
       │ SQLAlchemy ORM        │ HTTP Client (httpx)
       │ Async                │ Async
       │                      │
┌──────▼──────────────────────▼───────────────────────────────┐
│              Local Database (PostgreSQL)                    │
│  - markets (id, name, env_flow)                            │
│  - flags (id, key, market_id, growthbook_feature_id)        │
└─────────────────────────────────────────────────────────────┘
       
┌─────────────────────────────────────────────────────────────┐
│                GrowthBook API (External)                     │
│  - Feature flags with values per environment                │
│  - REST API with authentication                             │
└─────────────────────────────────────────────────────────────┘
```

---

## Architectural Decisions

### 1. Separation of Concerns

**Local Database (PostgreSQL)**
- Stores only metadata: flag-to-market mappings, environment flows
- Does NOT store flag values (source of truth is GrowthBook)
- Enables quick inventory queries without external API calls

**GrowthBook (External)**
- Source of truth for all flag values and configurations
- All read/write operations go through GrowthBook API
- Ensures consistency between dashboard and actual flag state

**Frontend (React)**
- UI/UX layer only
- No business logic
- Uses local React state for simplicity (POC)

**Backend (FastAPI)**
- All business logic and external integrations
- Async operations for performance
- Generic error handling

### 2. Data Flow

**Comparison Flow**
```
Frontend → Backend (POST /compare)
  ↓
Backend reads flag IDs from local DB
  ↓
Backend reads values from GrowthBook (source env)
  ↓
Backend reads values from GrowthBook (target env)
  ↓
Backend computes diff (in_sync/missing/different)
  ↓
Backend returns results to Frontend
```

**Promotion Flow**
```
Frontend → Backend (POST /promote)
  ↓
Backend reads flag IDs from request
  ↓
Backend reads source values from GrowthBook
  ↓
Backend reads target values from GrowthBook
  ↓
For each flag:
  - If missing: create in target with source value
  - If different: update target with source value
  - If same: noop
  ↓
Backend writes changes to GrowthBook
  ↓
Backend returns per-flag results to Frontend
```

**Registration Flow**
```
Frontend → Backend (POST /flags)
  ↓
Backend stores flag metadata in local DB
  ↓
Backend returns confirmation to Frontend
```

### 3. Technology Stack

**Frontend**
- React 18+
- Vite (build tool)
- React Router (navigation)
- Axios or fetch (HTTP client)
- Local React state (useState, useContext)

**Backend**
- Python 3.11+
- FastAPI (web framework)
- SQLAlchemy 2.0+ (ORM)
- asyncpg (PostgreSQL async driver)
- httpx (async HTTP client for GrowthBook)
- Pydantic (data validation)

**Database**
- PostgreSQL (already set up)
- Connection pooling via SQLAlchemy

**External Services**
- GrowthBook API (REST)
- Authentication via API key

### 4. Communication Patterns

**API Design**
- RESTful endpoints with standard HTTP methods
- JSON request/response bodies
- Async operations throughout (FastAPI + SQLAlchemy async)
- Generic error handling with status codes

**Error Handling**
- 400: Bad request (validation errors)
- 404: Not found (resource doesn't exist)
- 409: Conflict (concurrent modification)
- 500: Server error (unexpected failures)
- Per-flag error reporting for partial failures

**State Management**
- Frontend: Local React state (useState)
- Backend: Stateless (no session state)
- Database: Single source of truth for metadata

---

## Database Schema

### Table: markets

```sql
CREATE TABLE markets (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) NOT NULL UNIQUE,
    env_flow VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Index
CREATE INDEX idx_markets_name ON markets(name);
```

**Example Data:**
```json
{
  "id": 1,
  "name": "india",
  "env_flow": "dev->qa->uat->prod",
  "created_at": "2026-05-30T00:00:00Z"
}
```

### Table: flags

```sql
CREATE TABLE flags (
    id SERIAL PRIMARY KEY,
    key VARCHAR(255) NOT NULL,
    market_id INTEGER NOT NULL REFERENCES markets(id) ON DELETE CASCADE,
    growthbook_feature_id VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP DEFAULT NOW(),
    UNIQUE(key, market_id)
);

-- Indexes
CREATE INDEX idx_flags_market_id ON flags(market_id);
CREATE INDEX idx_flags_key ON flags(key);
CREATE INDEX idx_flags_growthbook_feature_id ON flags(growthbook_feature_id);
```

**Example Data:**
```json
{
  "id": 1,
  "key": "enable_checkout",
  "market_id": 1,
  "growthbook_feature_id": "feat_checkout_01",
  "created_at": "2026-05-30T00:00:00Z",
  "updated_at": "2026-05-30T00:00:00Z"
}
```

### Relationships

```
markets (1) ───< (N) flags
  └── id (PK)     └── market_id (FK)
```

---

## API Architecture

### Endpoint Organization

**Base URL:** `http://localhost:8000/api/v1`

**Router Structure:**
```
/api/v1
├── /markets
│   ├── GET    /          (list markets)
│   ├── GET    /{id}      (get market)
│   └── POST   /          (create market)
├── /flags
│   ├── GET    /          (list flags by market)
│   ├── GET    /{id}      (get flag)
│   ├── POST   /          (register flag)
│   ├── PUT    /{id}      (update flag)
│   └── POST   /import    (import from GrowthBook)
├── /compare
│   └── POST   /          (compare environments)
└── /promote
    ├── POST   /          (execute promotion)
    └── GET    /{job_id}  (get promotion status - optional)
```

### Request/Response Patterns

**Success Response**
```json
{
  "data": { ... },
  "status": "success"
}
```

**Error Response**
```json
{
  "error": {
    "message": "Error description",
    "code": "ERROR_CODE",
    "details": { ... }
  },
  "status": "error"
}
```

**Partial Success Response (Promotion)**
```json
{
  "results": [
    { "flag_id": 1, "status": "success", "action": "create" },
    { "flag_id": 2, "status": "failed", "action": "update", "error": "GB API error" }
  ],
  "summary": {
    "total": 2,
    "succeeded": 1,
    "failed": 1
  }
}
```

---

## GrowthBook Integration

### Authentication

**Environment Variables:**
```bash
GROWTHBOOK_API_KEY=your_api_key_here
GROWTHBOOK_BASE_URL=https://api.growthbook.io
```

**Client Configuration:**
```python
import httpx

class GrowthBookClient:
    def __init__(self):
        self.base_url = os.getenv("GROWTHBOOK_BASE_URL")
        self.api_key = os.getenv("GROWTHBOOK_API_KEY")
        self.headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
```

### API Operations

**Read Flag Value by Environment**
```
GET /api/v1/features/{feature_id}?environment={env}

Response:
{
  "id": "feat_checkout_01",
  "key": "enable_checkout",
  "value": true,
  "environment": "dev"
}
```

**Create Flag in Environment**
```
POST /api/v1/features/{feature_id}/environments/{env}

Body:
{
  "value": true
}

Response:
{
  "success": true
}
```

**Update Flag in Environment**
```
PATCH /api/v1/features/{feature_id}/environments/{env}

Body:
{
  "value": false
}

Response:
{
  "success": true
}
```

### Error Handling

**Client Implementation:**
```python
async def get_flag_value(self, feature_id: str, env: str):
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{self.base_url}/api/v1/features/{feature_id}",
                params={"environment": env},
                headers=self.headers,
                timeout=10.0
            )
            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        raise GrowthBookError(f"GB API error: {e.response.status_code}")
    except httpx.RequestError as e:
        raise GrowthBookError(f"Request failed: {str(e)}")
```

### Rate Limiting (Future Enhancement)

For POC: No rate limiting (assumes low volume)

For Production: Implement request throttling
```python
from asyncio import Semaphore

semaphore = Semaphore(10)  # Max 10 concurrent requests

async def get_flag_value(self, feature_id: str, env: str):
    async with semaphore:
        # ... existing code ...
```

---

## Backend Architecture

### Project Structure

```
api/
├── app/
│   ├── main.py              # FastAPI app entry point
│   ├── db.py                # Database connection and models
│   ├── routers/
│   │   ├── markets.py       # Market endpoints
│   │   ├── flags.py        # Flag endpoints
│   │   ├── compare.py      # Comparison endpoints
│   │   └── promote.py      # Promotion endpoints
│   ├── services/
│   │   ├── growthbook.py   # GrowthBook client
│   │   ├── comparison.py   # Comparison logic
│   │   └── promotion.py    # Promotion logic
│   └── models/
│       ├── market.py        # Market SQLAlchemy model
│       └── flag.py          # Flag SQLAlchemy model
├── requirements.txt
└── tests/
```

### Layer Architecture

**Presentation Layer (Routers)**
- Handle HTTP requests/responses
- Validate input with Pydantic
- Call service layer
- Return formatted responses

**Service Layer (Business Logic)**
- Implement comparison logic
- Implement promotion logic
- Coordinate GrowthBook calls
- Handle business rules

**Data Access Layer (Models)**
- SQLAlchemy ORM models
- Database queries
- Transaction management

**Integration Layer (GrowthBook Client)**
- External API calls
- Error handling
- Retry logic (optional)

### Async Pattern

All database and external API calls use async/await:

```python
async def compare_environments(market_id: int, source_env: str, target_env: str):
    async with AsyncSessionLocal() as session:
        flags = await get_flags_by_market(session, market_id)
    
    results = []
    for flag in flags:
        source_val = await gb_client.get_flag_value(flag.growthbook_feature_id, source_env)
        target_val = await gb_client.get_flag_value(flag.growthbook_feature_id, target_env)
        status = compute_status(source_val, target_val)
        results.append({...})
    
    return results
```

---

## Frontend Architecture

### Component Structure

```
src/
├── App.jsx                 # Main app component
├── components/
│   ├── MarketSelector.jsx  # Market dropdown
│   ├── EnvFlowDisplay.jsx  # Environment flow visualization
│   ├── FlagInventory.jsx   # Flag list table
│   ├── FlagRegistration.jsx # Flag registration form
│   ├── ComparisonView.jsx  # Comparison UI
│   └── PromotionDialog.jsx # Promotion confirmation
├── services/
│   └── api.js              # API client
└── utils/
    └── helpers.js          # Utility functions
```

### State Management

**Local State (useState)**
```jsx
function App() {
  const [selectedMarket, setSelectedMarket] = useState(null);
  const [flags, setFlags] = useState([]);
  const [comparisonResults, setComparisonResults] = useState([]);
  const [sourceEnv, setSourceEnv] = useState('dev');
  const [targetEnv, setTargetEnv] = useState('qa');
  
  // ...
}
```

**API Client**
```javascript
const api = {
  getMarkets: () => axios.get('/api/v1/markets'),
  getFlags: (marketId) => axios.get(`/api/v1/flags?market_id=${marketId}`),
  compare: (data) => axios.post('/api/v1/compare', data),
  promote: (data) => axios.post('/api/v1/promote', data)
};
```

### Component Hierarchy

```
App
├── Header
├── MarketSelector
├── EnvFlowDisplay
├── FlagInventory
│   └── FlagRow
├── ComparisonView
│   ├── EnvSelector
│   ├── ResultsTable
│   └── PromotionButton
└── PromotionDialog
    └── ConfirmationSummary
```

---

## Deployment Architecture (POC)

### Local Development

```
┌─────────────────────────────────────────┐
│  Developer Machine                      │
│  ┌───────────────────────────────────┐  │
│  │ Frontend (Vite dev server)         │  │
│  │ http://localhost:5173              │  │
│  └───────────────────────────────────┘  │
│  ┌───────────────────────────────────┐  │
│  │ Backend (FastAPI + uvicorn)       │  │
│  │ http://localhost:8000             │  │
│  └───────────────────────────────────┘  │
│  ┌───────────────────────────────────┐  │
│  │ PostgreSQL (Docker or local)      │  │
│  │ localhost:5432                    │  │
│  └───────────────────────────────────┘  │
└─────────────────────────────────────────┘
            │
            │ HTTPS
            │
┌───────────▼──────────────────────────────┐
│  GrowthBook API (cloud)                  │
│  https://api.growthbook.io              │
└──────────────────────────────────────────┘
```

### Environment Variables

**Backend (.env)**
```bash
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/flag_dashboard
GROWTHBOOK_API_KEY=your_api_key
GROWTHBOOK_BASE_URL=https://api.growthbook.io
CORS_ORIGINS=http://localhost:5173
```

**Frontend (.env)**
```bash
VITE_API_BASE_URL=http://localhost:8000/api/v1
```

---

## Security Considerations

### API Key Management
- GrowthBook API key stored in environment variable (never in code)
- .env file in .gitignore
- Document setup instructions for developers

### Data Handling
- No sensitive flag values logged
- Error messages don't expose internal details
- Generic error handling for production

### CORS
- Frontend origin whitelisted in CORS config
- POC: localhost:5173 only
- Production: specific domains

### POC Limitations (Out of Scope)
- No authentication/authorization
- No RBAC
- No audit logging
- No encryption at rest (assumes trusted network)

---

## Performance Considerations

### Database
- Indexed queries on market_id, key, growthbook_feature_id
- Connection pooling via SQLAlchemy
- Async operations prevent blocking

### GrowthBook API
- Concurrent requests with httpx async client
- No caching (real-time data)
- Timeout: 10 seconds per request

### Frontend
- Lazy loading of large datasets
- Pagination for flag lists
- Optimistic UI updates (optional)

### Monitoring (Future Enhancement)
- Log API response times
- Track GrowthBook API call counts
- Monitor database query performance

---

## Error Handling Strategy

### Backend Error Types

**Validation Errors (400)**
```python
raise HTTPException(
    status_code=400,
    detail={"message": "Invalid input", "field": "market_id"}
)
```

**Not Found (404)**
```python
raise HTTPException(
    status_code=404,
    detail={"message": "Flag not found", "flag_id": 123}
)
```

**GrowthBook API Errors (502)**
```python
try:
    await gb_client.update_flag(...)
except GrowthBookError as e:
    return {
        "flag_id": flag.id,
        "status": "failed",
        "error": str(e)
    }
```

**Generic Server Errors (500)**
```python
@app.exception_handler(Exception)
async def generic_exception_handler(request, exc):
    logger.error(f"Unexpected error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": {"message": "Internal server error"}}
    )
```

### Frontend Error Handling

```javascript
try {
  const response = await api.compare(data);
  setResults(response.data);
} catch (error) {
  if (error.response?.status === 400) {
    setError("Invalid request: " + error.response.data.error.message);
  } else {
    setError("Something went wrong. Please try again.");
  }
}
```

---

## Testing Strategy

### Unit Tests (Backend)
- Test service layer logic (comparison, promotion)
- Mock GrowthBook client
- Test database operations

### Integration Tests (Backend)
- Test API endpoints with test database
- Test GrowthBook integration with mock server

### E2E Tests (Frontend)
- Test user flows (register → compare → promote)
- Use Playwright or Cypress

### Manual Testing Checklist
- [ ] Register flag to market
- [ ] View flag inventory
- [ ] Compare environments
- [ ] Promote flags
- [ ] Verify changes in GrowthBook

---

## Future Enhancements (Post-POC)

1. **Authentication**: Add JWT-based auth
2. **RBAC**: Role-based access control
3. **Audit Logging**: Track all changes
4. **Caching**: Redis cache for GrowthBook responses
5. **Background Jobs**: Celery for long-running promotions
6. **Webhooks**: GrowthBook webhook integration
7. **Multi-Market Support**: Extend beyond India
8. **Rollback**: Automated rollback capability
9. **Scheduling**: Scheduled promotions
10. **Notifications**: Email/Slack alerts

---

## Appendix

### Technology Versions

- Python: 3.11+
- FastAPI: 0.104+
- SQLAlchemy: 2.0+
- asyncpg: 0.29+
- httpx: 0.25+
- React: 18+
- Vite: 5+
- PostgreSQL: 15+

### References
- FastAPI Documentation: https://fastapi.tiangolo.com
- SQLAlchemy Async: https://docs.sqlalchemy.org/en/20/orm/extensions/asyncio.html
- GrowthBook API: https://docs.growthbook.io/api
- React Documentation: https://react.dev
