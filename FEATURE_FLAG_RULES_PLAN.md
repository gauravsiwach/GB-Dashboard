# Feature Flag Rules Management Plan

This plan details the implementation of rule management capabilities for feature flags, focusing on conditional rollout based on user attributes with JSON-based rule editing.

---

## Phase 1: Backend Rule Management + Basic Frontend Display

### Objective
Set up backend rule management infrastructure and basic frontend rule display.

### Backend Tasks
1. **GrowthBook Client Enhancement** - Add `add_rule()`, `update_rule()`, `delete_rule()` methods
2. **JSON Validation Service** - Create `RuleValidator` service with structure validation
3. **Rule Management Endpoints** - POST/PUT/DELETE/GET /flags/{flag_id}/rules
4. **Schema Updates** - Add `RuleCreate`, `RuleUpdate`, `RuleResponse` schemas
5. **Get Flag Details Endpoint** - GET /flags/{flag_id}/gb-details to fetch rules from GB

### Frontend Tasks
1. **Flag Inventory Enhancement** - Add "Rules" column to flags table
2. **Rule Count Display** - Show rule count per flag
3. **Rule Summary Tooltip** - Display basic rule info on hover
4. **Basic Rule Display** - Show rules in JSON format in flag details

### Acceptance Criteria
- [ ] Can create rules via GB API
- [ ] JSON validation works before sending to GB
- [ ] Rule management endpoints working
- [ ] Frontend displays rule count in inventory
- [ ] Can view rules in JSON format

---

## Phase 2: Comparison & Promotion Enhancement + Rule UI

### Objective
Integrate rules into comparison/promotion and add rule editing UI.

### Backend Tasks
1. **Comparison Service Enhancement** - Update `_compare_flag()` to include rules
2. **Rule Comparison Logic** - Compare rule arrays between environments
3. **Promotion Service Enhancement** - Update `_promote_single_flag()` to copy rules
4. **Rule Copy Logic** - Preserve rule order and structure during promotion

### Frontend Tasks
1. **Rule Editor Component** - Create `RuleEditor` with JSON text input
2. **EditFlagModal Integration** - Add rules section to EditFlagModal
3. **Validation Feedback** - Show validation errors inline
4. **Comparison View Enhancement** - Display rules in comparison table
5. **Rule Differences** - Show rule differences between environments

### Acceptance Criteria
- [ ] Rules are compared between environments
- [ ] Rules are promoted along with flag values
- [ ] Frontend can edit rules via JSON text input
- [ ] Frontend shows validation errors
- [ ] Comparison view shows rule differences

---

## Phase 3: Search & Condition Filtering

### Objective
Add search functionality to find flags by name or condition, and filter comparisons by specific conditions.

### Backend Tasks
1. **Search Endpoint Enhancement** - Add `search` query parameter to GET /flags
2. **Name Search** - Filter flags by key/name
3. **Condition Search** - Parse rule conditions and filter by attribute/value
4. **Comparison Filtering** - Add `condition_filter` parameter to comparison endpoint
5. **Condition Parser** - Parse rule conditions for filtering

### Frontend Tasks
1. **Search Input** - Add search box to flag inventory
2. **Real-time Filtering** - Filter flags as user types
3. **Condition Filter UI** - Add condition selector to comparison view
4. **Search Results Display** - Show filtered results with highlighting

### Acceptance Criteria
- [ ] Can search flags by name/key
- [ ] Can search flags by condition (e.g., country=IN)
- [ ] Comparison can be filtered by specific condition
- [ ] Search results display in real-time
- [ ] UI shows search/filter options clearly

---

## Implementation Order
Phase 1 → Phase 2 → Phase 3

## Timeline Estimate
Total: 3-4 days
