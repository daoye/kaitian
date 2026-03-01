# 数据库与爬虫集成指南

## 系统架构概述

KaiTian 现在集成了以下核心组件：

```
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Application                       │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────────┐  ┌──────────────────┐                │
│  │   API Routes     │  │  Services Layer  │                │
│  └──────────────────┘  └──────────────────┘                │
│           ▼                      ▼                           │
│  ┌──────────────────────────────────────────────────────┐   │
│  │         Crawl4AI + MediaCrawler Integration          │   │
│  │  (Web Scraping & Content Extraction)                │   │
│  └──────────────────────────────────────────────────────┘   │
│           ▼                      ▼                           │
│  ┌─────────────────────────────────────────────────────┐    │
│  │        SQLite Database (ORM via SQLAlchemy)         │    │
│  │  - Posts / SearchSessions / CrawlSessions / Logs    │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

## 数据库配置

### SQLite Setup

**配置文件**: `.env`
```
DATABASE_URL=sqlite:///./kaitian.db
DATABASE_ECHO=false
```

**特点**:
- 无需外部数据库服务，文件自动创建
- 开发友好，部署简单
- 支持事务和外键约束
- MVP 阶段完全满足需求

### 数据库模型

位置: `app/models/db.py`

#### 核心表结构

**Posts 表** - 存储爬取的社交媒体帖子
```python
- id: 唯一标识
- source_id: 来源平台的帖子ID
- source_platform: reddit/twitter/linkedin/custom
- title: 帖子标题
- content: 帖子内容
- author: 作者
- status: pending/fetched/analyzed/relevant/published/failed
- relevance_score: 相关性评分 (0-1)
- generated_reply: AI生成的回复
- published_at: 发布时间
- created_at/updated_at: 时间戳
```

**SearchSessions 表** - 追踪搜索操作
```python
- id: 会话ID
- source_platform: 搜索的平台
- keywords: 搜索关键词 (JSON)
- total_posts_found: 找到的总帖数
- relevant_posts: 相关帖数
- status: started/completed/failed
- duration_seconds: 执行耗时
```

**CrawlSessions 表** - 追踪网页爬取操作
```python
- id: 会话ID
- crawler_type: crawl4ai / media_crawler
- target_url: 目标URL
- page_content: 爬取的内容
- extracted_data: 提取的数据 (JSON)
- status: pending/completed/failed
- retry_count: 重试次数
```

**ProcessingLogs 表** - 审计日志
```python
- id: 日志ID
- post_id: 关联的帖子
- operation: search/analyze/generate_reply/publish
- status: started/completed/failed
- duration_milliseconds: 操作耗时
```

## Crawl4AI 集成

位置: `app/integrations/crawl4ai_client.py`

### 功能特性

**主要优势**:
- 无头浏览器支持 (Chromium/Firefox)
- JavaScript 渲染支持
- AI 驱动的数据提取
- 内置重试机制
- 异步 API

### 使用示例

```python
from app.integrations.crawl4ai_client import get_crawl4ai_client
import asyncio

async def crawl_example():
    client = get_crawl4ai_client()
    
    # 基础爬取
    result = await client.crawl(
        url="https://example.com",
        wait_for_selector=".content"
    )
    
    # 带数据提取的爬取
    result = await client.crawl_with_extraction(
        url="https://example.com",
        extraction_fields={
            "title": "h1",
            "price": ".price",
            "description": ".desc"
        }
    )
    
    # 并发爬取多个URL
    results = await client.crawl_multiple(
        urls=["https://example1.com", "https://example2.com"]
    )
    
    # 解析内容中的关键词
    parsed = client.parse_crawled_content(
        content=result["content"],
        keywords=["python", "programming"]
    )

# 运行
asyncio.run(crawl_example())
```

### 配置参数

```
CRAWL4AI_ENABLED=true          # 启用/禁用
CRAWL4AI_TIMEOUT=30            # 超时时间(秒)
CRAWL4AI_BROWSER_TYPE=chromium # 浏览器类型
```

## MediaCrawler 集成

位置: `app/integrations/media_crawler_client.py`

### 功能特性

**主要优势**:
- 社交媒体专用优化
- 大量预构建爬虫
- 高并发支持
- 成熟稳定的库
- 广泛的平台支持

### 使用示例

```python
from app.integrations.media_crawler_client import get_media_crawler_client

def crawl_example():
    client = get_media_crawler_client()
    
    # 爬取 Reddit
    reddit_posts = client.crawl_reddit(
        subreddit="python",
        limit=10
    )
    
    # 爬取 Twitter
    tweets = client.crawl_twitter(
        keywords=["python", "programming"],
        limit=100
    )
    
    # 爬取 LinkedIn
    linkedin_posts = client.crawl_linkedin(
        keywords=["machine learning"],
        limit=50
    )
    
    # 带重试的爬取
    result = client.retry_crawl(
        client.crawl_reddit,
        subreddit="python",
        limit=10
    )

crawl_example()
```

### 配置参数

```
MEDIA_CRAWLER_ENABLED=true     # 启用/禁用
MEDIA_CRAWLER_TIMEOUT=30       # 超时时间(秒)
MEDIA_CRAWLER_MAX_RETRIES=3    # 最大重试次数
```

## 数据库服务层

位置: `app/services/database_service.py`

提供高级数据库操作接口:

```python
from app.services.database_service import (
    create_post,
    update_post_status,
    create_search_session,
    complete_search_session,
    log_operation,
    get_posts_by_status
)

# 创建帖子
post = create_post(
    db=db,
    source_id="reddit_12345",
    title="Python Tips",
    author="user123",
    source_url="https://reddit.com/...",
    content="...",
    source_platform="reddit"
)

# 更新状态
updated_post = update_post_status(
    db=db,
    post_id=post.id,
    status="analyzed",
    relevance_score=0.85,
    analyzed_at=datetime.utcnow()
)

# 创建搜索会话
session = create_search_session(
    db=db,
    keywords=["python", "programming"]
)

# 完成搜索会话
complete_search_session(
    db=db,
    session_id=session.id,
    total_posts=15,
    relevant_posts=3
)

# 记录操作
log_operation(
    db=db,
    operation="analyze",
    status="completed",
    post_id=post.id,
    duration_ms=250
)

# 获取特定状态的帖子
pending_posts = get_posts_by_status(db=db, status="pending", limit=10)
```

## 工作流程示例

### 完整的帖子处理流程

```
1. 搜索阶段
   - 创建 SearchSession
   - 使用 MediaCrawler 爬取 Reddit 帖子
   - 保存帖子到数据库 (status: fetched)

2. 分析阶段
   - 使用 Crawl4AI 提取帖子详细内容
   - 调用 AI 服务判断相关性
   - 更新帖子状态和相关性分数 (status: analyzed)
   - 过滤低相关性帖子 (status: irrelevant)

3. 回复生成阶段
   - 对相关帖子 (status: relevant) 生成回复
   - 保存生成的回复 (status: reply_generated)

4. 人工审核阶段
   - 通过 Linu 发送通知给操作者
   - 操作者审核并批准/拒绝
   - 更新状态 (status: reply_approved/rejected)

5. 发布阶段
   - 调用 Postiz API 发布回复
   - 更新发布信息 (status: published)
   - 记录发布时间和ID
```

## API 端点集成示例

### 创建爬取端点

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.integrations.crawl4ai_client import get_crawl4ai_client

router = APIRouter(prefix="/api/v1", tags=["crawl"])

@router.post("/crawl/url")
async def crawl_url(
    url: str,
    db: Session = Depends(get_db)
):
    """爬取单个URL并保存到数据库"""
    client = get_crawl4ai_client()
    
    # 创建爬虫会话
    from app.services.database_service import create_crawl_session, complete_crawl_session
    crawl_session = create_crawl_session(db, "crawl4ai", url)
    
    # 执行爬取
    result = await client.crawl(url)
    
    # 保存结果
    complete_crawl_session(
        db,
        crawl_session.id,
        page_content=result.get("content"),
        extracted_data=json.dumps(result.get("extracted_data")),
        status_code=result.get("status_code"),
        error_message=result.get("error") if not result.get("success") else None
    )
    
    return result

@router.post("/search/reddit")
async def search_reddit(
    subreddit: str,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """搜索 Reddit 帖子"""
    client = get_media_crawler_client()
    
    # 创建搜索会话
    from app.services.database_service import create_search_session, complete_search_session
    session = create_search_session(db, [subreddit])
    
    # 执行爬取
    result = client.crawl_reddit(subreddit=subreddit, limit=limit)
    
    # 保存帖子到数据库
    posts = result.get("posts", [])
    for post_data in posts:
        create_post(
            db,
            source_id=post_data.get("id"),
            title=post_data.get("title"),
            author=post_data.get("author"),
            source_url=post_data.get("url"),
            content=post_data.get("content"),
            source_platform="reddit"
        )
    
    # 完成搜索会话
    complete_search_session(
        db,
        session.id,
        total_posts=len(posts),
        error_message=result.get("error") if not result.get("success") else None
    )
    
    return result
```

## 迁移到其他数据库

如果将来需要使用 PostgreSQL，只需修改 `.env`:

```
# PostgreSQL
DATABASE_URL=postgresql://user:password@localhost:5432/kaitian
```

不需要修改代码，SQLAlchemy ORM 会自动处理差异。

## 最佳实践

1. **始终使用数据库服务层** - 不要直接操作 ORM 模型
2. **处理异常** - Crawl4AI 和 MediaCrawler 可能超时，需要错误处理
3. **记录操作** - 使用 `log_operation()` 记录所有重要操作
4. **并发控制** - 使用 `MAX_CONCURRENT_REQUESTS` 限制并发
5. **定期清理** - 定期清理旧的会话日志

## 常见问题

**Q: 如何初始化数据库表？**
```python
from app.core.database import init_db
db = next(get_db())
init_db()
```

**Q: 如何查询帖子？**
```python
from app.services.database_service import get_posts_by_status
pending = get_posts_by_status(db, "pending")
```

**Q: Crawl4AI 和 MediaCrawler 可以同时使用吗？**
是的，可以根据不同场景选择合适的爬虫。Crawl4AI 适合复杂的 JavaScript 渲染，MediaCrawler 适合社交媒体爬取。

**Q: 如何禁用某个爬虫？**
在 `.env` 中设置 `CRAWL4AI_ENABLED=false` 或 `MEDIA_CRAWLER_ENABLED=false`。
