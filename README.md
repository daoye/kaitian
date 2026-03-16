# KaiTian (开天)

模块化自动化采集与搬运工具集。

## 项目结构

```
kaitian/
├── packages/           # 原子模块
│   ├── core/          # 核心抽象层
│   ├── auth/          # 认证与会话管理
│   ├── browser/       # Playwright 浏览器封装
│   ├── stealth/       # 反检测/反反爬虫
│   ├── captcha/       # 验证码处理
│   ├── downloader/    # 资源下载
│   ├── validator/     # 资源校验
│   └── publisher/     # 资源发布
├── apps/              # 可执行应用
│   ├── cli/           # 命令行工具
│   └── api/           # FastAPI 服务
├── workflows/         # 工作流定义
└── docs/              # 文档
```

## 快速开始

### 安装依赖

```bash
# 安装 uv (如果未安装)
curl -LsSf https://astral.sh/uv/install.sh | sh

# 安装所有依赖
uv sync
```

### 使用 CLI

```bash
# 显示帮助
uv run kaitian --help

# 测试命令
uv run kaitian hello world
```

### 启动 API

```bash
uv run uvicorn api.main:app --reload
```

## 设计原则

- **简单优先**: 避免过度设计，优先可运行、可维护
- **原子化设计**: 每个模块只做一件事，模块间通过清晰数据结构交互
- **最小依赖**: 不依赖外部服务，优先使用嵌入式方案 (SQLite)
- **易于部署**: 支持单机运行，一键启动

## 技术栈

- Python 3.12+
- uv (依赖管理)
- Playwright (浏览器自动化)
- FastAPI (API 服务)
- SQLite (数据存储)

## 文档

- [项目结构设计](docs/architecture/project-structure.md)
- [反检测能力设计说明书](docs/architecture/anti-detection-design.md)

## License

MIT
