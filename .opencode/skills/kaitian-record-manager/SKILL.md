---
name: kaitian-record-manager
description: 使用 kaitian record CLI 管理多站点下载进度，避免重复下载并支持中断恢复。当需要记录已处理的 URL、查询历史下载、或从中断处继续采集时使用。
---

# Kaitian Record Manager

管理多站点下载进度的 CLI 工具操作规范。所有记录以站点为维度组织，支持任意来源网站。

> **执行方式**：`kaitian` 命令需通过 `uv run` 在项目根目录执行，以下所有命令均以 `uv run kaitian` 开头。

## Core Pattern: 先查后做

每次处理 URL 前先查重，避免重复劳动：

```bash
# 1. 查 → 已处理则跳过
uv run kaitian record check <site> <url>

# 2. 未处理则开始下载，完成后记录
uv run kaitian record set <site> <url> --step meta_extracted --name "..."
```

## Quick Reference

| 操作 | 命令 |
|------|------|
| 记录进度 | `uv run kaitian record set <site> <url> [--step] [--name]` |
| 查重 | `uv run kaitian record check <site> <url>` |
| 站点统计 | `uv run kaitian record status <site>` |
| 列表 | `uv run kaitian record list <site> [--status]` |
| 标记完成 | `uv run kaitian record done <site> <url>` |
| 删除记录 | `uv run kaitian record remove <site> <url>` |

## Agent 使用规范

### 1. 开始下载前 — 查重

```bash
uv run kaitian record check 3dbrute.com https://3dbrute.com/aura-pouf/
```

输出三种可能：
- **已完成** → 跳过此 URL
- **进行中，步骤: xxx** → 从中断处继续
- **未找到记录** → 开始新下载

### 2. 每完成一步 — 记录进度

```bash
uv run kaitian record set 3dbrute.com https://3dbrute.com/aura-pouf/ --step meta_extracted --name "Aura pouf"
```

### 3. 全部完成后 — 标记完成

```bash
uv run kaitian record done 3dbrute.com https://3dbrute.com/aura-pouf/
```

### 4. 查看站点整体进度

```bash
uv run kaitian record status 3dbrute.com
# 总计: 12  已完成: 8  进行中: 2  失败: 0  待处理: 2
```

### 5. 中断后恢复

```bash
# 列出进行中的任务
uv run kaitian record list 3dbrute.com --status running
```

## Steps（CLI 内建强类型）

`--step` 由 CLI 内置校验，传入非法值会报错。可选值：

| 步骤 | 含义 |
|------|------|
| `pending` | 待处理 |
| `fetching` | 正在获取页面信息 |
| `meta_extracted` | 元数据已提取 |
| `file_downloaded` | 主文件已下载 |
| `previews_downloaded` | 预览图已下载 |
| `processing` | 正在处理（解压/转换等） |
| `completed` | 完成（由 `done` 命令自动设置） |
| `failed` | 失败（由 `fail` 命令自动设置） |

非法步骤会收到：`无效步骤 'xxx'，有效值: pending, fetching, meta_extracted, ...`

## Common Mistakes

| 错误 | 后果 | 正确做法 |
|------|------|----------|
| 不查重直接下载 | 重复劳动 | 每次 `check` 后再开始 |
| 不记录进度 | 中断后无法恢复 | 每完成一步 `set` |
| 遗漏 `--name` | 列表中看不出内容 | 设置便于识别的名称 |
| step 命名不统一 | 难以判断进度 | 使用上述约定步骤名 |
