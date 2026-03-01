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

✅ **AI 内容生成** (LangChain)
- 使用 GPT-4/Claude 生成营销文章
- 支持多种语言和语气风格
- SEO 优化和关键词分析
- 内容质量评分

✅ **Simple API**
- Crawl, Query, Update endpoints
- Content generation endpoints (新增)
- JSON request/response
- Designed for n8n HTTP nodes

✅ **Production-Ready**
- Docker & Docker Compose included
- Environment-based configuration
- Health check endpoint
- Comprehensive logging and monitoring

---

## Quick Start

### 方式 1: 使用启动脚本（推荐）

```bash
# 启动所有服务（KaiTian + MediaCrawler + Postiz）
python start.py

# 只启动 KaiTian
python start.py --only kaitian

# 查看帮助
python start.py --help
```

**启动脚本会自动**:
- ✅ 创建 Python 虚拟环境（如果不存在）
- ✅ 克隆相关仓库（如果不存在）
- ✅ 安装所有依赖

详见：[docs/STARTUP_GUIDE.md](docs/STARTUP_GUIDE.md)

### 方式 2: 使用 Docker（推荐用于生产）

```bash
docker-compose up -d
```

Then:
- API available at `http://localhost:8000/api/v1`
- API docs at `http://localhost:8000/docs`

### 方式 3: 手动启动

```bash
# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Linux/macOS
# 或
venv\Scripts\activate     # Windows

# 安装依赖
pip install -r requirements.txt

# 运行
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

### 4. Generate Article (LangChain)

```bash
POST /api/v1/generate/article
Content-Type: application/json

{
  "topic": "AI 在营销中的应用",
  "keywords": ["AI", "营销", "自动化"],
  "tone": "professional",
  "length": "medium",
  "language": "zh",
  "target_audience": "营销团队"
}
```

**Response:**
```json
{
  "success": true,
  "content": {
    "title": "AI 如何改变现代营销...",
    "body": "# AI 如何改变现代营销\n\n...",
    "summary": "本文探讨了 AI 在营销中的应用...",
    "keywords": ["AI", "营销", "自动化"],
    "word_count": 750,
    "seo_score": 85.5
  },
  "metadata": {
    "generation_time": 3.45,
    "model": "gpt-4",
    "tokens_used": 1250
  }
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

# LangChain & AI 内容生成
# LLM 提供商选择: openai, azure, anthropic, ollama
LLM_PROVIDER=openai

# OpenAI 配置
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-3.5-turbo
OPENAI_TEMPERATURE=0.7

# Azure OpenAI 配置 (可选)
AZURE_OPENAI_KEY=your_azure_key
AZURE_OPENAI_ENDPOINT=your_azure_endpoint
AZURE_DEPLOYMENT_NAME=your_deployment

# Anthropic Claude 配置 (可选)
ANTHROPIC_API_KEY=your_anthropic_key

# 内容生成配置
CONTENT_GENERATION_MAX_TOKENS=2000
CONTENT_GENERATION_TEMPERATURE=0.7
CONTENT_GENERATION_TIMEOUT=30

# Redis 缓存 (可选)
REDIS_ENABLED=false
REDIS_URL=redis://localhost:6379
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

## 文档

### 核心文档
- **[LANGCHAIN_INTEGRATION.md](docs/LANGCHAIN_INTEGRATION.md)** - LangChain 集成详细指南，包括 API 设计、Prompt 工程、LLM 提供商配置
- **[SYSTEM_DESIGN.md](docs/SYSTEM_DESIGN.md)** - 完整的系统架构设计文档
- **[N8N_INTEGRATION.md](docs/N8N_INTEGRATION.md)** - n8n 工作流集成指南

### 启动和部署
- **[STARTUP_GUIDE.md](docs/STARTUP_GUIDE.md)** - 快速启动指南（中文）
- **[STARTUP_SCRIPTS.md](docs/STARTUP_SCRIPTS.md)** - 启动脚本技术文档
- **[DOCKER_DEPLOYMENT.md](docs/DOCKER_DEPLOYMENT.md)** - Docker 部署指南
- **[QUICK_REFERENCE.md](docs/QUICK_REFERENCE.md)** - 快速参考卡

### 其他资源
- **[PROJECT_STRUCTURE.md](docs/PROJECT_STRUCTURE.md)** - 项目结构说明
- **[DATABASE_CRAWLER_INTEGRATION.md](docs/DATABASE_CRAWLER_INTEGRATION.md)** - 数据库和爬虫集成

---

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
