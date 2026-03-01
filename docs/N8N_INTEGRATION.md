# n8n Integration Guide

## Architecture Overview

KaiTian is a lightweight API service that handles **data crawling and storage only**. n8n orchestrates everything else: AI analysis, human review, and publishing to external APIs.

```
┌─────────────────────────────────────────────────────────────┐
│                    n8n Workflow                              │
│  ├─ Crawl posts (via KaiTian)                               │
│  ├─ AI relevance scoring (OpenAI/Claude)                    │
│  ├─ AI reply generation (OpenAI/Claude)                     │
│  ├─ Human approval (Slack/Email)                            │
│  └─ Direct publishing (Reddit API, Twitter API, etc.)       │
└─────────────────────────────────────────────────────────────┘
        ↓
    KaiTian API
    ├─ POST /crawl/url        (Crawl any URL)
    ├─ GET /posts             (List stored posts)
    └─ PATCH /posts/{id}      (Update post status)
        ↓
    SQLite Database
```

## KaiTian's Role

KaiTian provides **3 core responsibilities**:

1. **Web Crawling** - Fetch and parse content from URLs
2. **Data Storage** - Persist posts in SQLite
3. **API Interface** - Expose simple JSON endpoints for n8n

**What KaiTian does NOT do:**
- AI analysis (n8n uses OpenAI/Claude directly)
- Publishing to social media (n8n calls APIs directly)
- User management, authentication, or UI

This simplicity makes KaiTian easy to understand, maintain, and extend.

---

## API Reference

All endpoints return JSON and are designed for n8n's HTTP Request node.

### Health Check

```
GET /health
```

**Response:**
```json
{
  "status": "ok"
}
```

---

### Crawl URL

Fetch and parse content from any webpage. Content is extracted as Markdown.

```
POST /api/v1/crawl/url
```

**Request:**
```json
{
  "url": "https://example.com",
  "wait_for": ".article",      // Optional: CSS selector to wait for
  "store_to_db": true          // Optional: Save to database
}
```

**Response:**
```json
{
  "success": true,
  "url": "https://example.com",
  "content": "# Page Title\n\nExtracted Markdown content...",
  "extracted_data": {
    "title": "Page Title",
    "description": "...",
    "images": ["..."],
    "links": ["..."]
  },
  "status_code": 200
}
```

**n8n Usage:**
```
HTTP Request node:
  Method: POST
  URL: http://localhost:8000/api/v1/crawl/url
  Body: {
    "url": "{{ $json.target_url }}",
    "store_to_db": true
  }
```

---

### List Posts

Query stored posts with optional filtering.

```
GET /api/v1/posts
```

**Query Parameters:**
- `status` - Filter by status (pending, analyzed, published, etc.)
- `platform` - Filter by platform (reddit, twitter, etc.)
- `limit` - Max results (default: 50)
- `offset` - Pagination offset (default: 0)

**Response:**
```json
{
  "success": true,
  "total": 8,
  "posts": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "source_id": "reddit_t3_abc123",
      "source_platform": "reddit",
      "title": "How to automate marketing?",
      "content": "I'm looking for ways to...",
      "author": "user123",
      "url": "https://reddit.com/r/marketing/...",
      "status": "pending",
      "relevance_score": null,
      "generated_reply": null,
      "created_at": "2024-03-01T10:00:00Z",
      "updated_at": "2024-03-01T10:00:00Z",
      "published_at": null
    }
  ]
}
```

**n8n Usage:**
```
HTTP Request node:
  Method: GET
  URL: http://localhost:8000/api/v1/posts?status=pending&limit=10
```

---

### Get Single Post

Retrieve detailed information about a specific post.

```
GET /api/v1/posts/{post_id}
```

**Response:**
```json
{
  "success": true,
  "post": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "source_id": "reddit_t3_abc123",
    "source_platform": "reddit",
    "title": "How to automate marketing?",
    "content": "I'm looking for ways to...",
    "author": "user123",
    "url": "https://reddit.com/r/marketing/...",
    "status": "pending",
    "relevance_score": null,
    "generated_reply": null,
    "created_at": "2024-03-01T10:00:00Z",
    "updated_at": "2024-03-01T10:00:00Z",
    "published_at": null
  }
}
```

---

### Update Post

Update post metadata (status, AI scores, replies, etc.).

```
PATCH /api/v1/posts/{post_id}
```

**Request:**
```json
{
  "status": "analyzed",
  "relevance_score": 0.87,
  "generated_reply": "Great question! Here's what I'd recommend...",
  "published_at": "2024-03-01T12:00:00Z"
}
```

**Response:**
```json
{
  "success": true,
  "post": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "status": "analyzed",
    "relevance_score": 0.87,
    "generated_reply": "Great question! Here's what I'd recommend...",
    "updated_at": "2024-03-01T10:05:00Z"
  }
}
```

**n8n Usage:**
```
HTTP Request node:
  Method: PATCH
  URL: http://localhost:8000/api/v1/posts/{{ $json.post_id }}
  Body: {
    "status": "reply_generated",
    "relevance_score": "{{ $json.ai_score }}",
    "generated_reply": "{{ $json.generated_reply }}"
  }
```

---

### Delete Post

Remove a post from the database.

```
DELETE /api/v1/posts/{post_id}
```

**Response:**
```json
{
  "success": true,
  "deleted_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

---

## Example n8n Workflow

### Complete Marketing Automation Loop

```
1. Schedule Trigger
   ├─ Every 30 minutes
   
2. HTTP Request: Crawl URLs
   ├─ Method: POST /api/v1/crawl/url
   ├─ Input: urls from config
   └─ Output: crawled content + stored post IDs
   
3. For Each Post (Loop)
   ├─ Get Post Details
   │  ├─ GET /api/v1/posts/{post_id}
   │  └─ Store in $json.post
   │
   ├─ Call OpenAI for Relevance
   │  ├─ Input: post.title + post.content
   │  └─ Output: score, reasoning
   │
   ├─ Update Post Status
   │  ├─ PATCH /api/v1/posts/{post_id}
   │  ├─ Body: { status: "analyzed", relevance_score: score }
   │  └─ Output: updated post
   │
   ├─ IF score > 0.7
   │  ├─ Call OpenAI to Generate Reply
   │  │  ├─ Input: post content
   │  │  └─ Output: reply_text
   │  │
   │  ├─ Update Post with Reply
   │  │  ├─ PATCH /api/v1/posts/{post_id}
   │  │  ├─ Body: { status: "reply_generated", generated_reply: reply_text }
   │  │  └─ Output: updated post
   │  │
   │  └─ Send Slack Notification
   │     ├─ Channel: #approvals
   │     ├─ Message: Post title, author, reply
   │     └─ Actions: Approve / Reject buttons
   │
   └─ ELSE (score <= 0.7)
      └─ Update Post as Ignored
         └─ PATCH /api/v1/posts/{post_id}
            └─ Body: { status: "ignored" }

4. Wait for Slack Approval
   ├─ Listen for button click
   └─ Store: approved = true/false

5. IF Approved
   ├─ Call Reddit API Directly (n8n Reddit node)
   │  ├─ subreddit: post.platform_details.subreddit
   │  ├─ parent_id: post.source_id
   │  ├─ text: post.generated_reply
   │  └─ Output: comment_id
   │
   └─ Update Post as Published
      ├─ PATCH /api/v1/posts/{post_id}
      └─ Body: { status: "published", published_at: now() }
```

---

## Environment Setup

### Docker Compose (Easiest)

```bash
docker-compose up -d
```

KaiTian will be available at:
- **API:** `http://localhost:8000/api/v1`
- **Docs:** `http://localhost:8000/docs` (Interactive API browser)

### n8n Configuration

In your n8n workflow, use these base URLs:

**Local Docker:**
```
http://kaitian:8000/api/v1
(KaiTian container hostname)
```

**Network:**
```
http://<kaitian-ip>:8000/api/v1
(Replace with actual IP/hostname)
```

**Test connection:**
```bash
curl http://localhost:8000/health
```

---

## Post Status Lifecycle

Track workflow progress using status values:

| Status | Meaning |
|--------|---------|
| `pending` | Just crawled, awaiting analysis |
| `fetched` | Retrieved from source platform |
| `analyzed` | AI relevance score assigned |
| `relevant` | Meets threshold, ready for reply |
| `reply_generated` | AI reply created |
| `reply_approved` | Human approved reply |
| `published` | Successfully posted to platform |
| `ignored` | Marked as not relevant |

**Update via n8n:**
```
PATCH /api/v1/posts/{post_id}
{
  "status": "reply_approved"
}
```

---

## Error Handling

All errors follow this format:

```json
{
  "success": false,
  "error": "Detailed error message"
}
```

**Common scenarios:**

```
POST /api/v1/crawl/url with bad URL
→ { "success": false, "error": "Invalid URL" }

GET /api/v1/posts/nonexistent-id
→ { "success": false, "error": "Post not found" }

PATCH /api/v1/posts/{id} with invalid status
→ { "success": false, "error": "Invalid status value" }
```

**n8n Error Handling:**
```
HTTP Request node
  ↓
Set: IF response.success = false
  ├─ Log error
  ├─ Send alert email
  └─ Mark workflow as failed
ELSE
  └─ Continue processing
```

---

## Performance Tips

### Rate Limiting

If you're crawling many URLs, add delays:

```
For Each URL:
  1. HTTP Request: Crawl
  2. Wait node: 1 second
```

This prevents overwhelming Crawl4AI.

### Batch Processing

For large post batches, use n8n's Batch node:

```
Get all pending posts
  ↓
Batch: Process 5 at a time
  ├─ AI analysis
  ├─ Update post
  └─ Wait 1 second between batches
```

### Database Cleanup

Periodically delete old posts:

```
Schedule: Weekly
  ↓
HTTP Request: GET /api/v1/posts?published=true&limit=1000&before=30days_ago
  ↓
For Each Post: DELETE /api/v1/posts/{post_id}
```

---

## Extending KaiTian

### Add a New Crawl Endpoint

To support a new platform, create an endpoint in `app/api/routes.py`:

```python
@router.post("/crawl/custom-platform")
async def crawl_custom_platform(request: CustomPlatformRequest):
    # Fetch from custom platform
    # Store posts
    return { "success": True, "posts": [...] }
```

Then call from n8n:
```
POST http://localhost:8000/api/v1/crawl/custom-platform
```

### Add Custom Post Metadata

Extend the Post model in `app/models/db.py` with new fields, then update posts:

```
PATCH /api/v1/posts/{id}
{
  "custom_field": "custom_value"
}
```

---

## Troubleshooting

**Q: n8n can't reach KaiTian**
A: Check firewall, verify container is running, test with `curl http://localhost:8000/health`

**Q: Crawl times out**
A: Increase timeout in Crawl4AI config, or use `wait_for` selector for specific element

**Q: Posts aren't being saved**
A: Pass `store_to_db=true` in crawl request, check database permissions

**Q: API returns 404**
A: Check endpoint path, verify HTTP method (POST vs GET), test with swagger docs

---

## Summary

**KaiTian's role:**
- Crawl content via simple API
- Store posts in database
- Provide query/update endpoints

**n8n's role:**
- Call KaiTian to crawl
- AI analysis (OpenAI/Claude)
- Human approval flow
- Call social media APIs directly

This separation makes both systems simpler and more flexible.

**Next step:** Check your n8n workflow and start integrating KaiTian endpoints!
