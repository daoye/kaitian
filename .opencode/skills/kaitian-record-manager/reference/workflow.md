# 完整工作流示例

以 3dbrute.com 为例，展示 agent 如何使用 record CLI 管理下载进度。

## 1. 准备：清理旧的测试数据

```bash
kaitian record remove 3dbrute.com https://3dbrute.com/aura-pouf/
```

## 2. 查重

```bash
kaitian record check 3dbrute.com https://3dbrute.com/aura-pouf/
# 输出: 未找到记录 → 开始新下载
```

## 3. 记录初始状态

```bash
kaitian record set 3dbrute.com https://3dbrute.com/aura-pouf/ --name "Aura pouf"
```

## 4. 每步推进

```bash
kaitian record set 3dbrute.com https://3dbrute.com/aura-pouf/ --step fetching --name "Aura pouf"
kaitian record set 3dbrute.com https://3dbrute.com/aura-pouf/ --step meta_extracted --name "Aura pouf"
kaitian record set 3dbrute.com https://3dbrute.com/aura-pouf/ --step file_downloaded --name "Aura pouf"
kaitian record set 3dbrute.com https://3dbrute.com/aura-pouf/ --step previews_downloaded --name "Aura pouf"
kaitian record set 3dbrute.com https://3dbrute.com/aura-pouf/ --step processing --name "Aura pouf"
```

## 5. 标记完成

```bash
kaitian record done 3dbrute.com https://3dbrute.com/aura-pouf/
```

## 6. 中断恢复

假设处理到 `file_downloaded` 时中断：

```bash
# 查询进度
kaitian record check 3dbrute.com https://3dbrute.com/aura-pouf/
# → 进行中，步骤: file_downloaded

# 从中断处继续，跳过已完成步骤
kaitian record set 3dbrute.com https://3dbrute.com/aura-pouf/ --step previews_downloaded --name "Aura pouf"
```

## 7. 查看批量进度

```bash
# 3dbrute.com 整体进度
kaitian record status 3dbrute.com

# 列出所有进行中的
kaitian record list 3dbrute.com --status running

# 列出所有站点
kaitian record sites
```
