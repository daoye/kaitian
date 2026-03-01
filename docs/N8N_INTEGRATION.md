# n8n 工作流集成指南

## 架构概览

```
┌─────────────────────────────────────────────────────────────┐
│                    n8n Workflow                              │
│  (主控制流程 - 编排所有步骤和逻辑)                          │
└─────────────────────────────────────────────────────────────┘
                          ↓
        ┌─────────────────────────────────────┐
        │  KaiTian API Service (本项目)       │
        │  负责补充 n8n 缺少的能力:          │
        ├─────────────────────────────────────┤
        │  • Web 爬虫 (Crawl4AI)              │
        │  • 社交媒体爬虫 (MediaCrawler)     │
        │  • 数据存储 (SQLite DB)             │
        │  • 社交媒体发帖 (Postiz API)       │
        └─────────────────────────────────────┘
```

## KaiTian 角色定位

KaiTian 是一个**专门的 API 后端**，提供以下能力:

1. **爬虫能力** (n8n 缺少)
   - Crawl4AI: 高级网页爬虫，支持 JavaScript 渲染
   - MediaCrawler: 社交媒体爬虫 (Reddit/Twitter/LinkedIn)

2. **发帖能力** (n8n 缺少)
   - 通过 Postiz 发布到 Reddit/Twitter/LinkedIn

3. **数据存储** (补充)
   - SQLite 数据库存储爬取的帖子
   - 追踪处理状态和历史记录

## API 端点设计

所有 API 都设计用于 n8n 的 HTTP Request 节点调用。

### 爬虫端点

#### 1. 爬取任意 URL
```
POST /api/v1/crawl/url
```

**请求参数:**
```json
{
  "url": "https://example.com",
  "wait_for": ".content"  // 可选：CSS 选择器，等待元素加载
}
```

**响应格式:**
```json
{
  "success": true,
  "url": "https://example.com",
  "content": "# 抓取的内容\n...",  // Markdown 格式
  "raw_html": "<html>...</html>",
  "extracted_data": {...},
  "status_code": 200
}
```

**n8n 中的用法:**
```
HTTP Request 节点 → 
  Method: POST
  URL: http://localhost:8000/api/v1/crawl/url
  Body: {
    "url": "{{ $json.target_url }}",
    "wait_for": ".article"
  }
```

---

#### 2. 爬取 Reddit 板块
```
POST /api/v1/crawl/reddit
```

**请求参数:**
```json
{
  "subreddit": "python",    // 板块名称（不带 /r/）
  "limit": 10,              // 最多获取帖数（1-100）
  "keywords": ["python", "tutorial"]  // 可选：关键词过滤
}
```

**响应格式:**
```json
{
  "success": true,
  "platform": "reddit",
  "subreddit": "python",
  "total_posts": 10,
  "stored_posts": 8,
  "posts": [
    {
      "id": "abc123",
      "source_id": "reddit_post_123",
      "title": "How to learn Python",
      "content": "...",
      "author": "user123",
      "url": "https://reddit.com/r/python/...",
      "matched_keywords": ["python", "tutorial"],
      "status": "pending"
    }
  ]
}
```

**n8n 中的用法:**
```
HTTP Request 节点 →
  Method: POST
  URL: http://localhost:8000/api/v1/crawl/reddit
  Body: {
    "subreddit": "{{ $json.subreddit }}",
    "limit": 15,
    "keywords": ["python", "programming"]
  }
```

---

### 发帖端点

#### 3. 发布到 Reddit
```
POST /api/v1/post/reddit
```

**请求参数:**
```json
{
  "post_id": "kaitian_post_uuid",  // KaiTian 数据库中的帖子 ID
  "reply_text": "Great post! Here's a useful tip..."
}
```

**响应格式:**
```json
{
  "success": true,
  "post_id": "kaitian_post_uuid",
  "platform": "reddit",
  "published": true,
  "published_id": "reddit_comment_abc123",
  "published_at": "2024-03-01T12:00:00"
}
```

**n8n 中的用法:**
```
IF approved = true THEN
  HTTP Request 节点 →
    Method: POST
    URL: http://localhost:8000/api/v1/post/reddit
    Body: {
      "post_id": "{{ $json.post_id }}",
      "reply_text": "{{ $json.generated_reply }}"
    }
```

---

#### 4. 发布到 Twitter
```
POST /api/v1/post/twitter
```

**请求参数:**
```json
{
  "post_id": "kaitian_post_uuid",
  "reply_text": "Great insight!"
}
```

**n8n 中的用法:** 类似 Reddit

---

### 数据管理端点

#### 5. 列表查询帖子
```
GET /api/v1/posts
```

**请求参数:**
```
?status=pending              // 按状态过滤
&platform=reddit             // 按平台过滤
&limit=50                    // 最多返回数量
```

**响应格式:**
```json
{
  "success": true,
  "total": 8,
  "posts": [
    {
      "id": "uuid",
      "source_id": "reddit_123",
      "title": "...",
      "author": "...",
      "status": "pending",
      "relevance_score": null,
      "created_at": "2024-03-01T10:00:00",
      "url": "..."
    }
  ]
}
```

**n8n 中的用法:**
```
HTTP Request 节点 →
  Method: GET
  URL: http://localhost:8000/api/v1/posts?status=pending&platform=reddit
```

---

#### 6. 获取单个帖子
```
GET /api/v1/posts/{post_id}
```

**响应格式:**
```json
{
  "success": true,
  "post": {
    "id": "uuid",
    "source_id": "reddit_123",
    "source_platform": "reddit",
    "title": "...",
    "content": "...",
    "author": "...",
    "url": "...",
    "status": "pending",
    "relevance_score": null,
    "generated_reply": null,
    "created_at": "...",
    "published_at": null
  }
}
```

---

#### 7. 更新帖子
```
PATCH /api/v1/posts/{post_id}
```

**请求参数:**
```json
{
  "status": "analyzed",
  "relevance_score": 0.85,
  "generated_reply": "Great post!"
}
```

**n8n 中的用法:**
```
HTTP Request 节点 →
  Method: PATCH
  URL: http://localhost:8000/api/v1/posts/{{ $json.post_id }}
  Body: {
    "status": "analyzed",
    "relevance_score": "{{ $json.ai_score }}"
  }
```

---

## 典型 n8n 工作流示例

### 工作流 1: Reddit 监控 → AI 判断 → 人工审核 → 发帖

```
1. Schedule (每 30 分钟)
   ↓
2. Call KaiTian: POST /api/v1/crawl/reddit
   Input:
     subreddit: "python"
     limit: 10
     keywords: ["python", "tutorial"]
   Output: posts[]
   
3. For Each Post
   ↓
4. Call AI Service (n8n 调用 OpenAI 等)
   Input: post.title + post.content
   Output: relevance_score, reason
   
5. Update Post: PATCH /api/v1/posts/{id}
   Input:
     status: "analyzed"
     relevance_score: relevance_score
   
6. IF relevance_score > 0.7
   ↓
7. Generate Reply (AI)
   Input: post content
   Output: reply_text
   
8. Update Post: PATCH /api/v1/posts/{id}
   Input:
     status: "reply_generated"
     generated_reply: reply_text
   
9. Send to Slack/Email for Human Review
   
10. IF user approved in Slack
   ↓
11. Call KaiTian: POST /api/v1/post/reddit
    Input:
      post_id: post.id
      reply_text: reply_text
    
12. Update Post: PATCH /api/v1/posts/{id}
    Input:
      status: "published"
```

**n8n JSON 节点配置示例:**
```json
{
  "schedule": {
    "interval": 30,
    "unit": "minutes"
  },
  "nodes": [
    {
      "name": "Crawl Reddit",
      "type": "n8n-nodes-base.httpRequest",
      "typeVersion": 4.1,
      "position": [250, 300],
      "parameters": {
        "method": "POST",
        "url": "http://kaitian:8000/api/v1/crawl/reddit",
        "sendBody": true,
        "specifyBody": "json",
        "jsonBody": {
          "subreddit": "python",
          "limit": 10,
          "keywords": ["python", "tutorial"]
        }
      }
    }
  ]
}
```

---

### 工作流 2: 手动触发爬取

```
1. Webhook Trigger (手动或外部触发)
   ↓
2. Input: { target_url, target_subreddit }
   ↓
3. IF target_url provided
   → Call POST /api/v1/crawl/url
   ELSE IF target_subreddit provided
   → Call POST /api/v1/crawl/reddit
   ↓
4. Store results
   ↓
5. Send notification
```

---

## 部署和连接

### KaiTian 启动
```bash
python main.py
# 服务运行在 http://localhost:8000
# API 文档: http://localhost:8000/docs
```

### n8n 中配置 KaiTian

在 n8n 的 HTTP Request 节点中:
```
URL: http://kaitian:8000/api/v1/crawl/reddit
    (如果 n8n 和 KaiTian 都在 Docker，使用容器名)
    
或

URL: http://192.168.x.x:8000/api/v1/crawl/reddit
    (使用 KaiTian 的实际 IP)
```

---

## 数据流向

```
Reddit
  ↓
MediaCrawler (KaiTian)
  ↓
SQLite Database (KaiTian)
  ↓
n8n 查询: GET /api/v1/posts?status=pending
  ↓
n8n 调用 AI 服务进行相关性判断
  ↓
n8n 更新: PATCH /api/v1/posts/{id}
  ↓
n8n 生成回复 (AI)
  ↓
n8n 通知人工审核
  ↓
人工批准 (Slack 或其他)
  ↓
n8n 调用: POST /api/v1/post/reddit
  ↓
Postiz (KaiTian)
  ↓
Reddit (发布回复)
```

---

## 错误处理

所有端点返回统一的错误格式:

```json
{
  "success": false,
  "error": "错误描述信息"
}
```

**n8n 中的错误处理:**
```
HTTP Request 节点
  ↓
IF response.success = false
  → Send error notification
  → Log to monitoring
ELSE
  → Continue processing
```

---

## 监控和日志

### 查看 KaiTian 日志
```bash
# 实时日志
tail -f logs/kaitian.log

# 设置日志级别
LOG_LEVEL=DEBUG python main.py
```

### n8n 中的监控
```
调用 KaiTian 后 → 保存响应数据 →
  IF response.success = false
    → 记录错误到数据库
    → 发送告警邮件
    → 记录到 ELK/Datadog
```

---

## 性能优化建议

1. **爬虫优化**
   - 使用 `limit` 参数限制爬取数量
   - 设置合理的超时参数
   - 考虑在 KaiTian 配置中调整并发数

2. **n8n 工作流优化**
   - 使用 Batch 节点处理多个帖子
   - 使用 Wait 节点实现速率限制
   - 使用 Set 节点存储中间结果

3. **数据库优化**
   - 定期清理过期数据
   - 为常用查询添加索引
   - 定期备份 kaitian.db

---

## 常见问题

**Q: n8n 无法连接到 KaiTian**
A: 检查 KaiTian 是否运行，确认 URL 和端口正确，检查防火墙设置

**Q: 爬虫超时**
A: 在环境变量中增加超时时间，或在请求中指定 `wait_for` 参数

**Q: 发帖失败**
A: 检查 Postiz API 配置，确保 API 密钥有效

**Q: 数据库速度变慢**
A: 使用 GET /api/v1/posts?limit=10 限制返回数据量，考虑添加数据库索引

---

## 总结

KaiTian 作为 n8n 的**专业爬虫和发帖扩展**:

✅ 提供 n8n 缺少的爬虫能力
✅ 提供 n8n 缺少的发帖能力
✅ 管理数据和处理状态
✅ 通过简单 HTTP API 集成
✅ 完全由 n8n 工作流控制

n8n 负责:
- 流程控制和编排
- AI 处理 (相关性判断、回复生成)
- 人工审核
- 其他业务逻辑

KaiTian 负责:
- 网页爬虫
- 社交媒体爬虫
- 发帖到社交媒体
- 数据存储
