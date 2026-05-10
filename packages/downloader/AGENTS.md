# 下载器

`packages/downloader/` 只包含通用能力，站点特定逻辑在 `packages/sites/` 中。

### 模块职责
| 模块 | 说明 |
|------|------|
| `client.py` | HTTP 客户端（httpx 封装） |
| `crawler.py` | 按 source 选择解析器 → 爬取 |
| `downloader.py` | 后处理（解压/转格式/更新路径/预览图下载） |
| `orchestrator.py` | 批量爬虫（batch/daemon 模式） |
| `repository.py` | SQLite 下载记录 |
| `parsers/` | 解析器注册表 → 路由到 sites/ |

### 爬虫编排
`crawl_detail(source, url, cookies)` 通过 `parsers.parse(source, html)` 路由到站点解析器。

### 后处理（通用）
- `update_archive_path()` — 修正 archive.path
- `convert_previews()` — webp→png/jpg
- `extract_archive()` — 解压（需 7-Zip）
- `download_preview()` — 下载预览图
