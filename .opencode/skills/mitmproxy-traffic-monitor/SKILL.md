---
name: mitmproxy-traffic-monitor
description: 使用 mitmproxy 监控和分析 HTTP/HTTPS 流量。当需要调试爬虫请求/响应、分析 API 调用、拦截修改流量、或对捕获的流量数据进行程序化分析提取端点/参数/错误时使用。
---

# Mitmproxy 流量监控

Mitmproxy 中间人代理，用于 HTTP/HTTPS 流量拦截和检查。

> 已通过 `uv add --group dev mitmproxy` 安装。

## 核心流程

```
proxy_manager.ps1 start → 爬虫请求经过代理 → addon 记录到 traffic.jsonl → proxy_manager.ps1 stop → 程序化分析
```

## 前置条件：安装 HTTPS 证书

首次使用需安装 mitmproxy CA 证书到系统，否则无法解密 HTTPS 流量：

```powershell
certutil -user -addstore Root "$env:USERPROFILE\.mitmproxy\mitmproxy-ca-cert.cer"
```

## 进程管理（proxy_manager.ps1）

使用固定端口 **8080**，参数已预置。Agent 按以下方式调用：

| 操作 | 命令 |
|------|------|
| 启动 | `& $p start -Script scripts/traffic_recorder.py -Insecure` |
| 停止 | `& $p stop` |
| 状态 | `& $p status` |
| 清理 | `& $p cleanup` |

```powershell
# 固定路径
$p = ".opencode/skills/mitmproxy-traffic-monitor/scripts/proxy_manager.ps1"

# 启动（验证脚本存在 → 释放端口 → 启动 → 等待就绪）
& $p start -Script scripts/traffic_recorder.py -Insecure

# 停止（通过 netstat 找监听进程 → 杀整棵树 → 清理残留）
& $p stop

# 清理所有驻留
& $p cleanup
```

> 端口固定 8080，不支持自定义。如需变更端口请编辑代理配置中的 `listen_port`。

## Addon 脚本

### traffic_recorder.py

记录请求到 `traffic.jsonl`（JSON Lines 格式），每行一个请求。

```bash
uv run mitmdump -p 8080 -s scripts/traffic_recorder.py -k -q
```

输出格式（每行一个 JSON，含完整 header 和 body）：
```json
{
  "ts": "2026-05-10T13:37:55+00:00",
  "method": "GET",
  "url": "https://httpbin.org/get?key=val",
  "request_headers": {"Host": "httpbin.org", ...},
  "request_body": "{\"name\":\"test\"}",
  "status": 200,
  "response_headers": {"Content-Type": "application/json", ...},
  "response_body": "{...}",
  "content_type": "application/json",
  "response_bytes": 314
}
```

字段说明：

| 字段 | 说明 |
|------|------|
| `ts` | ISO 时间戳 |
| `method` | HTTP 方法 |
| `url` | 完整 URL（含 query string） |
| `request_headers` | 请求头 dict |
| `request_body` | 请求体（截断 128KB，GET 为空字符串） |
| `status` | HTTP 状态码 |
| `response_headers` | 响应头 dict |
| `response_body` | 响应体（截断 128KB） |
| `content_type` | 响应 Content-Type |
| `response_bytes` | 响应体原始字节数 |

## 爬虫代理配置

```python
import httpx

with httpx.Client(proxy="http://127.0.0.1:8080", verify=False) as client:
    resp = client.get("https://api.example.com/data")
```

## 程序化分析 traffic.jsonl

```python
import json
from collections import Counter
from urllib.parse import urlparse

rows = [json.loads(l) for l in open("traffic.jsonl")]

# 状态码分布
status_dist = Counter(r["status"] for r in rows)

# 按请求量排序的 API 端点
api_urls = [r["url"] for r in rows if "json" in r["content_type"]]
top_endpoints = Counter(api_urls).most_common(20)

# 提取 URL 路径模式
paths = Counter(urlparse(r["url"]).path for r in rows if "json" in r["content_type"])

# 失败请求
fails = [r for r in rows if r["status"] >= 400]

# 解析响应体提取数据
for r in rows:
    body = r.get("response_body", "")
    if body.startswith("{"):
        obj = json.loads(body)
        # 提取字段...

# 找出包含特定 header 的请求
auth_reqs = [r for r in rows if "Authorization" in r["request_headers"]]
cookies = [r["response_headers"].get("set-cookie") for r in rows if "set-cookie" in r.get("response_headers", {})]
```

## 写自定义 Addon

```python
from mitmproxy import http


class MyAddon:
    def response(self, flow: http.HTTPFlow) -> None:
        resp = flow.response
        text = resp.get_text()  # 响应体
        headers = dict(flow.request.headers)  # 请求头

    def error(self, flow: http.HTTPFlow) -> None:
        pass

    def done(self) -> None:
        pass


addons = [MyAddon()]
```

> 注意：mitmproxy 11.1.3 + Python 3.14 下 `request` hook 存在兼容问题，建议只用 `response` hook。

## 常见问题

- **证书**：首次需要 `certutil -user -addstore Root ~\.mitmproxy\mitmproxy-ca-cert.cer`
- **SyntaxWarning**：Python 3.14 下 mitmproxy 11.x 的已知警告，不影响功能
- **端口占用**：默认 8080 被占用时用 `-p` 指定其他端口
- **后台启动**：`proxy_manager.ps1 start` 本身立即退出
