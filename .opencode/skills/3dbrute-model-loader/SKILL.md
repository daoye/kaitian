---
name: 3dbrute-model-loader
description: 从 3dbrute.com 搜索、浏览和下载 3D 模型的 BrowserOS 自动化工作流
---

# 3dbrute Model Loader

从 3dbrute.com 下载 3D 模型的 BrowserOS 自动化工作流。

**核心原则**：浏览器内 fetch blob 下载（CDN 认证要求），耐心等待页面加载，复用已有标签页避免重复开页，及时关闭无用标签页释放内存。使用 `uv run kaitian record` 记录每步进度以支持去重和中断恢复。

**REQUIRED SUB-SKILL:** 使用 `kaitian-record-manager` 管理下载进度。

## When to Use

- 需要从 3dbrute.com 下载免费或付费 3D 模型
- 遇到 CDN 资源 403 Forbidden（必须用浏览器会话下载）
- 页面加载缓慢需要等待策略
- 需要提取模型元数据（格式、多边形数、尺寸、作者等）
- 需要下载原始尺寸预览图
- 需要解压 .rar/.zip/.7z 模型压缩包
- 需要清理模型文件中的版权/推广信息

**不适用场景**：其他 3D 模型网站 / 仅需浏览而不下载

## Quick Reference

| 操作 | 命令 |
|------|------|
| 打开/复用网站 | `list_pages` 检查 → 有则 `navigate_page` / 无则 `new_page` |
| 筛选免费模型 | `navigate_page` → `/?type=free` |
| 进入详情页 | `click` 模型卡片 |
| 登录检测 | `evaluate_script` → `document.body.classList.contains('logged-in')` |

| 数据 | 来源 |
|------|------|
| 完整 meta | `kaitian crawl detail <URL>` 一键提取 |
| 模型参数 | `<meta name="description">` |
| 表格数据（备选） | `table#3dbrutecode01` 遍历行 |
| 作者/标签/分类 | LD+JSON `script.yoast-schema-graph` |
| 下载凭证 | `.download-button-free[data-*]` |
| 预览图 URL | `img[alt*="Image"]` 父级 `<a>.href` |

## Meta Schema

下载完成后将以下结构的 JSON 保存为模型目录下的 `meta.json`。由 `kaitian crawl detail` 一键提取。

```json
{
  "name": "<模型名称>",
  "slug": "<URL slug>",
  "platform": "3dbrute",
  "url": "<详情页 URL>",
  "product_id": "<data-order-id>",
  "license": "<free | pro>",
  "price": "<数字>",

  "author": {
    "name": "<作者名>",
    "profile_url": "<作者主页>",
    "followers": "<粉丝数>"
  },

  "previews": [
    { "url": "<原始大图 URL>", "alt": "<alt 文本>" }
  ],

  "files": [
    {
      "software_version": "<3D软件版本>",
      "formats": ["<源文件格式扩展名>"],
      "export_formats": ["<导出格式>"],
      "renderer": "<渲染器>",
      "polygons": "<面数>",
      "vertices": "<顶点数>",
      "material_classes": ["<材质类型>"],
      "units": "<单位制>",
      "dimensions": { "x": "<长>", "y": "<宽>", "z": "<高>" },
      "style": "<风格>",
      "low_poly": "<boolean>",
      "material": "<材质>",
      "colors": ["<颜色 hex>"],
      "size": "<文件大小含单位>",
      "archive": {
        "url": "<CDN 直链>",
        "nonce": "<认证令牌>",
        "path": "<本地原始文件相对路径>"
      }
    }
  ],

  "publication": {
    "date": "<发布日期>",
    "date_published": "<ISO 格式>",
    "views": "<浏览量>",
    "likes": "<点赞数>",
    "bookmarks": "<收藏数>",
    "category": "<分类>"
  },

  "metadata": {
    "manufacturer": "<制造商>",
    "product_url": "<产品页>",
    "tags": ["<标签>"]
  }
}
```

字段来源对照在 [`reference/extraction.md`](reference/extraction.md) 中。

## Core Pattern: 先查后做 + 记录进度

处理每个 URL 前查重，每完成一步记录：

```bash
# 查重
uv run kaitian record check 3dbrute.com <详情页URL>
# 输出 "已完成" → 跳过
# 输出 "进行中" → 从中断恢复
# 输出 "未找到" → 开始新下载

# 记录进度（每完成一步调用一次）
uv run kaitian record set 3dbrute.com <详情页URL> --step <步骤名> --name "<模型名>"

# 全部完成
uv run kaitian record done 3dbrute.com <详情页URL>
```

步骤对照：`fetching` → `meta_extracted` → `file_downloaded` → `previews_downloaded` → `processing`

## Core Pattern: Tab 复用

每次开页前先 `list_pages` 检查已有标签页，有则复用、无则新建。临时标签页（预览图下载）用完即关。代码见 `reference/workflow.md`。

## References

- [`reference/workflow.md`](reference/workflow.md) — 逐步操作流程
- [`reference/extraction.md`](reference/extraction.md) — 数据提取方法（meta/表格/LD+JSON）
- [`reference/download.md`](reference/download.md) — 文件/图片下载 + 解压 + 格式转换
- `kaitian crawl postprocess` — 后处理（解压/转换/更新路径）
- [`reference/troubleshooting.md`](reference/troubleshooting.md) — FAQ 与常见错误
- **REQUIRED:** [`kaitian-record-manager`](../kaitian-record-manager/SKILL.md) — 下载进度记录与去重
