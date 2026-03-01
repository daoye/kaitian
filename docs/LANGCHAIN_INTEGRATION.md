# LangChain 集成设计文档

## 概述

本文档描述了 KaiTian 中 LangChain 的集成方案，用于自动生成营销文章和内容。

## 架构设计

### 核心组件

```
用户/n8n
   ↓
[文章生成 API]
   ↓
[LangChain 处理链]
├─ 输入处理 (Input Processing)
├─ 内容分析 (Content Analysis)
├─ 文章生成 (Article Generation)
└─ 输出优化 (Output Refinement)
   ↓
[输出结果]
```

### 模块结构

```
app/
├── services/
│   └── content_generation.py      # 核心文章生成服务
├── chains/
│   ├── __init__.py
│   ├── article_chain.py            # 文章生成链
│   ├── prompt_templates.py         # Prompt 模板
│   └── analyzers.py                # 内容分析器
├── models/
│   ├── schemas.py (扩展)           # 添加文章相关的数据模型
└── api/
    └── routes.py (扩展)            # 添加文章生成 API 端点
```

## 核心功能设计

### 1. 文章生成链 (Article Generation Chain)

#### 输入参数
```python
{
    "topic": str,              # 文章主题
    "keywords": List[str],     # 关键词列表
    "tone": str,               # 语气风格: "professional", "casual", "technical"
    "length": str,             # 长度: "short" (300-500字), "medium" (500-1000字), "long" (1000+字)
    "language": str,           # 语言: "zh" (中文), "en" (英文)
    "target_audience": str,    # 目标受众
    "max_tokens": int = 2000   # 最大令牌数（可选）
}
```

#### 处理流程

1. **输入验证与预处理**
   - 验证主题和关键词
   - 标准化参数
   - 记录请求日志

2. **内容分析**
   - 分析关键词之间的关系
   - 确定文章结构
   - 规划内容框架

3. **文章生成**
   - 使用 LangChain 构建多步骤链
   - 集成 LLM (OpenAI/其他)
   - 生成初稿

4. **内容优化**
   - SEO 优化检查
   - 语法和风格检查
   - 关键词密度调整

#### 输出格式
```python
{
    "success": bool,
    "content": {
        "title": str,           # 文章标题
        "body": str,            # 文章正文（Markdown 格式）
        "summary": str,         # 文章摘要
        "keywords": List[str],  # 优化后的关键词
        "word_count": int,      # 字数统计
        "seo_score": float,     # SEO 评分 (0-100)
    },
    "metadata": {
        "generation_time": float,  # 生成耗时（秒）
        "model": str,              # 使用的模型
        "tokens_used": int,        # 使用的令牌数
    },
    "error": Optional[str]     # 错误信息（如有）
}
```

### 2. Prompt 模板

#### 文章生成 Prompt
```
主题：{topic}
关键词：{keywords}
语言：{language}
目标受众：{target_audience}
语气风格：{tone}
长度要求：{length}

请生成一篇符合以上要求的{language}文章：

1. 标题要吸引人，包含至少一个关键词
2. 内容要自然融入所有关键词
3. 结构清晰，包含引言、正文、结论
4. 符合{tone}的语气风格
5. 对{target_audience}有吸引力

生成的文章应该是 Markdown 格式。
```

#### SEO 优化 Prompt
```
分析以下文章并优化其 SEO：

文章：{article}
关键词：{keywords}
目标受众：{target_audience}

请提供：
1. SEO 评分 (0-100)
2. 关键词使用建议
3. 标题优化建议
4. 优化后的文章版本

返回 JSON 格式的结果。
```

### 3. 支持的 LLM 提供商

#### OpenAI (推荐)
```python
from langchain_openai import ChatOpenAI

llm = ChatOpenAI(
    model_name="gpt-4",  # 或 "gpt-3.5-turbo"
    api_key=settings.openai_api_key,
    temperature=0.7,
)
```

#### Azure OpenAI
```python
from langchain_openai import AzureChatOpenAI

llm = AzureChatOpenAI(
    deployment_name="your-deployment",
    api_key=settings.azure_openai_key,
)
```

#### Anthropic Claude
```python
from langchain_anthropic import ChatAnthropic

llm = ChatAnthropic(
    model="claude-3-sonnet-20240229",
    api_key=settings.anthropic_api_key,
)
```

#### 本地模型 (Ollama)
```python
from langchain_ollama import OllamaLLM

llm = OllamaLLM(model="llama2")
```

### 4. 链的构建示例

```python
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain_openai import ChatOpenAI

# 初始化 LLM
llm = ChatOpenAI(model_name="gpt-4", temperature=0.7)

# 定义 Prompt 模板
article_prompt = PromptTemplate(
    input_variables=["topic", "keywords", "tone", "length", "language"],
    template="""
    主题：{topic}
    关键词：{keywords}
    ...
    """
)

# 构建链
article_chain = LLMChain(llm=llm, prompt=article_prompt)

# 执行链
result = article_chain.run(
    topic="Python 最佳实践",
    keywords=["Python", "代码质量", "最佳实践"],
    tone="professional",
    length="medium",
    language="zh"
)
```

## API 端点设计

### 端点 1: 生成文章

```
POST /api/v1/generate/article
Content-Type: application/json

{
    "topic": "AI 在营销中的应用",
    "keywords": ["AI", "营销", "自动化"],
    "tone": "professional",
    "length": "medium",
    "language": "zh",
    "target_audience": "营销团队负责人"
}
```

**响应示例:**
```json
{
    "success": true,
    "content": {
        "title": "AI 如何改变现代营销：从自动化到个性化",
        "body": "# AI 如何改变现代营销...",
        "summary": "本文探讨了 AI 在营销中的应用...",
        "keywords": ["AI", "营销", "自动化", "个性化"],
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

### 端点 2: 批量生成文章

```
POST /api/v1/generate/articles/batch
Content-Type: application/json

{
    "articles": [
        {
            "topic": "主题1",
            "keywords": ["关键词1"],
            ...
        },
        {
            "topic": "主题2",
            "keywords": ["关键词2"],
            ...
        }
    ]
}
```

### 端点 3: 优化现有内容

```
POST /api/v1/generate/optimize
Content-Type: application/json

{
    "content": "现有文章内容...",
    "keywords": ["关键词1", "关键词2"],
    "optimization_type": "seo"  # "seo", "readability", "engagement"
}
```

## 环境配置

在 `.env` 文件中添加：

```bash
# LangChain 配置
LANGCHAIN_API_KEY=your_api_key_here
LANGCHAIN_TRACING_V2=true

# LLM 提供商选择
LLM_PROVIDER=openai  # openai, azure, anthropic, ollama

# OpenAI 配置
OPENAI_API_KEY=your_openai_key
OPENAI_MODEL=gpt-4
OPENAI_TEMPERATURE=0.7

# Azure OpenAI 配置 (如果使用 Azure)
AZURE_OPENAI_KEY=your_azure_key
AZURE_OPENAI_ENDPOINT=your_azure_endpoint
AZURE_DEPLOYMENT_NAME=your_deployment

# Anthropic 配置 (如果使用 Claude)
ANTHROPIC_API_KEY=your_anthropic_key
ANTHROPIC_MODEL=claude-3-sonnet-20240229

# 内容生成默认配置
CONTENT_GENERATION_MAX_TOKENS=2000
CONTENT_GENERATION_TEMPERATURE=0.7
CONTENT_GENERATION_TIMEOUT=30
```

## 错误处理

所有文章生成端点都应该返回标准的错误响应：

```json
{
    "success": false,
    "error": "错误消息",
    "error_code": "INVALID_TOPIC",
    "details": {
        "field": "topic",
        "message": "主题不能为空"
    }
}
```

### 常见错误码

| 错误码 | HTTP 状态 | 说明 |
|--------|----------|------|
| INVALID_TOPIC | 400 | 主题无效或为空 |
| INVALID_KEYWORDS | 400 | 关键词格式不正确 |
| INVALID_LANGUAGE | 400 | 不支持的语言 |
| API_ERROR | 500 | LLM API 调用失败 |
| TIMEOUT | 504 | 请求超时 |
| RATE_LIMIT | 429 | 超过速率限制 |

## 性能考虑

### 缓存策略

使用 Redis 缓存相同的生成请求：

```python
cache_key = f"article:{topic}:{keywords}:{language}:{tone}"
cached_result = redis_client.get(cache_key)

if cached_result:
    return json.loads(cached_result)

# 生成内容...
redis_client.set(cache_key, json.dumps(result), ex=86400)  # 24小时过期
```

### 异步处理

对于长时间运行的任务，使用异步队列（Celery/RQ）：

```python
@router.post("/api/v1/generate/articles/batch/async")
async def generate_articles_async(request: BatchGenerationRequest):
    task_id = generate_articles_task.delay(request.dict())
    return {
        "task_id": str(task_id),
        "status_url": f"/api/v1/generate/status/{task_id}"
    }

@router.get("/api/v1/generate/status/{task_id}")
async def get_generation_status(task_id: str):
    task = generate_articles_task.AsyncResult(task_id)
    return {
        "task_id": task_id,
        "status": task.state,
        "result": task.result if task.ready() else None
    }
```

## 安全性

### API 密钥保护

所有 LLM 提供商的 API 密钥应该：
- ✅ 存储在环境变量中
- ✅ 不在日志中暴露
- ✅ 使用加密存储
- ✅ 定期轮换

### 内容审查

生成的内容应该经过审查：

```python
async def review_generated_content(content: str) -> ReviewResult:
    # 检查敏感内容
    # 检查 SEO 合规性
    # 检查版权问题
    pass
```

### 使用限制

实施速率限制防止滥用：

```python
from slowapi import Limiter
from slowapi.util import get_remote_address

limiter = Limiter(key_func=get_remote_address)

@router.post("/api/v1/generate/article")
@limiter.limit("10/minute")
async def generate_article(request: ArticleGenerationRequest):
    pass
```

## 成本管理

### 令牌计数

追踪令牌使用量以管理 API 成本：

```python
from langchain.callbacks import get_openai_callback

with get_openai_callback() as cb:
    result = article_chain.run(...)
    
    print(f"总令牌: {cb.total_tokens}")
    print(f"提示令牌: {cb.prompt_tokens}")
    print(f"完成令牌: {cb.completion_tokens}")
    print(f"成本: ${cb.total_cost}")
```

### 成本限制

设置每月或每天的成本限制：

```python
async def check_cost_limit():
    today_cost = calculate_today_cost()
    if today_cost > settings.daily_cost_limit:
        raise HTTPException(
            status_code=429,
            detail="已达到今日成本限制"
        )
```

## 测试

### 单元测试示例

```python
import pytest
from app.services.content_generation import generate_article

@pytest.mark.asyncio
async def test_generate_article():
    result = await generate_article(
        topic="Python 最佳实践",
        keywords=["Python", "最佳实践"],
        language="zh",
        tone="professional"
    )
    
    assert result["success"] is True
    assert "content" in result
    assert "title" in result["content"]
    assert "body" in result["content"]
    assert len(result["content"]["title"]) > 0

@pytest.mark.asyncio
async def test_invalid_topic():
    result = await generate_article(
        topic="",  # 无效的空主题
        keywords=["测试"],
        language="zh"
    )
    
    assert result["success"] is False
    assert "error" in result
```

### 集成测试

```python
@pytest.mark.integration
async def test_article_generation_api():
    response = await client.post(
        "/api/v1/generate/article",
        json={
            "topic": "AI 营销",
            "keywords": ["AI", "营销"],
            "language": "zh"
        }
    )
    
    assert response.status_code == 200
    assert response.json()["success"] is True
```

## n8n 集成示例

### 在 n8n 中使用文章生成 API

1. **创建 HTTP Request 节点**
   ```
   Method: POST
   URL: http://localhost:8000/api/v1/generate/article
   ```

2. **配置请求体**
   ```json
   {
       "topic": "{{ $node.Input.json.topic }}",
       "keywords": "{{ $node.Input.json.keywords }}",
       "language": "zh",
       "tone": "professional"
   }
   ```

3. **处理响应**
   ```
   成功 → 保存到数据库
   失败 → 发送告警通知
   ```

## 后续优化方向

1. **缓存改进**
   - 实现分布式缓存
   - 使用向量数据库进行语义搜索

2. **模型优化**
   - 微调专门的营销文案生成模型
   - 支持多语言模型

3. **功能扩展**
   - 图片生成集成
   - 多媒体内容生成
   - A/B 测试支持

4. **性能提升**
   - 流式输出支持
   - 并行处理多个请求
   - GPU 加速

## 参考资源

- [LangChain 官方文档](https://python.langchain.com/)
- [OpenAI API 文档](https://platform.openai.com/docs)
- [FastAPI 文档](https://fastapi.tiangolo.com/)
