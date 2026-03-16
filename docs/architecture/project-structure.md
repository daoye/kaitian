# KaiTian 项目结构设计

> 文档版本：1.2
> 最后更新：2026-03-16
> 适用范围：KaiTian 模块化采集工具集
>
> **变更记录**：
> - v1.2: 新增 discovery（资源发现）模块，支持网站浏览、资源发现和持续监控
> - v1.1: 去掉 kaitian- 前缀简化命名，新增 stealth/captcha 模块，支持多站点独立会话
> - v1.0: 初始版本

## 1. 设计原则

本项目严格遵循以下核心原则：

### 1.1 简单优先
- 避免过度设计和复杂分层
- 优先可运行、可维护，而非"理论上完美"
- 每个决策都以"是否增加了不必要的复杂度"为检验标准

### 1.2 原子化设计
- 每个模块只做一件事，做好一件事
- 下载、校验、上传等能力完全独立
- 模块之间通过清晰的数据结构交互，禁止硬编码耦合

### 1.3 最小依赖
- 不依赖 Redis、PostgreSQL、MQ 等外部服务
- 优先使用嵌入式方案（SQLite）
- 核心依赖仅限于：Playwright、FastAPI、SQLite

### 1.4 易于本地部署
- 支持单机运行，一键启动
- 开发、测试、部署环境保持一致
- 降低环境复杂度，减少配置项

## 2. 整体架构

### 2.1 Monorepo 组织方式

采用 **uv Workspace** 模式管理多包结构：

```
kaitian/                      # 根项目（workspace root）
├── pyproject.toml            # Workspace 配置
├── packages/                 # 可独立发布的原子模块
│   ├── core/         # 核心抽象层
│   ├── auth/         # 账号与会话管理
│   ├── browser/      # Playwright 浏览器封装
│   ├── stealth/      # 反检测/反反爬虫
│   ├── captcha/      # 验证码识别与处理
│   ├── discovery/    # 资源发现与监控
│   ├── downloader/   # 资源下载
│   ├── validator/    # 资源校验
│   └── publisher/    # 资源上传与发布
├── apps/                     # 可执行应用
│   ├── cli/                  # 命令行工具
│   └── api/                  # FastAPI 服务
├── workflows/                # 工作流定义（串联脚本）
└── tests/                    # 集成测试
```

### 2.2 模块层级关系

```
┌─────────────────────────────────────────┐
│            应用层 (apps/)                │
│  ┌──────────┐  ┌─────────────────────┐  │
│  │   CLI    │  │     FastAPI API     │  │
│  └────┬─────┘  └──────────┬──────────┘  │
└───────┼───────────────────┼─────────────┘
        │                   │
        └─────────┬─────────┘
                  ▼
┌─────────────────────────────────────────┐
│           工作流层 (workflows/)          │
│     （编排脚本，串联原子模块）            │
└──────────────────┬──────────────────────┘
                   │
    ┌──────────────┼──────────────┬──────────────┬──────────────┬──────────────┬──────────────┐
    ▼              ▼              ▼              ▼              ▼              ▼              ▼
┌────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐   ┌──────────┐
│  Auth  │   │ Browser  │   │  Stealth │   │  Captcha │   │Discovery │   │ Download │   │ Validate │
└────────┘   └──────────┘   └──────────┘   └──────────┘   └──────────┘   └──────────┘   └──────────┘
       │           │              │              │              │              │              │
       └───────────┴──────────────┴──────────────┴──────────────┴──────────────┴──────────────┘
                                                                    │
                                                                    ▼
                                                            ┌──────────────┐
                                                            │     core     │  ← 所有模块依赖核心层
                                                            └──────────────┘

  外部依赖：Playwright、FastAPI、SQLite
```

## 3. 模块详细设计

### 3.1 core（核心抽象层）

**职责**：提供所有模块共享的基础抽象和数据结构

**包含内容**：
```python
# 核心数据结构
@dataclass
class Resource:
    """资源统一表示"""
    id: str
    url: str | None
    local_path: Path | None
    metadata: dict
    status: ResourceStatus  # pending, downloaded, validated, published

@dataclass
class Session:
    """会话状态 - 支持多站点独立会话"""
    session_id: str          # 会话唯一标识
    site: str               # 站点标识（如 "youtube", "bilibili"）
    account_id: str         # 账号标识（支持同一站点多账号）
    cookies: dict
    headers: dict
    expires_at: datetime | None
    metadata: dict          # 站点特定扩展信息

@dataclass
class SessionGroup:
    """会话组 - 工作流中定义来源和目标的会话组合"""
    name: str               # 会话组名称
    source_session: str     # 来源站点会话ID
    target_session: str     # 目标站点会话ID
    # 支持一对多、多对一等复杂场景
    source_sessions: list[str] | None = None
    target_sessions: list[str] | None = None

# 抽象接口
class Authenticator(ABC):
    @abstractmethod
    async def login(self, credentials: dict) -> Session: ...

class Downloader(ABC):
    @abstractmethod
    async def download(self, resource: Resource) -> Path: ...

class Validator(ABC):
    @abstractmethod
    async def validate(self, resource: Resource) -> ValidationResult: ...

class Publisher(ABC):
    @abstractmethod
    async def publish(self, resource: Resource) -> PublishResult: ...

# 配置管理
class Config:
    """统一配置管理"""
    # 从环境变量和 pyproject.toml [tool.kaitian] 读取
```

**依赖**：仅标准库 + Pydantic（数据验证）

### 3.2 auth（认证与会话）

**职责**：多站点账号登录和会话状态维护

**设计要点**：
- 每个站点实现独立的 `SiteAuthenticator`
- 支持同一站点多账号（通过 `account_id` 区分）
- 会话持久化到 SQLite，按站点隔离存储
- 支持 Cookie 和 Token 两种模式
- 自动刷新机制

```python
# 使用示例
from auth import AuthManager

auth = AuthManager(db_path="./data/auth.db")

# 为不同站点创建独立会话
youtube_session = await auth.login(
    "youtube",
    account_id="main",
    credentials={"email": "...", "password": "..."}
)

bilibili_session = await auth.login(
    "bilibili",
    account_id="uploader",
    credentials={"phone": "...", "password": "..."}
)

# 获取特定站点会话（自动处理过期刷新）
session = await auth.get_session("youtube", account_id="main")
```

### 3.3 browser（浏览器封装）

**职责**：Playwright 的轻量级封装

**设计要点**：
- 提供上下文管理器（async with）
- 与 stealth 模块集成，自动注入反检测脚本
- 统一的请求/响应拦截
- 与 auth 集成，自动携带会话（支持多站点独立会话）

```python
# 使用示例
from browser import Browser

async with Browser(headless=True) as browser:
    page = await browser.new_page()
    # 指定使用哪个站点的会话
    await browser.apply_session("youtube", account_id="main")
    await page.goto("https://youtube.com")
```

### 3.4 stealth（反检测/反反爬虫）

**职责**：浏览器指纹伪装和行为模拟，绕过常见反爬检测

**设计要点**：
- WebGL/Canvas 指纹随机化
- User-Agent、Viewport、Timezone 等特征伪装
- 自动化特征隐藏（移除 `navigator.webdriver` 等）
- 人类行为模拟（鼠标移动轨迹、点击延迟、滚动模式）
- 与 browser 模块深度集成，开箱即用

```python
# 使用示例
from stealth import StealthConfig

# 基础配置
config = StealthConfig(
    fingerprint="random",      # 或指定预设 "chrome_windows", "safari_mac"
    human_like=True,           # 启用人类行为模拟
    noise_level="medium"       # low/medium/high
)

# 与 browser 结合使用
from browser import Browser
async with Browser(stealth=config) as browser:
    page = await browser.new_page()
    # 自动应用所有反检测脚本
```

### 3.5 captcha（验证码处理）

**职责**：自动化验证码识别和处理

**设计要点**：
- 支持多种验证码类型：滑块、点选、旋转、 reCAPTCHA、GeeTest 等
- 插件化识别后端（本地模型、第三方打码平台）
- 与 browser 集成，自动检测和处理页面中的验证码
- 失败重试和人工介入兜底

```python
# 使用示例
from captcha import CaptchaSolver, SolverBackend

# 使用第三方打码平台
solver = CaptchaSolver(
    backend=SolverBackend.TWO_CAPTCHA,  # 或 CAPTCHA_SOLVER, LOCAL_MODEL
    api_key="..."
)

# 独立识别
result = await solver.solve_image("./captcha.png", type="text")

# 与 browser 集成自动处理
from browser import Browser
async with Browser(captcha_solver=solver) as browser:
    page = await browser.new_page()
    await page.goto("https://example.com/login")
    # 自动检测并解决页面中的验证码
    await browser.handle_captcha_if_present()
```

### 3.6 discovery（资源发现与监控）

**职责**：浏览网站、发现资源并持续监控新资源

**设计要点**：
- 站点适配器模式：每个站点实现独立的 `SiteDiscoveryAdapter`
- 增量抓取：记录上次抓取时间，仅获取更新的资源
- 多维度去重：URL去重、内容哈希去重、标题相似度去重
- 灵活的时间范围：支持历史回溯和实时监控
- 事件驱动：发现新资源时触发事件/回调
- 监控模式：持续运行，定期检查更新

**核心数据结构**：
```python
@dataclass
class DiscoveryTask:
    """发现任务配置"""
    task_id: str
    site: str                    # 站点标识
    source_type: str            # 来源类型：news, post, video 等
    time_range: TimeRange       # 时间范围
    filters: Dict[str, Any]     # 过滤条件（关键词、作者等）
    schedule: Optional[ScheduleConfig]  # 定时配置（None表示一次性）

@dataclass
class TimeRange:
    """时间范围"""
    start: Optional[datetime]   # None 表示从最早开始
    end: Optional[datetime]     # None 表示到最新

@dataclass
class DiscoveredResource:
    """发现的资源"""
    resource: Resource          # 核心 Resource 对象
    discovered_at: datetime     # 发现时间
    source_url: str            # 来源页面URL
    source_type: str           # 来源类型
    content_hash: str          # 内容哈希（用于去重）
    metadata: Dict[str, Any]   # 额外元数据（作者、发布时间等）
```

**使用示例**：
```python
from discovery import DiscoveryManager, DiscoveryTask, TimeRange
from datetime import datetime, timedelta

# 创建发现管理器
discovery = DiscoveryManager(db_path="./data/discovery.db")

# 一次性发现：获取过去24小时的资源
task = DiscoveryTask(
    task_id="task_001",
    site="example-news-site",
    source_type="news",
    time_range=TimeRange(
        start=datetime.now() - timedelta(days=1),
        end=datetime.now()
    ),
    filters={"category": "technology"}
)

# 执行发现
resources = await discovery.discover(task)
for r in resources:
    print(f"发现资源: {r.resource.url}")

# 持续监控：每5分钟检查一次更新
monitor_task = DiscoveryTask(
    task_id="monitor_001",
    site="example-forum",
    source_type="post",
    time_range=TimeRange(start=None, end=None),  # 始终获取最新
    schedule={"interval_minutes": 5}
)

# 启动监控（异步迭代器模式）
async for resource in discovery.monitor(monitor_task):
    print(f"新资源: {resource.resource.url}")
    # 可以在这里直接触发下载工作流
    await workflow.process(resource)
```

**增量抓取策略**：
1. **时间戳模式**：记录每个站点的最后抓取时间，只获取更新的内容
2. **页码模式**：支持按页码递增遍历历史内容
3. **ID序列模式**：基于资源ID的递增/递减获取新内容
4. **混合模式**：先时间戳定位，再页码遍历

**去重机制**：
1. **URL去重**：SQLite存储已发现的URL集合
2. **内容哈希去重**：对标题+摘要计算哈希，检测相似内容
3. **标题相似度**：使用编辑距离或余弦相似度检测变体标题
4. **布隆过滤器**：内存中快速预过滤，减少数据库查询

**站点适配器接口**：
```python
class DiscoveryAdapter(ABC):
    """资源发现适配器接口"""
    
    @abstractmethod
    async def discover(
        self, 
        task: DiscoveryTask,
        cursor: Optional[str] = None
    ) -> Tuple[List[DiscoveredResource], Optional[str]]:
        """
        发现资源
        
        Args:
            task: 发现任务配置
            cursor: 分页游标（用于增量抓取）
            
        Returns:
            (资源列表, 下一页游标)
        """
        pass
    
    @abstractmethod
    async def get_latest(self, limit: int = 10) -> List[DiscoveredResource]:
        """获取最新资源（用于监控模式）"""
        pass
    
    @abstractmethod
    def supports_monitoring(self) -> bool:
        """是否支持持续监控"""
        pass
```

**存储设计**：
```sql
-- 发现任务表
CREATE TABLE discovery_tasks (
    task_id TEXT PRIMARY KEY,
    site TEXT NOT NULL,
    source_type TEXT NOT NULL,
    config JSON,           -- 任务配置JSON
    last_run_at TIMESTAMP,
    last_cursor TEXT,      -- 上次抓取的游标
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 已发现资源表（用于去重）
CREATE TABLE discovered_urls (
    url_hash TEXT PRIMARY KEY,  -- URL的MD5哈希
    url TEXT NOT NULL,
    site TEXT NOT NULL,
    content_hash TEXT,          -- 内容哈希
    discovered_at TIMESTAMP,
    task_id TEXT
);

-- 发现历史表
CREATE TABLE discovery_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id TEXT,
    resource_id TEXT,
    discovered_at TIMESTAMP,
    metadata JSON
);
```

**与其他模块的关系**：
- **依赖**：core（Resource模型）、browser（网页浏览）、auth（登录状态）
- **被依赖**：downloader（发现后下载）、workflows（编排发现→下载→发布流程）

### 3.7 downloader（资源下载）

**职责**：多种协议的资源下载

**设计要点**：
- 支持 HTTP(S)、HLS、DASH 等协议
- 断点续传和并发下载
- 下载进度回调
- 自动重试和失败处理

```python
# 使用示例
from downloader import Downloader

downloader = Downloader(concurrent=3)
resource = Resource(url="https://example.com/video.mp4")
path = await downloader.download(resource, output_dir="./downloads")
```

### 3.7 validator（资源校验）

**职责**：下载后资源的质量检查

**设计要点**：
- 文件完整性校验（hash、size）
- 媒体文件元数据解析
- 基础质量检测（黑屏、静音检测）
- 可扩展的验证规则

```python
# 使用示例
from validator import Validator, ValidationRule

validator = Validator(rules=[ValidationRule.HASH, ValidationRule.DURATION])
result = await validator.validate(resource)
```

### 3.8 publisher（资源发布）

**职责**：资源上传到目标平台

**设计要点**：
- 每个平台实现独立 publisher
- 使用独立的目标站点会话（与下载会话隔离）
- 支持标题、标签、封面等元数据
- 发布状态跟踪
- 失败重试和队列管理

```python
# 使用示例
from publisher import PublisherManager

# 创建发布管理器，指定目标平台会话
publisher = PublisherManager(
    platform="bilibili",
    session_id="bilibili_uploader"  # 使用 auth 中配置的独立会话
)

# 发布资源
result = await publisher.publish(
    resource=resource,
    metadata={
        "title": "视频标题",
        "tags": ["标签1", "标签2"],
        "description": "视频描述"
    }
)
```

## 4. 数据流设计

### 4.1 标准工作流

**完整工作流（发现→下载→校验→发布）**:

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  输入配置   │────▶│  配置会话   │────▶│  发现资源   │
└─────────────┘     └─────────────┘     └──────┬──────┘
                                               │
    ┌──────────────────────────────────────────┘
    ▼
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  下载资源   │────▶│  校验资源   │────▶│  发布资源   │
└─────────────┘     └─────────────┘     └─────────────┘
                                               │
                                               ▼
                                        ┌─────────────┐
                                        │  输出结果   │
                                        └─────────────┘
```

**发现优先工作流**（适用于监控场景）:

```
┌─────────────────────────────────────────────────────────────┐
│                      监控循环                                 │
│  ┌─────────────┐     ┌─────────────┐     ┌─────────────┐   │
│  │  发现资源   │────▶│  过滤去重   │────▶│  触发处理   │   │
│  └─────────────┘     └─────────────┘     └──────┬──────┘   │
│       ▲                                         │          │
│       └─────────────────────────────────────────┘          │
│                    （新资源触发）                           │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
                    ┌─────────────────┐
                    │  进入标准工作流   │
                    │ （下载→校验→发布）│
                    └─────────────────┘
```

### 4.2 数据结构传递

各阶段统一使用 `Resource` 对象传递，通过 `status` 字段标识当前阶段：

```python
@dataclass
class Resource:
    id: str                    # 全局唯一标识
    source: str               # 来源站点
    source_url: str | None    # 原始 URL
    local_path: Path | None   # 本地路径
    metadata: ResourceMetadata # 标题、标签、描述等
    status: ResourceStatus     # 当前状态
    created_at: datetime
    updated_at: datetime
```

## 5. 依赖管理

### 5.1 Workspace 配置

根目录 `pyproject.toml`：

```toml
[project]
name = "kaitian"
version = "0.1.0"
description = "模块化自动化采集与搬运工具集"
requires-python = ">=3.12"

[tool.uv.workspace]
members = ["packages/*", "apps/*"]

[tool.uv.sources]
core = { workspace = true }
auth = { workspace = true }
browser = { workspace = true }
stealth = { workspace = true }
captcha = { workspace = true }
discovery = { workspace = true }
downloader = { workspace = true }
validator = { workspace = true }
publisher = { workspace = true }
```

### 5.2 模块依赖关系

```
core                ← 无依赖（被所有人依赖）
auth                ← core
stealth             ← core
browser             ← core, auth, stealth
captcha             ← core, browser
discovery           ← core, browser, auth
downloader          ← core, browser, discovery
validator           ← core
publisher           ← core, auth, browser
```

**依赖规则**：
- 禁止循环依赖
- 上层模块可依赖下层，同层模块尽量不互相依赖
- `browser` 依赖 `stealth` 实现反检测功能
- `discovery` 依赖 `browser` 进行网页浏览和资源发现
- `downloader` 依赖 `browser` 处理需要浏览器渲染的资源，可选依赖 `discovery` 获取资源列表
- `captcha` 依赖 `browser` 进行页面验证码检测

**会话管理原则**：
- `auth` 管理所有站点会话，支持多账号隔离
- `discovery`、`downloader` 和 `publisher` 可分别使用不同的会话
- 工作流层负责指定：发现会话 → 下载会话 → 发布会话的映射

**数据流向**：
```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  discovery  │────▶│  downloader │────▶│  validator  │────▶│  publisher  │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
      │                                                    │
      └────────────────────────────────────────────────────┘
                          ↕
                    ┌─────────────┐
                    │    core     │
                    │  (Resource) │
                    └─────────────┘
```

## 6. 配置管理

### 6.1 配置层级

按优先级从高到低：

1. **环境变量**：`KAITIAN_` 前缀
2. **本地配置文件**：`./kaitian.toml`
3. **用户配置**：`~/.config/kaitian/config.toml`
4. **项目默认**：`pyproject.toml [tool.kaitian]`

### 6.2 配置内容示例

```toml
# kaitian.toml
[database]
path = "./data/kaitian.db"  # SQLite 数据库路径

[browser]
headless = true
timeout = 30000
user_data_dir = "./data/browser"

[stealth]
enabled = true
fingerprint_preset = "chrome_windows"  # 或 random, safari_mac
human_like = true
noise_level = "medium"

[captcha]
enabled = true
default_backend = "2captcha"  # 或 capsolver, local
api_key = { env = "KAITIAN_CAPTCHA_API_KEY" }  # 从环境变量读取

[download]
concurrent = 3
chunk_size = "1MB"
retry_times = 3
output_dir = "./downloads"

[discovery]
db_path = "./data/discovery.db"  # 发现模块数据库路径
enable_deduplication = true       # 启用去重
deduplication_strategy = "url_hash"  # 去重策略: url_hash, content_hash, similarity

[discovery.task_defaults]
max_results_per_run = 100         # 每次运行最大结果数
request_interval = 1.0            # 请求间隔(秒)
retry_times = 3

# 发现任务配置示例
[discovery.tasks.tech_news]
site = "example-tech-site"
source_type = "news"
schedule = { interval_minutes = 30 }  # 每30分钟检查一次
filters = { category = "technology", language = "zh" }

[discovery.tasks.forum_monitor]
site = "example-forum"
source_type = "post"
schedule = { interval_minutes = 5 }   # 每5分钟检查一次
filters = { board = "hot", min_replies = 10 }

# 来源站点会话配置
[auth.youtube.main]
type = "cookie"
# 敏感信息通过环境变量：KAITIAN_AUTH_YOUTUBE_MAIN_COOKIE

[auth.youtube.backup]
type = "oauth"
# 敏感信息通过环境变量

# 目标站点会话配置（可与来源不同）
[auth.bilibili.uploader]
type = "cookie"
# 敏感信息通过环境变量：KAITIAN_AUTH_BILIBILI_UPLOADER_COOKIE

[auth.bilibili.backup]
type = "sms"
phone = "138****8888"
# 验证码通过交互输入或打码平台
```

## 7. 目录结构规范

### 7.1 包目录结构

每个包遵循统一结构（去掉 kaitian- 前缀）：

```
packages/core/
├── pyproject.toml           # 包元数据
├── README.md                # 包说明
├── src/
│   └── core/                # 包代码（简化命名）
│       ├── __init__.py
│       ├── __version__.py
│       ├── types.py         # 类型定义
│       ├── exceptions.py    # 异常定义
│       ├── config.py        # 配置读取
│       ├── models.py        # 数据模型
│       └── core.py          # 核心实现
├── tests/                   # 单元测试
│   ├── __init__.py
│   ├── test_xxx.py
│   └── conftest.py
└── examples/                # 使用示例
    └── basic_usage.py
```

### 7.2 应用目录结构

```
apps/cli/
├── pyproject.toml
├── README.md
├── src/
│   └── cli/                 # 简化命名
│       ├── __init__.py
│       ├── main.py          # 入口点
│       ├── commands/        # 子命令
│       └── utils.py
└── tests/

apps/api/
├── pyproject.toml
├── README.md
├── src/
│   └── api/                 # 简化命名
│       ├── __init__.py
│       ├── main.py          # FastAPI app
│       ├── routers/         # API 路由
│       ├── dependencies.py  # 依赖注入
│       └── models.py        # Pydantic 模型
└── tests/
```

### 7.3 工作流目录

```
workflows/
├── README.md
├── common/                  # 共享工具函数
├── youtube-to-bilibili/     # 具体工作流
│   ├── config.toml
│   ├── workflow.py
│   └── README.md
└── twitter-archive/         # 另一工作流
    ├── config.toml
    └── workflow.py
```

## 8. 接口设计规范

### 8.1 模块公共 API

每个模块的 `__init__.py` 必须显式导出公共 API：

```python
# packages/downloader/src/downloader/__init__.py

from .types import DownloadOptions, DownloadResult
from .exceptions import DownloadError, RetryExhausted
from .core import Downloader

__all__ = [
    "Downloader",
    "DownloadOptions",
    "DownloadResult",
    "DownloadError",
    "RetryExhausted",
]

__version__ = "0.1.0"
```

### 8.2 错误处理

使用异常而非返回码：

```python
class KaitianError(Exception):
    """所有异常的基类"""
    pass

class AuthError(KaitianError):
    """认证相关错误"""
    pass

class DownloadError(KaitianError):
    """下载相关错误"""
    def __init__(self, message: str, url: str, retryable: bool = True):
        super().__init__(message)
        self.url = url
        self.retryable = retryable
```

### 8.3 异步接口

所有 I/O 操作统一使用 `async/await`：

```python
class Downloader:
    async def download(self, resource: Resource) -> Path:
        """异步下载资源"""
        ...
    
    async def download_batch(
        self, 
        resources: list[Resource],
        *,
        max_concurrent: int = 3
    ) -> list[DownloadResult]:
        """批量异步下载，控制并发数"""
        ...
```

## 9. 测试策略

### 9.1 测试层级

```
tests/
├── unit/                    # 单元测试
│   ├── test_core.py
│   └── test_models.py
├── integration/             # 集成测试
│   ├── test_auth_flow.py
│   └── test_download_pipeline.py
└── e2e/                     # 端到端测试
    └── test_full_workflow.py
```

### 9.2 测试原则

- 单元测试：每个包独立运行，Mock 外部依赖
- 集成测试：使用测试数据库和临时目录
- E2E 测试：完整工作流验证，标记为 `slow`

### 9.3 运行测试

```bash
# 运行所有测试
uv run pytest

# 运行单元测试（快速）
uv run pytest -m "not slow"

# 运行特定模块测试
uv run pytest packages/downloader
```

## 10. 开发工作流

### 10.1 初始化开发环境

```bash
# 克隆仓库
git clone https://github.com/your-org/kaitian.git
cd kaitian

# 安装 uv（如果未安装）
curl -LsSf https://astral.sh/uv/install.sh | sh

# 安装所有依赖（workspace 模式）
uv sync

# 安装预提交钩子
uv run pre-commit install
```

### 10.2 日常开发

```bash
# 进入特定包开发
cd packages/downloader

# 安装该包及其依赖
uv sync

# 运行测试
uv run pytest

# 格式化和检查
uv run ruff check .
uv run ruff format .
uv run mypy src/

# 本地安装以便在其他包引用
uv pip install -e .
```

### 10.3 添加新模块

```bash
# 使用模板创建新包（简化命名，去掉 kaitian- 前缀）
cd packages
mkdir newmodule
cd newmodule

# 创建基础文件结构
touch pyproject.toml README.md
mkdir -p src/newmodule tests examples

# 编辑 pyproject.toml，添加 workspace 依赖
# 根目录 uv sync 自动识别新包
```

## 11. 风险与应对

### 11.1 识别风险

随着需求增加，可能出现以下问题：

1. **流程固化**：工作流脚本逐渐写死站点细节
2. **模块耦合**：模块之间产生隐式依赖
3. **配置膨胀**：配置文件变得复杂难以维护
4. **技术债务**：快速迭代导致代码质量下降

### 11.2 应对措施

| 风险 | 预防措施 | 检测方法 |
|------|----------|----------|
| 流程固化 | 工作流只负责串联，逻辑下沉到模块 | 代码审查检查站点硬编码 |
| 模块耦合 | 禁止跨模块直接导入 | 静态分析检查导入关系 |
| 配置膨胀 | 配置必须有默认值，可选即省略 | 定期审查配置项数量 |
| 技术债务 | 每个 PR 必须通过 lint 和测试 | CI 强制检查 |

## 12. 演进路线

### Phase 1：基础框架（当前）
- [x] 项目结构搭建
- [ ] core 实现
- [ ] auth 基础版本（支持多站点/多账号）
- [ ] browser 封装

### Phase 2：核心能力
- [ ] stealth 反检测模块
- [ ] captcha 验证码处理
- [ ] discovery 资源发现模块（站点适配、增量抓取、监控循环）
- [ ] downloader 实现
- [ ] validator 基础校验
- [ ] CLI 工具
- [ ] 首个完整工作流

### Phase 3：扩展与优化
- [ ] publisher 实现
- [ ] API 服务
- [ ] 更多平台适配
- [ ] 性能优化

### Phase 4：（待定）
根据实际使用反馈决定方向，可能包括：
- 可视化监控面板
- 更多存储后端支持
- 分布式部署方案

---

**文档维护**：任何结构变更必须同步更新本文档，并在 PR 中说明变更理由。
