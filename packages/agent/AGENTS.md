# 智能体基础设施

提供基础智能体能力，不包含站点特定逻辑。站点智能体在 `packages/sites/{site}/agent.py` 中实现。

使用 LangGraph 编排工作流。每个任务在 `tasks/` 下一个文件，导出 `run_*` 异步函数。

### LLM 配置
```toml
[tool.kaitian.llm]
provider = "deepseek"
model = "deepseek-v4-flash"
api_key = ""        # 或环境变量 DEEPSEEK_API_KEY
```

支持通过 `register_provider()` 注册多 Provider。

### MCP 集成
通过 `langchain-mcp-adapters` 加载 MCP 工具为 LangChain BaseTool。BrowserOS 端点 `http://localhost:9000/mcp`。

### 当前任务
| 任务 | 方式 | 说明 |
|------|------|------|
| `text_clean` | Chain | 模型文件版权文本清洗 |
