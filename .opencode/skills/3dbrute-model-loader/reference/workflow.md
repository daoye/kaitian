# 工作流程详解

## 一、网站访问与登录

### 1.1 打开/复用网站

先检查是否已有 3dbrute 标签页，避免重复创建：

1. 调用 `browserOS_list_pages()` 查看所有已打开的标签页
2. 若结果中存在 `3dbrute.com` 的页面 → 记下其 `id`，调用 `browserOS_navigate_page({ page: 该ID, url: "https://3dbrute.com/?type=free" })` 复用
3. 若不存在 → 调用 `browserOS_new_page({ url: "https://3dbrute.com/" })` 新建

**注意**：网站加载较慢，打开后等待 3-5 秒再操作。使用 `take_snapshot` 或 `take_enhanced_snapshot` 确认页面已加载。

### 1.2 登录验证

- 3dbrute 支持邮箱密码或 Google 登录
- **登录状态检测**：页脚始终有 Login/Register 链接，**不可作为判断依据**。使用以下可靠方法：

  ```
  browserOS_evaluate_script({
    page: 当前页ID,
    expression: `document.body.classList.contains('logged-in')`
  })
  ```

  - 返回 `true` → 已登录
  - 返回 `false` → 未登录（需用户手动登录）
- 未登录时点击 DOWNLOAD 会弹出登录对话框
- **用户必须手动在浏览器中完成登录**（BrowserOS 无法自动填验证码）

---

## 二、浏览与筛选模型

### 2.1 筛选免费模型

```
browserOS_navigate_page({ page: 已有标签页ID, url: "https://3dbrute.com/?type=free" })
```

**注意**：导航后等待页面加载完成（3-5秒），模型通过 AJAX 异步加载。

### 2.2 筛选条件

| 条件 | 可选值 | 页面操作 |
|------|--------|---------|
| 价格 | Free / Pro | 左侧筛选面板 checkbox 或 `?type=free` URL |
| 分类 | Furniture, Decoration, Plants, Lighting... | 左侧面板 clickable |
| 格式 | 3ds, Blender, DWG, FBX, 3ds Max, OBJ, SKP, Cinema 4D... | 左侧面板 clickable |
| 渲染器 | Corona, V-Ray, Standard | 左侧面板 checkbox |
| 风格 | Modern, Classic, Other | 左侧面板 checkbox |
| 附加 | PBR, Unwrapped UVs, Animated, Low Poly... | 展开 More 后 checkbox |
| 多边形 | Up to 5K, 5-10K, 10-50K... | 展开 More 后 checkbox |

**注意**：部分选项在 "More" 折叠面板中，需要先点击展开。

### 2.3 页面结构

模型列表位于 `div.thumbnail-grid` 中，每张卡片结构：

```html
<div class="thumbnail-item-wrapper" data-post-id="661275">
  <a href="/aura-pouf/" class="ajax-load-post custom-link-class">
    <img src="...width-508.webp" alt="Aura pouf">
  </a>
  <div class="thumbnail-content">
    <h2 class="thumbnail-title">Aura pouf</h2>
    <div class="thumbnail-meta">
      <div class="formats">max, obj</div>
      <div class="type">Free</div>
      <div class="an-display-view">549</div>
      <div class="product-price">0 $</div>
    </div>
  </div>
</div>
```

- 每张卡片包含 `data-post-id`（模型唯一 ID，可用于后续 API 调用）
- 卡片标题 `<h2 class="thumbnail-title">` 显示模型名称
- 分页链接：`?paged=2`, `?paged=3`... 或底部的数字链接
- 每页约 24 个模型

---

## 三、目录结构详解

### 3.1 标准目录组织

```
data/models/3dbrute.com/{model_name}/
├── meta.json               # 模型元数据（Meta Schema）
├── previews/               # 预览图片（仅保留 png/jpg）
├── originals/              # 从浏览器下载的原始压缩包
│   └── {product_id}.{rar|zip|7z}
└── extracted/              # 解压后的模型文件
    └── {model_folder}/     # 每个原始文件对应一个子目录
```

**注意**：
- 原始压缩包格式不固定，可能是 `.rar`、`.zip` 或 `.7z`
- 每个原始文件解压后各自对应 `extracted/` 下的一个独立子目录，不会混在一起
- 解压后的内部文件结构由原始压缩包决定，不固定

### 3.2 创建目录并移动文件

```powershell
$base = "data\models\3dbrute.com\{model_name}"
New-Item -ItemType Directory -Path "$base\previews" -Force
New-Item -ItemType Directory -Path "$base\originals" -Force

Move-Item -Path "D:\downloads\{model_name}_*.webp" -Destination "$base\previews\"

$archive = Get-ChildItem -Path "D:\downloads" -Filter "*$product_id*" | Select-Object -First 1
if ($archive) { Copy-Item -Path $archive.FullName -Destination "$base\originals\" }
```

---

## 三、文本文件审查

解压后，`extracted/` 中可能包含 `index.txt`、`README.txt` 等文本文件，通常包含：

1. **模型使用说明**（保留）— 格式、渲染器、安装方法、材质说明等
2. **版权/法律信息**（删除）— Copyright、All Rights Reserved、License、Disclaimer 等
3. **下载站推广**（删除）— "Download more models at..."、水印网址等

审查方式：依次 `read` 每个 `.txt` 文件，人工判断并 `edit` 删除无关内容。只保留对使用模型有直接帮助的信息。

---

## 四、完整工作流

对于列表中的每个模型，先查重再处理，已完成的直接跳过。

### 外层循环：遍历模型列表

```
对列表页中的每个模型卡片：
  1. [自动] 获取卡片中的模型 URL（卡片链接的 href）
  2. [自动] 查重：uv run kaitian record check 3dbrute.com <模型URL>
      → "已完成" → 跳过，处理下一个
      → "进行中，步骤: xxx" → 从对应步骤继续
      → "未找到" → 执行下方下载流程
```

### 内层流程：单个模型下载

```
 1. [手动] 用户登录 3dbrute.com（如未登录）
 2. [自动] 查找已有 3dbrute 标签页，有则复用 / 无则新建
 3. [自动] 点击模型卡片链接，进入详情页（等待 AJAX 加载）
      → uv run kaitian record set 3dbrute.com <URL> --step fetching --name "<名>"
 4. [自动] 提取数据（参考 extraction.md）：
      a. <meta name="description"> 解析模型参数
      b. table#3dbrutecode01 遍历表格行（备选）
      c. LD+JSON 提取作者/标签/分类
      d. .download-button-free 获取下载凭证
      e. img[alt*="Image"] 父级 <a> 获取预览图 URL
      → uv run kaitian record set 3dbrute.com <URL> --step meta_extracted
 5. [自动] 构造 Meta Schema 对象（参考 SKILL.md 的 schema 结构）
 6. [自动] 点击 DOWNLOAD 下载压缩包
      → uv run kaitian record set 3dbrute.com <URL> --step file_downloaded
 7. [自动] 为每张原始大图打开隐藏标签页，fetch blob 下载预览图
 8. [自动] 下载完成后立即关闭隐藏标签页
      → uv run kaitian record set 3dbrute.com <URL> --step previews_downloaded
 9. [自动] 创建目录 data/models/3dbrute.com/{name}/
10. [自动] 保存 meta.json 到模型目录（通过 console.log 输出后写文件）
 11. [自动] 移动压缩包到 originals/，预览图到 previews/
 12. [自动] 后处理（更新路径 + 解压 + 转格式）：
      → uv run kaitian crawl postprocess data/models/3dbrute.com/{name}
14. [手动] 审查 extracted/ 中的文本文件，删除版权/法律/推广等无关信息，仅保留模型使用说明
15. [自动] 关闭所有相关标签页，释放内存
      → uv run kaitian record done 3dbrute.com <URL>
```
