# KaiTian - AI 营销自动化引擎

**关键词宇宙 → 实时爬取 → AI 评判 → 生成回复 → LihuApp 审核 → 自动发布。完整的营销自动化闭环。**

---

## 什么是 KaiTian？

KaiTian 是一个为营销团队设计的 AI 驱动营销自动化引擎。它以结构化的"关键词宇宙"为起点，**实时**在社交媒体上发现相关讨论，使用 LangChain Agent 评判内容相关性，生成针对性回复，通过 LihuApp 推送到手机进行人工审核，最后自动发布到社交媒体。

**核心工作流：**
```
关键词宇宙（n8n 读取）
    ↓
循环每个关键词
    ↓
实时爬取社交媒体（crawl4ai 实时爬取，非数据库查询）
    ↓
AI 相关性评判（LangChain Agent，支持中英文）
    ↓
AI 生成回复（LangChain Agent，支持中英文）
    ↓
推送审核（LihuApp 手机通知）
    ↓
人工审核（手机确认）
    ↓
自动发布（审核通过后）
```

**核心价值：**
- ⏱️ **从数小时到几分钟** - 自动化整个营销回复流程
- 📊 **实时爬取** - 使用 crawl4ai 实时爬取最新内容，不是查询数据库
- 🤖 **真正的 LangChain Agent** - 支持中英文帖子的评判和回复生成
- 🎯 **精准匹配** - AI Agent 评判相关性确保高质量的回复机会
- 👁️ **保留控制权** - 所有回复都需要你的手机审核才能发布
- 📈 **完整历史** - 保存所有搜索、评判、生成和发布记录

---

## 快速开始

### 安装依赖（使用 uv）

\`\`\`bash
# 克隆项目
git clone <repository-url>
cd kaitian

# 使用 uv 同步依赖
uv sync

# 安装浏览器驱动（crawl4ai 需要）
uv run playwright install
\`\`\`

### 配置环境变量

创建 \`.env\` 文件：

\`\`\`env
# KaiTian 核心
KAITIAN_API_URL=http://localhost:8000
KAITIAN_DEBUG=false
APP_VERSION=1.0.0

# 数据库
DATABASE_URL=sqlite:///./kaitian.db

# AI & LangChain
LLM_PROVIDER=openai
OPENAI_API_KEY=your_openai_key
OPENAI_MODEL=gpt-3.5-turbo
OPENAI_TEMPERATURE=0.7

# LihuApp 集成（手机审核）
LIHUO_API_URL=https://your-lihuo-instance.com
LIHUO_API_KEY=your_lihuo_key
\`\`\`

### 启动服务

\`\`\`bash
# 启动 KaiTian API 服务器
uv run uvicorn main:app --reload --port 8000

# API 文档
http://localhost:8000/docs
\`\`\`

---

## 核心工作流程详解

### 1. 编辑关键词宇宙
创建关键词集合供 n8n 循环使用

### 2. 实时爬取社交媒体
使用 crawl4ai **实时爬取**最新内容（非数据库查询）

### 3. AI Agent 评判相关性
LangChain Agent 评判帖子是否与产品相关（支持中英文）

### 4. AI Agent 生成回复
LangChain Agent 生成针对性回复（支持中英文）

### 5. 推送手机审核
LihuApp 推送到手机

### 6. 人工审核
手机上批准或拒绝

### 7. 自动发布
审核通过后自动发布

---

## 关键技术实现

### ✅ crawl4ai 真实用法

使用 \`AsyncWebCrawler\` 和 \`arun()\` 方法：

\`\`\`python
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig

async with AsyncWebCrawler() as crawler:
    result = await crawler.arun(url="https://example.com")
    print(result.markdown)
\`\`\`

### ✅ LangChain Agent

真正的 Agent 实现，支持工具和推理：

\`\`\`python
from langchain.agents import AgentExecutor, create_react_agent
from langchain.tools import Tool

# 创建工具
tools = [
    Tool(name="EvaluateRelevance", func=evaluate_func),
    Tool(name="GenerateReply", func=generate_func),
]

# 创建 Agent
agent = create_react_agent(llm, tools, prompt)
executor = AgentExecutor(agent=agent, tools=tools)
\`\`\`

### ✅ uv 依赖管理

\`\`\`bash
# 安装依赖
uv sync

# 运行项目
uv run python main.py
\`\`\`

---

## 已移除的内容

按照你的要求：
- ❌ Docker 支持（Dockerfile, docker-compose.yml 已删除）
- ❌ pip requirements.txt（改用 uv）
- ❌ start.sh（改用 Python start.py）

---

## API 端点

- \`POST /api/v1/keywords/universe\` - 创建关键词宇宙
- \`POST /api/v1/search/social-media\` - 实时爬取（crawl4ai）
- \`POST /api/v1/ai/evaluate-relevance\` - AI Agent 评判（中英文）
- \`POST /api/v1/ai/generate-reply\` - AI Agent 生成（中英文）
- \`POST /api/v1/notifications/push-for-review\` - 推送 LihuApp
- \`POST /api/v1/webhooks/review-callback\` - LihuApp 回调

---

## 文档

- \`docs/NEW_WORKFLOW_DESIGN.md\` - 完整工作流设计
- \`docs/LANGCHAIN_INTEGRATION.md\` - LangChain 集成
- \`docs/N8N_INTEGRATION.md\` - n8n 集成指南
