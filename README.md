# KaiTian - AI 营销自动化引擎

## 业务目标

KaiTian 是一个营销自动化工具，帮助营销团队在社交媒体上发现和回复潜在客户。

**核心价值：**
- 自动发现相关的社交媒体讨论
- 自动生成针对性的回复
- 人工审核后自动发布
- 将回复时间从几小时缩短到几分钟

## 工作流程

1. **编辑关键词** - 在系统中创建产品相关的关键词集合

2. **自动搜索** - 系统定时读取关键词，在 Reddit、Twitter、LinkedIn 等平台搜索相关内容

3. **AI 评判** - 系统自动判断搜索到的内容是否与产品相关

4. **生成回复** - 对相关的内容，AI 自动生成针对性的回复

5. **手机审核** - 通过 LihuApp 将回复推送到手机，人工确认是否合适

6. **自动发布** - 审核通过后，系统自动将回复发布到社交媒体

## 主要功能

**关键词管理**
- 创建和管理关键词集合
- 支持分类和标签
- 为不同产品设置不同的关键词

**社交媒体搜索**
- 支持 Reddit、Twitter、LinkedIn 平台
- 实时搜索最新内容
- 获取帖子的互动数据（点赞、评论等）

**AI 评判和生成**
- 自动评判内容与产品的相关性
- 自动生成回复内容
- 支持中文和英文

**手机审核**
- 通过 LihuApp 接收审核通知
- 在手机上查看原始帖子和生成的回复
- 一键批准或拒绝

**自动发布**
- 审核通过后自动发布
- 记录发布状态和链接
- 完整的发布历史

## 使用方式

### 安装

```bash
git clone <repository-url>
cd kaitian
uv sync
uv run playwright install
```

### 配置

创建 `.env` 文件：

```env
# 数据库
DATABASE_URL=sqlite:///./kaitian.db

# AI 配置
OPENAI_API_KEY=your_openai_key
OPENAI_MODEL=gpt-3.5-turbo

# LihuApp 配置
LIHUO_API_URL=https://your-lihuo-instance.com
LIHUO_API_KEY=your_lihuo_key
```

### 启动

```bash
uv run uvicorn main:app --reload --port 8000
```

访问 `http://localhost:8000/docs` 查看 API 文档。

## API 端点

**关键词管理**
- `POST /api/v1/keywords/universe` - 创建关键词集合
- `GET /api/v1/keywords/universe` - 获取关键词列表
- `PUT /api/v1/keywords/universe/{id}` - 更新关键词
- `DELETE /api/v1/keywords/universe/{id}` - 删除关键词

**搜索和 AI**
- `POST /api/v1/search/social-media` - 搜索社交媒体内容
- `POST /api/v1/ai/evaluate-relevance` - 评判内容相关性
- `POST /api/v1/ai/generate-reply` - 生成回复

**审核和发布**
- `POST /api/v1/notifications/push-for-review` - 推送审核通知
- `POST /api/v1/webhooks/review-callback` - 接收审核结果
- `POST /api/v1/publish/record` - 记录已发布内容

## 技术栈

- 后端：FastAPI, Python 3.10+
- 依赖管理：uv
- AI：LangChain + OpenAI
- 爬虫：crawl4ai
- 数据库：SQLite
- 审核通知：LihuApp
- 工作流编排：n8n

## 文档

- `docs/NEW_WORKFLOW_DESIGN.md` - 完整工作流设计
- `docs/LANGCHAIN_INTEGRATION.md` - AI 集成说明
- `docs/N8N_INTEGRATION.md` - n8n 工作流配置指南
