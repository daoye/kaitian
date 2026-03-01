# KaiTian 工作流程改进方案

## 📋 新工作流程概述

### 核心需求
用户的理想工作流程：
1. **编辑关键词宇宙** - 编辑一批关键词集合
2. **n8n 循环处理** - 对每个关键词执行以下操作：
3. **社交媒体爬虫** - 调用社交媒体查询 API，获取前三页相关帖子/评论
4. **AI 相关性评判** - 使用 LangChain 评判内容与产品是否相关
5. **生成回复** - 如果相关，使用 AI 生成回复文本
6. **消息推送** - 通过 LihuApp webhook 将生成的回复推送到手机
7. **人工审核** - 在 LihuApp 中审核通过/拒绝
8. **发布** - 审核通过后，n8n 调用发帖 API 发布回复

---

## 🏗️ 改进的系统架构

### 整体流程图
```
┌─────────────────────────────────────────────────────────────────┐
│                    用户/营销团队                                  │
│  ├─ 编辑关键词宇宙 (KaiTian UI 或 JSON 文件)                    │
│  └─ 在 LihuApp 中审核回复                                        │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│                   n8n 工作流编排平台                              │
│  ├─ 定时触发                                                    │
│  ├─ 循环每个关键词                                              │
│  ├─ 调用 KaiTian API 查询社交媒体                              │
│  ├─ 调用 KaiTian API 评判相关性                                │
│  ├─ 调用 KaiTian API 生成回复                                  │
│  ├─ 调用 KaiTian API 推送消息到 LihuApp                        │
│  └─ 等待 LihuApp webhook 反馈（审核结果）                       │
└────────────────────────┬────────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────────┐
│                    KaiTian API Server                            │
├─────────────────────────────────────────────────────────────────┤
│ ┌────────────────┐ ┌──────────────┐ ┌──────────────────────┐   │
│ │ 关键词管理模块 │ │ 社交媒体爬虫 │ │ 消息推送与 Webhook  │   │
│ ├────────────────┤ ├──────────────┤ ├──────────────────────┤   │
│ │ • 创建/编辑   │ │ • Reddit     │ │ • LihuApp webhook   │   │
│ │ • 查询/删除   │ │ • Twitter    │ │ • 推送管理          │   │
│ │ • 分类/分组   │ │ • 其他社交   │ │ • 回调处理          │   │
│ └────────────────┘ │ • 获取前3页  │ └──────────────────────┘   │
│                    └──────────────┘                             │
│ ┌───────────────────────────────────────────────────────────┐  │
│ │          AI 模块（LangChain + LLM）                       │  │
│ ├───────────────────────────────────────────────────────────┤  │
│ │ • 相关性评判 - 判断内容是否与产品相关                     │  │
│ │ • 回复生成 - 基于帖子内容生成针对性回复                   │  │
│ │ • 内容优化 - SEO 优化和语言改进                          │  │
│ └───────────────────────────────────────────────────────────┘  │
│ ┌───────────────────────────────────────────────────────────┐  │
│ │          数据存储 & 管理                                  │  │
│ ├───────────────────────────────────────────────────────────┤  │
│ │ • 帖子存储 - 爬取的社交媒体内容                           │  │
│ │ • 回复存储 - AI 生成的回复和状态                         │  │
│ │ • 历史记录 - 所有操作的完整审计日志                       │  │
│ └───────────────────────────────────────────────────────────┘  │
└────────────────────────┬────────────────────────────────────────┘
                         │
         ┌───────────────┼───────────────┐
         ↓               ↓               ↓
    ┌─────────┐    ┌──────────┐    ┌──────────┐
    │ SQLite  │    │ Redis    │    │  LLM     │
    │ 数据库  │    │ 缓存     │    │ (OpenAI) │
    └─────────┘    └──────────┘    └──────────┘
                         │
                         ↓
                  ┌─────────────────┐
                  │  LihuApp        │
                  │  消息推送和     │
                  │  审核工具       │
                  └─────────────────┘
```

---

## 📊 新增 API 端点设计

### 1. 关键词宇宙管理模块

#### 1.1 创建关键词集合
```http
POST /api/v1/keywords/universe
Content-Type: application/json

{
  "name": "产品A_营销关键词",
  "description": "针对产品A的营销关键词集合",
  "keywords": [
    "产品A功能1",
    "产品A功能2",
    "竞争对手对比"
  ],
  "category": "产品营销",
  "tags": ["重要", "季度推广"]
}
```

**响应：**
```json
{
  "success": true,
  "universe_id": "uuid",
  "name": "产品A_营销关键词",
  "keyword_count": 3,
  "created_at": "2024-03-01T10:00:00",
  "updated_at": "2024-03-01T10:00:00"
}
```

#### 1.2 获取关键词集合列表
```http
GET /api/v1/keywords/universe?limit=10&offset=0
```

**响应：**
```json
{
  "success": true,
  "total": 5,
  "universes": [
    {
      "universe_id": "uuid",
      "name": "产品A_营销关键词",
      "keyword_count": 3,
      "category": "产品营销",
      "created_at": "2024-03-01T10:00:00"
    }
  ]
}
```

#### 1.3 获取单个关键词集合详情
```http
GET /api/v1/keywords/universe/{universe_id}
```

**响应：**
```json
{
  "success": true,
  "universe_id": "uuid",
  "name": "产品A_营销关键词",
  "description": "针对产品A的营销关键词集合",
  "keywords": ["关键词1", "关键词2"],
  "category": "产品营销",
  "tags": ["重要"],
  "created_at": "2024-03-01T10:00:00",
  "updated_at": "2024-03-01T10:00:00"
}
```

#### 1.4 更新关键词集合
```http
PUT /api/v1/keywords/universe/{universe_id}
Content-Type: application/json

{
  "name": "产品A_营销关键词_v2",
  "keywords": ["新关键词1", "新关键词2"],
  "category": "产品营销"
}
```

#### 1.5 删除关键词集合
```http
DELETE /api/v1/keywords/universe/{universe_id}
```

---

### 2. 社交媒体爬虫模块

#### 2.1 查询社交媒体内容（支持多平台）
```http
POST /api/v1/search/social-media
Content-Type: application/json

{
  "keyword": "产品A功能1",
  "platforms": ["reddit", "twitter", "linkedin"],
  "limit_per_page": 10,
  "pages": 3,
  "filters": {
    "min_engagement": 5,
    "max_age_days": 30,
    "language": "zh,en"
  }
}
```

**响应：**
```json
{
  "success": true,
  "keyword": "产品A功能1",
  "search_id": "uuid",
  "total_results": 45,
  "results_per_platform": {
    "reddit": {
      "count": 20,
      "posts": [
        {
          "post_id": "reddit_xyz123",
          "platform": "reddit",
          "title": "有人用过产品A吗？",
          "content": "我最近在评估产品A...",
          "author": "username",
          "url": "https://reddit.com/r/xxx/post_id",
          "engagement": {"upvotes": 120, "comments": 45},
          "created_at": "2024-02-28T10:00:00"
        }
      ]
    },
    "twitter": {
      "count": 15,
      "posts": [...]
    },
    "linkedin": {
      "count": 10,
      "posts": [...]
    }
  },
  "created_at": "2024-03-01T10:00:00"
}
```

#### 2.2 获取搜索历史
```http
GET /api/v1/search/history?limit=20&offset=0
```

---

### 3. AI 相关性评判模块

#### 3.1 评判单条内容的相关性
```http
POST /api/v1/ai/evaluate-relevance
Content-Type: application/json

{
  "post_id": "reddit_xyz123",
  "content": "我最近在评估产品A，想知道有没有替代方案",
  "product_description": "产品A是一个营销自动化工具，专注于社交媒体内容管理和AI生成回复",
  "context": "这是来自Reddit的帖子，讨论营销工具"
}
```

**响应：**
```json
{
  "success": true,
  "post_id": "reddit_xyz123",
  "is_relevant": true,
  "relevance_score": 0.85,
  "confidence": 0.92,
  "reasoning": "帖子讨论的营销工具选型与我们的产品直接相关",
  "suggested_angle": "可以突出产品A的AI生成回复功能和易用性",
  "analysis": {
    "sentiment": "positive",
    "intent": "product_evaluation",
    "urgency": "medium"
  }
}
```

---

### 4. AI 回复生成模块

#### 4.1 生成针对性回复
```http
POST /api/v1/ai/generate-reply
Content-Type: application/json

{
  "post_id": "reddit_xyz123",
  "original_content": "我最近在评估产品A，想知道有没有替代方案",
  "author": "user123",
  "platform": "reddit",
  "product_info": {
    "name": "产品A",
    "key_features": ["AI 生成回复", "多平台支持", "自动发布"],
    "target_audience": "营销团队"
  },
  "tone": "professional",
  "approach": "helpful_expert",
  "max_length": 300
}
```

**响应：**
```json
{
  "success": true,
  "post_id": "reddit_xyz123",
  "generated_reply": "感谢你的问题！我正好用过产品A...",
  "reply_confidence": 0.88,
  "metrics": {
    "word_count": 180,
    "tone_match": 0.92,
    "sentiment": "positive",
    "engagement_score": 0.85
  },
  "alternatives": [
    {
      "reply": "替代方案1：...",
      "tone_match": 0.80
    },
    {
      "reply": "替代方案2：...",
      "tone_match": 0.75
    }
  ]
}
```

---

### 5. 消息推送与人工审核模块

#### 5.1 推送消息到 LihuApp（等待审核）
```http
POST /api/v1/notifications/push-for-review
Content-Type: application/json

{
  "message_type": "reply_approval",
  "post_id": "reddit_xyz123",
  "original_content": "原始帖子内容...",
  "generated_reply": "生成的回复...",
  "metadata": {
    "platform": "reddit",
    "relevance_score": 0.85,
    "confidence": 0.92,
    "timestamp": "2024-03-01T10:00:00"
  },
  "callback_url": "https://your-n8n-instance.com/webhook/review-callback"
}
```

**响应：**
```json
{
  "success": true,
  "notification_id": "uuid",
  "lihuo_message_id": "lihu_msg_xyz",
  "status": "sent",
  "message": "消息已推送到 LihuApp，等待用户审核",
  "sent_at": "2024-03-01T10:00:00",
  "expires_at": "2024-03-02T10:00:00"
}
```

#### 5.2 处理 LihuApp webhook 回调（用户审核结果）
```http
POST /api/v1/webhooks/review-callback
Content-Type: application/json

{
  "notification_id": "uuid",
  "action": "approved",  # approved or rejected
  "user_notes": "改一下第二句",
  "timestamp": "2024-03-01T10:30:00",
  "user_id": "user_device_id"
}
```

**响应：**
```json
{
  "success": true,
  "notification_id": "uuid",
  "action_recorded": true,
  "message": "审核结果已记录，n8n 将继续处理"
}
```

#### 5.3 获取待审核消息列表
```http
GET /api/v1/notifications/pending?limit=20&offset=0
```

---

### 6. 发布管理模块

#### 6.1 记录已发布的内容
```http
POST /api/v1/publish/record
Content-Type: application/json

{
  "post_id": "reddit_xyz123",
  "reply": "生成的回复...",
  "platform": "reddit",
  "published_url": "https://reddit.com/comment/abc123",
  "published_at": "2024-03-01T11:00:00",
  "status": "published"
}
```

#### 6.2 获取发布历史
```http
GET /api/v1/publish/history?limit=50&status=published
```

---

## 📈 数据库模型扩展

### 新增表设计

#### 1. KeywordUniverse（关键词宇宙表）
```python
class KeywordUniverse(Base):
    __tablename__ = "keyword_universes"
    
    id: str = Column(String, primary_key=True)
    name: str = Column(String, not_null=True)
    description: str = Column(String)
    category: str = Column(String)
    tags: str = Column(String)  # JSON array
    keywords: str = Column(String, not_null=True)  # JSON array
    created_at: datetime = Column(DateTime, default=datetime.utcnow)
    updated_at: datetime = Column(DateTime, onupdate=datetime.utcnow)
```

#### 2. SocialMediaPost（社交媒体帖子表）
```python
class SocialMediaPost(Base):
    __tablename__ = "social_media_posts"
    
    id: str = Column(String, primary_key=True)
    post_id: str = Column(String, unique=True)
    platform: str = Column(String)  # reddit, twitter, linkedin
    title: str = Column(String)
    content: str = Column(Text)
    author: str = Column(String)
    url: str = Column(String)
    engagement: str = Column(String)  # JSON
    relevance_score: float = Column(Float)
    is_relevant: bool = Column(Boolean, nullable=True)
    relevance_reasoning: str = Column(String)
    created_at: datetime = Column(DateTime)
    fetched_at: datetime = Column(DateTime, default=datetime.utcnow)
```

#### 3. GeneratedReply（生成回复表）
```python
class GeneratedReply(Base):
    __tablename__ = "generated_replies"
    
    id: str = Column(String, primary_key=True)
    post_id: str = Column(String, ForeignKey("social_media_posts.id"))
    original_reply: str = Column(Text)
    current_reply: str = Column(Text)  # 可能被用户修改
    status: str = Column(String)  # pending, approved, rejected, published
    confidence: float = Column(Float)
    review_status: str = Column(String)  # pending_review, approved, rejected
    user_notes: str = Column(String)
    published_url: str = Column(String, nullable=True)
    published_at: datetime = Column(DateTime, nullable=True)
    created_at: datetime = Column(DateTime, default=datetime.utcnow)
    updated_at: datetime = Column(DateTime, onupdate=datetime.utcnow)
```

#### 4. ReviewNotification（审核通知表）
```python
class ReviewNotification(Base):
    __tablename__ = "review_notifications"
    
    id: str = Column(String, primary_key=True)
    reply_id: str = Column(String, ForeignKey("generated_replies.id"))
    lihuo_message_id: str = Column(String, nullable=True)
    status: str = Column(String)  # sent, acknowledged, approved, rejected, expired
    callback_url: str = Column(String)
    expires_at: datetime = Column(DateTime)
    result: str = Column(String)  # approved, rejected
    user_notes: str = Column(String)
    created_at: datetime = Column(DateTime, default=datetime.utcnow)
    callback_received_at: datetime = Column(DateTime, nullable=True)
```

#### 5. SearchSession（搜索会话表 - 扩展）
```python
class SearchSession(Base):
    __tablename__ = "search_sessions"
    
    id: str = Column(String, primary_key=True)
    universe_id: str = Column(String, ForeignKey("keyword_universes.id"))
    keyword: str = Column(String)
    platforms: str = Column(String)  # JSON array
    pages: int = Column(Integer)
    total_results: int = Column(Integer)
    relevant_count: int = Column(Integer)
    status: str = Column(String)  # in_progress, completed, failed
    error_message: str = Column(String, nullable=True)
    duration_seconds: float = Column(Float)
    created_at: datetime = Column(DateTime, default=datetime.utcnow)
    completed_at: datetime = Column(DateTime, nullable=True)
```

---

## 🔄 工作流执行过程

### n8n 工作流步骤（推荐实现）

```
1. [定时触发] - 每天 9:00 AM
   ↓
2. [HTTP] GET /api/v1/keywords/universe/{selected_universe_id}
   获取要使用的关键词集合
   ↓
3. [Loop] 循环关键词数组
   │
   ├─→ 4. [HTTP] POST /api/v1/search/social-media
   │       发送：keyword, platforms=["reddit","twitter","linkedin"], pages=3
   │       接收：45 个帖子
   │
   ├─→ 5. [Loop] 对每个帖子
   │       │
   │       ├─→ 6. [HTTP] POST /api/v1/ai/evaluate-relevance
   │       │       发送：帖子内容 + 产品信息
   │       │       接收：是否相关 + 评分
   │       │
   │       ├─→ 7. [Condition] if relevance_score > 0.7
   │       │       │
   │       │       ├─→ True:
   │       │       │   │
   │       │       │   ├─→ 8. [HTTP] POST /api/v1/ai/generate-reply
   │       │       │   │       生成回复
   │       │       │   │
   │       │       │   ├─→ 9. [HTTP] POST /api/v1/notifications/push-for-review
   │       │       │   │       推送到 LihuApp（获得 notification_id）
   │       │       │   │
   │       │       │   ├─→ 10. [Wait for Webhook] 等待用户审核
   │       │       │        设置 webhook: /api/v1/webhooks/review-callback
   │       │       │        超时：24小时
   │       │       │
   │       │       │   ├─→ 11. [Condition] if webhook_action == "approved"
   │       │       │   │        │
   │       │       │   │        ├─→ 12. [社交媒体 API] 发送回复
   │       │       │   │        │        (使用各平台原生 API)
   │       │       │   │        │
   │       │       │   │        ├─→ 13. [HTTP] POST /api/v1/publish/record
   │       │       │   │                 记录已发布
   │       │       │   │
   │       │       │   └─→ else: 跳过发布
   │       │       │
   │       │       └─→ False: 跳过此帖子
   │
   ├─→ 14. [End Loop]
   │
   ├─→ 15. [HTTP] GET /api/v1/search/history
   │        获取本次搜索的统计数据
   │
   └─→ 16. [完成] 发送总结通知
```

---

## 💾 数据流和存储

### 完整的数据流向

```
社交媒体平台
    ↓
API: /search/social-media
    ↓ (存储)
SocialMediaPost 表
    ↓
API: /ai/evaluate-relevance
    ↓ (更新)
SocialMediaPost 表 (relevance_score, is_relevant)
    ↓ (if relevant)
API: /ai/generate-reply
    ↓ (存储)
GeneratedReply 表 (status: pending)
    ↓
API: /notifications/push-for-review
    ↓ (存储)
ReviewNotification 表 (status: sent)
    ↓
LihuApp 推送消息
    ↓ (用户审核)
LihuApp 触发 Webhook
    ↓
API: /webhooks/review-callback
    ↓ (更新)
ReviewNotification + GeneratedReply 表
    ↓ (if approved)
社交媒体发帖 API
    ↓
API: /publish/record
    ↓ (更新)
GeneratedReply 表 (status: published, published_url)
```

---

## 🎯 实现优先级

### Phase 1: 核心功能（第1-2周）
- [ ] 关键词宇宙管理 API（CRUD）
- [ ] 社交媒体爬虫 API（至少 Reddit）
- [ ] 数据库模型扩展
- [ ] 基本的 n8n 集成示例

### Phase 2: AI 和审核（第3-4周）
- [ ] AI 相关性评判 API
- [ ] AI 回复生成 API
- [ ] LihuApp webhook 集成
- [ ] 发布管理 API

### Phase 3: 优化和文档（第5周）
- [ ] 性能优化和缓存
- [ ] 完整的 n8n 工作流示例
- [ ] 详细的用户指南
- [ ] 错误处理和日志完善

---

## 🔧 技术实现建议

### 新增依赖
```
praw>=7.7.0              # Reddit API
tweepy>=4.14.0           # Twitter API
linkedin-api>=2.0.0      # LinkedIn API (optional)
httpx>=0.24.0            # 异步 HTTP 客户端
```

### 新增目录结构
```
app/
├── services/
│   ├── keyword_service.py          # 关键词管理
│   ├── social_media_service.py     # 社交媒体爬虫
│   ├── relevance_service.py        # 相关性评判
│   ├── reply_generation_service.py # 回复生成
│   ├── notification_service.py     # 消息推送
│   └── publish_service.py          # 发布管理
├── integrations/
│   ├── reddit_client.py            # Reddit 集成
│   ├── twitter_client.py           # Twitter 集成
│   ├── lihuo_client.py             # LihuApp 集成
│   └── social_media_base.py        # 基类
├── models/
│   ├── db.py (扩展)
│   └── schemas.py (扩展)
└── api/
    ├── routes.py (扩展)
    └── webhooks.py (新增)
```

---

这个方案完全基于你的需求设计，核心是支持：
1. ✅ 关键词宇宙管理
2. ✅ 多平台社交媒体爬虫（前3页）
3. ✅ AI 相关性评判
4. ✅ AI 回复生成
5. ✅ LihuApp 消息推送
6. ✅ 人工审核流程
7. ✅ 自动发布
