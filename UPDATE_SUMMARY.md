# 数据库与爬虫集成更新总结

## 概述

已成功将 KaiTian 项目升级为包含完整的数据库支持和多爬虫集成能力。

## 核心更改

### 1. 数据库集成 (SQLite)

**文件修改**:
- `pyproject.toml` - 移除 `asyncpg` 和 `redis`，添加 SQLite ORM 配置
- `.env.example` - 更新为 SQLite 数据库 URL

**新增文件**:
- `app/core/database.py` - 数据库连接和会话管理
- `app/models/db.py` - SQLAlchemy ORM 模型
- `app/services/database_service.py` - 数据库操作服务

**特点**:
- ✅ 文件型数据库，无需外部依赖
- ✅ 完整的 ORM 支持
- ✅ 外键约束和事务支持
- ✅ 可轻松迁移到 PostgreSQL

### 2. Crawl4AI 集成

**文件**: `app/integrations/crawl4ai_client.py`

**功能**:
- 异步网页爬取
- JavaScript 渲染支持
- AI 驱动的数据提取
- 并发爬取多个 URL
- 自动重试和超时控制

**配置**:
```
CRAWL4AI_ENABLED=true
CRAWL4AI_TIMEOUT=30
CRAWL4AI_BROWSER_TYPE=chromium
```

**用途**: 
- 复杂网页爬取
- 动态内容提取
- 需要浏览器渲染的网站

### 3. MediaCrawler 集成

**文件**: `app/integrations/media_crawler_client.py`

**功能**:
- Reddit 爬取优化
- Twitter 爬取支持
- LinkedIn 爬取支持
- 通用 URL 爬取
- 自动重试和指数退避

**配置**:
```
MEDIA_CRAWLER_ENABLED=true
MEDIA_CRAWLER_TIMEOUT=30
MEDIA_CRAWLER_MAX_RETRIES=3
```

**用途**:
- 社交媒体爬取
- 大规模并发
- 已验证的爬虫实现

## 数据库架构

### 四个核心表

1. **Posts** - 存储爬取的社交媒体帖子
2. **SearchSessions** - 追踪搜索操作
3. **CrawlSessions** - 追踪网页爬取操作
4. **ProcessingLogs** - 操作审计日志

### 状态流转

```
创建 → 获取 → 分析 → 相关性判断 → 生成回复 → 人工审核 → 发布
pending → fetched → analyzed → relevant/irrelevant → reply_generated → reply_approved → published
```

## 新增 API 端点示例

可以基于现有框架添加以下端点:

- `POST /api/v1/crawl/url` - 爬取单个 URL
- `POST /api/v1/search/reddit` - 搜索 Reddit
- `POST /api/v1/search/twitter` - 搜索 Twitter  
- `GET /api/v1/posts` - 列表查询帖子
- `GET /api/v1/posts/{id}` - 获取帖子详情
- `PATCH /api/v1/posts/{id}` - 更新帖子状态

## 文件结构更新

```
kaitian/
├── app/
│   ├── core/
│   │   ├── app.py          ✨ 更新 - 添加数据库初始化
│   │   ├── config.py       ✨ 更新 - 添加爬虫配置
│   │   ├── database.py     🆕 新增 - 数据库连接管理
│   │   └── logging.py
│   ├── models/
│   │   ├── schemas.py      - Pydantic 请求/响应模型
│   │   └── db.py           🆕 新增 - SQLAlchemy ORM 模型
│   ├── services/
│   │   └── database_service.py  🆕 新增 - 数据库操作服务
│   ├── integrations/
│   │   ├── crawl4ai_client.py   🆕 新增 - Crawl4AI 集成
│   │   └── media_crawler_client.py  🆕 新增 - MediaCrawler 集成
│   └── ...
├── docs/
│   ├── PROJECT_STRUCTURE.md
│   └── DATABASE_CRAWLER_INTEGRATION.md  🆕 新增 - 集成指南
├── pyproject.toml          ✨ 更新 - 新增依赖
├── .env.example            ✨ 更新 - 新增配置选项
├── requirements.txt        ✨ 更新 - 同步依赖
└── ...
```

## 使用快速开始

### 1. 安装依赖

```bash
pip install -e ".[dev]"
# 或
pip install -r requirements.txt
```

### 2. 配置环境

```bash
cp .env.example .env
# 编辑 .env，填写必要的凭证
```

### 3. 初始化数据库

```bash
python main.py
# 启动时会自动创建数据库表
```

### 4. 使用爬虫

```python
# Crawl4AI 异步爬取
import asyncio
from app.integrations.crawl4ai_client import get_crawl4ai_client

async def example():
    client = get_crawl4ai_client()
    result = await client.crawl("https://example.com")
    print(result)

asyncio.run(example())

# MediaCrawler 同步爬取
from app.integrations.media_crawler_client import get_media_crawler_client

client = get_media_crawler_client()
posts = client.crawl_reddit(subreddit="python", limit=10)
print(posts)
```

### 5. 数据库操作

```python
from sqlalchemy.orm import Session
from app.services.database_service import (
    create_post, update_post_status, get_posts_by_status
)

# 创建帖子
post = create_post(
    db=db,
    source_id="reddit_123",
    title="Python Tips",
    author="user123",
    source_url="https://reddit.com/...",
    source_platform="reddit"
)

# 更新状态
update_post_status(db, post.id, "analyzed", relevance_score=0.85)

# 查询
pending_posts = get_posts_by_status(db, "pending")
```

## 技术亮点

1. **双爬虫策略**
   - Crawl4AI: 高级渲染和提取
   - MediaCrawler: 稳定的社交媒体爬取

2. **完整的数据追踪**
   - 搜索会话记录
   - 爬虫会话记录
   - 操作日志记录

3. **灵活的配置**
   - 每个爬虫可独立启用/禁用
   - 超时和重试参数可配置
   - 支持多种数据库后端

4. **生产就绪**
   - 异常处理完善
   - 日志记录详细
   - 事务支持

## 依赖关系

```
FastAPI
├── Uvicorn (服务器)
├── Pydantic (数据验证)
├── SQLAlchemy (ORM)
├── PRAW (Reddit API)
├── Crawl4AI (网页爬虫)
├── MediaCrawler (社交媒体爬虫)
└── python-json-logger (日志)
```

## 下一步

### 短期 (MVP)
1. 实现核心服务层（相关性分析、回复生成）
2. 开发 API 端点
3. 集成 AI 服务
4. 前端通知系统

### 中期
1. 性能优化（缓存、索引）
2. 监控和告警
3. 错误恢复机制
4. 数据备份策略

### 长期
1. 多用户支持
2. 数据分析报表
3. Web 管理后台
4. 迁移到 PostgreSQL

## 常见问题

**Q: 为什么选择 SQLite 而不是 PostgreSQL？**
A: MVP 阶段需要快速部署，SQLite 无需外部依赖，足以满足需求。后期可轻松迁移。

**Q: Crawl4AI 和 MediaCrawler 如何选择？**
A: Crawl4AI 用于复杂网页、需要 JS 渲染的场景；MediaCrawler 用于社交媒体、已有现成爬虫的平台。

**Q: 爬虫禁用会发生什么？**
A: 如果禁用爬虫，API 会返回"disabled"错误信息，不会崩溃。可根据业务需求灵活启用/禁用。

**Q: 如何处理爬虫超时？**
A: 配置 `TIMEOUT` 参数，使用重试机制，在数据库中记录失败原因以便调试。

## 文档参考

详见 `docs/DATABASE_CRAWLER_INTEGRATION.md` 获取:
- 详细的架构图
- 代码使用示例
- 完整的工作流程说明
- 性能优化建议
- 故障排查指南
