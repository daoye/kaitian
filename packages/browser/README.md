# browser

KaiTian browser 模块 - 基于 rebrowser-playwright 的生产级浏览器自动化管理。

## 安装

```bash
pip install -e .
```

### 系统依赖

- Python 3.12+
- rebrowser-playwright 1.52+
- 系统 Chrome（优先使用系统已安装的 Google Chrome / Chrome Stable）


rebrowser-playwright 是 Playwright 的兼容发行版，当前项目保留 `playwright.*` API 不变，但默认在 `chromium` 引擎上优先启动系统 Chrome。

```bash
# Debian / Ubuntu 示例
google-chrome-stable --version
```

## 快速开始

```python
from browser import BrowserManager, BrowserLaunchOptions

# 创建浏览器管理器
manager = BrowserManager(BrowserLaunchOptions(headless=True))

# 使用 async with 自动管理生命周期
async with manager:
    # 获取默认上下文
    context = await manager.get_default_context()

    # 创建页面
    page = await context.new_page()

    # 导航到目标网站
    await page.goto("https://example.com")

    # 获取页面内容
    content = await page.content()
```

## CLI 使用

KaiTian CLI 支持通过命令行控制 CDP 模式：

```bash
# 启用 CDP，使用默认端口
uv run kaitian auth login --site znzmo --account test --enable-cdc --no-headless

# 启用 CDP，指定端口
uv run kaitian auth login --site znzmo --account test --enable-cdc --cdp-port 9223 --no-headless

# 禁用 CDP（默认）
uv run kaitian auth login --site znzmo --account test --disable-cdc
```

**CLI 参数说明**：

- `--enable-cdc` / `--disable-cdc`：控制是否启用 Chrome DevTools Protocol
- `--cdp-port`：指定 CDP 端口（可选，默认 9222）
- `--headless` / `--no-headless`：控制是否无头模式（CDP 模式通常需要 `--no-headless`）

**连接到 CDP**：

启用 CDP 后，可以使用 Chrome DevTools 连接：

1. 打开 Chrome DevTools：在浏览器地址栏输入 `chrome://inspect`
2. 或者直接访问：`http://localhost:9222/json`
3. 点击对应的会话进行调试

**运行时兼容性**：

- `rebrowser-playwright` 仅替换浏览器运行时分发包，`playwright.*` API 保持不变
- `BrowserManager` 仍然使用 `playwright.async_api` 导入方式，无需额外适配代码
- `BrowserManager` 在 `chromium` 模式下默认优先启动系统 Chrome，不走 Playwright 自带浏览器

## 核心 API

### BrowserManager

浏览器生命周期管理器，负责浏览器启动、上下文管理和资源释放。

```python
class BrowserManager:
    def __init__(
        self,
        launch_options: BrowserLaunchOptions | None = None,
        playwright_factory: Any = None,
        stealth_hook: Any = None,
    )

    async def start(self) -> "BrowserManager"
    """启动浏览器，幂等操作"""

    async def new_context(
        self,
        options: BrowserContextOptions | None = None
    ) -> ManagedBrowserContext
    """创建新的浏览器上下文，支持复用键"""

    async def get_default_context(self) -> ManagedBrowserContext
    """获取默认上下文（自动创建）"""

    async def new_page(self) -> Any
    """在默认上下文中创建新页面"""

    async def add_route(self, pattern: str, handler: RouteHandler) -> None
    """添加全局路由规则"""

    async def close(self) -> None
    """关闭浏览器和所有上下文，幂等操作"""

    async def apply_session(
        self,
        session: Session,
        base_url: str | None = None
    ) -> None
    """应用会话状态（cookies 和 headers）"""
```

### ManagedBrowserContext

托管的浏览器上下文，提供页面管理和状态操作。

```python
class ManagedBrowserContext:
    @property
    def raw(self) -> Any
    """获取原始 Playwright 上下文对象"""

    async def new_page(self) -> Any
    """在上下文中创建新页面"""

    async def add_cookies(self, cookies: list[dict[str, Any]]) -> None
    """添加 cookies 到上下文"""

    async def cookies(self) -> list[dict[str, Any]]
    """获取上下文中的所有 cookies"""

    async def storage_state(
        self,
        path: str | None = None
    ) -> dict[str, Any]
    """导出存储状态（cookies + localStorage）"""

    async def set_extra_http_headers(
        self,
        headers: dict[str, str]
    ) -> None
    """设置额外的 HTTP 请求头"""

    async def close(self) -> None
    """关闭上下文，幂等操作"""
```

### 数据模型

#### BrowserLaunchOptions

```python
@dataclass
class BrowserLaunchOptions:
    engine: BrowserEngine = "chromium"      # 浏览器引擎
    headless: bool = True                    # 是否无头模式
    timeout_ms: int = 30000                  # 启动超时（毫秒）
    slow_mo_ms: int = 0                      # 慢速模式（毫秒）
    enable_cdc: bool = False                 # 是否启用 Chrome DevTools Protocol
    cdp_port: int | None = None              # Chrome DevTools Protocol 端口（默认 9222）
    launch_args: list[str] = []              # 额外启动参数
    proxy: dict[str, str] | None = None      # 代理配置
```

**Chrome DevTools Protocol (CDP) 模式**

启用 CDP 模式后，浏览器将开启远程调试端口，允许外部工具（如 Chrome DevTools、Puppeteer）连接。

```python
# 启用 CDP，使用默认端口 9222
launch_options = BrowserLaunchOptions(
    enable_cdc=True,
    headless=False,  # CDP 模式通常需要非无头模式
)

# 启用 CDP，指定端口
launch_options = BrowserLaunchOptions(
    enable_cdc=True,
    cdp_port=9223,
    headless=False,
)
```

**使用场景**：
- 开发调试：使用 Chrome DevTools 连接到浏览器
- 自动化测试：使用 CDP 协议进行高级控制
- 性能分析：监控浏览器性能指标

#### BrowserContextOptions

```python
@dataclass
class BrowserContextOptions:
    reuse_key: str | None = None             # 复用键，相同键返回同一上下文
    base_url: str | None = None              # 基础 URL
    viewport: dict[str, int] | None = None   # 视口大小 {"width": 1920, "height": 1080}
    user_agent: str | None = None            # 用户代理
    locale: str | None = None                # 区域设置
    timezone_id: str | None = None           # 时区 ID
    storage_state: str | dict | None = None  # 存储状态（路径或对象）
    extra_http_headers: dict[str, str] = {}  # 额外请求头
    default_timeout_ms: int | None = None    # 默认超时
    navigation_timeout_ms: int | None = None # 导航超时
```

#### Cookie

```python
@dataclass
class Cookie:
    name: str                    # Cookie 名称
    value: str                   # Cookie 值
    domain: str                  # 域名（如 ".example.com"）
    path: str = "/"              # 路径
    expires: int | None = None   # 过期时间戳
    http_only: bool = False      # HttpOnly 标志
    secure: bool = False         # Secure 标志
    same_site: str | None = None # SameSite 属性
```

## 生命周期管理

### 所有权模型

```
BrowserManager (1) ---> ManagedBrowserContext (N) ---> Page (M)
    |                           |                        |
    |                           |                        |
  负责启动                    负责隔离                 负责操作
  和关闭浏览器                和状态管理               和导航
```

**关键规则**：

1. **BrowserManager** 拥有浏览器进程生命周期
   - `start()` 启动浏览器（幂等）
   - `close()` 关闭浏览器和所有上下文（幂等）
   - 使用 `async with` 自动管理

2. **ManagedBrowserContext** 拥有上下文生命周期
   - 每个上下文是独立的浏览器会话（隔离的 cookies、storage）
   - `reuse_key` 相同则返回同一上下文实例
   - `close()` 关闭上下文（幂等）

3. **页面** 不单独管理
   - 页面生命周期由上下文管理
   - 页面关闭不影响上下文

### 推荐调用顺序

```python
# 1. 创建管理器（未启动）
manager = BrowserManager(launch_options)

# 2. 启动浏览器（显式或隐式）
await manager.start()
# 或在 new_context 时自动启动

# 3. 创建/获取上下文
context = await manager.new_context(options)

# 4. 创建页面
page = await context.new_page()

# 5. 执行操作...
await page.goto("https://example.com")

# 6. 清理（从里到外）
await page.close()           # 可选，非必须
await context.close()        # 关闭上下文
await manager.close()        # 关闭浏览器

# 或使用 async with 自动清理
async with BrowserManager() as manager:
    async with await manager.new_context() as context:
        page = await context.new_page()
        # ...
```

### 复用键语义

`reuse_key` 用于在多个调用间共享同一上下文：

```python
# 第一次创建
context1 = await manager.new_context(
    BrowserContextOptions(reuse_key="session_123")
)

# 第二次返回同一实例
context2 = await manager.new_context(
    BrowserContextOptions(reuse_key="session_123")
)

assert context1 is context2  # True
```

**约束**：
- 相同 `reuse_key` 返回同一 `ManagedBrowserContext` 实例
- 不同 `reuse_key` 创建独立上下文
- `reuse_key` 为 `None` 时总是创建新上下文
- 复用上下文的生命周期由调用方共同管理

## 状态管理

### Cookie 管理

```python
# 添加单个 cookie
await context.add_cookies([{
    "name": "session_id",
    "value": "abc123",
    "domain": ".example.com",
    "path": "/",
    "httpOnly": True,
    "secure": True,
}])

# 获取所有 cookies
all_cookies = await context.cookies()

# 从 Session 应用 cookies
from core.models import Session
session = Session(
    site="example.com",
    cookies={"session_id": "abc123"},
    headers={"Authorization": "Bearer token"}
)
await manager.apply_session(session, base_url="https://example.com")
```

**边界与约束**：
- Cookie domain 必须匹配目标站点，否则会被浏览器拒绝
- `apply_session` 自动推断 cookie domain（从 base_url 或 session.site）
- Cookie 大小和数量受浏览器限制（通常 4KB/个，300 个/域）

### Storage State 导入/导出

```python
# 导出完整状态（cookies + localStorage）
state = await context.storage_state()
# 或保存到文件
await context.storage_state(path="./state.json")

# 在创建上下文时导入状态
context = await manager.new_context(
    BrowserContextOptions(storage_state="./state.json")
)
# 或直接传入对象
context = await manager.new_context(
    BrowserContextOptions(storage_state=state)
)
```

**边界与约束**：
- `storage_state` 包含 cookies 和 localStorage，不包含 sessionStorage
- 导入状态后，新上下文继承原状态但独立演化
- 文件路径不存在时会抛出 `BrowserContextError`
- 无效的状态格式会抛出异常，不会静默失败

## 路由拦截

```python
# 拦截特定 URL 模式
await manager.add_route(
    "**/*.{png,jpg,jpeg}",
    lambda route: route.abort()  # 拦截图片加载
)

# 在上下文中拦截
context = await manager.new_context()
await context._context.route(
    "**/api/**",
    lambda route: route.fulfill(status=200, body='{"mock": true}')
)
```

## 与 stealth 模块集成

```python
from browser import BrowserManager
from stealth import StealthManager, StealthConfig

# 创建 stealth 管理器
stealth = StealthManager(StealthConfig(
    fingerprint_preset="chrome_windows",
    noise_level="medium",
))

# 传入 stealth hook
manager = BrowserManager(
    launch_options=BrowserLaunchOptions(headless=True),
    stealth_hook=stealth.apply_to_context,
)

async with manager:
    # 新创建的上下文自动应用反检测
    context = await manager.new_context()
    page = await context.new_page()
    # 页面已应用反检测脚本
```

**集成约束**：
- `stealth_hook` 在 `ManagedBrowserContext.initialize()` 时调用
- hook 接收原始 Playwright 上下文对象
- 如果 hook 失败，上下文初始化失败，抛出 `BrowserContextError`

## 异常处理

### 异常类型

```python
from browser.exceptions import (
    BrowserError,           # 基类
    BrowserLaunchError,     # 浏览器启动失败
    BrowserContextError,    # 上下文操作失败
    BrowserPageError,       # 页面操作失败
    BrowserCookieError,     # Cookie 操作失败
    BrowserSessionError,    # 会话应用失败
    BrowserTimeoutError,    # 超时错误
)

# 捕获特定异常
try:
    await manager.start()
except BrowserLaunchError as e:
    print(f"启动失败: {e}")
    print(f"详情: {e.details}")  # {"cause": "..."}
```

### 错误处理模式

```python
# 模式 1: 细粒度处理
async def safe_operation(manager: BrowserManager):
    try:
        context = await manager.new_context()
    except BrowserLaunchError:
        # 浏览器未启动或启动失败
        return None
    except BrowserContextError as e:
        # 上下文创建失败
        logger.error(f"Context failed: {e.details}")
        return None

    try:
        page = await context.new_page()
    except BrowserContextError:
        # 页面创建失败
        await context.close()
        return None

    return page

# 模式 2: 使用上下文管理器自动清理
async with BrowserManager() as manager:
    try:
        context = await manager.new_context()
        page = await context.new_page()
        # ...
    except BrowserError as e:
        # 任何浏览器相关错误都会触发清理
        logger.error(f"Browser operation failed: {e}")
        raise
```

## 生产部署

### 环境要求

- **Python**: 3.12+
- **Playwright**: 1.40+
- **浏览器**: Chromium（优先使用系统 Chrome）/Firefox/WebKit（仅保留原始接口）
- **系统**: Linux/macOS/Windows，推荐 Linux 服务器
- **内存**: 至少 2GB RAM（每个浏览器实例约 100-300MB）
- **磁盘**: 至少 1GB 可用空间（浏览器二进制 + 缓存）

### Docker 部署示例

```dockerfile
FROM python:3.12-slim

# 安装 Playwright 依赖
RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    libnss3 \
    libnspr4 \
    libatk1.0-0 \
    libatk-bridge2.0-0 \
    libcups2 \
    libdrm2 \
    libdbus-1-3 \
    libxcb1 \
    libxkbcommon0 \
    libx11-6 \
    libxcomposite1 \
    libxdamage1 \
    libxext6 \
    libxfixes3 \
    libxrandr2 \
    libgbm1 \
    libpango-1.0-0 \
    libcairo2 \
    libasound2 \
    && rm -rf /var/lib/apt/lists/*

# 安装 Python 依赖
COPY requirements.txt .
RUN pip install -r requirements.txt

# 确保镜像内已有系统 Chrome
RUN google-chrome-stable --version

# 复制应用代码
COPY . /app
WORKDIR /app

CMD ["python", "main.py"]
```

### CI/CD 配置

```yaml
# .github/workflows/test.yml
name: Browser Tests

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3

      - name: Setup Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          pip install -e packages/browser
          google-chrome-stable --version

      - name: Run tests
        run: uv run pytest packages/browser/tests -v
```

## 故障排除

### 启动失败

**症状**: `BrowserLaunchError: failed to launch browser`

**常见原因与解决**:

1. **系统 Chrome 不可用**
   ```bash
   # 检查
   google-chrome-stable --version
   ```

2. **系统依赖缺失**（Linux）
   ```bash
   # Ubuntu/Debian
   apt-get install -y libglib2.0-0 libnss3 libnspr4 libatk1.0-0
   ```

3. **权限问题**
   - 确保浏览器二进制有执行权限
   - 在 Docker 中运行时使用非 root 用户

4. **端口冲突**
   - Playwright 使用随机端口，但如果系统端口耗尽会失败
   - 检查并释放占用端口

### Cookie 应用失败

**症状**: `BrowserCookieError: failed to add cookies`

**常见原因**:
- Cookie domain 不匹配当前页面
- Cookie 已过期
- Cookie 大小超过限制

**解决**:
```python
# 确保在导航到目标站点后添加 cookie
await page.goto("https://example.com")
await context.add_cookies([{
    "name": "key",
    "value": "value",
    "domain": ".example.com",  # 注意前面的点
    "path": "/",
}])
```

### 上下文复用混乱

**症状**: 多个调用者使用同一 `reuse_key`，但期望独立上下文

**解决**:
- 为每个独立会话使用不同的 `reuse_key`
- 或使用 `reuse_key=None` 总是创建新上下文

```python
# 为不同用户创建独立上下文
context_a = await manager.new_context(
    BrowserContextOptions(reuse_key=f"user_{user_id}_session")
)
```

### 资源泄漏

**症状**: 进程内存持续增长，浏览器实例不关闭

**常见原因**:
- 未调用 `close()`
- 异常中断导致清理代码未执行

**解决**:
```python
# 始终使用 async with
async with BrowserManager() as manager:
    # ...
    pass  # 自动清理

# 或确保 finally 块
manager = BrowserManager()
try:
    await manager.start()
    # ...
finally:
    await manager.close()  # 确保关闭
```

### 页面导航超时

**症状**: `TimeoutError: page.goto: Timeout`

**解决**:
```python
# 增加导航超时
context = await manager.new_context(
    BrowserContextOptions(navigation_timeout_ms=60000)
)

# 或使用 wait_until 参数
await page.goto(url, wait_until="domcontentloaded")  # 更快但不等待资源
```

## 测试

```bash
# 运行所有测试
uv run pytest packages/browser/tests -v

# 运行特定测试文件
uv run pytest packages/browser/tests/test_manager.py -v

# 覆盖率报告
uv run pytest packages/browser/tests --cov=browser --cov-report=html
```

## 性能优化

### 减少资源占用

```python
# 使用复用键减少上下文数量
context = await manager.new_context(
    BrowserContextOptions(reuse_key="shared_session")
)

# 限制页面数量
# 每个上下文内的页面共享资源，但过多页面会影响性能
# 建议每个上下文不超过 10 个页面
```

### 加速启动

```python
# 使用预安装的浏览器快照
# 在 Docker 中预先安装浏览器，避免运行时下载

# 禁用不必要的功能
launch_options = BrowserLaunchOptions(
    headless=True,
    launch_args=[
        "--disable-gpu",
        "--disable-dev-shm-usage",
        "--disable-setuid-sandbox",
        "--no-sandbox",
    ]
)
```

## 设计原则

1. **简单优先**：API 表面小，概念少，易于理解
2. **显式生命周期**：关闭操作幂等，资源清理可预测
3. **隔离性**：每个上下文是独立的浏览器会话
4. **可观测**：关键操作有日志，错误有上下文
5. **可扩展**：Hooks 机制支持 stealth、captcha 等扩展

## 许可证

MIT
