# KaiTian Cloudflare 解决方案可行性评估（FlareSolverr 与 undetected-chromedriver）

> 文档版本：v1.0
> 最后更新：2026-03-22
> 适用范围：`packages/browser`、`packages/stealth`、`packages/auth`

## 1. 目标与边界

### 1.1 目标

在 KaiTian 当前架构约束下，评估以下两种外部方案用于 Cloudflare 验证处理的可行性，并给出可落地建议：

1. FlareSolverr
2. undetected-chromedriver

### 1.2 边界

1. 仅做工程可行性与落地成本评估，不承诺任何站点 100% 通过率。
2. 保持项目既有原则：简单优先、模块原子化、最小依赖、易于本地部署。
3. 评估结论必须包含证据来源与风险说明。

## 2. 当前现状（KaiTian）

### 2.1 现有能力

1. `browser` 基于 Playwright，负责挑战检测与编排。
2. `stealth` 提供补丁化反检测能力与风险分级。
3. `auth` 站点认证器负责登录流程，不应承载过多挑战实现细节。

代码证据（仓库内）：

1. `packages/browser/src/browser/core.py`：`BrowserManager` 负责浏览器生命周期、context 创建、`stealth_hook` 注入。
2. `packages/browser/src/browser/challenges.py`：挑战检测与 token 应用入口。
3. `packages/stealth/src/stealth/core.py`：`StealthManager.apply_to_context()` 与策略计划构建。
4. `packages/captcha/src/captcha/core.py`：`CaptchaSolver` 协议与 `CaptchaOrchestrator` 编排。
5. `packages/auth/src/auth/sites/znzmo/authenticator.py`：站点登录流程对 browser/captcha 的调用方式。
6. `docs/architecture/anti-detection-design.md`：明确 `browser -> stealth/captcha` 与 `auth` 职责边界。

### 2.2 当前问题

1. 在 `3dbrute` 场景中，仍可能出现 "verify you are human" 循环验证。
2. 需要评估是否引入外部方案，及其与现有架构的契合度。

## 3. 候选方案概览

### 3.1 FlareSolverr

定位：独立代理服务，通过 REST API 驱动 Selenium + undetected-chromedriver 打开页面并返回 HTML/Cookies。

关键证据：

1. 官方 README 明确工作机制与调用方式：`/v1` API、`request.get/post`、`sessions.create/destroy`（<https://github.com/FlareSolverr/FlareSolverr/blob/master/README.md>）。
2. 官方 README 明确资源特征：每次请求会启动浏览器，内存占用较高（同上 `How it works` 段落）。
3. 官方 README 明确 captcha 现状："At this time none of the captcha solvers work"（同上 `Captcha Solvers` 段落）。
4. 版本与维护信号：仓库显示仍有近期版本发布与 issue 活动（<https://github.com/FlareSolverr/FlareSolverr>）。

### 3.2 undetected-chromedriver

定位：Selenium 生态下的 ChromeDriver 补丁库，目标是减少自动化特征暴露。

关键证据：

1. 官方 README 声明其为 Selenium ChromeDriver patch，并提供 `uc.Chrome()` 用法（<https://github.com/ultrafunkamsterdam/undetected-chromedriver/blob/master/README.md>）。
2. 官方 README 明确限制：不隐藏 IP，数据中心环境可能无法通过（同上 `What this is not` 段落）。
3. 项目维护压力信号：大量开放 issues、维护者对 issue tracker 限流声明（仓库主页与 README）
   - <https://github.com/ultrafunkamsterdam/undetected-chromedriver>
   - <https://github.com/ultrafunkamsterdam/undetected-chromedriver/blob/master/README.md>

## 4. 评估维度

1. 架构契合度（是否符合 `browser -> stealth/captcha -> auth` 边界）
2. 改造成本（代码改动范围、接口影响、回归风险）
3. 运维复杂度（新增服务、依赖、资源占用、本地部署成本）
4. 稳定性与维护性（上游维护活跃度、版本兼容风险）
5. 合规与安全风险（使用边界、潜在法律/条款风险）

## 5. 方案对比矩阵（工程决策）

| 维度 | FlareSolverr | undetected-chromedriver | 备注 |
|---|---|---|---|
| 架构契合度 | 中（可做外部 fallback） | 低（与 Playwright 主栈不兼容） | 依据 `BrowserManager` 现状与抽象边界 |
| 落地复杂度 | 中（新增外部服务 + 适配器） | 高（若替换引擎需大改） | `packages/browser/src/browser/core.py` |
| 运维成本 | 中高（新增容器与健康检查） | 中（库级依赖） | FlareSolverr 需要独立运行时 |
| 维护风险 | 中（外部服务变化） | 中高（维护活跃度与兼容性不确定） | 以 GitHub 活跃度与 issue 密度为信号 |
| 稳定性预期 | 站点相关、波动较大 | 站点相关、波动较大 | 均不能承诺通用稳定绕过 |
| 与现有 Playwright 兼容性 | 中（通过 cookie/session 引导） | 低（并非 Playwright 原生路径） | Oracle 建议避免直接引擎替换 |
| 综合建议优先级 | P1（实验性白名单试点） | P2（仅保留复评，不入主路径） | 主路径仍是 Playwright 增强 |

## 6. KaiTian 接入评估（待填充）

### 6.1 最小接入点

推荐最小改造路径（遵循现有边界）：

1. 在 `packages/captcha/src/captcha/` 新增 FlareSolverr 求解器实现（例如 `flare_solver.py`），作为 `CaptchaSolver` 的一个实现。
2. 在 `auth` 站点认证器构造参数中允许注入该 solver（当前 `znzmo` 已支持注入式求解器模式）。
3. 保持 `BrowserManager` 不做引擎替换，仅复用现有 challenge 检测与编排链路。

不建议直接改动区域（高风险）：

1. 不建议直接把 `BrowserManager` 从 Playwright 替换为 Selenium/undetected-chromedriver。
2. 不建议让 `auth` 直接耦合挑战求解细节（会破坏模块边界）。

### 6.2 潜在阻塞点

1. 引擎替换成本：Playwright 与 undetected-chromedriver 的 API 和对象模型差异显著，直接替换会影响 context/page/cookie/storage 等核心路径。
2. 注入能力差异：现有 stealth 注入与 challenge 脚本依赖 Playwright context 机制，迁移后需要重做适配层。
3. 观测与回归成本：现有日志、错误映射、测试路径与 Playwright 强耦合，替换引擎将引入大面积回归。
4. 外部求解器接口稳定性：FlareSolverr 若接入 captcha 层，需要确认 API 版本、输入输出格式、超时与错误语义。

## 7. 风险与缓解策略

1. 技术风险：上游版本变化导致绕过能力不稳定。
2. 运维风险：新增组件或运行方式增加部署复杂度。
3. 合规风险：目标站点条款与法律边界风险。

关键风险与缓解：

### 7.1 抽象边界错位风险

风险：把 FlareSolverr 误当成纯 captcha 求解器，会把 challenge/cookie/session 逻辑耦合进 `auth`。

缓解：

1. 定义为“challenge/session bootstrap”能力，不改变 `auth` 契约。
2. 保持 `browser` 编排与 `captcha` 求解分层，`auth` 只消费结果。

### 7.2 主路径收益被高估风险

风险：不同站点与防护版本差异大，单点样本成功不代表可长期稳定。

缓解：

1. 仅白名单站点试点，不做全局默认启用。
2. 以指标门槛决策：成功率、人工介入率、超时率、平均耗时。

### 7.3 运维面扩张风险

风险：FlareSolverr 增加独立服务、资源占用与排障链路。

缓解：

1. 通过 feature flag 默认关闭。
2. 失败自动回退到现有 Playwright 路径。
3. 增加健康检查和超时熔断。

## 8. 结论与建议

### 8.1 结论

1. **主路径**：继续强化现有 `Playwright + stealth + captcha`，这是当前架构约束下成本最低且一致性最好的路径。
2. **FlareSolverr**：可作为实验性 fallback（challenge/session 引导），仅白名单试点，不作为默认依赖。
3. **undetected-chromedriver**：现阶段不作为主路径，不在 `BrowserManager` 层做引擎切换。

### 8.2 Go/No-Go 决策门槛

#### FlareSolverr Go 条件

1. 不修改 `auth` 公共契约。
2. 不在 `BrowserManager` 增加站点特化分支。
3. 白名单试点中，成功率有明确提升，且人工介入率可控。
4. 失败可自动回退，不增加常态人工运维负担。

#### FlareSolverr No-Go 条件

1. 必须侵入 `auth` 才能接入。
2. 成功率提升不稳定或收益不足以覆盖运维成本。
3. 回退路径不可靠。

#### undetected-chromedriver 复评触发条件

1. Playwright 主路径在关键站点长期低于可接受成功率。
2. 经过多轮增强仍无明显改善。
3. 证明“换引擎收益 > 改造与维护成本”。

### 8.3 必须声明的边界

1. 本文结论是“当前阶段工程决策”，不承诺对所有 Cloudflare/Turnstile 场景长期有效。
2. FlareSolverr 是可关闭实验路径，不是核心运行前提。
3. 本评估只覆盖技术与运维可行性，不构成法律或条款合规背书。

## 9. 分阶段落地计划（待填充）

### Phase A

目标：完成最小 PoC，验证“captcha 层接入外部求解器”的可行性。

1. 在 `captcha` 层新增外部求解器适配实现（接口与 `CaptchaSolver` 协议对齐）。
2. 在一个站点认证器中通过注入方式启用该求解器（不改 browser 核心 API）。
3. 定义最小验收标准：
   - 可以正确调用外部服务；
   - 失败时可降级到人工介入；
   - 不破坏现有登录链路。

### Phase B

目标：小范围灰度与观测，确认稳定性收益。

1. 建立对比指标：挑战触发率、登录成功率、平均登录耗时。
2. 灰度范围：仅单站点、单账号组、可回滚开关控制。
3. 回滚机制：
   - 配置开关关闭外部求解器；
   - 回落到现有 `stealth + manual` 路径。

### Phase C

目标：根据灰度结果决定是否长期维护。

1. 若收益显著且维护成本可控，进入长期维护并补齐测试基线。
2. 若收益不稳定或成本过高，保留为可选实验路径，不进入默认主路径。

## 10. 参考资料

### 10.1 FlareSolverr

1. 仓库主页：<https://github.com/FlareSolverr/FlareSolverr>
2. 官方 README（工作原理、API、环境变量、Captcha 声明）：
   <https://github.com/FlareSolverr/FlareSolverr/blob/master/README.md>
3. 发行版本页：<https://github.com/FlareSolverr/FlareSolverr/releases>
4. 相关 issue（示例）：
   - <https://github.com/FlareSolverr/FlareSolverr/issues/1694>
   - <https://github.com/FlareSolverr/FlareSolverr/issues/1678>
   - <https://github.com/FlareSolverr/FlareSolverr/issues/1699>
5. 与 Playwright 讨论（示例）：
   - <https://github.com/FlareSolverr/FlareSolverr/discussions/856>

### 10.2 undetected-chromedriver

1. 仓库主页：<https://github.com/ultrafunkamsterdam/undetected-chromedriver>
2. 官方 README（定位、限制、维护者声明）：
   <https://github.com/ultrafunkamsterdam/undetected-chromedriver/blob/master/README.md>
3. 关键 issue（兼容性/稳定性信号示例）：
   - <https://github.com/ultrafunkamsterdam/undetected-chromedriver/issues/2286>
   - <https://github.com/ultrafunkamsterdam/undetected-chromedriver/issues/2288>
   - <https://github.com/ultrafunkamsterdam/undetected-chromedriver/issues/2295>
   - <https://github.com/ultrafunkamsterdam/undetected-chromedriver/issues/2287>

### 10.3 KaiTian 内部实现与约束

1. 架构约束：`docs/architecture/anti-detection-design.md`
2. Browser 核心：`packages/browser/src/browser/core.py`
3. Challenge 检测：`packages/browser/src/browser/challenges.py`
4. Stealth 核心：`packages/stealth/src/stealth/core.py`
5. Captcha 抽象：`packages/captcha/src/captcha/core.py`
6. 站点认证器示例：`packages/auth/src/auth/sites/znzmo/authenticator.py`
