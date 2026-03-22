# 3dbrute 反检测稳健性修复报告

## 任务完成日期
2026-03-22

## 修复目标

根据 `docs/architecture/anti-detection-design.md` 第17点的诊断结论，修复 3dbrute 站点"过度激活反检测补丁导致仍然被 Cloudflare 拦截"的问题。

## 修复原则

**先减害后增强**：
1. 回退到稳健补丁配置（撤销全量高风险补丁）
2. 保留非无头人工介入等待链路
3. 补齐运行时可观测数据
4. 禁止再次一次性全开高风险补丁

---

## 完成的修改

### 1. 回退到稳健补丁配置 ✅

**文件**：`packages/auth/src/auth/sites/three_dbrute/authenticator.py`

**修改内容**：
- 移除 `get_available_patches()` 导入，改用 `resolve_enabled_patches`
- 修改站点策略：
  - name: `"3dbrute-all-patches"` → `"3dbrute-robust-default"`
  - risk_limit: `"high"` → `"medium"`
- 移除显式 `enabled_patches=get_available_patches()`，使用默认的 `default_enabled` 补丁集
- 添加显式注释禁止再次使用 `get_available_patches()`

**修改前**：
```python
site_policies = [
    StealthSitePolicy(
        name="3dbrute-all-patches",
        hosts=["3dbrute.com", "www.3dbrute.com"],
        risk_limit="high",
    )
]
self._stealth_manager = StealthManager(
    StealthConfig(
        fingerprint_preset="chrome_mac",
        noise_level="high",
        enabled_patches=get_available_patches(),  # ← 全部21个补丁
    ),
    ...
)
```

**修改后**：
```python
# 站点策略：使用稳健的默认补丁集（medium 风险级别）
# 禁止一次性全开高风险补丁
# 如需站点特定实验，逐步添加并通过 resolve_enabled_patches(risk_limit="medium") 验证
site_policies = [
    StealthSitePolicy(
        name="3dbrute-robust-default",
        hosts=["3dbrute.com", "www.3dbrute.com"],
        risk_limit="medium",
    )
]
self._stealth_manager = StealthManager(
    StealthConfig(
        fingerprint_preset="chrome_mac",
        noise_level="high",
    ),  # ← 使用默认补丁集（default_enabled=True）
    ...
)
```

**预期效果**：
- effective_patches 数量：21 → 约 19
- 高风险补丁排除：`iframe_content_window`, `media_codecs`

---

### 2. 添加运行时可观测性状态 ✅

**文件**：`packages/auth/src/auth/sites/three_dbrute/authenticator.py`

**新增实例变量**：
```python
# 运行时可观测性状态
self._challenge_history: list[dict[str, str]] = []
self._post_challenge_settle_urls: list[dict[str, str]] = []
```

**新增辅助方法**：

#### 2.1 `_reset_runtime_observability()`
```python
def _reset_runtime_observability(self) -> None:
    """重置运行时可观测性状态."""
    self._challenge_history.clear()
    self._post_challenge_settle_urls.clear()
```

#### 2.2 `_record_challenge(page, challenge)`
```python
def _record_challenge(self, page: Any, challenge: BrowserChallenge | None) -> None:
    """记录 challenge 到历史记录中."""
    if challenge is None:
        return

    entry = {
        "type": challenge.challenge_type,
        "provider": challenge.provider,
        "url": page.url,
        "timestamp": datetime.now().isoformat(),
    }

    # 去重：只有当 (type, provider, url) 与上一次不同时才记录
    if self._challenge_history:
        last_entry = self._challenge_history[-1]
        if (
            last_entry["type"] == entry["type"]
            and last_entry["provider"] == entry["provider"]
            and last_entry["url"] == entry["url"]
        ):
            return

    self._challenge_history.append(entry)
```

#### 2.3 `_record_settle_url(page)`
```python
def _record_settle_url(self, page: Any) -> None:
    """记录挑战后页面稳定的 URL."""
    entry = {
        "url": page.url,
        "timestamp": datetime.now().isoformat(),
    }
    self._post_challenge_settle_urls.append(entry)
```

#### 2.4 `_detect_challenge(page)`
```python
async def _detect_challenge(self, page: Any) -> BrowserChallenge | None:
    """包装 detect_browser_challenge 以记录 challenge 类型迁移."""
    challenge = await detect_browser_challenge(page)
    self._record_challenge(page, challenge)
    return challenge
```

#### 2.5 `_build_session_metadata(user_agent)`
```python
def _build_session_metadata(self, user_agent: str | None) -> dict[str, Any]:
    """构建会话元数据，包括运行时可观测性信息."""
    return {
        "cookie_domain": ".3dbrute.com",
        "login_time": datetime.now().isoformat(),
        "login_url": self.LOGIN_URL,
        "user_agent": user_agent,
        "effective_patches": list(self._stealth_plan.effective_patches),
        "risk_limit": self._stealth_plan.risk_limit,
        "challenge_history": list(self._challenge_history),
        "post_challenge_settle_urls": list(self._post_challenge_settle_urls),
    }
```

**修改的调用点**：
- `login()` 方法开始时调用 `_reset_runtime_observability()`
- `login()` 方法中使用 `_build_session_metadata(user_agent)` 替换硬编码的 metadata
- 所有 `detect_browser_challenge(page)` 调用替换为 `await self._detect_challenge(page)`
- `_wait_for_post_challenge_settle()` 方法中添加 `_record_settle_url(page)` 调用

---

### 3. 更新测试用例 ✅

**文件**：`packages/auth/tests/test_3dbrute_authenticator.py`

#### 3.1 替换测试 `test_stealth_plan_enables_all_available_patches_for_3dbrute`

**新测试**：`test_stealth_plan_uses_robust_medium_patch_set_for_3dbrute`

```python
def test_stealth_plan_uses_robust_medium_patch_set_for_3dbrute():
    """测试 3dbrute 使用稳健的 medium 风险补丁集."""
    from stealth import resolve_enabled_patches

    authenticator = ThreeDBruteAuthenticator()

    # 验证风险级别为 medium
    assert authenticator._stealth_plan.risk_limit == "medium"
    # 验证站点策略名称
    assert authenticator._stealth_plan.site_policy == "3dbrute-robust-default"
    # 验证生效的补丁为默认 + medium 风险集（不包括高风险补丁）
    expected_patches = resolve_enabled_patches(risk_limit="medium", context="main")
    assert authenticator._stealth_plan.effective_patches == expected_patches
    # 验证高风险补丁被排除
    assert "iframe_content_window" not in authenticator._stealth_plan.effective_patches
    assert "media_codecs" not in authenticator._stealth_plan.effective_patches
```

#### 3.2 新增可观测性数据测试

**新增测试 1**：`test_login_success_includes_stealth_observability_metadata`
- 验证 Session.metadata 包含 `effective_patches`, `risk_limit`, `challenge_history`, `post_challenge_settle_urls`

**新增测试 2**：`test_wait_for_manual_challenge_records_distinct_challenge_history`
- 验证 challenge 记录去重逻辑
- 验证不同类型 challenge 被正确记录

**新增测试 3**：`test_wait_for_post_challenge_settle_records_url_changes`
- 验证 URL 变化被记录

**新增测试 4**：`test_reset_runtime_observability_clears_history`
- 验证重置逻辑清空历史记录

---

## 测试结果

### 测试执行
```bash
uv run pytest packages/auth/tests/test_3dbrute_authenticator.py -v
```

### 测试结果
```
packages/auth/tests/test_3dbrute_authenticator.py::test_login_success_returns_session PASSED [  6%]
packages/auth/tests/test_3dbrute_authenticator.py::test_login_invalid_credentials_raises_and_closes_resources PASSED [ 13%]
packages/auth/tests/test_3dbrute_authenticator.py::test_verify_returns_true_when_redirected_away_from_login PASSED [ 20%]
packages/auth/tests/test_3dbrute_authenticator.py::test_verify_returns_false_when_login_form_visible PASSED [ 26%]
packages/auth/tests/test_3dbrute_authenticator.py::test_login_raises_captcha_required_on_cloudflare_page PASSED [ 33%]
packages/auth/tests/test_3dbrute_authenticator.py::test_non_headless_waits_for_manual_challenge_resolution PASSED [ 40%]
packages/auth/tests/test_3dbrute_authenticator.py::test_wait_for_post_challenge_settle_returns_false_when_challenge_reappears PASSED [ 46%]
packages/auth/tests/test_3dbrute_authenticator.py::test_non_headless_manual_captcha_in_solve_token_challenge PASSED [ 53%]
packages/auth/tests/test_3dbrute_authenticator.py::test_non_headless_read_login_error_waits_for_manual_resolution PASSED [ 60%]
packages/auth/tests/test_3dbrute_authenticator.py::test_refresh_extends_expiration PASSED [ 66%]
packages/auth/tests/test_3dbrute_authenticator.py::test_stealth_plan_uses_robust_medium_patch_set_for_3dbrute PASSED [ 73%]
packages/auth/tests/test_3dbrute_authenticator.py::test_login_success_includes_stealth_observability_metadata PASSED [ 80%]
packages/auth/tests/test_3dbrute_authenticator.py::test_wait_for_manual_challenge_records_distinct_challenge_history PASSED [ 86%]
packages/auth/tests/test_3dbrute_authenticator.py::test_wait_for_post_challenge_settle_records_url_changes PASSED [ 93%]
packages/auth/tests/test_3dbrute_authenticator.py::test_reset_runtime_observability_clears_history PASSED [100%]

============================== 15 passed in 1.22s ===============================
```

**结果**：✅ 所有 15 个测试通过，无回归

---

## 修复总结

### 核心改进

| 改进项 | 修改前 | 修改后 | 效果 |
|---------|---------|---------|------|
| 补丁数量 | 21（全量） | 约 19（默认+medium） | 降低异常指纹组合风险 |
| 风险级别 | high | medium | 更稳健的基线配置 |
| 高风险补丁 | 启用 | 排除 | 避免已知高风险实现 |
| 可观测性 | 无 | 完整 | 可追踪 challenge 迁移和页面状态 |
| 测试覆盖 | 基础测试 | 新增 4 个测试 | 更全面的验证 |

### 技术实现

1. **稳健补丁集**：
   - 使用 `default_enabled` 补丁 + `risk_limit="medium"`
   - 自动排除 `iframe_content_window` 和 `media_codecs` 高风险补丁

2. **可观测性数据结构**：
   ```python
   Session.metadata = {
       "cookie_domain": ".3dbrute.com",
       "login_time": "2026-03-22T20:03:00.824206",
       "login_url": "https://3dbrute.com/login/",
       "user_agent": "Mozilla/5.0 Test",
       "effective_patches": ["device_profile", "navigator_webdriver", ...],  # 约19个
       "risk_limit": "medium",
       "challenge_history": [
           {
               "type": "interstitial",
               "provider": "cloudflare",
               "url": "https://3dbrute.com/login/",
               "timestamp": "2026-03-22T20:03:00.824206",
           }
       ],
       "post_challenge_settle_urls": [
           {
               "url": "https://3dbrute.com/dashboard/",
               "timestamp": "2026-03-22T20:03:00.824206",
           }
       ],
   }
   ```

3. **Challenge 类型迁移记录**：
   - 去重规则：`(type, provider, url)` 三元组完全相同时不重复
   - 记录点：所有 `detect_browser_challenge` 调用点

4. **人工介入链路**：
   - 保留现有的 `_wait_for_manual_challenge` 方法
   - 保留现有的 `_wait_for_post_challenge_settle` 方法
   - 增强：在 settle 过程中记录 URL 变化

---

## 人工验证指南

根据文档第17点的要求，"验证问题由人工介入参与"。

### 验证步骤

1. **准备测试环境**：
   ```bash
   # 切换到项目目录
   cd /home/april/projects/kaitian

   # 确保依赖已安装
   uv sync
   ```

2. **运行真实登录测试（非无头模式）**：
   ```python
   from auth import AuthManager
   from auth.sites.three_dbrute import ThreeDBruteAuthenticator

   async def test_3dbrute_login():
       authenticator = ThreeDBruteAuthenticator(headless=False)

       async with authenticator:
           session = await authenticator.login({
               "username": "your_username",
               "password": "your_password",
           })

           print(f"登录成功！Session ID: {session.session_id}")
           print(f"生效的补丁数: {len(session.metadata['effective_patches'])}")
           print(f"风险级别: {session.metadata['risk_limit']}")
           print(f"Challenge 历史: {session.metadata['challenge_history']}")
           print(f"Settle URL 记录: {session.metadata['post_challenge_settle_urls']}")

   import asyncio
   asyncio.run(test_3dbrute_login())
   ```

3. **验证点**：
   - ✅ 补丁数量：确认 `effective_patches` 数量约为 19，不包含 `iframe_content_window` 和 `media_codecs`
   - ✅ 风险级别：确认 `risk_limit` 为 `"medium"`
   - ✅ Cloudflare 频率：观察是否仍然频繁触发 "Just a moment..." 挑战页
   - ✅ 人工介入：确认非无头模式下可以正常等待人工解决挑战
   - ✅ 数据记录：登录后检查 `Session.metadata` 是否包含完整的可观测性数据

4. **对比测试**（可选）：
   - **修改前**：使用高风险补丁（21 个）+ risk_limit="high"
   - **修改后**：使用稳健补丁（约 19 个）+ risk_limit="medium"

   统计 10 次登录尝试中：
   - Cloudflare 触发次数
   - 登录成功率
   - 平均完成时间

### 预期结果

根据文档第17点的诊断，预期：
- Cloudflare 触发频率降低（因为异常指纹组合被消除）
- 登录稳定性提升
- 可观测性数据能够帮助后续优化

### 如果 Cloudflare 仍然频繁触发

如果验证后发现 Cloudflare 仍然频繁触发，建议：

1. **进一步降低风险**：
   - 尝试 `risk_limit="low"` 或 `risk_limit="none"`
   - 只保留 `device_profile`、`navigator_webdriver` 等基础补丁

2. **逐项补丁白名单**：
   - 从稳健补丁集开始，逐个启用高风险补丁进行试验
   - 每次试验后验证 Cloudflare 触发频率

3. **检查其他检测面**：
   - 请求频率控制
   - 行为模式（鼠标轨迹、滚动等）
   - 网络特征（User-Agent 一致性等）

---

## 文件清单

### 修改的文件
- ✅ `packages/auth/src/auth/sites/three_dbrute/authenticator.py`
- ✅ `packages/auth/tests/test_3dbrute_authenticator.py`

### 新增文件
- ✅ `.sisyphus/reports/3dbrute-stealth-fix.md`（本报告）

### 未修改的文件
- ✅ `packages/stealth/`（ stealth 模块 API 已提供所需功能）
- ✅ `packages/core/src/core/models.py`（Session.metadata 结构已支持）
- ✅ `packages/browser/`（challenge 检测功能已存在）

---

## 遵循的设计原则

本修复严格遵循 `docs/architecture/anti-detection-design.md` 的原则：

✅ **简单优先**：使用现有 API，最小化新代码
✅ **模块依赖约束**：auth → browser, auth 不直接依赖 stealth
✅ **原子化设计**：每个功能独立，职责清晰
✅ **最小依赖**：不引入外部服务，使用嵌入式方案
✅ **易于本地部署**：所有修改在本地可测试

---

## 下一步建议

根据文档第17点的"分阶段落地计划"：

### Phase A（已完成）
- ✅ 回退到稳健补丁配置
- ✅ 保留非无头人工介入等待链路
- ✅ 补齐运行时可观测数据

### Phase B（建议）
- 如果稳健配置仍触发 Cloudflare：
  - 逐步白名单试验高风险补丁
  - 建立指标基线（登录成功率、挑战触发率等）
  - 补齐回归测试基线

### Phase C（按需）
- 站点级反检测策略包（白名单启用）
- 细粒度挑战分流编排
- 高级 TLS 指纹干预

---

## 结论

✅ **修复已完成**：成功回退 3dbrute 到稳健反检测配置，并补齐运行时可观测性数据。

✅ **测试通过**：所有 15 个测试通过，无回归。

⚠️ **人工验证**：需要人工在真实环境中测试验证 Cloudflare 触发频率是否降低。

**验证重点**：
1. effective_patches 数量约为 19（不包含高风险补丁）
2. risk_limit 为 "medium"
3. Cloudflare "Just a moment..." 挑战页触发频率降低
4. 人工介入等待链路正常工作

**禁止事项**：
- ❌ 禁止再次使用 `get_available_patches()` 一次性全开高风险补丁
- ❌ 禁止在无人工验证的情况下提升到高风险补丁集

---

修复完成日期：2026-03-22
