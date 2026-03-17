# stealth

KaiTian 反检测/反反爬虫模块。

## 功能特性

### P0 基线能力（已实现）

1. **指纹一致性处理**
   - User-Agent、语言、时区、视口尺寸对齐
   - 支持 8 种预设指纹模板（Chrome/Safari/Firefox/Edge，桌面端+移动端）
   - 会话内指纹保持一致，避免随机切换

2. **自动化特征隐藏**
   - `navigator.webdriver` 隐藏
   - `navigator.plugins` 模拟
   - `navigator.languages` 设置
   - WebGL 指纹修改
   - Canvas 噪声添加
   - Screen 对象修正

3. **行为微扰**
   - 随机点击/输入/滚动/等待延迟
   - 三级噪声级别（低/中/高）
   - 可配置的延迟范围

4. **浏览器启动参数**
   - 自动化控制特征禁用
   - 安全策略调整（可选）

## 快速开始

```python
from stealth import StealthManager, StealthConfig

# 使用默认配置
manager = StealthManager()
plan = manager.build_plan()

# 应用到 Playwright 上下文
await manager.apply_to_context(context)

# 获取随机延迟
click_delay = manager.get_random_delay("click")
```

## 配置选项

```python
from stealth import StealthConfig, StealthProfile

# 使用预设模板
config = StealthConfig(
    enabled=True,
    fingerprint_preset="chrome_windows",  # 可选: chrome_windows, safari_mac, firefox_windows, mobile_android 等
    human_like=True,
    noise_level="medium",  # 可选: low, medium, high
)

# 自定义指纹画像
custom_profile = StealthProfile(
    user_agent="Mozilla/5.0...",
    viewport={"width": 1920, "height": 1080},
    locale="zh-CN",
    timezone="Asia/Shanghai",
    platform="Win32",
)

manager = StealthManager(config, custom_profile)
```

## 预设指纹模板

| 模板 | UA 标识 | 平台 | 视口 | 适用场景 |
|------|---------|------|------|----------|
| `chrome_windows` | Chrome 120 | Win32 | 1920x1080 | 桌面端通用 |
| `chrome_mac` | Chrome 120 | MacIntel | 1920x1080 | Mac 桌面端 |
| `safari_mac` | Safari 17 | MacIntel | 1920x1080 | Mac 原生浏览器 |
| `firefox_windows` | Firefox 120 | Win32 | 1920x1080 | Firefox 用户 |
| `firefox_mac` | Firefox 120 | MacIntel | 1920x1080 | Mac Firefox |
| `edge_windows` | Edge 120 | Win32 | 1920x1080 | Windows Edge |
| `mobile_android` | Chrome Mobile | Linux armv8l | 412x915 | Android 移动端 |
| `mobile_ios` | Safari Mobile | iPhone | 393x852 | iOS 移动端 |

## 核心 API

### StealthManager

```python
class StealthManager:
    def __init__(
        self,
        config: StealthConfig | None = None,
        custom_profile: StealthProfile | None = None,
    )
    
    def build_plan(self) -> StealthPlan
    """构建反检测执行计划"""
    
    async def apply_to_context(self, context: Any) -> None
    """应用反检测设置到 Playwright 上下文"""
    
    def get_random_delay(self, action: str) -> float
    """获取随机行为延迟（click/type/scroll/wait）"""
```

### 数据模型

```python
@dataclass
class StealthProfile:
    """指纹画像配置"""
    user_agent: str
    viewport: dict[str, int]
    locale: str
    timezone: str
    platform: str
    color_depth: int
    pixel_ratio: float
    hardware_concurrency: int
    device_memory: int
    extra_headers: dict[str, str]

@dataclass
class StealthConfig:
    """反检测配置"""
    enabled: bool
    fingerprint_preset: str
    human_like: bool
    noise_level: str
    enabled_patches: list[str]

@dataclass
class StealthPlan:
    """反检测执行计划"""
    profile: StealthProfile
    init_scripts: list[str]
    launch_args: list[str]
    behavior_delays: dict[str, tuple[float, float]]
```

## 与 browser 模块集成

```python
from browser import BrowserManager
from stealth import StealthManager, StealthConfig

# 创建 stealth 管理器
stealth_manager = StealthManager(StealthConfig(
    fingerprint_preset="chrome_mac",
    noise_level="medium",
))

# 创建 browser 管理器，传入 stealth hook
browser = BrowserManager(
    stealth_hook=stealth_manager.apply_to_context
)

# 使用 browser，自动应用反检测
async with browser:
    page = await browser.new_page()
    # 页面已自动应用反检测脚本
```

## 设计原则

1. **简单优先**：只实现稳定可靠的技术，避免"魔法技巧"
2. **会话一致性**：同一会话内指纹保持一致，不频繁随机切换
3. **可配置**：所有功能可通过配置开关控制
4. **可观测**：提供完整的执行计划，便于调试和验证
5. **渐进增强**：P0 基线方案已可用，P1/P2 能力后续按需添加

## 测试

```bash
# 运行单元测试
uv run pytest packages/stealth/tests -v

# 覆盖率报告
uv run pytest packages/stealth/tests --cov=stealth --cov-report=html
```

## 注意事项

1. **不保证 100% 绕过**：现代反爬系统复杂多变，本模块提供的是基础防护
2. **遵守法律法规**：仅用于合法授权的自动化测试和数据采集
3. **避免滥用**：尊重目标站点的服务条款，合理控制请求频率
4. **持续更新**：反爬技术不断演进，需要定期维护和更新

## 参考

- [KaiTian 反检测能力设计说明书](../../docs/architecture/anti-detection-design.md)
- Playwright 官方文档: https://playwright.dev/python/

## License

MIT

