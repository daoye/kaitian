# KaiTian - AI Marketing Automation Engine

**Find marketing opportunities in real-time. Let AI generate replies. You approve. We publish.**

---

## What is KaiTian?

KaiTian is a lightweight backend service that powers AI-driven marketing automation. It finds relevant posts on social media, stores them efficiently, and provides simple APIs for orchestration tools like n8n to build complete marketing workflows.

**Core value:** Reduce time-to-reply from hours to seconds. Find 5+ relevant posts daily. Never miss a marketing opportunity again.

---

## Architecture: Simple & Modular

```
Your Marketing Workflow (n8n/Zapier/Custom)
        ↓
    KaiTian API
    ├─ Crawl posts
    ├─ Store data
    └─ Publish replies
        ↓
   Social Media
   (Reddit, Twitter, etc.)
```

**KaiTian does one thing well:** Crawl, store, and manage marketing posts via API.

**n8n orchestrates everything else:** Relevance scoring, AI reply generation, human review, publishing.

---

## Features

✅ **Post Discovery**
- Find posts containing your keywords on Reddit
- Crawl any URL with JavaScript rendering support
- Automatic full-text storage

✅ **Data Management**
- Query posts by status, platform, or date
- Track post lifecycle (pending → fetched → analyzed → published)
- SQLite database included

✅ **Simple API**
- 3 core endpoints: Crawl, Query, Update
- JSON request/response
- Designed for n8n HTTP nodes

✅ **Production-Ready**
- Docker & Docker Compose included
- Environment-based configuration
- Health check endpoint

---

## Quick Start

### Using Docker (Recommended)

```bash
docker-compose up -d
```

Then:
- API available at `http://localhost:8000/api/v1`
- API docs at `http://localhost:8000/docs`

### Local Setup

```bash
# Install dependencies with uv (or pip)
uv pip install -r requirements.txt

# Run
python main.py
```

---

## API Overview

### 1. Crawl Posts

```bash
POST /api/v1/crawl/url
Content-Type: application/json

{
  "url": "https://example.com",
  "store_to_db": true
}
```

**Response:**
```json
{
  "success": true,
  "url": "https://example.com",
  "content": "# Extracted content in Markdown",
  "extracted_data": {...}
}
```

### 2. List Posts

```bash
GET /api/v1/posts?status=pending&limit=10
```

**Response:**
```json
{
  "success": true,
  "total": 8,
  "posts": [
    {
      "id": "uuid",
      "title": "...",
      "content": "...",
      "status": "pending",
      "created_at": "2024-03-01T10:00:00"
    }
  ]
}
```

### 3. Update Post

```bash
PATCH /api/v1/posts/{post_id}

{
  "status": "analyzed",
  "relevance_score": 0.85,
  "generated_reply": "Great post!"
}
```

---

## Example n8n Workflow

```
Schedule (every 30 min)
  ↓
POST /api/v1/crawl/url
  ↓
For Each Post:
  ├─ Call OpenAI for relevance scoring
  ├─ PATCH /api/v1/posts/{id}
  ├─ IF relevant:
  │   ├─ Generate reply
  │   ├─ PATCH /api/v1/posts/{id}
  │   └─ Send Slack notification
  └─ Wait for human approval
  ↓
If approved:
  └─ Call social media API to reply
```

See [docs/N8N_INTEGRATION.md](docs/N8N_INTEGRATION.md) for detailed examples.

---

## Environment Configuration

Create `.env` file:

```env
# KaiTian Core
KAITIAN_API_URL=http://localhost:8000
KAITIAN_DEBUG=false

# Search Keywords (comma-separated)
SEARCH_KEYWORDS=automation,marketing,workflow

# Crawl4AI
CRAWL4AI_API_URL=http://localhost:11235

# Database
DATABASE_URL=sqlite:///./kaitian.db
```

See `.env.example` for all options.

---

## Deployment

### Docker Compose (Local Dev)

```bash
docker-compose up -d
```

Includes:
- KaiTian API service
- Crawl4AI service

### Production

1. Build: `docker build -t kaitian:latest .`
2. Deploy container with environment variables
3. Mount volume for SQLite database persistence
4. Set `KAITIAN_DEBUG=false`

See [docs/DOCKER_DEPLOYMENT.md](docs/DOCKER_DEPLOYMENT.md) for details.

---

## Key Concepts

### Post Status Lifecycle

Posts move through stages:
- `pending`: Initial crawl
- `fetched`: Retrieved from source
- `analyzed`: AI relevance scored
- `relevant`: Meets relevance threshold
- `reply_generated`: AI reply created
- `reply_approved`: Human approved
- `published`: Posted to social media
- `ignored`: Skipped by human

### Separation of Concerns

| Component | Responsibility |
|-----------|-----------------|
| **KaiTian** | Crawl posts, store data, provide API |
| **n8n** | Orchestration, AI analysis, human flow, direct API calls |

This keeps KaiTian lightweight and lets n8n do what it does best: workflow automation.

---

## FAQ

**Q: Do I need Crawl4AI?**  
A: Yes for JavaScript-rendered content. For simple HTML, you can use any HTTP client.

**Q: Can KaiTian publish directly to Reddit?**  
A: No. KaiTian stores and retrieves data. n8n orchestrates publishing via social media APIs directly.

**Q: What if n8n isn't available?**  
A: Any HTTP client can call KaiTian APIs. Use curl, Postman, or build your own orchestration layer.

**Q: How do I extend this?**  
A: Add more POST /crawl/* endpoints for other platforms. Add more PATCH /posts endpoints for additional metadata.

**Q: Is SQLite sufficient?**  
A: Yes for MVP. For 1000s of posts/day, consider PostgreSQL.

---

## Development

### Run Locally

```bash
# Install
uv pip install -r requirements.txt

# Run with debug
KAITIAN_DEBUG=true python main.py

# Test
curl http://localhost:8000/health
```

### Project Structure

```
kaitian/
├── app/
│   ├── api/routes.py       # API endpoints
│   ├── core/               # Config, database, app setup
│   ├── services/           # Business logic
│   ├── integrations/       # External service clients
│   └── models/             # Database models
├── docker-compose.yml      # Local dev setup
├── Dockerfile              # Production image
└── main.py                 # Entry point
```

---

## Cost

**$0 per month:**
- No proprietary services
- All open-source dependencies
- SQLite (no DB costs)
- Self-hosted

**Optional costs:**
- n8n (free self-hosted or paid cloud)
- OpenAI/Claude for AI (pay-per-token)
- Hosting infrastructure (your choice)

---

## Next Steps

1. **Setup:** `docker-compose up -d`
2. **Test API:** `curl http://localhost:8000/health`
3. **Build workflow:** Check n8n integration guide
4. **Monitor:** Check logs and database queries

---

## Support & Feedback

- Found a bug? Open an issue
- Have a feature request? Contribute!
- Need help? See docs/ folder for detailed guides

---

**Ready to automate?** Start with Docker Compose, build your first n8n workflow, and publish your first reply in minutes.
