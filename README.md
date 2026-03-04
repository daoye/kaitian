# KaiTian - N8N 能力扩展

## 项目定位

KaiTian 是一个为 n8n 工作流提供能力的后端服务，**专注提供底层能力，不包含业务逻辑**。

**核心原则：**
- 纯粹的能力提供者
- 数据存储和业务管理由 n8n 负责
- 提供标准化 API 供 n8n 调用
- 无数据库设计，基于文件系统状态持久化

## 项目结构 (Monorepo)

```
kaitian/
├── app/                          # KaiTian 主服务
│   ├── api/                      # API 路由
│   ├── core/                     # 核心配置
│   ├── models/                   # 数据模型
│   └── services/                 # 业务服务
│       ├── xiaohongshu_publisher.py  # 小红书发布 (Playwright)
│       ├── publisher_service.py      # 发布服务
│       └── ...
├── packages/
│   └── MediaCrawler/             # 社交媒体爬虫 (git submodule)
│       ├── api/                  # WebUI API
│       ├── media_platform/       # 平台爬虫实现
│       └── config/               # 配置文件
├── data/                         # 数据存储
├── logs/                         # 日志文件
├── start.py                      # 服务管理脚本
└── pyproject.toml                # 项目配置
```

## 快速开始

### 启动所有服务

```bash
# 初始化子模块并启动所有服务
python start.py

# 仅启动 KaiTian
python start.py --only kaitian

# 仅启动 MediaCrawler
python start.py --only mediacrawler

# 停止所有服务
python start.py stop

# 查看服务状态
python start.py status
```

### 安装依赖

```bash
# 安装所有服务依赖
python start.py --install-deps

# 或手动安装
# KaiTian
uv sync

# MediaCrawler
cd packages/MediaCrawler
uv sync
uv run playwright install
```

## 提供的能力

### 1. 爬虫能力

**API 端点：**
- `POST /api/v1/crawler/url` - 爬取任意 URL 内容
- `POST /api/v1/crawler/search` - 搜索社交媒体内容
- `POST /api/v1/crawler/get` - 爬取帖子详细内容

**支持平台：**
- Reddit、Twitter、LinkedIn（通过 crawl4ai）
- 小红书、抖音、快手、B站、微博、贴吧、知乎（通过 MediaCrawler）

**状态持久化：**
- 搜索会话状态保存到 `data/sessions/`
- 爬取检查点保存到 `data/sessions/checkpoints/`
- 支持崩溃恢复和重试

### 2. AI 能力

**API 端点：**
- `POST /api/v1/ai/evaluate/relevance` - 评判内容相关性
- `POST /api/v1/ai/generate/reply` - 生成回复
- `POST /api/v1/ai/generate/article` - 生成营销文章
- `POST /api/v1/ai/generate/articles/batch` - 批量生成文章
- `POST /api/v1/ai/generate/optimize` - SEO 优化
- `GET /api/v1/ai/status` - 查看 AI 服务状态

**特性：**
- 支持中英文
- 可配置语气、平台适配

### 3. 发布能力

**API 端点：**
- `POST /api/v1/publisher/post` - 发布帖子
- `POST /api/v1/publisher/comment` - 发布评论/回复

**支持平台：**
- Reddit（使用 praw）
- Twitter/X（使用 tweepy）
- LinkedIn（使用官方 API）
- **Xiaohongshu/小红书**（使用 Playwright 浏览器自动化）

**Xiaohongshu 发布配置：**
```env
# Xiaohongshu (小红书) - Playwright 浏览器自动化
XIAOHONGSHU_HEADLESS=true           # 首次登录建议设为 false
XIAOHONGSHU_COOKIE_PATH=            # 可选，默认 data/platform_sessions/
XIAOHONGSHU_SLOW_MO=100             # 操作间隔毫秒
XIAOHONGSHU_LOGIN_TIMEOUT=120       # 登录超时秒数
```

**发布配置：**
```env
# Reddit
REDDIT_CLIENT_ID=your_client_id
REDDIT_CLIENT_SECRET=your_client_secret
REDDIT_USER_AGENT=KaiTian/0.1.0
REDDIT_USERNAME=your_username
REDDIT_PASSWORD=your_password

# Twitter/X
TWITTER_CONSUMER_KEY=your_consumer_key
TWITTER_CONSUMER_SECRET=your_consumer_secret
TWITTER_ACCESS_TOKEN=your_access_token
TWITTER_ACCESS_TOKEN_SECRET=your_access_token_secret

# LinkedIn
LINKEDIN_CLIENT_ID=your_client_id
LINKEDIN_CLIENT_SECRET=your_client_secret
LINKEDIN_ACCESS_TOKEN=your_access_token
LINKEDIN_PERSON_URN=your_person_urn
```

### 4. 文件存储结构

```
data/
├── sessions/                          # 搜索会话状态
│   ├── {session_id}.json              # 会话数据
│   └── checkpoints/                   # 爬取检查点
│       ├── {session_id}_{platform}_page_1.json
│       └── {session_id}_{platform}_batch_{timestamp}.json
└── failed/                            # 失败项目
    ├── {session_id}_failed.json       # 失败项目列表
    └── platform_sessions/             # 平台登录状态
        ├── reddit_session.json
        ├── twitter_session.json
        └── xhs_session.json
```

## N8N 集成示例

### 典型工作流

```
1. n8n 定时触发
   ↓
2. n8n 从数据库/配置读取关键词
   ↓
3. n8n 调用 POST /api/v1/crawler/search
   ↓
4. n8n 遍历返回的帖子列表
   ↓
5. n8n 调用 POST /api/v1/crawler/get 获取帖子详情
   ↓
6. n8n 调用 POST /api/v1/ai/evaluate/relevance
   ↓
7. n8n 判断评分是否 > 0.7
   ↓
8. n8n 调用 POST /api/v1/ai/generate/reply
   ↓
9. n8n 保存到数据库
   ↓
10. n8n 推送通知（通过 Linu 或其他通知服务）
    ↓
11. n8n 等待审批回调
    ↓
12. n8n 调用 POST /api/v1/publisher/post 或 /publisher/comment 发布
```

### 数据管理

**由 n8n 负责：**
- 关键词存储（PostgreSQL/MySQL/SQLite）
- 帖子数据存储
- 回复历史记录
- 审核状态管理
- Linu 推送

**KaiTian 负责：**
- 提供爬取能力
- 提供 AI 能力
- 提供发布能力
- 爬虫状态持久化（用于崩溃恢复）

## 使用方式

### 快速启动

```bash
# 克隆项目
git clone <repository-url>
cd kaitian

# 使用启动脚本（推荐）
python start.py

# 或手动启动
uv sync
uv run uvicorn main:app --reload --port 8000
```

### 配置

创建 `.env` 文件：

```env
# AI 配置（必需）
OPENAI_API_KEY=your_openai_key
OPENAI_MODEL=gpt-3.5-turbo

# 数据库（可选，用于爬虫状态持久化）
DATABASE_URL=sqlite:///./kaitian.db

# Crawl4AI（可选）
CRAWL4AI_API_URL=http://localhost:8001
```

### 访问

- KaiTian API: `http://localhost:8000/docs`
- MediaCrawler WebUI: `http://localhost:8080`

## API 快速参考

| 端点 | 方法 | 功能 |
|------|------|------|
| `/health` | GET | 健康检查 |
| `/crawler/url` | POST | 爬取 URL 内容 |
| `/crawler/search` | POST | 搜索社交媒体 |
| `/crawler/get` | POST | 爬取帖子详情 |
| `/ai/evaluate/relevance` | POST | AI 评判相关性 |
| `/ai/generate/reply` | POST | AI 生成回复 |
| `/ai/generate/article` | POST | 生成文章 |
| `/ai/generate/articles/batch` | POST | 批量生成文章 |
| `/ai/generate/optimize` | POST | SEO 优化 |
| `/ai/status` | GET | AI 服务状态 |
| `/publisher/post` | POST | 发布帖子 |
| `/publisher/comment` | POST | 发布评论 |

详细 API 文档请访问 `http://localhost:8000/docs`

## 技术栈

- 后端：FastAPI, Python 3.10+
- 依赖管理：uv
- AI：LangChain + OpenAI
- 爬虫：crawl4ai + MediaCrawler
- 数据库：SQLite（可选，用于状态持久化）

## MediaCrawler 说明

MediaCrawler 是一个独立的爬虫工具，通过 KaiTian 的启动脚本自动管理。

**配置文件：** `MediaCrawler/config/base_config.py`

**常用命令：**
```bash
cd MediaCrawler
uv run main.py --platform xhs --lt qrcode --type search
uv run main.py --help
```

## 项目结构

```
app/
├── api/
│   └── routes.py              # API 端点定义
├── services/
│   ├── langchain_agent.py     # AI 能力（评判、生成）
│   ├── social_media_crawler.py # 爬虫能力
│   ├── publisher_service.py   # 发布能力
│   ├── content_generation.py   # 内容生成能力
│   └── state_store.py         # 文件系统状态存储
├── models/
│   └── schemas.py             # API 请求/响应模型
└── core/
    ├── app.py                 # FastAPI 应用
    └── config.py              # 配置管理
data/
├── sessions/                  # 搜索会话和检查点
└── failed/                    # 失败项目和平台会话
```

## 文档

- `docs/N8N_INTEGRATION.md` - n8n 集成详细指南
- `docs/LANGCHAIN_INTEGRATION.md` - AI 能力说明
