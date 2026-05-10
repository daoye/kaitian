# LangChain Agent 集成设计

## 目标

引入 LangChain 智能体，处理两类任务：
1. **文本清洗** — 清理解压后模型文件中的版权/法律/推广文字，保留使用说明
2. **浏览器自动化** — 自动登录网站、获取 download nonce 并保存

为未来更多智能体场景预留扩展能力。

## 架构

```
packages/agent/
├── pyproject.toml
├── src/agent/
│   ├── __init__.py
│   ├── config.py          # LLM 多 Provider 配置
│   ├── factory.py         # Agent 工厂
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── browseros.py   # BrowserOS MCP 工具适配
│   │   ├── files.py       # 文件读写
│   │   └── kaitian.py     # kaitian CLI 封装
│   └── tasks/
│       ├── __init__.py
│       ├── text_clean.py  # 版权文本清洗
│       └── auth_setup.py  # 自动登录+获取 nonce
```

## Config — 多 Provider

```toml
[tool.kaitian.llm]
provider = "openai"
model = "gpt-4o"
api_key = ""            # 或环境变量 LLM_API_KEY / OPENAI_API_KEY
base_url = ""           # 可选，兼容 OpenAI API 格式的代理
```

LangChain `init_chat_model("openai:gpt-4o")` 统一接口，支持 openai / anthropic / ollama / deepseek 等。

## Factory — Agent 组装

`factory.create_agent(tasks=["text_clean", "auth_setup"])` 根据任务注册对应工具：

| 任务 | 工具 |
|------|------|
| `text_clean` | read_file, write_file, run_command |
| `auth_setup` | browseros (MCP), kaitian_auth_set_meta |

通过 `langchain-mcp-adapters` 将 BrowserOS MCP 工具转为 LangChain Tool。

## 文本清洗流程

```
agent 收到任务 → 扫描 extracted/*.txt
  → 对每个文件：read → LLM 判断保留/删除 → write
  → 返回处理统计
```

保留：格式说明、安装方法、材质说明、渲染参数
删除：Copyright, All Rights Reserved, License, "Download more at", 推广水印

## 认证设置流程

```
agent 收到任务 → browserOS_navigate(网站)
  → 检查登录状态 → 如未登录则提示用户
  → 已登录则提取 window.nonce_download_nonce
  → kaitian auth set-meta 保存
```

## 集成到批处理

在 `crawl batch --daemon` 模式下，启动前自动执行 `auth_setup` 检查 nonce 有效性。

## 配置示例

```toml
[tool.kaitian.llm]
provider = "openai"
model = "gpt-4o"

[tool.kaitian.llm]
provider = "anthropic"
model = "claude-sonnet-4-6"

[tool.kaitian.llm]
provider = "ollama"
model = "qwen3:14b"
base_url = "http://localhost:11434/v1"
```

## CLI 接口

```bash
kaitian agent text-clean <model_dir>    # 清洗指定模型目录
kaitian agent auth-setup <site>         # 自动获取 nonce
kaitian agent run <task>                # 运行指定任务
```
