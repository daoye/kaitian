# FAQ 和故障排除

## 常见问题

### Q: 页面加载很慢？
A: **正常现象**，3dbrute.com 服务器在国外。每次导航后等待 3-5 秒再操作。

### Q: 直接访问图片 URL 返回 403？
A: 必须通过浏览器 fetch 获取 blob 后触发下载，不能直接用 Python requests。

### Q: `.format-cell`、`.polygons-cell` 等选择器找不到元素？
A: **这些 CSS 类名不存在于实际页面中**。模型数据在 `<table id="3dbrutecode01">` 中，通过遍历表格行 `<tr><td>Label:</td><td>Value</td></tr>` 提取，或直接从 `<meta name="description">` 解析。

### Q: 如何准确判断登录状态？
A: **不要看页脚的 Login/Register 链接**（始终存在）。改为执行：
```
browserOS_evaluate_script({
  page: 当前页ID,
  expression: `document.body.classList.contains('logged-in')`
})
```
返回 `true` 即已登录。WordPress 会在登录后给 `<body>` 添加 `logged-in` class。

### Q: 详情页长时间空白/加载中？
A: 3dbrute 使用 AJAX 加载详情页内容（`ajax-load-post` 类）。点击模型卡片后等待 3-5 秒，使用 `take_snapshot` 确认页面已有内容再操作。

### Q: LD+JSON 数据比 meta description 缺少某些字段？
A: LD+JSON 主要用于 SEO，可能不包含技术参数。建议优先使用 `<meta name="description">` 提取完整参数。

### Q: 如何获取原始尺寸预览图？
A: **通过父级 `<a>` 标签的 href 属性获取**，不要硬编码尺寸参数。主图的父级 `<a>` 直接指向原始大图。

### Q: 预览图下载失败？
A: 确保在隐藏标签页中使用 `fetch` + `blob` + `createElement('a')` 方式下载。

### Q: 下载按钮 DOM 中存在但 click 没反应？
A: 确认已登录。3dbrute 对未登录用户点击 DOWNLOAD 会弹出登录弹窗，不会触发下载。检查导航栏是否有 "Login" 链接来判断登录状态。

### Q: 模型列表页卡片的格式如何获取？
A: 模型名称在 `<h2 class="thumbnail-title">`，格式列表在 `<div class="formats">`（如 `max, obj`），价格类型在 `<div class="type">`（`Free` / `Pro`），浏览量在 `<div class="an-display-view">`。

### Q: 浏览器内存占用过高？
A: **及时关闭隐藏标签页**。每下载完一张图片就关闭对应的隐藏标签页。

### Q: 压缩包解压后目录层级不对？
A: RAR 文件内部可能包含子目录（如 `Aura pouf/`），这是正常的。解压脚本会自动保留原有结构。

### Q: schema 字段直接硬编码模型名？
A: schema 结构固定，但每个字段的值必须从页面动态提取。参考 `extraction.md` 中每种数据来源对应的提取方法。

---

## 常见错误速查

| 错误 | 后果 | 正确做法 |
|------|------|----------|
| 使用 `.format-cell` 等不存在的 CSS 类 | 返回 null，数据缺失 | 用 `meta[name="description"]` 或遍历表格行 |
| 用 Invoke-WebRequest/curl 下载 CDN 直链 | 403 AccessDenied | 必须通过浏览器点击按钮下载 |
| 用 Python requests 直接下载 | 403 Forbidden | 使用浏览器 fetch blob |
| 硬编码图片尺寸参数 | 获取错误尺寸 | 通过父级 `<a>` 标签获取原始 URL |
| 用页脚 Login/Register 链接判断登录态 | 始终存在，误判为未登录 | 用 `document.body.classList.contains('logged-in')` |
| 不关闭隐藏标签页 | 内存泄漏 | 下载完成后立即 `close_page` |
| 页面未加载就操作 | 元素找不到 | 等待 3-5 秒或使用快照确认 |
| 直接访问图片 URL | 跨域失败 | 在隐藏标签页内 fetch 后触发下载 |
| schema 字段硬编码 | 模型不匹配时出错 | 每种数据从指定来源动态提取 |

---


