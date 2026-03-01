# KaiTian 系统设计文档

## 项目概述

KaiTian 是一个智能营销自动化引擎，结合了网页爬虫、数据持久化和 AI 内容生成功能。它为营销团队提供了一个完整的解决方案，从发现营销机会到自动生成回复和发布内容。

### 核心价值

- **发现机会**：自动发现相关的社交媒体帖子
- **生成内容**：使用 LangChain + LLM 生成高质量的营销文章
- **管理数据**：持久化存储所有数据和交互历史
- **集成编排**：与 n8n 等工作流工具无缝集成

## 架构设计

### 整体架构

```
┌─────────────────────────────────────────────────────────┐
│                   用户/营销团队                          │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                   n8n 工作流编排                         │
├─────────────────────────────────────────────────────────┤
│ • 定时爬取 → 分析相关性 → 生成内容 → 审核 → 发布      │
└─────────────────────────────────────────────────────────┘
                            ↓
┌─────────────────────────────────────────────────────────┐
│                    KaiTian API                           │
├─────────────────────────────────────────────────────────┤
│ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐     │
│ │   爬虫模块   │ │  数据管理    │ │  生成模块    │     │
│ │ (Crawl4AI)   │ │  (数据库)    │ │ (LangChain)  │     │
│ └──────────────┘ └──────────────┘ └──────────────┘     │
└─────────────────────────────────────────────────────────┘
                            ↓
┌──────────────┬──────────────┬──────────────┐
│   SQLite     │   Redis      │  LLM 服务    │
│   数据库     │   缓存       │ (OpenAI)     │
└──────────────┴──────────────┴──────────────┘
```

### 模块组件

#### 1. FastAPI 应用层
```
app/
├── core/
│   ├── config.py           # 配置管理
│   ├── app.py              # FastAPI 应用程序
│   ├── database.py         # 数据库连接
│   └── logging.py          # 日志配置
├── api/
│   └── routes.py           # API 路由
│       ├── /health         # 健康检查
│       ├── /crawl/*        # 爬虫端点
│       ├── /posts/*        # 数据管理端点
│       └── /generate/*     # 内容生成端点
├── models/
│   ├── db.py               # 数据库模型
│   └── schemas.py          # Pydantic 数据模型
├── services/
│   ├── database_service.py # 数据库服务
│   ├── content_generation.py # 内容生成服务
│   └── prompt_templates.py # Prompt 模板
├── integrations/
│   ├── crawl4ai_client.py  # Crawl4AI 集成
│   └── llm_provider.py     # LLM 提供商管理
└── utils/
    └── helpers.py          # 辅助函数
```

#### 2. 爬虫模块
- **Crawl4AI**：JavaScript 渲染和内容提取
- **特性**：
  - 支持动态网页
  - 自动 Markdown 转换
  - 超时和错误处理

#### 3. 数据模型

**Post（帖子）**
```python
class Post(Base):
    id: str                    # 唯一标识
    title: str                 # 标题
    content: str               # 内容
    source: str                # 来源 (reddit, twitter, etc)
    source_id: str             # 来源 ID
    url: str                   # URL
    status: str                # 状态 (pending, fetched, analyzed, published)
    relevance_score: float     # 相关性评分
    generated_reply: str       # 生成的回复
    created_at: datetime       # 创建时间
    updated_at: datetime       # 更新时间
```

#### 4. 内容生成模块

**LangChain 链式处理**
```
输入参数
   ↓
[验证和预处理]
   ↓
[Prompt 构建]
   ↓
[LLM 调用] → OpenAI/Claude/Gemini
   ↓
[输出解析]
   ↓
[内容优化] (可选)
   ↓
[缓存存储]
   ↓
返回结果
```

## API 设计

### 爬虫 API

**POST /api/v1/crawl/url**
- 爬取单个 URL
- 支持 JavaScript 渲染
- 自动 Markdown 转换

**POST /api/v1/crawl/reddit**
- 爬取 Reddit 帖子
- 按关键词搜索
- 批量处理

### 数据管理 API

**GET /api/v1/posts**
- 列出帖子
- 支持过滤、排序、分页
- 支持状态查询

**PATCH /api/v1/posts/{id}**
- 更新帖子状态
- 更新相关性评分
- 更新生成的回复

### 内容生成 API

**POST /api/v1/generate/article** (新增)
- 生成营销文章
- 支持多语言
- 支持 SEO 优化

**POST /api/v1/generate/articles/batch** (新增)
- 批量生成文章
- 异步处理

**POST /api/v1/generate/optimize** (新增)
- SEO 优化现有内容
- 关键词分析

## 核心功能设计

### 1. 智能爬虫

**特性**
- 动态内容渲染（JavaScript）
- 智能内容提取
- Markdown 自动转换
- 错误恢复和重试

**流程**
```
请求 URL
  ↓
获取 HTML
  ↓
执行 JavaScript
  ↓
提取内容
  ↓
转换 Markdown
  ↓
存储到数据库
```

### 2. 数据管理

**状态流转**
```
pending (待处理)
   ↓
fetched (已抓取)
   ↓
analyzed (已分析)
   ↓
published (已发布)
```

**查询优化**
- 索引字段：status, created_at, source
- 支持全文搜索
- 分页查询

### 3. AI 内容生成

**Prompt 工程**
```
主题 + 关键词 + 目标受众 + 语气风格
   ↓
LangChain 链式处理
   ↓
LLM 推理
   ↓
内容输出 + SEO 优化
```

**内容质量检查**
- 关键词密度分析
- 可读性评分
- SEO 评分

## 部署架构

### 开发环境

```bash
# 启动所有服务
python start.py

# 或单独启动 KaiTian
python main.py
```

**依赖**
- Python 3.9+
- FastAPI
- SQLAlchemy
- LangChain
- OpenAI SDK

### 生产环境

**Docker 部署**
```yaml
services:
  kaitian:
    image: kaitian:latest
    ports:
      - "8000:8000"
    environment:
      - DATABASE_URL=sqlite:///./kaitian.db
      - OPENAI_API_KEY=<your-key>
    volumes:
      - ./data:/app/data
```

**性能优化**
- Redis 缓存
- 连接池
- 异步处理
- 任务队列 (Celery)

## 安全设计

### 认证和授权

```python
@app.get("/api/v1/protected")
async def protected_endpoint(
    api_key: str = Header(...)
):
    if not verify_api_key(api_key):
        raise HTTPException(status_code=401)
```

### 数据保护

- API 密钥在环境变量中管理
- 敏感数据加密存储
- 日志中过滤敏感信息

### 速率限制

```python
limiter = Limiter(key_func=get_remote_address)

@app.post("/api/v1/generate/article")
@limiter.limit("10/minute")
async def generate_article(request):
    pass
```

## 性能考虑

### 缓存策略

**Redis 缓存层**
```python
cache_key = f"article:{topic}:{keywords}"
cached = redis.get(cache_key)
if cached:
    return json.loads(cached)

# 生成内容...
redis.set(cache_key, json.dumps(result), ex=86400)
```

**缓存键策略**
- 按主题、关键词、语言组合
- TTL：24 小时
- 支持手动清除

### 异步处理

**长时间运行的任务**
```python
@app.post("/api/v1/generate/articles/batch/async")
async def generate_batch_async(requests):
    task_id = generate_task.delay(requests)
    return {"task_id": task_id, "status_url": f"/status/{task_id}"}
```

### 监控和日志

```python
# 请求日志
logger.info(f"Article generated: {topic}, "
            f"time: {generation_time}s, "
            f"tokens: {tokens_used}")

# 性能指标
metrics.record(
    name="article_generation_time",
    value=generation_time,
    labels={"model": model_name}
)
```

## 扩展性设计

### 支持多个 LLM 提供商

**接口设计**
```python
class LLMProvider(ABC):
    @abstractmethod
    async def generate(self, prompt: str) -> str:
        pass

class OpenAIProvider(LLMProvider):
    async def generate(self, prompt: str) -> str:
        # OpenAI 实现

class AnthropicProvider(LLMProvider):
    async def generate(self, prompt: str) -> str:
        # Claude 实现
```

### 支持新的内容类型

**可扩展的内容生成框架**
```python
class ContentGenerator(ABC):
    @abstractmethod
    async def generate(self, request) -> Response:
        pass

class ArticleGenerator(ContentGenerator):
    pass

class SocialMediaPostGenerator(ContentGenerator):
    pass

class EmailCopyGenerator(ContentGenerator):
    pass
```

### 支持新的数据源

**爬虫适配器模式**
```python
class CrawlerAdapter(ABC):
    @abstractmethod
    async def crawl(self, query: str) -> List[Post]:
        pass

class RedditCrawler(CrawlerAdapter):
    pass

class TwitterCrawler(CrawlerAdapter):
    pass

class LinkedInCrawler(CrawlerAdapter):
    pass
```

## 集成流程

### n8n 工作流示例

**自动文章生成工作流**

```
1. 定时触发器 (每天 9:00)
   ↓
2. 获取关键词列表
   ↓
3. POST /api/v1/generate/article
   ├─ 主题：{关键词}
   ├─ 目标受众：{目标受众}
   └─ 语言：{语言}
   ↓
4. 保存到数据库
   ↓
5. 发送电子邮件通知
   ↓
6. 发送 Slack 通知
```

### 与爬虫的集成

```
1. 爬取帖子
   ↓
2. 调用 /api/v1/generate/article
   生成对应的回复文章
   ↓
3. 评分和过滤
   ↓
4. 人工审核
   ↓
5. 发布
```

## 错误处理

### 错误分类

| 错误码 | HTTP 状态 | 说明 | 处理方法 |
|--------|----------|------|---------|
| INVALID_INPUT | 400 | 输入验证失败 | 返回详细错误信息 |
| NOT_FOUND | 404 | 资源不存在 | 检查 ID |
| API_ERROR | 500 | LLM API 失败 | 重试或使用备用提供商 |
| RATE_LIMIT | 429 | 超过速率限制 | 实现退避策略 |
| TIMEOUT | 504 | 请求超时 | 增加超时或分解任务 |

### 重试策略

```python
async def call_llm_with_retry(prompt: str, max_retries: int = 3):
    for attempt in range(max_retries):
        try:
            return await llm.generate(prompt)
        except RateLimitError:
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)  # 指数退避
                continue
            raise
```

## 测试策略

### 单元测试

```python
@pytest.mark.asyncio
async def test_generate_article():
    service = ContentGenerationService()
    result = await service.generate_article(
        ArticleGenerationRequest(
            topic="Python",
            keywords=["Python", "编程"],
            language="zh"
        )
    )
    assert result.success
    assert len(result.content.title) > 0
```

### 集成测试

```python
@pytest.mark.integration
async def test_full_workflow():
    # 1. 爬取
    # 2. 生成内容
    # 3. 保存
    # 4. 验证
```

### 压力测试

```python
async def stress_test():
    tasks = [
        generate_article(request)
        for _ in range(100)
    ]
    results = await asyncio.gather(*tasks)
    assert all(r.success for r in results)
```

## 监控和运维

### 健康检查

```
GET /api/v1/health
→ {
    "status": "ok",
    "version": "0.1.0",
    "timestamp": "2024-03-01T10:00:00"
  }
```

### 日志级别

- **DEBUG**：详细开发信息
- **INFO**：一般信息（请求、处理完成）
- **WARNING**：警告（缓存失败、降级）
- **ERROR**：错误（API 失败）
- **CRITICAL**：严重错误（数据库离线）

### 指标收集

```
• 请求延迟 (p50, p95, p99)
• 生成文章耗时
• API 错误率
• LLM 调用成功率
• 缓存命中率
```

## 未来优化方向

### 短期（1-2 周）

- [ ] 实现 Redis 缓存
- [ ] 添加身份验证和授权
- [ ] 增加 API 速率限制
- [ ] 添加更多测试用例

### 中期（1-2 月）

- [ ] 支持 Claude 和 Gemini
- [ ] 实现异步任务队列
- [ ] 添加 Webhook 支持
- [ ] 实现内容分版本管理

### 长期（3-6 月）

- [ ] 微调专门的文章生成模型
- [ ] 支持多媒体内容生成（图片、视频）
- [ ] 增加内容 A/B 测试功能
- [ ] 构建内容库和知识库

## 参考资源

- [FastAPI 官方文档](https://fastapi.tiangolo.com/)
- [SQLAlchemy 文档](https://docs.sqlalchemy.org/)
- [LangChain 官方文档](https://python.langchain.com/)
- [OpenAI API 文档](https://platform.openai.com/docs)
- [n8n 集成文档](https://docs.n8n.io/)
