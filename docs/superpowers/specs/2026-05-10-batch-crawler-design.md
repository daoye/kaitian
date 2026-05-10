# 批量爬虫设计

## 目标

一条命令即可启动自动持续下载：登录和 nonce ready 后，爬虫自动遍历免费模型列表，下载、后处理，记录成功/失败，支持中断恢复和限流。

## 架构

```
CLI: kaitian crawl batch
  → CrawlOrchestrator
    → ListingFetcher (HTTP AJAX → 模型 URL 列表)
    → ModelProcessor (对每个 URL 执行 crawl model)
    → Recorder (kaitian record)
    → RateLimiter (配置化间隔)
```

## ListingFetcher

通过 `apply_custom_filters` AJAX 端点获取免费模型列表。

**请求：**
```
POST https://3dbrute.com/wp-admin/admin-ajax.php
Referer: https://3dbrute.com/?type=free
X-Requested-With: XMLHttpRequest

action=apply_custom_filters
&paged=N
&types[]=free
&apply_custom_filters_nonce=<从首页提取>
```

**响应：** `{"success":true,"data":{"posts":"<HTML>"}}`

HTML 中包含 `.thumbnail-item-wrapper` 卡片，每页 63 个，共 ~73 页。

**排序：** 支持 `sort-by=newest`（默认）和 `sort-by=oldest`。

**流程：**
1. `GET /?type=free` → 提取 `apply_custom_filters_nonce`
2. `POST paged=N, sort-by=newest` → 解析 63 个 URL
3. 逐个处理完成后翻页
4. nonce 在单次会话中不变，无需更新

## ModelProcessor

对每个模型 URL：

```
1. kaitian record check → 已完成/进行中则跳过
2. crawl detail → 提取 meta
3. 下载预览图（HTTP）
4. 下载主文件（需 nonce → presigned URL）
5. postprocess（更新路径 + 解压 + 转格式）
6. kaitian record set completed
```

失败时记录为 failed，不阻塞后续。

## 执行模式

### Batch 模式
```bash
kaitian crawl batch --limit 20
```
处理 20 个模型后退出。适合配合定时任务或手动触发。

### Daemon 模式
```bash
kaitian crawl batch --daemon
```

**首次运行**：遍历所有页（1→73），全部下载。

**后续增量检查**：不再遍历全部页面。
1. 只请求第 1 页（`sort-by=newest`）
2. 检查最新模型（第1个卡片）是否已在 `kaitian record` 中
3. 已存在 → 无新数据 → 等待 `restart_delay_hours` 后重新检查
4. 不存在 → 从第 1 页开始下载新模型，直到遇到已下载的模型后停止
5. 回到步骤 1

### 中断恢复
天然支持。每个模型处理前 `kaitian record check` 跳过已完成的。中断后重新运行即可从断点继续。

## 限流

| 操作 | 间隔 | 配置项 |
|------|------|--------|
| 列表页请求 | 3s | `request_delay_seconds` |
| 模型下载 | 3s | `request_delay_seconds` |
| 网络错误重试 | 3 次 | `retry_count` |
| Daemon 重启等待 | 24h | `restart_delay_hours` |

## 配置

```toml
[tool.kaitian.crawl]
restart_delay_hours = 24
request_delay_seconds = 3
retry_count = 3
```

环境变量：`KAITIAN_CRAWL__RESTART_DELAY_HOURS=48`

## 错误处理

| 场景 | 处理 |
|------|------|
| 列表页 AJAX 失败 | 重试 3 次，间隔 10s |
| 模型下载失败 | `record set failed` → 继续下一个 |
| nonce 过期 | 重新 GET 首页提取（实测单次会话内不变） |
| Ctrl+C | 退出，下次自动从断点继续 |

## CLI

```bash
kaitian crawl batch --limit 20          # 批处理 20 个
kaitian crawl batch --daemon            # 守护模式
kaitian crawl batch --page 5            # 从第 5 页开始
kaitian crawl batch --daemon --delay 5  # 覆盖请求间隔
```

## 实现计划

1. 实现 `ListingFetcher`：提取 nonce → AJAX 分页 → 返回 URL 列表
2. 实现 `CrawlOrchestrator`：遍历页 → 遍历 URL → 调用 `crawl_model`
3. 实现 `batch` CLI 命令
4. 编写测试
