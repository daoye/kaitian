# KaiTian - AI 编码代理指南

## 项目概述

KaiTian 是一个为 n8n 工作流提供能力的 AI 营销自动化后端服务，提供爬虫、AI 评估/生成、社交媒体发布能力。

- **语言**: Python 3.11+
- **框架**: FastAPI
- **包管理**: uv (现代化 Python 包管理工具)
- **项目结构**: Monorepo (主项目 + 子模块)
- **架构原则**: 纯能力提供者（无业务逻辑，核心功能无数据库）

## Monorepo 结构

```
kaitian/                          # 主项目根目录
├── app/                          # KaiTian 主服务代码
│   ├── api/                      # FastAPI 路由处理器
│   ├── core/                     # 核心配置、日志、应用工厂
│   ├── models/                   # Pydantic 数据模型
│   ├── services/                 # 业务逻辑服务
│   └── utils/                    # 工具函数
├── packages/
│   └── MediaCrawler/             # 社交媒体爬虫子模块 (git submodule)
├── data/                         # 数据存储 (文件持久化)
├── logs/                         # 日志文件
├── tests/                        # 测试文件
├── pyproject.toml                # 项目配置 (uv)
├── start.py                      # 服务管理脚本
└── main.py                       # 应用入口
```

## 构建与运行命令

```bash
# 安装依赖
uv sync                                    # 安装主项目依赖
cd packages/MediaCrawler && uv sync        # 安装子模块依赖

# 运行开发服务器
python start.py                            # 启动所有服务 (KaiTian + MediaCrawler)
python start.py --only kaitian             # 仅启动 KaiTian
python start.py --only mediacrawler        # 仅启动 MediaCrawler
uv run uvicorn main:app --reload --port 8000  # 直接运行主服务

# 服务管理
python start.py stop                       # 停止所有服务
python start.py status                     # 查看服务状态

# 运行测试
pytest                                     # 运行所有测试
pytest tests/test_xiaohongshu_publisher.py -v   # 运行单个测试文件
pytest -k test_login                       # 按名称模式运行测试
pytest tests/test_file.py::test_func -v    # 运行特定测试函数

# 代码检查与格式化
ruff check .                               # 检查代码规范
ruff check --fix .                         # 自动修复代码问题
black .                                    # 格式化代码
mypy app/                                  # 类型检查

# MediaCrawler 子模块
cd packages/MediaCrawler
uv run main.py --platform xhs --lt qrcode --type search   # 运行爬虫
uv run uvicorn api.main:app --port 8080                   # 启动 WebUI
```

## 代码风格规范

### 导入顺序
```python
# 1. 标准库
import json
import os
from pathlib import Path
from typing import Dict, List, Optional, Any

# 2. 第三方库
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

# 3. 本地模块 (使用绝对路径)
from app.core.config import get_settings
from app.core.logging import get_logger
```

### 格式化规则
- 行长度: 100 字符 (pyproject.toml 配置)
- 使用 Black 格式化
- 使用 Ruff 检查 (规则: E, F, W, I)
- 字符串使用双引号
- 缩进使用 4 空格

### 类型注解
```python
# 使用类型注解
def get_settings() -> Settings:
    ...

# 使用 Optional 表示可空类型
def load_session(session_id: str) -> Optional[Dict[str, Any]]:
    ...

# 使用内置泛型 (Python 3.9+)
def list_sessions() -> list[dict[str, Any]]:
    ...

# API 请求/响应使用 Pydantic 模型
class PostRequest(BaseModel):
    title: str
    content: str
    tags: Optional[list[str]] = None
```

### 命名规范
| 类型 | 风格 | 示例 |
|------|------|------|
| 类名 | PascalCase | `ContentGenerationService` |
| 函数/变量 | snake_case | `get_settings`, `relevance_score` |
| 常量 | UPPER_CASE | `SESSIONS_DIR`, `DATA_DIR` |
| 私有方法 | 前置下划线 | `_initialize_llm`, `_load_json` |
| 枚举值 | UPPER_CASE | `PostStatusEnum.PENDING` |

### 注释与文档字符串
```python
"""模块级文档字符串 - 说明模块用途。"""

class StateStore:
    """基于文件的状态存储服务。"""
    
    @staticmethod
    def save_search_session(session_id: str, session_data: Dict[str, Any]) -> bool:
        """保存或更新搜索会话状态。
        
        Args:
            session_id: 唯一会话标识符
            session_data: 会话数据字典
            
        Returns:
            保存成功返回 True，否则返回 False
        """
        ...
```

### 错误处理
```python
# API 响应统一格式
return {"success": True, "data": result}
return {"success": False, "error": "错误信息"}

# 异常处理模式
try:
    result = await some_operation()
except Exception as e:
    logger.error(f"操作失败: {str(e)}")
    return {"success": False, "error": str(e)}
```

### 日志规范
```python
from app.core.logging import get_logger

logger = get_logger(__name__)

logger.info(f"会话创建: {session_id}")
logger.warning(f"配置缺失，使用默认值: {key}")
logger.error(f"请求失败: {url}, 错误: {error}")
```

## 架构模式

### 服务单例模式
```python
# services/example_service.py
from functools import lru_cache

class ExampleService:
    def __init__(self):
        self._initialized = False
    
    def _initialize(self):
        if self._initialized:
            return
        # 初始化逻辑
        self._initialized = True

# 模块级单例
_service_instance = None

def get_service() -> ExampleService:
    global _service_instance
    if _service_instance is None:
        _service_instance = ExampleService()
    return _service_instance
```

### 配置管理
```python
# 使用 Pydantic Settings + lru_cache
from pydantic_settings import BaseSettings
from functools import lru_cache

class Settings(BaseSettings):
    app_name: str = "KaiTian"
    debug: bool = False
    
    class Config:
        env_file = ".env"

@lru_cache()
def get_settings() -> Settings:
    return Settings()
```

### API 路由模式
```python
from fastapi import APIRouter, Depends
from app.models.schemas import SomeRequest, SomeResponse

router = APIRouter(prefix="/api/v1/some", tags=["some"])

@router.post("/action", response_model=SomeResponse)
async def do_action(request: SomeRequest, settings = Depends(get_settings)):
    # 处理逻辑
    return {"success": True, "data": result}
```

### 文件存储模式
```
data/
├── sessions/                    # 搜索会话状态
│   ├── {session_id}.json
│   └── checkpoints/             # 爬取检查点
└── failed/                      # 失败项目
    ├── {session_id}_failed.json
    └── platform_sessions/       # 平台登录状态
```

## 测试规范

```python
# tests/test_example.py
import pytest
from app.services.example import get_service

@pytest.mark.asyncio
async def test_async_operation():
    """测试异步操作。"""
    service = get_service()
    result = await service.do_something()
    assert result["success"] is True

def test_sync_operation():
    """测试同步操作。"""
    service = get_service()
    assert service.is_ready()
```

## 环境变量

```bash
# .env 文件示例
APP_NAME="KaiTian"
DEBUG=false
LOG_LEVEL=INFO

# AI 配置
OPENAI_API_KEY=your_key
OPENAI_MODEL=gpt-3.5-turbo

# 数据库 (可选，用于状态持久化)
DATABASE_URL=sqlite:///./kaitian.db
```

## 常用命令速查表

| 任务 | 命令 |
|------|------|
| 安装依赖 | `uv sync` |
| 启动开发 | `python start.py` |
| 运行测试 | `pytest` |
| 单个测试 | `pytest tests/test_file.py::test_func -v` |
| 代码检查 | `ruff check .` |
| 格式化 | `black .` |
| 类型检查 | `mypy app/` |
| 停止服务 | `python start.py stop` |

## AI 代理注意事项

1. **无数据库设计**: KaiTian 核心功能是无状态的，使用 `data/` 目录进行文件持久化
2. **能力提供者**: 实现纯粹的功能/服务，业务逻辑由 n8n 处理
3. **Monorepo**: MediaCrawler 在 `packages/MediaCrawler/` 是独立子模块，不要混用代码
4. **错误响应**: API 统一返回 `{"success": bool, "error": str, "data": any}` 格式
5. **异步优先**: I/O 操作使用 `async/await`，服务类外部调用方法应为异步

## UI/UX 设计参考

项目包含 ui-ux-pro-max 工作流 (`.cursor/commands/ui-ux-pro-max.md`)：
- 50+ UI 风格
- 21 种调色板
- 50 种字体配对
- 默认技术栈: `html-tailwind`
