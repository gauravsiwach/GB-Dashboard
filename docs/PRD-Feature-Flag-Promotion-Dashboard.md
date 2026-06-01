# Product Requirements Document (PRD)
## Feature Flag Promotion Dashboard - POC

**Version:** 1.0  
**Date:** May 30, 2026  
**Status:** Draft for Review  
**Target Market:** India (POC)

---

## Executive Summary

A market-aware feature flag promotion dashboard that provides visibility and control over feature flag management across environments, with GrowthBook as the source of truth. This POC addresses critical operational risks in manual flag promotion workflows by providing a centralized tool for comparison and controlled promotion.

---

## Problem Statement

### Current Pain Points

**1. Visibility Gap**
- Teams maintain flag-to-market mappings in Excel/Notepad
- No centralized view of which flags are used in which markets
- Cannot see current state of flag values across all environments
- Async/existing values make state unclear

**2. Operational Risk**
- Manual flag promotions frequently misconfigure values → release failures
- Any incorrect update has direct production impact
- High cognitive load on operators during release windows
- No validation before applying changes

**3. Process Issues**
- Flag values drift across environments per market
- No controlled promotion workflow
- No single source of truth for flag state
- Manual changes require extreme attention and are error-prone

**4. Data Complexity**
- Multiple markets with different environment flows
- Multiple environments (dev → qa → uat → prod)
- Many flags with different types and values
- GrowthBook as external system of record

### Impact
- Release failures due to misconfigured flags
- Increased time to resolve flag-related incidents
- High operational overhead during promotions
- Risk of production outages

---

## Solution Overview

A dashboard that:
1. **Maintains flag-to-market mappings** in local database
2. **Reads flag values from GrowthBook** (source of truth)
3. **Compares flags across environments** to show sync status
4. **Promotes flags with user confirmation** (create missing or update existing)
5. **Writes changes directly to GrowthBook** with validation

### Key Benefits
- **Visibility**: Clear view of which flags belong to which markets
- **Control**: User-controlled, step-by-step promotion workflow
- **Safety**: Compare before promote, explicit confirmation required
- **Accuracy**: Direct GrowthBook integration eliminates manual errors
- **Traceability**: Know exactly what will change before executing

---

## Stakeholders

- **Product Owner:** Feature flag owner
- **Primary Users:** Release engineers, market owners
- **Secondary Users:** QA leads, DevOps engineers
- **Approver:** Engineering lead

---

## Personas

### Release Engineer
- **Goal:** Promote flags safely during release windows
- **Pain:** Manual promotions are error-prone and time-consuming
- **Need:** Step-by-step promotion with validation

### Market Owner
- **Goal:** Verify per-market flag values and request promotions
- **Pain:** No visibility into which flags are used in their market
- **Need:** Clear inventory and comparison view

### QA Lead
- **Goal:** Confirm behavior after promotion
- **Pain:** Cannot verify flag state across environments easily
- **Need:** Quick comparison to validate sync status

---

## User Journey

### 1. Setup (One-time)
**User:** Admin  
**Action:** Register flags to market (india)
- Manually add flag name and GrowthBook feature ID
- Or import flags from GrowthBook

### 2. View Inventory
**User:** Release Engineer  
**Action:** Select market (india)
- See list of all flags registered to market
- View environment flow (dev→qa→uat→prod)

### 3. Compare Environments
**User:** Release Engineer  
**Action:** Select source env (e.g., qa) and target env (e.g., uat)
- System reads current values from GrowthBook for both environments
- Shows comparison results:
  - **In sync**: Values match (no action needed)
  - **Missing**: Flag not in target env (will be created)
  - **Different**: Flag exists but values differ (will be updated)

### 4. Promote Flags
**User:** Release Engineer  
**Action:** Select flags to promote, review changes, confirm
- System determines action (create or update)
- User confirms promotion
- System writes changes to GrowthBook
- Shows per-flag results (success/failure)

### 5. Verify
**User:** QA Lead  
**Action:** Re-run comparison to verify sync
- Confirms target environment now matches source

---

## Functional Requirements

### FR1 - Market Management
**Priority:** High  
**Description:** Define and manage markets with environment flows

**Acceptance Criteria:**
- Can create market with name and environment flow (e.g., "dev->qa->uat->prod")
- Can view list of markets
- Can view market details including environment flow
- POC: India market only

**API:**
- `GET /markets` - list markets
- `GET /markets/{id}` - get market details
- `POST /markets` - create market (admin)

---

### FR2 - Flag Registration
**Priority:** High  
**Description:** Register flags to markets with GrowthBook mapping

**Acceptance Criteria:**
- Can manually register flag with name, market, and GrowthBook feature ID
- Can view all flags for a selected market
- Can update flag mapping
- Can import flags from GrowthBook

**API:**
- `GET /flags?market_id={id}` - list flags for market
- `POST /flags` - register flag
  - Body: `{ key, market_id, growthbook_feature_id }`
- `PUT /flags/{id}` - update flag mapping
- `POST /flags/import` - import from GrowthBook
  - Body: `{ market_id, growthbook_feature_ids[] }`

**Data Stored Locally:**
- Flag key (name)
- Market ID
- GrowthBook feature ID (mapping)

**Data NOT Stored Locally:**
- Flag values (read from GrowthBook)
- Flag configurations (read from GrowthBook)

---

### FR3 - Inventory View
**Priority:** High  
**Description:** View all flags registered to a market

**Acceptance Criteria:**
- Can select market from dropdown
- Shows list of all flags for selected market
- Displays flag key and GrowthBook feature ID
- Shows environment flow for market
- No values displayed (values live in GrowthBook)

**UI Components:**
- Market selector dropdown
- Environment flow display (e.g., "dev → qa → uat → prod")
- Flag list table (key, GB feature ID)

---

### FR4 - Environment Comparison
**Priority:** High  
**Description:** Compare flag values between source and target environments

**Acceptance Criteria:**
- Can select source environment (e.g., qa)
- Can select target environment (e.g., uat)
- System reads current values from GrowthBook for both environments
- Shows comparison results with status:
  - **In sync**: Source and target values match
  - **Missing**: Flag not present in target environment
  - **Different**: Flag exists but values differ
- Displays source value and target value for each flag
- Can filter/search flags in comparison results

**API:**
- `POST /compare`
  - Body: `{ market_id, source_env, target_env, flag_ids[] }`
  - Response: `{ results: [{ flag_id, flag_key, status, source_value, target_value }] }`

**Comparison Logic:**
```
if target_value is null:
    status = "missing"
elif source_value == target_value:
    status = "in_sync"
else:
    status = "different"
```

---

### FR5 - Flag Promotion
**Priority:** High  
**Description:** Promote flags from source to target environment with user confirmation

**Acceptance Criteria:**
- Can select flags to promote from comparison results
- Shows preview of actions (create or update)
- Requires explicit user confirmation before execution
- Executes promotion:
  - If flag missing in target: creates flag with source value
  - If flag exists in target: updates value to match source
- Writes changes directly to GrowthBook
- Shows per-flag results (success/failure with error details)
- Supports step-by-step promotion (user controls: dev→qa, then qa→uat, etc.)

**API:**
- `POST /promote`
  - Body: `{ market_id, source_env, target_env, flag_ids[] }`
  - Response: `{ results: [{ flag_id, status, action, error? }] }`

**Promotion Logic:**
```
for each flag:
    read source_value from GrowthBook
    read target_value from GrowthBook
    
    if target_value is null:
        action = "create"
        create flag in target_env with source_value
    elif source_value != target_value:
        action = "update"
        update flag in target_env with source_value
    else:
        action = "noop"
        no change needed
    
    write to GrowthBook
    return result
```

**Error Handling:**
- If GrowthBook API fails, report error for that flag
- Continue processing remaining flags (partial success)
- Return detailed error messages per flag

---

### FR6 - GrowthBook Import
**Priority:** Medium  
**Description:** Import flags from GrowthBook for flags created manually outside the tool

**Acceptance Criteria:**
- Can trigger import for specific GrowthBook feature IDs
- System fetches flag metadata from GrowthBook
- Creates flag registration in local DB
- Maps to selected market
- Shows import results (success/failure per flag)

**API:**
- `POST /flags/import`
  - Body: `{ market_id, growthbook_feature_ids[] }`
  - Response: `{ results: [{ feature_id, status, error? }] }`

**Use Case:**
Flags created manually in GrowthBook need to be registered in the dashboard for promotion workflows.

---

## Non-Functional Requirements

### NFR1 - Performance
- Comparison of up to 100 flags completes within 5 seconds
- Promotion of up to 50 flags completes within 10 seconds
- UI remains responsive during operations

### NFR2 - Reliability
- GrowthBook API failures are handled gracefully
- Partial failures reported clearly (which flags succeeded/failed)
- Retry mechanism for transient failures (optional for POC)

### NFR3 - Usability
- Clear visual indication of sync status (colors, icons)
- Confirmation dialog before promotion with summary of changes
- Error messages are actionable and specific

### NFR4 - Security
- GrowthBook API key stored in environment variable (not in code)
- No sensitive data logged
- POC: No authentication (out of scope)

---

## Data Model

### Local Database (PostgreSQL/SQLite)

**markets**
```
id              INTEGER PRIMARY KEY
name            VARCHAR(100) NOT NULL UNIQUE
env_flow        VARCHAR(255) NOT NULL
created_at      TIMESTAMP DEFAULT NOW()
```

**flags**
```
id                      INTEGER PRIMARY KEY
key                     VARCHAR(255) NOT NULL
market_id               INTEGER NOT NULL REFERENCES markets(id)
growthbook_feature_id   VARCHAR(255) NOT NULL
created_at              TIMESTAMP DEFAULT NOW()
updated_at              TIMESTAMP DEFAULT NOW()

UNIQUE(key, market_id)
```

### GrowthBook (External API)
- Feature flags with values per environment
- Accessed via GrowthBook REST API
- Not stored locally

---

## API Specifications

### Base URL
`http://localhost:8000/api/v1`

### Endpoints

#### Markets
```
GET /markets
Response: { markets: [{ id, name, env_flow }] }

GET /markets/{id}
Response: { id, name, env_flow, created_at }

POST /markets
Body: { name, env_flow }
Response: { id, name, env_flow, created_at }
```

#### Flags
```
GET /flags?market_id={id}
Response: { flags: [{ id, key, market_id, growthbook_feature_id }] }

POST /flags
Body: { key, market_id, growthbook_feature_id }
Response: { id, key, market_id, growthbook_feature_id, created_at }

PUT /flags/{id}
Body: { key?, growthbook_feature_id? }
Response: { id, key, market_id, growthbook_feature_id, updated_at }

POST /flags/import
Body: { market_id, growthbook_feature_ids: [] }
Response: { results: [{ feature_id, status, error? }] }
```

#### Comparison
```
POST /compare
Body: {
    market_id: number,
    source_env: string,
    target_env: string,
    flag_ids: number[]
}
Response: {
    results: [{
        flag_id: number,
        flag_key: string,
        status: "in_sync" | "missing" | "different",
        source_value: any,
        target_value: any
    }]
}
```

#### Promotion
```
POST /promote
Body: {
    market_id: number,
    source_env: string,
    target_env: string,
    flag_ids: number[]
}
Response: {
    results: [{
        flag_id: number,
        flag_key: string,
        status: "success" | "failed",
        action: "create" | "update" | "noop",
        error?: string
    }]
}
```

---

## GrowthBook Integration

### Configuration
- **API Key:** Stored in `GROWTHBOOK_API_KEY` environment variable
- **Base URL:** `https://api.growthbook.io` (configurable via `GROWTHBOOK_BASE_URL`)

### Operations

#### Read Flag Values
```
GET /api/v1/features/{feature_id}?environment={env}
Response: { id, key, value, ... }
```

#### Create Flag in Environment
```
POST /api/v1/features/{feature_id}/environments/{env}
Body: { value }
Response: { success, ... }
```

#### Update Flag in Environment
```
PATCH /api/v1/features/{feature_id}/environments/{env}
Body: { value }
Response: { success, ... }
```

### Error Handling
- API key missing → fail with clear error message
- Network error → retry once, then fail with error
- 4xx/5xx response → fail with GrowthBook error message
- Partial failures → continue processing, report per-flag

---

## UI/UX Design

### Main Dashboard Layout

```
┌─────────────────────────────────────────────────────────┐
│  Feature Flag Promotion Dashboard                       │
├─────────────────────────────────────────────────────────┤
│  Market: [India ▼]     Env Flow: dev → qa → uat → prod │
├─────────────────────────────────────────────────────────┤
│  [Register Flag] [Import from GB] [Compare] [Promote]   │
├─────────────────────────────────────────────────────────┤
│  Flags for India Market                                 │
│  ┌───────────────────────────────────────────────────┐  │
│  │ Key              │ GB Feature ID    │ Actions     │  │
│  ├───────────────────────────────────────────────────┤  │
│  │ enable_checkout  │ feat_checkout_01 │ [Edit]      │  │
│  │ show_banner      │ feat_banner_02   │ [Edit]      │  │
│  │ ...              │ ...              │ ...         │  │
│  └───────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

### Comparison View

```
┌─────────────────────────────────────────────────────────┐
│  Compare Environments                                   │
├─────────────────────────────────────────────────────────┤
│  Source: [qa ▼]    Target: [uat ▼]    [Compare]        │
├─────────────────────────────────────────────────────────┤
│  Results                                                │
│  ┌───────────────────────────────────────────────────┐  │
│  │ ☑ │ Flag          │ Status    │ Source │ Target  │  │
│  ├───────────────────────────────────────────────────┤  │
│  │ ☑ │ checkout      │ 🔴 Missing│ true   │ -       │  │
│  │ ☑ │ banner        │ 🟡 Diff   │ "v2"   │ "v1"    │  │
│  │ ☐ │ feature_x     │ 🟢 Sync   │ false  │ false   │  │
│  └───────────────────────────────────────────────────┘  │
│  [Promote Selected]                                     │
└─────────────────────────────────────────────────────────┘
```

### Promotion Confirmation

```
┌─────────────────────────────────────────────────────────┐
│  Confirm Promotion                                      │
├─────────────────────────────────────────────────────────┤
│  You are about to promote 2 flags from qa to uat:      │
│                                                         │
│  • enable_checkout: CREATE with value true             │
│  • show_banner: UPDATE from "v1" to "v2"               │
│                                                         │
│  This will write changes directly to GrowthBook.        │
│                                                         │
│  [Cancel]  [Confirm Promotion]                          │
└─────────────────────────────────────────────────────────┘
```

---

## Out of Scope (POC)

- **Type/schema validation** - no validation of flag value types
- **RBAC/authentication** - no user authentication or role-based access
- **Audit logging** - no audit trail of who changed what
- **Dry-run preview** - preview is computed on-demand, not persisted
- **Multiple markets** - POC focuses on India market only
- **Background jobs** - all operations are synchronous
- **Conflict resolution** - simple overwrite, no merge logic
- **Rollback** - no automated rollback on failure
- **Scheduling** - no scheduled promotions
- **Notifications** - no email/slack notifications

---

## Success Criteria

### POC Success Metrics
1. Can register 10+ flags to India market
2. Can compare flags across all environments (dev/qa/uat/prod)
3. Can promote flags with 100% accuracy (changes reflect in GrowthBook)
4. Reduces manual promotion time by 50%
5. Zero misconfiguration errors during POC testing

### User Acceptance
- Release engineers can complete promotion workflow without documentation
- QA leads can verify flag state in under 1 minute
- Market owners can see which flags belong to their market

---

## Implementation Phases

### Phase 1: Foundation (Week 1)
- Set up database with markets and flags tables
- Seed India market with env flow
- Flag registration API and UI
- Basic inventory view

### Phase 2: GrowthBook Integration (Week 1-2)
- GrowthBook API client (read/write)
- Import flags from GrowthBook
- Test integration with real GrowthBook instance

### Phase 3: Comparison (Week 2)
- Comparison API endpoint
- Read values from GrowthBook for both environments
- Comparison UI with status indicators

### Phase 4: Promotion (Week 2-3)
- Promotion API endpoint
- Write to GrowthBook (create/update)
- Confirmation dialog and results display
- End-to-end testing

### Phase 5: Polish & Testing (Week 3)
- Error handling improvements
- UI/UX refinements
- User acceptance testing
- Documentation

---

## Risks & Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| GrowthBook API rate limits | High | Implement request throttling, batch operations |
| GrowthBook API changes | Medium | Version API calls, monitor GB changelog |
| Network failures during promotion | High | Implement retry logic, clear error messages |
| Partial promotion failures | Medium | Report per-flag status, allow retry of failed flags |
| User promotes to wrong environment | High | Confirmation dialog with clear summary |

---

## Open Questions

1. What is the GrowthBook API rate limit?
2. Do we need to support rollback of promotions?
3. Should we log promotion history for audit purposes?
4. Do we need to support bulk import of flags (CSV upload)?
5. Should we validate that environment names match GrowthBook environments?

---

## Appendix

### Glossary
- **Market:** Geographic or business segment (e.g., India, US)
- **Environment:** Deployment stage (dev, qa, uat, prod)
- **Flag:** Feature flag/toggle with key and value
- **Promotion:** Copying flag value from source to target environment
- **Sync Status:** Whether flag values match across environments

### References
- GrowthBook API Documentation: https://docs.growthbook.io/api
- Existing PRD: `_bmad-output/planning-artifacts/feature-flag-promote-PRD.md` (archived)
