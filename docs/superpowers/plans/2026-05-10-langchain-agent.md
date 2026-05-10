# LangChain Agent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development to implement this plan task-by-task.

**Goal:** 引入 LangChain 智能体，支持文本清洗和 BrowserOS 自动化任务。

**Architecture:** 新建 `packages/agent/` 包，通过 `langchain-mcp-adapters` 集成 BrowserOS MCP 工具，通过 LangChain `init_chat_model` 支持多 Provider。

**Tech Stack:** Python 3.12, LangChain, langchain-mcp-adapters, httpx

---

### Task 1: LLM Config

**Files:**
- Modify: `packages/core/src/core/config.py` (新增 LlmConfig)
- Modify: `packages/core/src/core/__init__.py` (导出 LlmConfig)

- [ ] **Step 1: Add LlmConfig to core/config.py**

After `CrawlConfig` class, add:

```python
class LlmConfig(BaseSettings):
    """LLM 配置"""

    provider: str = Field(default="openai", description="LLM 提供商 (openai/anthropic/ollama/deepseek)")
    model: str = Field(default="gpt-4o", description="模型名称")
    api_key: str = Field(default="", description="API Key（留空从环境变量读取）")
    base_url: str = Field(default="", description="API 基础 URL（兼容 OpenAI 格式的代理）")

    model_config = SettingsConfigDict(env_prefix="KAITIAN_LLM_")
```

In `CoreConfig`, add:
```python
llm: LlmConfig = Field(default_factory=LlmConfig)
```

- [ ] **Step 2: Export in __init__.py**

Add to imports and `__all__`:
```python
from .config import ..., LlmConfig
"LlmConfig",
```

- [ ] **Step 3: Add default to pyproject.toml**

In `[tool.kaitian]` section:
```toml
[tool.kaitian.llm]
provider = "openai"
model = "gpt-4o"
```

- [ ] **Step 4: Verify**

Run: `uv run ruff check packages/core/src/core/config.py packages/core/src/core/__init__.py`
Expected: All checks passed

- [ ] **Step 5: Commit**

```bash
git add packages/core/src/core/config.py packages/core/src/core/__init__.py pyproject.toml
git commit -m "feat: add LlmConfig for multi-provider LLM support"
```

---

### Task 2: Agent package scaffold

**Files:**
- Create: `packages/agent/pyproject.toml`
- Create: `packages/agent/src/agent/__init__.py`
- Create: `packages/agent/src/agent/config.py`
- Modify: `pyproject.toml` (workspace member)

- [ ] **Step 1: Create pyproject.toml**

```toml
[project]
name = "agent"
version = "0.1.0"
description = "LangChain 智能体模块"
requires-python = ">=3.12"
dependencies = [
    "core",
    "langchain>=0.3.0",
    "langchain-mcp-adapters>=0.1.0",
    "httpx>=0.27.0",
]

[project.optional-dependencies]
openai = ["langchain-openai"]
anthropic = ["langchain-anthropic"]
ollama = ["langchain-ollama"]
deepseek = ["langchain-deepseek"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["src/agent"]
```

- [ ] **Step 2: Create __init__.py**

```python
"""LangChain 智能体模块。"""
```

- [ ] **Step 3: Create config.py**

```python
"""LLM 配置加载器，从核心配置读取并初始化 LangChain 模型。"""

from core import get_config
from langchain.chat_models import init_chat_model


def create_llm():
    """根据配置创建 LangChain chat model 实例。"""
    cfg = get_config().llm
    params = {"model": f"{cfg.provider}:{cfg.model}"}
    if cfg.api_key:
        params["api_key"] = cfg.api_key
    if cfg.base_url:
        params["base_url"] = cfg.base_url
    return init_chat_model(**params)
```

- [ ] **Step 4: Add workspace member to root pyproject.toml**

In `[tool.uv.workspace]` members list, `packages/agent` is already included via `packages/*`.

- [ ] **Step 5: Verify**

Run: `uv run ruff check packages/agent/src/`
Expected: All checks passed

- [ ] **Step 6: Commit**

```bash
git add packages/agent/
git commit -m "feat: add agent package scaffold with LLM config"
```

---

### Task 3: File tools

**Files:**
- Create: `packages/agent/src/agent/tools/__init__.py`
- Create: `packages/agent/src/agent/tools/files.py`

- [ ] **Step 1: Create tools/__init__.py**

```python
"""Agent 工具集。"""
```

- [ ] **Step 2: Create files.py**

```python
"""文件读写工具，供 LangChain agent 调用。"""

import os
from pathlib import Path
from typing import Optional

from langchain_core.tools import tool


@tool
def read_text_file(path: str) -> str:
    """读取文本文件内容。用于审查模型文件中的文本。"""
    p = Path(path)
    if not p.exists():
        return f"文件不存在: {path}"
    try:
        return p.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        try:
            return p.read_text(encoding="gbk")
        except UnicodeDecodeError:
            return f"无法解码文件: {path}"


@tool
def write_text_file(path: str, content: str) -> str:
    """写入文本文件。用于保存清洗后的文件内容。"""
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content, encoding="utf-8")
    return f"已写入: {path} ({len(content)} chars)"


@tool
def list_text_files(directory: str) -> str:
    """列出目录下所有 .txt 文件。"""
    p = Path(directory)
    if not p.exists():
        return f"目录不存在: {directory}"
    files = [str(f.relative_to(p)) for f in sorted(p.rglob("*.txt"))]
    return "\n".join(files) if files else "无 .txt 文件"


TOOLS = [read_text_file, write_text_file, list_text_files]
```

- [ ] **Step 3: Verify**

Run: `uv run ruff check packages/agent/src/`
Expected: All checks passed

- [ ] **Step 4: Commit**

```bash
git add packages/agent/src/agent/tools/
git commit -m "feat: add file read/write tools for agent"
```

---

### Task 4: Kaitian CLI tool

**Files:**
- Create: `packages/agent/src/agent/tools/kaitian.py`

- [ ] **Step 1: Create kaitian.py**

```python
"""封装 kaitian CLI 为 LangChain tool。"""

import subprocess
from pathlib import Path

from langchain_core.tools import tool


@tool
def kaitian_auth_set_meta(site: str, account: str, key: str, value: str) -> str:
    """设置站点账号的 metadata。用于保存 download nonce 等。"""
    result = subprocess.run(
        ["uv", "run", "kaitian", "auth", "set-meta", site, account, key, value],
        capture_output=True, text=True, timeout=30,
    )
    out = (result.stdout or "").strip()
    err = (result.stderr or "").strip()
    return out or err or f"set-meta {key}={value}"


@tool
def kaitian_record_check(site: str, url: str) -> str:
    """检查 URL 是否已下载。"""
    result = subprocess.run(
        ["uv", "run", "kaitian", "record", "check", site, url],
        capture_output=True, text=True, timeout=30,
    )
    return (result.stdout or result.stderr or "").strip()


TOOLS = [kaitian_auth_set_meta, kaitian_record_check]
```

- [ ] **Step 2: Verify**

Run: `uv run ruff check packages/agent/src/`
Expected: All checks passed

- [ ] **Step 3: Commit**

```bash
git add packages/agent/src/agent/tools/kaitian.py
git commit -m "feat: add kaitian CLI tools for agent"
```

---

### Task 5: BrowserOS MCP tools

**Files:**
- Create: `packages/agent/src/agent/tools/browseros.py`

- [ ] **Step 1: Create browseros.py**

BrowserOS MCP 工具通过 `langchain-mcp-adapters` 自动加载，此文件提供辅助函数用于初始化 MCP 连接。

```python
"""BrowserOS MCP 工具适配器。"""

from langchain_core.tools import BaseTool


async def create_browseros_tools(mcp_server_config: dict) -> tuple[list[BaseTool], callable]:
    """通过 langchain-mcp-adapters 加载 BrowserOS MCP 工具。

    用法:
        tools, cleanup = await create_browseros_tools(mcp_server_config)
        agent = create_agent(model, tools)
        # ... use agent ...
        await cleanup()
    """
    from langchain_mcp_adapters import convert_mcp_to_tools

    tools, cleanup = await convert_mcp_to_tools(mcp_server_config)
    return tools, cleanup
```

- [ ] **Step 2: Verify**

Run: `uv run ruff check packages/agent/src/`
Expected: All checks passed

- [ ] **Step 3: Commit**

```bash
git add packages/agent/src/agent/tools/browseros.py
git commit -m "feat: add BrowserOS MCP tool adapter"
```

---

### Task 6: Text clean task

**Files:**
- Create: `packages/agent/src/agent/tasks/__init__.py`
- Create: `packages/agent/src/agent/tasks/text_clean.py`

- [ ] **Step 1: Create tasks/__init__.py**

```python
"""Agent 任务定义。"""
```

- [ ] **Step 2: Create text_clean.py**

```python
"""文本清洗任务 — 清除版权/法律/推广信息，保留使用说明。"""

from pathlib import Path

from langchain_core.prompts import ChatPromptTemplate

from ..config import create_llm
from ..tools.files import TOOLS as file_tools

SYSTEM_PROMPT = """你是模型文件文本清洗助手。你的任务是清理模型目录中的文本文件。

规则：
1. 保留：格式说明、渲染参数、安装方法、材质说明、模型参数、使用说明
2. 删除：Copyright 声明、All Rights Reserved、License 协议、Disclaimer、推广信息、下载站水印
3. 删除空行和多余空白
4. 保持原文的语言和编码
"""

CLEAN_PROMPT = ChatPromptTemplate.from_messages([
    ("system", SYSTEM_PROMPT),
    ("human", "请清洗以下文件内容，只保留使用说明，删除版权/法律/推广信息：\n\n{content}"),
])


def clean_text(content: str, model_dir: str, filename: str) -> str:
    """用 LLM 清洗单文件内容。"""
    llm = create_llm()
    chain = CLEAN_PROMPT | llm
    result = chain.invoke({"content": content})
    return result.content


async def run_text_clean(model_dir: str) -> str:
    """运行文本清洗任务。"""
    from langchain.agents import create_agent

    llm = create_llm()
    agent = create_agent(
        model=llm,
        tools=file_tools,
        system_prompt=SYSTEM_PROMPT,
    )

    result = await agent.ainvoke({
        "messages": [{
            "role": "user",
            "content": f"扫描目录 {model_dir}/extracted 下的所有 .txt 文件，"
                       f"对每个文件读取内容、清洗版权/法律/推广信息后写回。"
                       f"删除空行，只保留使用说明。完成后列出处理了哪些文件。"
        }]
    })
    return result["messages"][-1].content
```

- [ ] **Step 3: Verify**

Run: `uv run ruff check packages/agent/src/`
Expected: All checks passed

- [ ] **Step 4: Commit**

```bash
git add packages/agent/src/agent/tasks/
git commit -m "feat: add text clean agent task"
```

---

### Task 7: Agent factory + CLI

**Files:**
- Create: `packages/agent/src/agent/factory.py`
- Modify: `apps/cli/src/cli/commands/crawl.py` (新增 agent 子命令)

- [ ] **Step 1: Create factory.py**

```python
"""Agent 工厂 — 根据任务名创建对应 agent。"""

from langchain.agents import create_agent

from .config import create_llm
from .tasks.text_clean import run_text_clean
from .tools.files import TOOLS as file_tools
from .tools.kaitian import TOOLS as kaitian_tools

TASK_REGISTRY = {
    "text_clean": {
        "handler": run_text_clean,
        "tools": file_tools,
        "description": "清洗模型文件中的版权/法律/推广信息",
    },
}

async def run_task(task: str, **kwargs) -> str:
    """运行指定任务。"""
    entry = TASK_REGISTRY.get(task)
    if not entry:
        raise ValueError(f"未知任务: {task}，可用: {list(TASK_REGISTRY)}")
    return await entry["handler"](**kwargs)


def register_task(name: str, handler, tools: list, description: str):
    """注册新任务（供未来扩展）。"""
    TASK_REGISTRY[name] = {"handler": handler, "tools": tools, "description": description}
```

- [ ] **Step 2: Add agent CLI command**

In `apps/cli/src/cli/commands/crawl.py`, add after the `batch` command:

```python
@router.command()
def agent(
    task: str = typer.Argument(..., help="任务名 (text_clean)"),
    model_dir: str = typer.Option(None, "--model-dir", "-d", help="模型目录路径"),
):
    """运行 LangChain 智能体任务。"""
    import asyncio
    from agent.factory import run_task, TASK_REGISTRY

    if task not in TASK_REGISTRY:
        console.print(f"[red]未知任务: {task}[/red]")
        console.print(f"可用: {', '.join(TASK_REGISTRY)}")
        raise typer.Exit(1)

    if task == "text_clean" and not model_dir:
        console.print("[red]text_clean 需要 --model-dir 参数[/red]")
        raise typer.Exit(1)

    console.print(f"[blue]运行任务:[/blue] {task}")
    try:
        result = asyncio.run(run_task(task, model_dir=model_dir))
        console.print(result)
    except Exception as e:
        console.print(f"[red]任务失败:[/red] {e}")
        raise typer.Exit(1)
```

- [ ] **Step 3: Verify**

Run: `uv run ruff check packages/agent/src/ apps/cli/src/cli/commands/crawl.py`
Expected: All checks passed

- [ ] **Step 4: Commit**

```bash
git add packages/agent/src/agent/factory.py apps/cli/src/cli/commands/crawl.py
git commit -m "feat: add agent factory and CLI command"
```

---

### Task 8: Sync dependencies

- [ ] **Step 1: Install agent package**

Run: `uv sync --package agent 2>&1 | tail -5`
Expected: agent package installed successfully

- [ ] **Step 2: Verify CLI help**

Run: `uv run kaitian crawl agent --help`
Expected: Shows agent command with task argument

- [ ] **Step 3: Commit**

```bash
git add uv.lock
git commit -m "chore: sync dependencies for agent package"
```
