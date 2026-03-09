# Tieba Search Fix - MediaCrawler Integration

## TL;DR

> **Quick Summary**: Fix the broken MediaCrawler API integration in KaiTian that prevents Tieba keyword search from working. The integration has wrong API parameters and missing result retrieval logic.
> 
> **Deliverables**:
> - Fixed API parameters in social_media_crawler.py (crawler_type, keywords)
> - Implemented proper task ID handling and result retrieval
> - Working /api/v1/crawler/search endpoint with crawler_platform=tieba
> 
> **Estimated Effort**: Short
> **Parallel Execution**: NO - sequential tasks
> **Critical Path**: Fix params → Fix task ID → Implement retrieval → Test

---

## Context

### Original Request
User reported: "贴吧帖子搜索的功能存在一些问题，我没办法根据关键字获取搜索结果，帮我修复此问题。"
(There's a problem with the Tieba post search function - I cannot get search results by keyword. Please fix it.)

### Interview Summary
**Key Discussions**:
- User wants to search Tieba posts by keyword
- Current /api/v1/crawler/search endpoint with crawler_platform=tieba doesn't return results
- User chose to fix MediaCrawler integration (vs. enabling direct Tieba API)

**Research Findings**:
- MediaCrawler API schema expects: `crawler_type`, `keywords`, `platform`, `login_type`
- KaiTian sends wrong params: `type`, `keyword`, `config` (invalid)
- MediaCrawler returns `{"status": "ok"}` but KaiTian expects `task_id`
- Data stored in `packages/MediaCrawler/data/` as JSON files

### Metis Review
**Identified Gaps** (addressed):
- Need to understand MediaCrawler's data file naming convention to retrieve results
- Need to handle login_type properly (qrcode vs cookie)
- Need to poll status until completion, then read data files

---

## Work Objectives

### Core Objective
Fix Tieba keyword search so users can get search results via the API.

### Concrete Deliverables
- Fixed `app/services/social_media_crawler.py` - correct API parameters
- Implemented task tracking and result retrieval from MediaCrawler data files
- Working API: `POST /api/v1/crawler/search?crawler_platform=tieba&keyword=xxx`

### Definition of Done
- [ ] API call with crawler_platform=tieba returns posts
- [ ] Results contain post_id, title, author, content, url
- [ ] Error handling for failed crawler start

### Must Have
- Correct MediaCrawler API parameters
- Proper polling for crawler completion
- Result retrieval from MediaCrawler data directory

### Must NOT Have (Guardrails)
- Don't modify other platforms (xhs, dy, bili, zhihu)
- Don't modify the crawl4ai integration
- Don't enable commented-out Tieba endpoints in routes.py

---

## Verification Strategy (MANDATORY)

> **ZERO HUMAN INTERVENTION** — ALL verification is agent-executed.
> 
### Test Decision
- **Infrastructure exists**: NO (no unit tests for this service)
- **Automated tests**: None (integration test via API call)
- **Framework**: N/A

### QA Policy
Every task MUST include agent-executed QA scenarios.

**Verification Method**: Use Bash (curl) to call the API endpoint
- Start KaiTian server
- Call `POST /api/v1/crawler/search?crawler_platform=tieba&keyword=test&max_results=5`
- Verify response contains posts array with expected fields

---

## Execution Strategy

### Parallel Execution Waves
Single wave - tasks are sequential:
1. Fix API parameters
2. Fix task ID handling  
3. Implement result retrieval
4. Test end-to-end

---

## TODOs

---

- [ ] 1. Fix MediaCrawler API parameters in social_media_crawler.py

  **What to do**:
  - Locate the `crawl_with_mediacrawler` method in `app/services/social_media_crawler.py`
  - Fix the payload at lines 209-218:
    - Change `"type": "search"` to `"crawler_type": "search"`
    - Change `"keyword": keyword` to `"keywords": keyword`
    - Remove invalid `"config": {"max_results": max_results}`
  - Add `"login_type": "qrcode"` to match MediaCrawler schema

  **Must NOT do**:
  - Don't modify crawl4ai related code
  - Don't change other platform handling

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Simple parameter fix in existing code
  - **Skills**: []
  - **Skills Evaluated but Omitted**:
    - `playwright`: Not needed for API parameter fix

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential
  - **Blocks**: Task 2
  - **Blocked By**: None (can start immediately)

  **References**:
  - `packages/MediaCrawler/api/schemas/crawler.py:59-73` - MediaCrawler expected payload schema
  - `app/services/social_media_crawler.py:209-218` - Current (broken) payload

  **Acceptance Criteria**:
  - [ ] Code compiles without syntax errors
  - [ ] Payload now has correct field names: crawler_type, keywords

  **QA Scenarios**:

  Scenario: Verify API parameter fix
    Tool: Bash
    Preconditions: File modified
    Steps:
      1. Read the modified function to verify field names
      2. Check payload has "crawler_type" not "type"
      3. Check payload has "keywords" not "keyword"
    Expected Result: Correct field names present in payload construction
    Evidence: N/A (code review)

---

- [ ] 2. Fix task ID handling in crawl_with_mediacrawler

  **What to do**:
  - The MediaCrawler `/api/crawler/start` returns `{"status": "ok", "message": "..."}` without task_id
  - Modify the code to handle this correctly:
    - Check for `"status": "ok"` instead of `"task_id"`
    - Use `/api/crawler/status` endpoint to poll for completion
  - After successful start, poll status until "idle" or "error"

  **Must NOT do**:
  - Don't break the error handling flow

  **Recommended Agent Profile**:
  - **Category**: `quick`
    - Reason: Simple logic change to handle different response format
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential  
  - **Blocks**: Task 3
  - **Blocked By**: Task 1

  **References**:
  - `packages/MediaCrawler/api/routers/crawler.py:53-56` - Status endpoint
  - `packages/MediaCrawler/api/schemas/crawler.py:75-81` - Status response schema

  **Acceptance Criteria**:
  - [ ] Code handles "status": "ok" response
  - [ ] Polls /api/crawler/status for completion

  **QA Scenarios**:

  Scenario: Verify status polling logic
    Tool: Bash
    Preconditions: Code modified
    Steps:
      1. Read the modified method
      2. Verify it checks for "status": "ok" 
      3. Verify it polls /api/crawler/status endpoint
    Expected Result: Proper status handling implemented
    Evidence: N/A (code review)

---

- [ ] 3. Implement result retrieval from MediaCrawler data files

  **What to do**:
  - MediaCrawler saves data to `packages/MediaCrawler/data/` as JSON files
  - After crawler completes, read the latest JSON file for the platform
  - Parse the JSON and convert to standard post format
  - The data structure in MediaCrawler follows their model (see m_baidu_tieba.py)

  **Must NOT do**:
  - Don't break existing functionality for other platforms

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Need to understand MediaCrawler data format and parse correctly
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential
  - **Blocks**: Task 4
  - **Blocked By**: Task 2

  **References**:
  - `packages/MediaCrawler/data/` - Where MediaCrawler saves data (verify format)
  - `packages/MediaCrawler/model/m_baidu_tieba.py` - Tieba data model

  **Acceptance Criteria**:
  - [ ] After crawler completes, reads data from MediaCrawler data directory
  - [ ] Returns parsed posts in standard format

  **QA Scenarios**:

  Scenario: Verify data retrieval logic
    Tool: Bash
    Preconditions: Code modified
    Steps:
      1. Read the new result retrieval code
      2. Verify it looks for JSON files in MediaCrawler data directory
      3. Verify it parses and returns posts
    Expected Result: Data retrieval logic implemented
    Evidence: N/A (code review)

---

- [ ] 4. End-to-end test of Tieba search API

  **What to do**:
  - Start KaiTian server
  - Call: `POST /api/v1/crawler/search?crawler_platform=tieba&keyword=test&max_results=5`
  - Verify response contains posts array with expected fields
  - Verify no errors in response

  **Must NOT do**:
  - Don't test with real login (may require QR code scan)

  **Recommended Agent Profile**:
  - **Category**: `unspecified-high`
    - Reason: Integration test requires running services
  - **Skills**: []

  **Parallelization**:
  - **Can Run In Parallel**: NO
  - **Parallel Group**: Sequential
  - **Blocks**: None
  - **Blocked By**: Tasks 1, 2, 3

  **References**:
  - `app/api/routes.py:145-186` - The search endpoint implementation
  - `app/services/social_media_crawler.py` - The fixed service

  **Acceptance Criteria**:
  - [ ] API returns success: true
  - [ ] Response contains posts array
  - [ ] Each post has: post_id, title, author, content, url

  **QA Scenarios**:

  Scenario: Test Tieba search API returns results
    Tool: Bash
    Preconditions: KaiTian server running
    Steps:
      1. Start KaiTian: python start.py --only kaitian
      2. Wait for server to start
      3. Call: curl -X POST "http://localhost:8000/api/v1/crawler/search?crawler_platform=tieba&keyword=python&max_results=5"
      4. Parse JSON response
    Expected Result: {"success": true, "total_results": N, "posts": [...]}
    Failure Indicators: {"success": false, "error": "..."}
    Evidence: .sisyphus/evidence/task-4-tieba-search.json

  Scenario: Verify post structure
    Tool: Bash
    Preconditions: API returned results
    Steps:
      1. Read the evidence file
      2. Check first post has required fields
    Expected Result: Each post has post_id, title, author, content, url
    Evidence: .sisyphus/evidence/task-4-post-structure.json

---

## Final Verification Wave

> After ALL implementation tasks

- [ ] F1. **API Integration Test** — Test the fixed endpoint with real Tieba search
  - Start KaiTian server
  - Call API with tieba keyword
  - Verify posts are returned

---

## Commit Strategy

- **1**: `fix(tieba): correct MediaCrawler API parameters and result retrieval` — social_media_crawler.py

---

## Success Criteria

### Verification Commands
```bash
# Start KaiTian
python start.py --only kaitian

# Test Tieba search
curl -X POST "http://localhost:8000/api/v1/crawler/search?crawler_platform=tieba&keyword=python&max_results=5"

# Expected: {"success": true, "total_results": N, "posts": [...]}
```

### Final Checklist
- [ ] API returns success=true with posts array
- [ ] Posts contain: post_id, title, author, content, url
- [ ] No errors in KaiTian logs
