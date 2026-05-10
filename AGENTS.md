# 约定
- 使用中文跟我交流
- 本项目的所有文档使用中文书写

# 项目概述

**KaiTian（开天）** — 模块化自动化采集与搬运工具集，monorepo 组织。

核心场景：网站登录 → 资源采集 → 下载 → 校验 → 发布

### 设计原则
- **简单优先**：可运行 > 理论上完美，避免过度设计
- **站点隔离**：站点特定代码集中在 `packages/sites/{site}/`，`packages/downloader/` 只放通用能力
- **原子化**：每个模块只做一件事
- **最小依赖**：默认不用 Redis/PostgreSQL/消息队列，优先 SQLite
- **非浏览器优先**：元数据提取走 HTTP（httpx），文件下载走 presigned URL，只在必要时用 Playwright

### 技术选型
Python 3.12+ | uv | httpx | BeautifulSoup4 | LangGraph | langchain-mcp-adapters | Playwright（可选） | SQLite | toml | Pillow

### 项目结构
```
packages/
├── core/       # 配置、数据模型、类型、异常
├── auth/       # 认证与会话（SessionRepository）
├── browser/    # Playwright 封装（可选）
├── downloader/ # HTTP 客户端、爬虫编排、后处理、SQLite 记录
├── agent/      # LangGraph 智能体（文本清洗、MCP）
├── sites/      # 站点实现（three_dbrute/ 等）
├── captcha/    # 验证码
├── validator/  # 校验
├── publisher/  # 发布
└── stealth/    # 隐身
apps/
├── cli/        # kaitian 命令
└── api/        # FastAPI
```

### 配置
`kaitian.toml`，支持环境变量覆盖（`KAITIAN_LLM__API_KEY` 等）。

### CLI 速查
| 命令 | 用途 |
|------|------|
| `auth import` | 批量导入 cookie |
| `auth set-meta <site> <account> <key> <val>` | 设置会话 metadata |
| `crawl detail <url>` | HTTP 提取元数据 |
| `crawl model <url>` | 完整采集一个模型 |
| `crawl batch --limit N` | 批量下载 |
| `crawl batch --daemon` | 守护模式持续下载 |
| `crawl postprocess <dir>` | 后处理（解压/转格式） |
| `crawl agent text_clean --model-dir <dir>` | LLM 文本清洗 |
| `record check/set/list/done` | 下载进度管理 |

### 非目标
分布式架构 / Redis / MQ / 权限系统 / 多租户 / 插件系统
