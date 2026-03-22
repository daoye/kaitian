# KaiTian 反检测能力设计说明书

> 文档版本：v1.0（草案）
> 最后更新：2026-03-16
> 适用范围：`packages/browser`、`packages/stealth`、`packages/captcha`、`packages/auth`

## 1. 目标与边界

### 1.1 目标

在不引入复杂基础设施的前提下，为 KaiTian 构建生产可用的反检测能力，满足以下目标：

1. 提升自动化流程在常见站点的稳定性与通过率。
2. 降低因明显自动化指纹导致的拦截概率。
3. 在触发验证码时，形成可观测、可恢复、可回退的处理链路。
4. 保持模块职责清晰，符合“简单优先、显式依赖、避免依赖注入复杂化”的项目原则。

### 1.2 非目标

1. 不引入 Redis、MQ、分布式协调等重型组件。

## 2. 设计原则

1. 简单优先：优先稳定、可维护的方案，避免“魔法技巧堆叠”。
2. 显式依赖：模块通过直接依赖与明确 API 协作。
3. 原子化：`stealth` 负责反检测能力，`captcha` 负责验证码求解，`browser` 负责流程调度。
4. 可观测：每个关键步骤应有结构化事件与失败原因。
5. 可降级：反检测失败不应导致系统崩溃，允许降级到基础模式或人工介入。

## 3. 当前现状与差距

基于仓库当前代码（2026-03-16）现状：

1. `packages/browser/src/browser/core.py` 已存在 `stealth_hook` 扩展点，在上下文初始化阶段可调用反检测逻辑。
2. `packages/stealth/src/stealth/core.py` 目前为骨架，尚无实质能力实现。
3. `packages/captcha/src/captcha/core.py` 目前为骨架，尚无统一求解编排实现。
4. `packages/auth/src/auth/sites/znzmo/authenticator.py` 已具备验证码分支，但尚未沉淀为 browser 统一挑战处理机制,需要调整，auth不关心验证码，统一由browser处理。

主要差距：

1. 缺少可配置的反检测策略模型（配置、指纹画像、行为策略）。
2. 缺少统一挑战检测与验证码处理编排。
3. 缺少反检测效果评估指标与回归测试基线。

## 4. 检测面与威胁模型（工程视角）

本项目聚焦以下常见检测面：

1. 浏览器环境指纹：`navigator.webdriver`、语言/时区、屏幕与视口一致性等。
2. 行为模式：固定速度点击、零停顿跳转、缺少滚动与鼠标轨迹。
3. 网络特征：请求过于密集、节奏稳定到不自然、错误重试不合理。
4. 会话异常：cookie/UA/时区不一致，短时间高频失效。
5. 挑战触发：出现滑块/点选/旋转/reCAPTCHA 等验证组件。

## 5. 总体架构与依赖关系

### 5.1 依赖关系（必须遵守）

```text
core      <- 无依赖
stealth   <- core
captcha   <- core
browser   <- core, stealth, captcha
auth      <- core, browser
```

说明：

1. `browser` 在页面流程中负责调用 `stealth` 与 `captcha`。
2. `captcha` 只做识别与求解，不知道浏览器实现细节。
3. `auth` 直接使用 `browser`，不关心验证码、反爬虫等browser细节。

### 5.2 运行时链路

```text
Auth 登录流程
  -> BrowserManager.start()
  -> BrowserManager.new_context()
       -> StealthManager.apply_to_context()
  -> BrowserManager.new_page()
  -> 页面操作（goto/fill/click/wait）
  -> BrowserManager.detect_challenge(page)
       -> CaptchaManager.solve(...)
       -> BrowserManager.apply_challenge_solution(...)
  -> 登录结果判断与会话提取
```

## 6. 可行方案分级

### 6.1 P0 基线方案（建议先落地）

目标：低风险、可快速上线。

外部实践共识：会话内一致性优先于高噪声随机化。

能力包含：

1. 基础指纹一致性处理：语言、时区、UA、viewport 与 headers 对齐。
2. `navigator.webdriver` 等常见自动化暴露项基础修正（通过初始化脚本）。
3. 页面行为微扰：随机停顿区间、滚动与点击节奏抖动。
4. 挑战检测与统一事件上报：发现验证码即进入 `captcha` 处理链路。
5. 失败降级：求解失败时返回 `manual_required`，不中断主进程。

适用：大多数普通目标站点的第一阶段生产部署。

### 6.2 P1 增强方案

目标：提升稳定性和对复杂场景的适配。

能力包含：

1. 指纹画像模板（按站点/地区/设备类型切换）。
2. 行为策略分层（阅读型、搜索型、登录型三类轨迹模型）。
3. 会话连续性增强（cookie、storage_state、header 协同校验）。
4. 风险评分与动态策略：根据挑战触发率自动降频和切换策略。

### 6.3 P2 高阶方案（谨慎）

目标：在可维护前提下进一步优化通过率。

能力包含：

1. 站点级反检测策略包（白名单启用，避免全局副作用）。
2. 更细粒度的网络节奏建模（非固定间隔请求窗口）。
3. 面向挑战类型的分流编排（滑块/点选/旋转/文本验证码）。

注意：P2 仅在 P0/P1 指标稳定后推进，禁止一次性堆叠高复杂策略。

## 7. 模块职责设计

### 7.0 core 侧数据模型建议

为避免能力散落在各模块私有字段中，建议在 `core` 先补齐以下纯数据模型：

1. `SitePolicy`：站点策略（挑战选择器、最大重试、冷却时间、是否自动求解）。
2. `FingerprintProfile`：指纹画像（UA、viewport、locale、timezone、headers）。
3. `StealthPlan`：由 `stealth` 生成的执行计划（launch args、context options、init scripts）。
4. `ChallengeSignal`：挑战检测信号（类型、来源选择器、置信度、截图路径）。
5. `ChallengeSolveRequest`：验证码求解请求（challenge 元信息 + 图片/上下文）。
6. `ChallengeResult`：求解结果（`solved/manual_required/unsupported/failed`）。
7. `DetectionEvent`：结构化观测事件（阶段、结果、耗时、错误码）。

说明：

1. 先落 dataclass，不引入额外复杂抽象。
2. `Session.metadata` 继续承载运行时绑定信息，如 `profile_id`、`proxy_key`、`challenge_count`。

### 7.1 stealth 模块

职责：提供“反检测能力集合”，不负责页面业务流程。

建议对外 API（示意）：

1. `StealthManager(profile: StealthProfile)`
2. `apply_to_context(context) -> None`
3. `apply_to_page(page) -> None`（可选）

建议配置项：

1. `fingerprint_preset`: `random | chrome_windows | safari_mac | mobile_android`
2. `human_like`: `true/false`
3. `noise_level`: `low | medium | high`
4. `enabled_patches`: 明确启用哪些补丁，避免黑盒。

### 7.2 captcha 模块

职责：识别与求解验证码，返回统一结果对象。

建议对外 API（示意）：

1. `CaptchaManager.solve(challenge: CaptchaChallenge) -> CaptchaOutcome`
2. `CaptchaOutcome.status`: `solved | failed | manual_required | not_present`
3. `CaptchaOutcome.data`: 结构化求解结果与置信信息。

### 7.3 browser 模块

职责：流程编排者。

关键职责：

1. 在 context 初始化时调用 `stealth`。
2. 在页面流程中检测挑战并调用 `captcha`。
3. 统一记录挑战事件和处理结果。
4. 对外暴露稳定 API（`new_page`、`apply_session`、`solve_challenge_if_present` 等）。

建议新增/收敛 API：

1. `guarded_goto(page, url, checkpoint)`：带检查点的导航。
2. `guarded_checkpoint(page, checkpoint)`：执行挑战检测与策略决策。
3. `handle_challenge(page, signal)`：统一调用 captcha 并回填。

关键策略：

1. fail-closed：超过重试预算或未知挑战时，立即终止当前流程并记录事件。
2. 保持会话内一致性：同一会话内禁止频繁随机切换 UA/时区/视口。
3. 限制重试：避免无限循环触发风控升级。

### 7.4 auth 模块

职责：站点登录业务编排。

关键点：

1. 直接使用 `BrowserManager`（遵循当前项目“避免复杂 DI”约束）。
2. 登录流程中复用 browser 的挑战处理能力，不自行重复实现 challenge 编排。

## 8. 配置与开关设计

建议在统一配置中加入：

```toml
[stealth]
enabled = true
fingerprint_preset = "chrome_windows"
human_like = true
noise_level = "medium"

[captcha]
enabled = true
default_backend = "2captcha"
timeout_seconds = 20
max_retry = 2

[browser.challenge]
auto_solve = true
manual_fallback = true
max_challenge_per_session = 3
```

## 9. 验证指标与验收标准

### 9.1 核心指标

1. 登录成功率（按站点/账号分层统计）。
2. 挑战触发率（challenge per 100 sessions）。
3. 自动求解成功率与平均耗时。
4. 会话有效期中位数（反映稳定性）。
5. 回归失败率（升级策略后核心流程失败比例）。
6. 指纹一致性失败率（同会话内 UA/时区/语言/viewport 冲突占比）。
7. 挑战识别覆盖率（已识别挑战 / 总挑战事件）。

### 9.2 验收门槛（建议）

1. P0 上线前：核心站点登录成功率 >= 90%。
2. 挑战处理后续流程不中断率 >= 95%。
3. 引入新策略后，回归测试通过率 100%。

## 10. 测试策略

### 10.1 单元测试

1. `stealth`：补丁注入是否生效、配置是否合法。
2. `captcha`：不同 challenge 类型分发与返回状态。
3. `browser`：挑战检测、求解调用、失败降级逻辑。

### 10.2 集成测试

1. `auth + browser + captcha` 登录链路联测。
2. 有验证码与无验证码两条主路径。
3. 会话提取与复用行为一致性验证。

### 10.3 回归测试

1. 每次策略调整都跑固定站点样本集。
2. 输出对比报告：成功率、耗时、挑战率变化。

## 11. 风险与合规

1. 反检测策略可能在站点升级后失效，必须具备快速回滚与降级路径。
2. 禁止实现非法用途导向能力，严格遵守目标站点条款和法律边界。
3. 高复杂策略必须灰度验证，避免全量启用导致系统性失败。
4. 禁止高噪声随机化策略破坏会话一致性，避免“越伪装越异常”。
5. 遇到 403/429 等拒绝信号必须退避与降频，禁止盲目重试。

## 12. 分阶段落地计划

### Phase A（1-2 周）：P0 基线落地

1. 完成 `stealth` 基础补丁与配置解析。
2. 在 `browser` 中落地挑战检测与 `captcha` 调用入口。
3. 打通 `auth` 登录流程复用 browser 挑战处理能力。
4. 建立基础观测事件与测试用例。

### Phase B（2-4 周）：P1 增强能力

1. 指纹模板与行为策略分层。
2. 风险评分和动态降频策略。
3. 补齐集成测试和回归基线报告。

### Phase C（按需）：P2 高阶优化

1. 站点级策略包白名单。
2. 细粒度挑战分流与策略编排。

## 13. 可行性策略矩阵（工程决策）

| 能力 | 价值 | 风险 | 建议优先级 |
|---|---|---|---|
| 指纹一致性对齐（UA/Locale/Timezone/Viewport） | 高 | 低 | P0 |
| 行为微扰（停顿/滚动/点击节奏） | 高 | 中 | P0 |
| 会话持续化（cookies/storage_state） | 高 | 低 | P0 |
| 挑战检测与降级闭环 | 高 | 低 | P0 |
| 指纹模板池（按站点切换） | 中高 | 中 | P1 |
| 风险评分与动态降频 | 中高 | 中 | P1 |
| 高级 TLS 指纹干预 | 中 | 高 | P2 |
| 激进随机化（全信号频繁切换） | 低 | 高 | 禁用 |

## 14. 当前版本执行清单（可直接转开发任务）

1. 在 `packages/stealth` 定义 `StealthProfile` 与最小可用 `StealthManager`。
2. 在 `packages/captcha` 定义 `CaptchaChallenge/CaptchaOutcome` 与 `CaptchaManager`。
3. 在 `packages/browser` 增加 `solve_challenge_if_present(page)` 与结构化事件记录。
4. 在 `packages/auth` 登录流程中复用 browser 挑战处理入口。
5. 增加 `stealth`、`captcha`、`browser` 三层测试与一条登录集成测试。

## 15. 外部参考（调研依据）

1. rebrowser-playwright / Playwright BrowserContext 文档（storage_state、cookies、context 配置）。
2. `playwright-stealth` 项目文档（可选能力参考，不强耦合）。
3. Browserless 2026 实践总结（强调信号一致性、渐进式升级）。
4. Cloudflare/验证码处理公开资料（用于挑战识别与恢复策略边界）。

注：外部资料仅作为工程参考，项目实现以可维护性、合规性和可观测性为第一优先。当前浏览器运行时主路径为 `rebrowser-playwright + chromium`。

## 16. 关键工程约束（必须遵守）

1. 架构分层固定：`browser` 编排、`stealth` 产出方案、`captcha` 求解、`auth` 站点流程。
2. 依赖方向固定：`browser -> stealth/captcha`，`captcha` 不反向依赖 `browser`。
3. 不引入依赖注入容器，保持显式构造与直接依赖。
4. 先指标后优化：没有指标不允许升级策略复杂度。

## 17. 当前诊断结论（2026-03-22）

基于 `3dbrute.com` 真实链路复测与代码审计，当前反检测实现存在“过度激活导致异常指纹组合”的风险，属于实现不准确而非手段不足。关键证据：`packages/auth/src/auth/sites/three_dbrute/authenticator.py` 当前使用 `enabled_patches=get_available_patches()` 且 `risk_limit="high"`，导致 `packages/stealth/src/stealth/types.py` 中默认禁用的高风险补丁也被启用；运行态采样显示 `effective_patches=21`（含 `iframe_content_window`、`media_codecs`），但仍落在 Cloudflare `Just a moment...` interstitial。

当前应执行“先减害后增强”的修复顺序：第一，撤销 `three_dbrute` 的全量补丁与高风险策略，回到默认稳健补丁集（`default_enabled + medium`）；第二，保留并继续使用非无头人工介入等待链路（挑战后等待页面稳定并再次检测）；第三，补齐运行时可观测数据（effective_patches、challenge 类型迁移、页面稳定阶段 URL 变化）后再做逐项白名单试验，禁止再次一次性全开高风险补丁。

---

本说明书用于指导 KaiTian 反检测能力从“骨架状态”走向“可上线状态”。
原则是先稳定再增强，先可观测再优化，避免一次性过度设计。
