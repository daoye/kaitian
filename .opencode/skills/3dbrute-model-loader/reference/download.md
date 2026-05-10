# 下载详细指南

## 模型文件下载

### 下载按钮关键属性

```html
<button type="button" class="download-button-free"
  data-file-urls="https://ap-south-1.linodeobjects.com/.../FILENAME.{rar|zip|7z}"
  data-nonce="d8c4450e20"
  data-order-id="661275">
  Download
</button>
```

| 属性 | 说明 | 获取方式 |
|------|------|----------|
| `data-file-urls` | 压缩包下载直链 | `.download-button-free[data-file-urls]` |
| `data-nonce` | 下载认证令牌 | `.download-button-free[data-nonce]` |
| `data-order-id` | 模型唯一 ID | `.download-button-free[data-order-id]` |

### 验证按钮存在

```
browserOS_evaluate_script({
  page: 详情页标签页ID,
  expression: `document.querySelector('.download-button-free')?.outerHTML || 'NOT_FOUND'`
})
```

预期输出应包含 `download-button-free`、`data-file-urls`、`data-nonce` 等属性。

### 点击下载

```
browserOS_click({ page: 详情页标签页ID, element: DOWNLOAD按钮ID })
```

**正确流程（三步）：**

```powershell
$downloadDir = "D:\downloads"

# 1. 点击前：记录已有文件列表
$before = Get-ChildItem $downloadDir | ForEach-Object { $_.Name }

# 2. 点击浏览器下载按钮（不要用 Invoke-WebRequest 或 curl 直连 CDN，会返回 403）
```

```
browserOS_click({ page: 详情页标签页ID, element: DOWNLOAD按钮的 snapshot ID })
```

```powershell
# 3. 轮询等待新文件（模型文件较大，下载需要时间）
$maxRetries = 30
$retryDelay = 3  # 秒
for ($i = 0; $i -lt $maxRetries; $i++) {
    Start-Sleep -Seconds $retryDelay
    $after = Get-ChildItem $downloadDir
    $newFile = $after | Where-Object { $_.Name -notin $before } | Sort-Object LastWriteTime -Descending | Select-Object -First 1
    if ($newFile) {
        Write-Output "新下载文件: $($newFile.Name) 大小: $($newFile.Length) bytes"
        break
    }
    Write-Output "等待下载... ($($i + 1)/$maxRetries)"
}
if (-not $newFile) {
    Write-Output "等待超时，可能未登录或下载被拦截"
}
```

**注意**：
- 下载直链 `data-file-urls` 受 CDN 保护，**不要用 `Invoke-WebRequest`、`curl`、`wget` 等 HTTP 工具下载**，一定会返回 403
- 必须通过浏览器点击按钮下载，文件会保存到浏览器设置的下载目录
- 下载的文件名由浏览器决定，**不要假定扩展名是 `.rar`**，可能是 `.zip` 或 `.7z`
- 如果点击后无文件出现，检查登录状态（`document.body.classList.contains('logged-in')`）

---

## 预览图下载

### 步骤1：获取原始大图 URL

详情页轮播中的主图被包裹在 `<a>` 标签中，父级 `<a>` 的 href 即原始大图 URL：

```
browserOS_evaluate_script({
  page: 详情页标签页ID,
  expression: `
    var images = [];
    document.querySelectorAll('img').forEach(function(img) {
      if (img.alt.includes('Image') && !img.alt.includes('Thumbnail')) {
        var parentA = img.closest('a');
        if (parentA && parentA.href) {
          images.push({
            thumb: img.src,
            original: parentA.href,
            alt: img.alt
          });
        }
      }
    });
    return JSON.stringify(images);
  `
})
```

**输出示例（Aura pouf）：**
```json
[
  {
    "thumb": "https://cdn.3dbrute.com/3d-images-resize/2026/03/446617802e72925f04-height-800.webp",
    "original": "https://cdn.3dbrute.com/3d-images-resize/2026/03/446617802e72925f04-height-1200.webp",
    "alt": "Aura pouf Image 1"
  }
]
```

### 步骤2：浏览器 fetch blob 下载

每张图片在独立的隐藏标签页中下载：

1. 调用 `browserOS_new_hidden_page({ url: 原始大图URL })` 打开隐藏标签页，记下返回的标签页 ID
2. 调用 `browserOS_evaluate_script` 在该标签页中下载：

   ```
   browserOS_evaluate_script({
     page: 隐藏标签页ID,
     expression: `
       (async function() {
         var resp = await fetch(window.location.href);
         var blob = await resp.blob();
         var url = URL.createObjectURL(blob);
         var a = document.createElement('a');
         a.href = url;
         a.download = 'preview_01.webp';
         document.body.appendChild(a);
         a.click();
         document.body.removeChild(a);
         URL.revokeObjectURL(url);
         return 'Downloaded, size: ' + blob.size;
       })();
     `
   })
   ```

3. 立即调用 `browserOS_close_page({ page: 隐藏标签页ID })` 关闭（避免内存泄漏）

### 关键点

- 主图 `alt` 包含 `"Image"`，缩略图 `alt` 包含 `"Thumbnail"`
- 使用 `img.closest('a')` 而非 `parentElement` 更稳健
- **不要硬编码尺寸参数**（如 `-height-1200`），直接从父级 `<a>` 获取
- 必须用浏览器 `fetch` 获取 blob，直接设置 `a.href = imageUrl` 会跨域失败
- **每下载完一张立即关闭隐藏标签页**

---

## 图片格式转换

预览图下载时可能是 webp 等格式，需统一转换为 png 或 jpg（保留透明通道的用 png，其余用 jpg）。

```bash
uv run kaitian crawl postprocess data/models/3dbrute.com/{name} --skip-extract
```

---

## 解压资源包

### 解压

```bash
uv run kaitian crawl postprocess data/models/3dbrute.com/{name}
```

或单独解压：

```bash
uv run kaitian crawl postprocess data/models/3dbrute.com/{name} --skip-convert
```
