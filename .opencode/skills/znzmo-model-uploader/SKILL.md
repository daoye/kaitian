---
name: znzmo-model-uploader
description: 将 3D 模型上传到 znzmo.com（知末）的 BrowserOS 自动化工作流
---

# znzmo Model Uploader

将 3D 模型上传到 [znzmo.com](https://znzmo.com/)（知末）的完整工作流。

---

## 一、登录与导航

### 1.1 登录

- 知末支持 **微信扫码** / **QQ** / **手机号** 登录
- **用户必须手动在浏览器中完成登录**
- 登录后导航栏的"登录/注册"按钮会变为用户头像图标

### 1.2 进入上传页面

```javascript
// 步骤1：点击导航栏"上传"按钮，弹出下拉菜单
browserOS_click({ page: N, element: UPLOAD_NAV_BUTTON_ID })

// 步骤2：从下拉菜单中点击"上传"（第一个选项）
// 下拉菜单包含：上传、作品管理、互动管理、任务中心、等级权益、收益中心、创作灵感
browserOS_click({ page: N, element: MENUITEM_UPLOAD_ID })
```

### 1.3 上传页面结构

- **页面 URL**：`https://www.znzmo.com/creatorCenter/upload`
- **左侧菜单**：发布作品、首页、作品管理、互动管理、创作灵感、任务中心、等级权益、收益中心、AI中心、创作者QA
- **顶部 Tab**：上传素材（默认）、发布作品、上传校园素材、发布课程
- **初始弹窗**："盗模模型公示" — 点击"我知道了"关闭

---

## 二、选择品类与原创度

### 2.1 选择品类

| 选项 | 适用场景 | value |
|------|---------|-------|
| 模型 | 3ds Max / Blender / SketchUp 等3D模型 | 30 |
| 高清贴图 | 纹理贴图 | 2 |
| 材质 | 材质球 | 18 |
| PS素材 | Photoshop 素材 | 8 |
| CAD图纸 | CAD 图纸 | 5 |
| 方案文本 | 设计说明文档 | 20 |

```javascript
// 选择"模型"
browserOS_click({ page: N, element: RADIO_MODEL_ID })
```

### 2.2 选择原创度

| 选项 | 说明 |
|------|------|
| 原创模型 | 由上传者独立完成整体设计与构建 |
| 衍生模型 | 基于他人作品修改创作 |
| 共享模型 | 无版权限制、可自由使用（**适合从其他平台搬运的免费模型**） |

```javascript
// 选择"共享模型"
browserOS_click({ page: N, element: RADIO_SHARED_ID })
```

---

## 三、上传文件

### 3.1 上传压缩包

**支持的格式：** `.rar` / `.zip` / `.7z`

**压缩包内需包含：**
- `.max` / `.blend` / `.skp` / `.3dm` / `.rvt` / `.c4d` 等模型文件

**上传方式：**

```javascript
// 方法1：通过 BrowserOS 的 upload_file 工具
// 步骤1：将隐藏的 file input 设为可见
browserOS_evaluate_script({
  page: N,
  expression: `
    var input = document.getElementById('materialType3');
    input.style.display = 'block';
    input.style.position = 'fixed';
    input.style.top = '200px';
    input.style.left = '200px';
    input.style.zIndex = '99999';
    input.style.opacity = '1';
    return 'input visible';
  `
})

// 步骤2：上传文件
browserOS_upload_file({
  page: N,
  element: UPLOAD_FILE_BUTTON_ID,  // 或 upload_dragger 区域
  files: ["D:\\projects\\kaitian\\data\\models\\Aura_pouf\\model\\Aura_pouf.rar"]
})
```

**注意：**
- `materialType3` 是隐藏的 `<input type="file" accept=".rar,.zip,.7z">`
- 上传成功后页面会跳转到详情填写表单

---

## 四、填写基本信息

### 4.1 表单字段

上传文件后，页面展开更多必填字段：

| 字段 | 类型 | 说明 |
|------|------|------|
| **领域** | 下拉框 | 室内 / 建筑 / 景观 / 其他 |
| **类型** | 下拉框 | 依赖"领域"的选择，**需先选领域** |
| **软件版本** | 下拉框 | 3ds Max 2019, Blender 3.0 等 |
| **渲染器** | 下拉框 | Corona, V-Ray, Standard 等 |
| **标签** | 文本输入 | 输入后按回车，最多5个 |
| **分成** | 单选 | 独家（50%）/ 非独家 |

### 4.2 填写示例

```javascript
// 选择"室内"
browserOS_click({ page: N, element: COMBOBOX_LINGYU_ID })
browserOS_click({ page: N, element: OPTION_INDOOR_ID })

// 选择类型（需等待选项加载）
browserOS_click({ page: N, element: COMBOBOX_TYPE_ID })
// 等待选项加载后选择

// 选择软件版本
browserOS_click({ page: N, element: COMBOBOX_VERSION_ID })

// 选择渲染器
browserOS_click({ page: N, element: COMBOBOX_RENDERER_ID })

// 输入标签
browserOS_type({ page: N, element: TAGS_INPUT_ID, text: "pouf" })
// 按回车
browserOS_keypress({ page: N, key: "Enter" })

// 选择"非独家"（共享模型适用）
browserOS_click({ page: N, element: RADIO_NON_EXCLUSIVE_ID })
```

---

## 五、上传封面图

### 5.1 封面图要求

- **必填**
- 推荐尺寸：宽高比 **4:3**
- 格式：JPG / PNG / WebP

### 5.2 上传方式

```javascript
// 点击封面图上传按钮
browserOS_click({ page: N, element: COVER_UPLOAD_BUTTON_ID })

// 通过 upload_file 工具选择图片
browserOS_upload_file({
  page: N,
  element: COVER_FILE_INPUT_ID,
  files: ["D:\\projects\\kaitian\\data\\models\\Aura_pouf\\preview\\Aura_pouf_preview.webp"]
})
```

### 5.3 获取预览图的推荐方式

从原平台获取预览图：
1. 在原模型页面找到预览图 URL
2. 通过 `browserOS_new_hidden_page` 打开图片 URL
3. 使用 JavaScript 触发下载
4. 移动到项目预览目录

---

## 六、提交审核

### 6.1 勾选协议

```javascript
browserOS_click({ page: N, element: AGREEMENT_CHECKBOX_ID })
```

### 6.2 提交

```javascript
browserOS_click({ page: N, element: SUBMIT_BUTTON_ID })
```

### 6.3 提交后状态

- 模型进入审核队列
- 可在"作品管理"页面查看审核状态

---

## 七、常见问题

### Q: "类型"下拉没有选项？
A: "类型"选项依赖于"领域"的选择，**必须先选择"领域"后再点击"类型"**。

### Q: 上传文件失败？
A: 
- 检查文件格式是否为 `.rar` / `.zip` / `.7z`
- 确认文件内包含有效的模型文件（.max/.blend/.skp 等）
- 文件 input 为隐藏元素，需先通过 JavaScript 设为可见再使用 upload_file

### Q: 封面图上传后不显示？
A: 检查图片格式和尺寸，推荐 4:3 宽高比。

### Q: 共享模型选"独家"还是"非独家"？
A: 共享模型（从其他平台搬运的免费模型）应选择 **"非独家"**。

### Q: 软件版本和渲染器如何选择？
A: 从模型元数据中获取：
- 3dbrute 模型的 `index.txt` 中包含 Format 和 Render 信息
- meta.json 的 `parameters.format` 和 `parameters.renderer` 字段

---

## 八、完整工作流

```
1. [手动] 用户登录知末
2. [自动] 导航到创作者中心上传页面
3. [自动] 关闭"盗模模型公示"弹窗
4. [自动] 选择品类 = 模型
5. [自动] 选择原创度 = 共享模型
6. [自动] 上传 .rar 压缩包
7. [自动] 等待上传完成，页面跳转
8. [自动] 填写基本信息：
   - 领域（如：室内）
   - 类型（依赖领域选择）
   - 软件版本（如：3ds Max 2019）
   - 渲染器（如：Corona）
   - 标签（如：pouf, 沙发墩, 现代）
   - 分成 = 非独家
9. [自动] 上传封面图
10. [自动] 勾选协议并提交审核
```

---

## 九、常用工具速查

| 工具 | 用途 |
|------|------|
| `click` | 点击元素（按钮、下拉选项、单选框） |
| `upload_file` | 上传文件到 file input |
| `type` | 在文本框输入内容 |
| `keypress` | 模拟按键（如 Enter） |
| `evaluate_script` | 执行 JavaScript（如显示隐藏 input） |
| `take_enhanced_snapshot` | 获取页面结构，查找元素 ID |

---

## 十、与 3dbrute-model-loader 的协作

```
3dbrute-model-loader          znzmo-model-uploader
       ↓                                ↓
  下载模型 + 预览图              读取 meta.json
  生成标准目录结构               获取软件版本/渲染器
  生成 meta.json                 上传到知末
```

**数据传递：**
- `meta.json` 中的 `source.url` → 知末不需要，但保留溯源信息
- `meta.json` 中的 `parameters` → 填写软件版本、渲染器、标签
- `preview/*.webp` → 作为封面图上传
- `model/*.rar` → 作为上传文件
