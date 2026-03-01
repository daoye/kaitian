# KaiTian - AI 营销自动化引擎

**编辑关键词 → 自动发现 → AI 评判 → 生成回复 → 手机审核 → 自动发布。完整的营销自动化闭环。**

---

## 什么是 KaiTian？

KaiTian 是一个为营销团队设计的 AI 驱动营销自动化引擎。它以结构化的"关键词宇宙"为起点，自动在社交媒体上发现相关讨论，使用 AI 评判内容相关性，生成针对性回复，通过手机推送进行人工审核，最后自动发布。

**核心工作流：**
1. 📝 **编辑关键词宇宙** - 定义你的营销关键词集合
2. 🔍 **自动发现** - n8n 自动在社交媒体上发现相关帖子（前3页）
3. 🤖 **AI 评判** - 使用 LangChain 评判内容与产品是否相关
4. ✍️ **生成回复** - AI 根据帖子内容生成针对性回复
5. 📱 **推送审核** - 通过 LihuApp 将回复推送到你的手机
6. ✅ **人工确认** - 你审核通过/拒绝，可编辑备注
7. 📤 **自动发布** - 审核通过后自动发布到社交媒体

**核心价值：**
- ⏱️ **从数小时到几分钟** - 自动化整个营销回复流程
- 📊 **多平台覆盖** - 同时监控 Reddit、Twitter、LinkedIn 等
- 🎯 **精准匹配** - AI 相关性评判确保高质量的回复机会
- 👁️ **保留控制权** - 所有回复都需要你的手机审核才能发布
- 📈 **完整历史** - 保存所有搜索、评判、生成和发布记录

---

## 架构概览

### 工作流完整图

```
┌──────────────────────────────────────────────────┐
│             你（营销人员）                         │
│  • 编辑关键词宇宙                                 │
│  • 在 LihuApp 上审核生成的回复                    │
└────────────────┬─────────────────────────────────┘
                 │
                 ↓ 定时触发（每天/每小时）
┌──────────────────────────────────────────────────┐
│            n8n 工作流编排                         │
│  • 循环关键词                                     │
│  • 调用 KaiTian API 查询社交媒体                 │
│  • 调用 AI 评判和生成                            │
│  • 推送到 LihuApp                               │
│  • 等待审核反馈                                  │
│  • 发布到社交媒体                                │
└────────────────┬─────────────────────────────────┘
                 │
                 ↓ 
┌──────────────────────────────────────────────────────┐
│              KaiTian API 服务器                      │
├──────────────────────────────────────────────────────┤
│                                                       │
│  • 关键词宇宙管理 (Create/Read/Update/Delete)        │
│  • 社交媒体爬虫（Reddit/Twitter/LinkedIn）         │
│  • AI 相关性评判（使用 LangChain）                 │
│  • AI 回复生成（支持多种风格）                      │
│  • LihuApp 消息推送和 Webhook 回调                 │
│  • 发布管理和历史记录                               │
│                                                       │
│  所有数据存储在 SQLite 数据库中                      │
│  使用 Redis 缓存优化性能（可选）                     │
│  使用 OpenAI/Claude 进行 AI 处理                    │
│                                                       │
└────────────────┬──────────────────────────────────────┘
                 │
         ┌───────┼────────┐
         ↓       ↓        ↓
    ┌────────┐ ┌──────┐ ┌───────┐
    │ SQLite │ │Redis │ │OpenAI │
    │ 数据库 │ │ 缓存 │ │ 服务  │
    └────────┘ └──────┘ └───────┘
         │
         ↓
    社交媒体平台
    (Reddit, Twitter, LinkedIn)
```

---

## 主要功能

### ✅ 关键词宇宙管理
- 创建、编辑、删除关键词集合
- 为关键词添加分类和标签
- 支持多个产品的独立关键词集合

### ✅ 社交媒体爬虫
- **Reddit** - 完整支持（热门贴、新贴、评论）
- **Twitter** - 推文和讨论
- **LinkedIn** - 文章和讨论
- 自动获取前 3 页内容（可配置）
- 提取帖子的点赞、评论等互动数据

### ✅ AI 智能评判
- 自动评判内容与你的产品是否相关
- 返回相关性评分（0-1）和置信度
- 提供评判理由和建议的回复方向
- 分析帖子情绪、意图和紧急程度

### ✅ AI 回复生成
- 根据原始帖子内容生成针对性回复
- 支持多种风格（专业、友好、技术、)
- 可配置回复长度（短、中、长）
- 提供多个备选方案供选择
- 评估回复的相关性和参与度

### ✅ 手机审核系统
- 通过 LihuApp 推送待审核的回复
- 在手机上直接看到原始帖子和 AI 生成的回复
- 一键批准、拒绝或编辑
- 支持添加备注说明

### ✅ 自动发布
- 审核通过后自动发布到社交媒体
- 记录发布成功/失败状态
- 保存发布的链接和时间
- 完整的发布历史追踪

### ✅ 生产就绪
- 包含 Docker 和 Docker Compose
- 基于环境变量配置
- 完善的错误处理和日志
- 健康检查端点
- 可轻松扩展到其他社交媒体平台

---

## 快速开始

### 方式 1: 使用启动脚本（推荐）

```bash
# 启动 KaiTian
python start.py --only kaitian

# 或启动所有服务
python start.py

# 查看帮助
python start.py --help
```

**脚本会自动：**
- ✅ 创建虚拟环境
- ✅ 克隆依赖仓库
- ✅ 安装所有依赖

详见：[docs/STARTUP_GUIDE.md](docs/STARTUP_GUIDE.md)

### 方式 2: 使用 Docker

```bash
docker-compose up -d
```

然后访问：
- API 文档：`http://localhost:8000/docs`
- API 端点：`http://localhost:8000/api/v1`

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

## API 快速参考

### 1️⃣ 管理关键词宇宙

#### 创建关键词集合
```bash
curl -X POST http://localhost:8000/api/v1/keywords/universe \
  -H "Content-Type: application/json" \
  -d '{
    "name": "产品A_营销关键词",
    "description": "针对产品A的营销关键词",
    "keywords": ["AI营销", "自动化工具", "社交媒体"],
    "category": "产品营销"
  }'
```

#### 获取关键词集合
```bash
curl http://localhost:8000/api/v1/keywords/universe
```

#### 更新关键词集合
```bash
curl -X PUT http://localhost:8000/api/v1/keywords/universe/{universe_id} \
  -H "Content-Type: application/json" \
  -d '{
    "keywords": ["新关键词1", "新关键词2"]
  }'
```

### 2️⃣ 查询社交媒体

#### 搜索相关帖子
```bash
curl -X POST http://localhost:8000/api/v1/search/social-media \
  -H "Content-Type: application/json" \
  -d '{
    "keyword": "AI营销",
    "platforms": ["reddit", "twitter"],
    "pages": 3,
    "filters": {
      "min_engagement": 5,
      "language": "zh,en"
    }
  }'
```

**响应示例：**
```json
{
  "success": true,
  "keyword": "AI营销",
  "total_results": 45,
  "results_per_platform": {
    "reddit": {
      "count": 25,
      "posts": [
        {
          "post_id": "reddit_abc123",
          "platform": "reddit",
          "title": "求推荐AI营销工具",
          "content": "我在找一个好用的AI营销工具...",
          "author": "user123",
          "url": "https://reddit.com/r/xxx/post_id",
          "engagement": {
            "upvotes": 120,
            "comments": 45
          },
          "created_at": "2024-02-28T10:00:00"
        }
      ]
    }
  }
}
```

### 3️⃣ AI 相关性评判

#### 评判内容相关性
```bash
curl -X POST http://localhost:8000/api/v1/ai/evaluate-relevance \
  -H "Content-Type: application/json" \
  -d '{
    "post_id": "reddit_abc123",
    "content": "我在找一个好用的AI营销工具...",
    "product_description": "产品A是一个AI驱动的营销自动化平台"
  }'
```

**响应示例：**
```json
{
  "success": true,
  "post_id": "reddit_abc123",
  "is_relevant": true,
  "relevance_score": 0.87,
  "confidence": 0.92,
  "reasoning": "用户正在寻找AI营销工具，这正是我们产品的核心功能",
  "suggested_angle": "突出我们产品的自动化能力和易用性"
}
```

### 4️⃣ 生成 AI 回复

#### 生成针对性回复
```bash
curl -X POST http://localhost:8000/api/v1/ai/generate-reply \
  -H "Content-Type: application/json" \
  -d '{
    "post_id": "reddit_abc123",
    "original_content": "求推荐AI营销工具",
    "platform": "reddit",
    "tone": "professional",
    "max_length": 300
  }'
```

**响应示例：**
```json
{
  "success": true,
  "post_id": "reddit_abc123",
  "generated_reply": "我最近在用产品A，感觉还不错。主要优点是...",
  "reply_confidence": 0.88,
  "word_count": 180,
  "alternatives": [
    {
      "reply": "我也在找类似工具，可以分享一下使用心得吗..."
    }
  ]
}
```

### 5️⃣ 推送审核通知

#### 推送到 LihuApp
```bash
curl -X POST http://localhost:8000/api/v1/notifications/push-for-review \
  -H "Content-Type: application/json" \
  -d '{
    "post_id": "reddit_abc123",
    "original_content": "求推荐AI营销工具",
    "generated_reply": "我最近在用产品A...",
    "callback_url": "https://your-n8n.com/webhook/review"
  }'
```

**响应：**
```json
{
  "success": true,
  "notification_id": "uuid",
  "status": "sent",
  "message": "消息已推送到LihuApp"
}
```

#### LihuApp 审核结果回调
n8n 设置 webhook 接收：
```
POST /api/v1/webhooks/review-callback
{
  "notification_id": "uuid",
  "action": "approved",  # approved 或 rejected
  "user_notes": "改一下表述方式"
}
```

### 6️⃣ 发布和记录

#### 记录已发布的回复
```bash
curl -X POST http://localhost:8000/api/v1/publish/record \
  -H "Content-Type: application/json" \
  -d '{
    "post_id": "reddit_abc123",
    "reply": "我最近在用产品A...",
    "platform": "reddit",
    "published_url": "https://reddit.com/r/xxx/comment/123"
  }'
```

---

## 环境配置

创建 `.env` 文件：

```env
# KaiTian 核心
KAITIAN_API_URL=http://localhost:8000
KAITIAN_DEBUG=false
APP_VERSION=1.0.0

# 数据库
DATABASE_URL=sqlite:///./kaitian.db

# AI & LLM
LLM_PROVIDER=openai
OPENAI_API_KEY=your_openai_key
OPENAI_MODEL=gpt-3.5-turbo
OPENAI_TEMPERATURE=0.7

# 可选：Azure OpenAI
AZURE_OPENAI_KEY=your_azure_key
AZURE_OPENAI_ENDPOINT=your_endpoint

# 可选：Anthropic Claude
ANTHROPIC_API_KEY=your_anthropic_key

# 社交媒体配置
REDDIT_CLIENT_ID=your_reddit_client_id
REDDIT_CLIENT_SECRET=your_reddit_secret
REDDIT_USER_AGENT=KaiTian/1.0

TWITTER_API_KEY=your_twitter_key
TWITTER_API_SECRET=your_twitter_secret
TWITTER_BEARER_TOKEN=your_bearer_token

LINKEDIN_API_KEY=your_linkedin_key

# LihuApp 集成
LIHUO_API_URL=https://your-lihuo-instance.com
LIHUO_API_KEY=your_lihuo_key
LIHUO_WEBHOOK_SECRET=your_webhook_secret

# 缓存
REDIS_ENABLED=false
REDIS_URL=redis://localhost:6379

# 日志
LOG_LEVEL=INFO
```

详见 `.env.example`。

---

## 完整工作流示例（n8n）

### n8n 配置步骤

#### 1. 定时触发（每天9点）
```
Schedule: Every day at 09:00 AM
```

#### 2. 获取关键词集合
```
HTTP Request:
  Method: GET
  URL: {{ $kaitian.api_url }}/api/v1/keywords/universe/{{ selected_universe }}
```

#### 3. 循环关键词
```
Loop: forEach keyword in universe.keywords
```

#### 4. 搜索社交媒体
```
HTTP Request:
  Method: POST
  URL: {{ $kaitian.api_url }}/api/v1/search/social-media
  Body: {
    "keyword": "{{ $loop.value }}",
    "platforms": ["reddit", "twitter"],
    "pages": 3
  }
```

#### 5. 循环结果
```
Loop: forEach post in search_results
```

#### 6. 评判相关性
```
HTTP Request:
  Method: POST
  URL: {{ $kaitian.api_url }}/api/v1/ai/evaluate-relevance
  Body: {
    "post_id": "{{ $loop.value.post_id }}",
    "content": "{{ $loop.value.content }}",
    "product_description": "{{ product_info }}"
  }
```

#### 7. 如果相关（relevance_score > 0.7）

##### 7.1 生成回复
```
HTTP Request:
  Method: POST
  URL: {{ $kaitian.api_url }}/api/v1/ai/generate-reply
  Body: {
    "post_id": "{{ $loop.value.post_id }}",
    "original_content": "{{ $loop.value.content }}",
    "platform": "{{ $loop.value.platform }}",
    "tone": "professional"
  }
```

##### 7.2 推送审核通知
```
HTTP Request:
  Method: POST
  URL: {{ $kaitian.api_url }}/api/v1/notifications/push-for-review
  Body: {
    "post_id": "{{ $loop.value.post_id }}",
    "original_content": "{{ $loop.value.content }}",
    "generated_reply": "{{ generate_reply.generated_reply }}",
    "callback_url": "{{ $webhook.url }}"
  }
```

##### 7.3 等待 Webhook 回调（24小时超时）
```
Wait for Webhook:
  Webhook URL: {{ $webhook.url }}
  Timeout: 24 hours
```

##### 7.4 检查审核结果
```
If webhook.action == "approved":
  ↓
  调用社交媒体 API 发布回复
  ↓
  记录发布
Else:
  跳过此帖子
```

#### 8. 流程完成
```
Send Slack/Email 总结通知
```

---

## 数据库架构

### 核心表结构

**关键词集合表（keyword_universes）**
- id、name、description、category、tags
- keywords（JSON 数组）
- created_at、updated_at

**社交媒体帖子表（social_media_posts）**
- id、post_id、platform、title、content
- author、url、engagement（JSON）
- relevance_score、is_relevant、relevance_reasoning
- created_at、fetched_at

**生成的回复表（generated_replies）**
- id、post_id、original_reply、current_reply
- status、confidence、review_status
- user_notes、published_url、published_at
- created_at、updated_at

**审核通知表（review_notifications）**
- id、reply_id、lihuo_message_id
- status、callback_url、expires_at
- result、user_notes、created_at

详见 [docs/NEW_WORKFLOW_DESIGN.md](docs/NEW_WORKFLOW_DESIGN.md)。

---

## 文档

### 工作流文档
- **[NEW_WORKFLOW_DESIGN.md](docs/NEW_WORKFLOW_DESIGN.md)** - 完整的新工作流设计（API、数据模型、实现指南）
- **[LANGCHAIN_INTEGRATION.md](docs/LANGCHAIN_INTEGRATION.md)** - LangChain 集成详细指南

### 快速指南
- **[STARTUP_GUIDE.md](docs/STARTUP_GUIDE.md)** - 快速启动指南
- **[N8N_INTEGRATION.md](docs/N8N_INTEGRATION.md)** - n8n 工作流集成

### 系统设计
- **[SYSTEM_DESIGN.md](docs/SYSTEM_DESIGN.md)** - 系统架构设计
- **[PROJECT_STRUCTURE.md](docs/PROJECT_STRUCTURE.md)** - 项目结构说明

### 部署
- **[DOCKER_DEPLOYMENT.md](docs/DOCKER_DEPLOYMENT.md)** - Docker 部署指南
- **[QUICK_REFERENCE.md](docs/QUICK_REFERENCE.md)** - 快速参考卡

---

## 常见问题

**Q: 我需要自己设置 Reddit/Twitter API 吗？**  
A: 是的。KaiTian 是开源的，你需要在各平台获取 API 凭证。详见环境配置章节。

**Q: 可以离线使用吗？**  
A: AI 评判和生成需要 OpenAI API。但帖子爬虫部分可以独立运行。

**Q: 支持哪些社交媒体平台？**  
A: 目前支持 Reddit、Twitter、LinkedIn。易于扩展到其他平台。

**Q: 如果 LihuApp 连接失败怎么办？**  
A: 系统会重试推送，并在日志中记录错误。未审核的回复会保留在数据库中。

**Q: 可以修改已生成的回复吗？**  
A: 可以。在 LihuApp 审核时可以编辑回复内容，系统会记录所有修改。

**Q: 数据安全怎么保证？**  
A: 数据存储在本地 SQLite 数据库，你完全控制。建议定期备份。

---

## 下一步

1. **环境配置** - 设置 `.env` 文件，配置 API 凭证
2. **启动 KaiTian** - `python start.py --only kaitian`
3. **创建关键词集合** - 在 API 中创建你的第一个关键词宇宙
4. **配置 n8n** - 按照工作流示例设置自动化
5. **测试流程** - 手动测试完整的审核和发布流程
6. **定时运行** - 在 n8n 中设置定时触发

---

## 支持与反馈

- 📚 完整文档：`docs/` 文件夹
- 🐛 问题反馈：提交 Issue
- 💡 功能建议：欢迎贡献
- 📖 API 文档：访问 `/docs` 端点

---

**准备好了吗？** 从创建你的第一个关键词宇宙开始，享受全自动的营销机会发现和回复流程！
