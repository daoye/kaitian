---
name: auth-cookie-import
description: 将本地 cookies 目录中的站点 cookie 批量导入 auth.db，供爬虫使用。当爬虫需要登录态但无法通过浏览器自动化获取时使用。
---

# Auth Cookie Import

将 `cookies/` 目录中的站点 cookie 批量导入认证数据库，供 HTTP 爬虫使用。

## 工作流程

```
1. 从浏览器导出 cookie 保存到 cookies/{domain}.txt
2. kaitian auth import 批量导入 auth.db
3. 爬虫从 auth.db 读取 cookie 进行 HTTP 请求
```

## Cookie 文件格式

`cookies/{domain}.txt`，多账号交替行，`#` 和空行忽略：

```
# 3dbrute.com
default
wordpress_logged_in=xxx; PHPSESSID=xxx

admin@example.com
wordpress_logged_in=yyy; PHPSESSID=yyy
```

## 导入

```bash
uv run kaitian auth import
```

## 设置站点扩展信息

某些站点需要额外信息（如 3dbrute 的 download nonce），通过通用 metadata 机制存储：

```bash
uv run kaitian auth set-meta 3dbrute.com daoye.more@gmail.com download_nonce <从浏览器获取的值>
```

爬虫自动读取 metadata，无需每次传入。

## 验证

```bash
uv run kaitian auth list
```

## 爬虫使用

```python
from downloader.client import fetch_page
from auth.repository import SessionRepository

repo = SessionRepository()
session = repo.get_by_account("3dbrute.com", "default")
html = fetch_page("https://3dbrute.com/...", cookies=session.cookies)
```

## Common Mistakes

| 错误 | 后果 | 正确做法 |
|------|------|----------|
| 多账号行数不配对 | 解析错位 | 严格「账号行 → cookie 行」交替 |
| 导入后修改密码 | cookie 失效 | 重新导出并导入 |
