# KaiTian - AI 营销自动化引擎

**在线发现营销机会。让 AI 生成回复。你来审核。我们来发布。**

---

## 什么是 KaiTian？

KaiTian 是一个轻量级后端服务，为 AI 驱动的营销自动化提供动力。它在社交媒体上发现相关帖子，高效地存储它们，并为 n8n 等编排工具提供简单的 API，以构建完整的营销工作流。

**核心价值：** 将回复时间从数小时减少到几秒钟。每天发现 5 个以上相关帖子。再也不会错过营销机会。

---

## 架构：简单且模块化

```
您的营销工作流（n8n/Zapier/自定义）
         ↓
     KaiTian API
     ├─ 抓取帖子
     ├─ 存储数据
     └─ 发布回复
         ↓
    社交媒体
    (Reddit、Twitter 等)
```

**KaiTian 做一件事做得很好：** 通过 API 抓取、存储和管理营销帖子。

**n8n 编排其他所有事情：** 相关性评分、AI 回复生成、人工审核、发布。

---

## 主要功能

✅ **帖子发现**
- 在 Reddit 上查找包含关键字的帖子
- 使用 JavaScript 渲染支持抓取任何 URL
- 自动全文存储

✅ **数据管理**
- 按状态、平台或日期查询帖子
- 跟踪帖子生命周期（待处理 → 已获取 → 已分析 → 已发布）
- 包含 SQLite 数据库

✅ **AI 内容生成** (LangChain)
- 使用 GPT-4/Claude 生成营销文章
- 支持多种语言和语气风格
- SEO 优化和关键词分析
- 内容质量评分

✅ **简单 API**
- 抓取、查询、更新端点
- 内容生成端点（新增）
- JSON 请求/响应
- 为 n8n HTTP 节点设计

✅ **生产就绪**
- 包含 Docker 和 Docker Compose
- 基于环境的配置
- 健康检查端点
- 综合日志和监控

---

## 快速开始

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

然后：
- API 可在 `http://localhost:8000/api/v1` 访问
- API 文档在 `http://localhost:8000/docs`

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

## API 概览

### 1. 抓取帖子

```bash
POST /api/v1/crawl/url
Content-Type: application/json

{
  "url": "https://example.com",
  "store_to_db": true
}
```

**响应：**
```json
{
  "success": true,
  "url": "https://example.com",
  "content": "# 以 Markdown 格式提取的内容",
  "extracted_data": {...}
}
```

### 2. 列出帖子

```bash
GET /api/v1/posts?status=pending&limit=10
```

**响应：**
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

### 3. 更新帖子

```bash
PATCH /api/v1/posts/{post_id}

{
  "status": "analyzed",
  "relevance_score": 0.85,
  "generated_reply": "很棒的帖子！"
}
```

### 4. 生成文章 (LangChain)

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

**响应：**
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

### 5. 批量生成文章

```bash
POST /api/v1/generate/articles/batch
Content-Type: application/json

{
  "articles": [
    {
      "topic": "AI 在营销中的应用",
      "keywords": ["AI", "营销"],
      "tone": "professional"
    },
    {
      "topic": "营销自动化工具",
      "keywords": ["自动化", "工具"],
      "tone": "friendly"
    }
  ]
}
```

### 6. SEO 优化

```bash
POST /api/v1/generate/optimize
Content-Type: application/json

{
  "content": "原始文章内容...",
  "target_keywords": ["AI", "营销"],
  "optimization_level": "high"
}
```

### 7. 获取生成服务状态

```bash
GET /api/v1/generate/status
```

**响应：**
```json
{
  "success": true,
  "status": "available",
  "llm_provider": "openai",
  "model": "gpt-3.5-turbo",
  "timestamp": "2024-03-01T10:00:00"
}
```

---

## 示例 n8n 工作流

```
定时任务（每 30 分钟）
   ↓
POST /api/v1/crawl/url
   ↓
对每个帖子执行：
   ├─ 调用 OpenAI 进行相关性评分
   ├─ PATCH /api/v1/posts/{id}
   ├─ 如果相关：
   │   ├─ 生成回复
   │   ├─ PATCH /api/v1/posts/{id}
   │   └─ 发送 Slack 通知
   └─ 等待人工审核
   ↓
如果批准：
   └─ 调用社交媒体 API 发布回复
```

详见 [docs/N8N_INTEGRATION.md](docs/N8N_INTEGRATION.md)。

---

## 环境配置

创建 `.env` 文件：

```env
# KaiTian 核心
KAITIAN_API_URL=http://localhost:8000
KAITIAN_DEBUG=false

# 搜索关键字（逗号分隔）
SEARCH_KEYWORDS=automation,marketing,workflow

# Crawl4AI
CRAWL4AI_API_URL=http://localhost:11235

# 数据库
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

# Google Gemini 配置 (可选)
GOOGLE_API_KEY=your_google_api_key

# 内容生成配置
CONTENT_GENERATION_MAX_TOKENS=2000
CONTENT_GENERATION_TEMPERATURE=0.7
CONTENT_GENERATION_TIMEOUT=30

# Redis 缓存 (可选)
REDIS_ENABLED=false
REDIS_URL=redis://localhost:6379

# 日志配置
LOG_LEVEL=INFO
```

所有选项详见 `.env.example`。

---

## 部署

### Docker Compose（本地开发）

```bash
docker-compose up -d
```

包含：
- KaiTian API 服务
- Crawl4AI 服务

### 生产环境

1. 构建：`docker build -t kaitian:latest .`
2. 使用环境变量部署容器
3. 为 SQLite 数据库挂载卷以实现持久化
4. 设置 `KAITIAN_DEBUG=false`

详见 [docs/DOCKER_DEPLOYMENT.md](docs/DOCKER_DEPLOYMENT.md)。

---

## 核心概念

### 帖子状态生命周期

帖子经历以下阶段：
- `pending`：初始抓取
- `fetched`：从源检索
- `analyzed`：AI 相关性评分
- `relevant`：符合相关性阈值
- `reply_generated`：AI 回复已创建
- `reply_approved`：人工批准
- `published`：已发布到社交媒体
- `ignored`：人工跳过

### 关注点分离

| 组件 | 责任 |
|------|------|
| **KaiTian** | 抓取帖子、存储数据、提供 API |
| **n8n** | 编排、AI 分析、人工流程、直接 API 调用 |

这使 KaiTian 保持轻量级，并让 n8n 做它最擅长的事情：工作流自动化。

---

## 常见问题

**Q: 我需要 Crawl4AI 吗？**  
A: 是的，用于 JavaScript 渲染的内容。对于简单的 HTML，你可以使用任何 HTTP 客户端。

**Q: KaiTian 可以直接发布到 Reddit 吗？**  
A: 不行。KaiTian 存储和检索数据。n8n 通过社交媒体 API 直接编排发布。

**Q: 如果 n8n 不可用怎么办？**  
A: 任何 HTTP 客户端都可以调用 KaiTian API。使用 curl、Postman 或构建你自己的编排层。

**Q: 我如何扩展它？**  
A: 为其他平台添加更多 POST /crawl/* 端点。为其他元数据添加更多 PATCH /posts 端点。

**Q: SQLite 足够吗？**  
A: 是的，对于 MVP。对于每天有 1000 个以上帖子的情况，请考虑使用 PostgreSQL。

---

## 文档

### 核心文档
- **[LANGCHAIN_INTEGRATION.md](docs/LANGCHAIN_INTEGRATION.md)** - LangChain 集成详细指南，包括 API 设计、Prompt 工程、LLM 提供商配置
- **[SYSTEM_DESIGN.md](docs/SYSTEM_DESIGN.md)** - 完整的系统架构设计文档
- **[N8N_INTEGRATION.md](docs/N8N_INTEGRATION.md)** - n8n 工作流集成指南

### 启动和部署
- **[STARTUP_GUIDE.md](docs/STARTUP_GUIDE.md)** - 快速启动指南
- **[STARTUP_SCRIPTS.md](docs/STARTUP_SCRIPTS.md)** - 启动脚本技术文档
- **[DOCKER_DEPLOYMENT.md](docs/DOCKER_DEPLOYMENT.md)** - Docker 部署指南
- **[QUICK_REFERENCE.md](docs/QUICK_REFERENCE.md)** - 快速参考卡

### 其他资源
- **[PROJECT_STRUCTURE.md](docs/PROJECT_STRUCTURE.md)** - 项目结构说明
- **[DATABASE_CRAWLER_INTEGRATION.md](docs/DATABASE_CRAWLER_INTEGRATION.md)** - 数据库和爬虫集成

---

## 本地运行

```bash
# 安装
pip install -r requirements.txt

# 以调试模式运行
KAITIAN_DEBUG=true python main.py

# 测试
curl http://localhost:8000/health
```

## 项目结构

```
kaitian/
├── app/
│   ├── api/
│   │   └── routes.py           # API 端点
│   ├── core/                   # 配置、数据库、应用设置
│   ├── services/               # 业务逻辑
│   │   ├── content_generation.py    # LangChain 内容生成
│   │   └── prompt_templates.py      # Prompt 模板
│   ├── integrations/           # 外部服务客户端
│   └── models/                 # 数据库模型
├── docs/                       # 文档
│   ├── LANGCHAIN_INTEGRATION.md
│   ├── SYSTEM_DESIGN.md
│   ├── N8N_INTEGRATION.md
│   └── ...
├── docker-compose.yml          # 本地开发设置
├── Dockerfile                  # 生产镜像
├── start.py                    # 启动脚本
├── main.py                     # 入口点
├── requirements.txt            # Python 依赖
└── README.md                   # 本文件
```

---

## 成本

**0 元/月：**
- 无专有服务
- 所有开源依赖
- SQLite（无数据库成本）
- 自托管

**可选成本：**
- n8n（免费自托管或付费云）
- OpenAI/Claude 用于 AI（按使用量付费）
- 托管基础设施（你的选择）

---

## 下一步

1. **设置：** `docker-compose up -d`
2. **测试 API：** `curl http://localhost:8000/health`
3. **构建工作流：** 查看 n8n 集成指南
4. **监控：** 检查日志和数据库查询

---

## 支持和反馈

- 发现错误？开启一个 issue
- 有功能请求？贡献代码！
- 需要帮助？查看 docs/ 文件夹获取详细指南

---

**准备好自动化了吗？** 使用 Docker Compose 开始，构建你的第一个 n8n 工作流，在几分钟内发布你的第一条回复。
