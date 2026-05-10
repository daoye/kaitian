# 数据提取指南

## 一键提取（推荐）

```bash
uv run kaitian crawl detail --source 3dbrute <详情页URL>
```

返回完整 Meta Schema JSON，通过 `--output` 保存到目录。

## 数据来源

| 来源 | 提取的字段 |
|------|-----------|
| `<meta name="description">` | Name, Format, Export, Render, Polys, Verts, Matclasses, Units, Dimension, Manufacturer, Product_url |
| `table#3dbrutecode01` | Version, Formats, Render, Size, Material, Colors, Polygons, Vertices, Dimensions, Opt. Standards, Date, Views, Style |
| LD+JSON | author.name, author.url, datePublished, keywords, articleSection |
| `.download-button-free` | data-file-urls, data-nonce, data-order-id |
| `img[alt*="Image"]` 父级 `<a>.href` | 预览图 URL |

## meta.json 保存

`kaitian crawl detail --output <目录>` 自动保存 meta.json。

## 字段对照

| 字段 | 来源 |
|------|------|
| `name` | `<h1>` / meta `Name:` |
| `slug` | URL 路径最后一段 |
| `product_id` | `[data-order-id]` |
| `license` | 列表页 `.type`（Free/Pro） |
| `author.name` / `author.profile_url` | LD+JSON Person / DOM 回退 |
| `parameters.software_version` | meta `Format:` / 表格 `Version:` |
| `parameters.formats` | `.format-item img[alt]` |
| `parameters.export_formats` | meta `Export:` 逗号分割 |
| `parameters.renderer` | meta `Render:` / 表格 `Render:` |
| `parameters.polygons` / `parameters.vertices` | meta / 表格 |
| `parameters.material_classes` | meta `Matclasses:` |
| `parameters.units` | meta `Units:` |
| `parameters.dimensions` | meta `Dimension:` / 内联 Verts / 表格 |
| `parameters.style` | 表格 `Style:` |
| `parameters.low_poly` | 表格 `Opt. Standards:` |
| `parameters.material` / `parameters.colors` | 表格 |
| `parameters.size` | 表格 `Size:` |
| `files[0].archive.url/nonce` | `.download-button-free` |
| `files[0].archive.path` | 由 `crawl postprocess` 更新 |
| `previews[].url` | 主图父级 `<a>.href` |
| `publication.*` | 表格 / LD+JSON |
| `metadata.*` | meta / 表格 / LD+JSON |
