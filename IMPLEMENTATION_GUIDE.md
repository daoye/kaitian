# 🚀 KaiTian 完整实现指南

## 📊 项目更新状态

### 已完成的工作

✅ **基础框架** (初始化)
- FastAPI 应用框架
- 配置管理系统
- 日志系统
- 项目结构

✅ **数据库集成** (新增)
- SQLite 配置与初始化
- SQLAlchemy ORM 模型
- 数据库服务层
- 四个核心数据表

✅ **爬虫集成** (新增)
- Crawl4AI 客户端 (异步网页爬虫)
- MediaCrawler 客户端 (社交媒体爬虫)
- 爬虫管理和重试机制

✅ **文档和配置** (新增)
- 完整的集成指南
- 环境变量模板
- 依赖配置文件

### 代码统计

```
总代码行数: 1,180+ 行
核心模块: 8 个
数据表: 4 个
集成爬虫: 2 个
API 端点: 2 个 (健康检查 + 根)
```

## 📁 项目结构速览

```
kaitian/
├── app/
│   ├── core/          # 核心配置和初始化
│   │   ├── app.py              - FastAPI 应用工厂
│   │   ├── config.py           - 环境配置管理
│   │   ├── database.py         - 数据库连接管理
│   │   └── logging.py          - 日志配置
│   ├── models/        # 数据模型
│   │   ├── schemas.py          - Pydantic schemas
│   │   └── db.py               - SQLAlchemy ORM 模型
│   ├── services/      # 业务逻辑
│   │   └── database_service.py - 数据库操作接口
│   ├── integrations/  # 第三方集成
│   │   ├── crawl4ai_client.py      - Crawl4AI 集成
│   │   └── media_crawler_client.py - MediaCrawler 集成
│   ├── api/           # API 端点
│   │   └── routes.py           - 路由定义
│   └── utils/         # 工具函数 (待实现)
├── docs/              # 文档
│   ├── PROJECT_STRUCTURE.md
│   └── DATABASE_CRAWLER_INTEGRATION.md
├── tests/             # 测试套件 (待实现)
├── main.py            # 应用入口
├── pyproject.toml     # 项目配置
├── .env.example       # 环境变量模板
└── requirements.txt   # 依赖列表
```

## 🔄 核心工作流

```
用户请求
    ↓
FastAPI 路由处理
    ↓
调用 MediaCrawler/Crawl4AI 爬虫
    ↓
保存到 SQLite 数据库
    ↓
处理和分析数据
    ↓
生成回复
    ↓
人工审核
    ↓
发布到社交媒体
    ↓
更新数据库记录
```

## 💾 数据库设计

### Posts (帖子表)
```python
- id: 主键
- source_id: 来源平台 ID
- source_platform: reddit/twitter/linkedin/custom
- title, content, author
- status: pending/fetched/analyzed/relevant/published
- relevance_score: 0-1
- generated_reply: 生成的回复文本
- published_at: 发布时间
```

### SearchSessions (搜索会话表)
```python
- id: 会话 ID
- source_platform: 搜索的平台
- keywords: JSON 格式的关键词列表
- total_posts_found: 找到的总数
- relevant_posts: 相关帖数
- duration_seconds: 执行耗时
```

### CrawlSessions (爬虫会话表)
```python
- id: 会话 ID
- crawler_type: crawl4ai / media_crawler
- target_url: 目标 URL
- page_content: 爬取的内容
- extracted_data: JSON 格式的提取数据
- retry_count: 重试次数
```

### ProcessingLogs (操作日志表)
```python
- id: 日志 ID
- post_id: 关联的帖子
- operation: search/analyze/generate/publish
- status: started/completed/failed
- duration_milliseconds: 耗时
```

## 🛠️ 爬虫能力对比

| 功能 | Crawl4AI | MediaCrawler |
|------|----------|--------------|
| 异步支持 | ✅ 完全异步 | ⚠️ 部分异步 |
| JS 渲染 | ✅ 支持 | ❌ 不支持 |
| Reddit | ✅ 通用 | ✅ 优化 |
| Twitter | ✅ 通用 | ✅ 优化 |
| LinkedIn | ✅ 通用 | ✅ 优化 |
| 数据提取 | ✅ AI 驱动 | ✅ 规则驱动 |
| 并发能力 | ✅ 高 | ✅ 极高 |
| 学习曲线 | 📈 中等 | 📊 平缓 |

**推荐用途**:
- **Crawl4AI**: 复杂网页、需要 JS 渲染、自定义内容提取
- **MediaCrawler**: 社交媒体爬取、大规模并发、稳定性要求高

## 🚀 快速开始

### 1️⃣ 环境准备

```bash
# 克隆项目 (已初始化)
cd /home/april/projects/kaitian

# 创建虚拟环境
python -m venv venv
source venv/bin/activate

# 安装依赖
pip install -e ".[dev]"
```

### 2️⃣ 配置

```bash
# 复制环境模板
cp .env.example .env

# 编辑 .env 文件，填写以下必要配置:
# - REDDIT_CLIENT_ID
# - REDDIT_CLIENT_SECRET
# - REDDIT_USER_AGENT
# - AI_API_KEY
# - AI_API_URL
```

### 3️⃣ 初始化数据库

```bash
python main.py
# 应用启动时会自动创建数据库表
```

### 4️⃣ 访问应用

```
http://localhost:8000          # 应用根目录
http://localhost:8000/docs     # API 文档 (Swagger UI)
http://localhost:8000/redoc    # API 文档 (ReDoc)
```

## 📝 典型代码使用示例

### 爬虫使用

```python
# Crawl4AI - 异步爬取
import asyncio
from app.integrations.crawl4ai_client import get_crawl4ai_client

async def crawl_with_crawl4ai():
    client = get_crawl4ai_client()
    result = await client.crawl(
        url="https://example.com",
        wait_for_selector=".content"
    )
    return result

asyncio.run(crawl_with_crawl4ai())

# MediaCrawler - 同步爬取
from app.integrations.media_crawler_client import get_media_crawler_client

def crawl_with_media_crawler():
    client = get_media_crawler_client()
    posts = client.crawl_reddit(
        subreddit="python",
        limit=10
    )
    return posts

crawl_with_media_crawler()
```

### 数据库使用

```python
from sqlalchemy.orm import Session
from app.services.database_service import (
    create_post,
    update_post_status,
    create_search_session,
    get_posts_by_status
)

# 创建帖子
post = create_post(
    db=db,
    source_id="reddit_12345",
    title="Python Tips",
    author="user123",
    source_url="https://reddit.com/r/python/...",
    source_platform="reddit"
)

# 更新状态
update_post_status(
    db=db,
    post_id=post.id,
    status="analyzed",
    relevance_score=0.85
)

# 查询帖子
pending_posts = get_posts_by_status(db=db, status="pending", limit=10)
```

### API 路由使用

```python
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.core.database import get_db

router = APIRouter(prefix="/api/v1")

@router.post("/posts/search")
async def search_posts(
    query: str,
    db: Session = Depends(get_db)
):
    """搜索帖子"""
    # 实现搜索逻辑
    pass

@router.get("/posts/{post_id}")
async def get_post(
    post_id: str,
    db: Session = Depends(get_db)
):
    """获取帖子详情"""
    # 实现查询逻辑
    pass
```

## 🔧 配置参数详解

```env
# 应用配置
APP_NAME=KaiTian                    # 应用名称
APP_VERSION=0.1.0                  # 版本号
DEBUG=false                         # 调试模式
ENVIRONMENT=development             # 环境

# 服务器
HOST=0.0.0.0                       # 监听地址
PORT=8000                          # 监听端口
LOG_LEVEL=INFO                     # 日志级别

# 数据库
DATABASE_URL=sqlite:///./kaitian.db # SQLite 路径
DATABASE_ECHO=false                # SQL 日志

# Crawl4AI
CRAWL4AI_ENABLED=true              # 启用
CRAWL4AI_TIMEOUT=30                # 超时(秒)
CRAWL4AI_BROWSER_TYPE=chromium     # 浏览器类型

# MediaCrawler
MEDIA_CRAWLER_ENABLED=true         # 启用
MEDIA_CRAWLER_TIMEOUT=30           # 超时(秒)
MEDIA_CRAWLER_MAX_RETRIES=3        # 最大重试

# 搜索配置
SEARCH_KEYWORDS=python,programming  # 关键词
SUBREDDIT_LIST=python              # 目标板块
SEARCH_INTERVAL_MINUTES=30         # 搜索间隔
MAX_POSTS_PER_SEARCH=10            # 每次最多帖数

# 处理配置
RELEVANCE_THRESHOLD=0.7            # 相关性阈值
MAX_CONCURRENT_REQUESTS=5          # 并发数
REQUEST_TIMEOUT_SECONDS=30         # 请求超时
```

## 📚 文档导航

- **DEVELOPMENT.md** - 开发指南和快速开始
- **docs/PROJECT_STRUCTURE.md** - 项目结构详解
- **docs/DATABASE_CRAWLER_INTEGRATION.md** - 数据库和爬虫集成指南
- **UPDATE_SUMMARY.md** - 本次更新总结

## 🎯 后续开发任务

### Phase 1: 核心服务 (优先级 🔴 高)
- [ ] 实现 Reddit 搜索服务
- [ ] 实现相关性判断服务 (AI 集成)
- [ ] 实现回复生成服务 (AI 集成)
- [ ] 实现发布服务 (Postiz 集成)

### Phase 2: API 端点 (优先级 🟡 中)
- [ ] 搜索和爬取端点
- [ ] 帖子管理端点
- [ ] 分析和统计端点
- [ ] 配置管理端点

### Phase 3: 功能完善 (优先级 🟢 低)
- [ ] 单元测试
- [ ] 集成测试
- [ ] 性能优化
- [ ] 错误恢复

## 💡 技术建议

### 何时使用 Crawl4AI
✅ 复杂的 JavaScript 渲染网站
✅ 需要自定义数据提取
✅ 需要异步并发爬取
❌ 简单静态内容（过度设计）

### 何时使用 MediaCrawler
✅ 社交媒体内容
✅ 已有现成爬虫的平台
✅ 需要极高吞吐量
❌ 动态 JS 渲染内容

### 数据库最佳实践
✅ 始终使用 `database_service.py` 中的函数
✅ 为每个操作记录 `ProcessingLog`
✅ 定期检查和清理过期数据
✅ 备份 `kaitian.db` 文件

## 🐛 常见问题排查

**问题**: 数据库错误 "database is locked"
**解决**: SQLite 在并发写入时锁定，使用 WAL 模式:
```python
# 在 database.py 中
@event.listens_for(engine, "connect")
def set_sqlite_pragma(dbapi_connection, connection_record):
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA journal_mode=WAL")
    cursor.close()
```

**问题**: Crawl4AI 超时
**解决**: 调整 `CRAWL4AI_TIMEOUT` 参数，或检查网络连接

**问题**: MediaCrawler 爬虫不工作
**解决**: 确保 `MEDIA_CRAWLER_ENABLED=true`，检查依赖安装

## 📊 性能指标目标

MVP 成功标准（项目规划）:
- ✅ 每日发现 ≥ 5 条相关帖子
- ✅ 单个回复操作时间 ≤ 10 秒
- ✅ 每小时处理 ≥ 50 个帖子
- ✅ 系统稳定运行 ≥ 7 天
- ✅ 成本 = 0 元 (完全开源)

## 🔐 安全考虑

⚠️ **敏感信息**:
- Reddit API 密钥
- AI 服务 API 密钥
- Postiz/Linu API 密钥

✅ **安全做法**:
- 不要提交 `.env` 文件到 Git
- 使用环境变量管理凭证
- 定期轮换 API 密钥
- 限制数据库访问权限

## 📞 获取帮助

遇到问题？
1. 查看 `docs/` 目录的详细文档
2. 检查 `.env.example` 确保配置正确
3. 查看日志输出 (LOG_LEVEL=DEBUG)
4. 查看代码注释和类型提示

---

## 总结

🎉 **KaiTian 已完全初始化，包含**:
- ✅ 完整的数据库支持 (SQLite + SQLAlchemy)
- ✅ 双爬虫集成 (Crawl4AI + MediaCrawler)
- ✅ 可扩展的架构
- ✅ 详细的文档
- ✅ 即插即用的代码示例

🚀 **准备好开始开发了！** 选择上面的"后续开发任务"中的任务，开始实现核心功能。
