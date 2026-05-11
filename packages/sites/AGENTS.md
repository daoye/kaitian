# 站点隔离

每个站点在 `packages/sites/{site}/` 下独立实现，通过注册表接入下载器。

### 模块结构
```
{site}/
├── parsers.py     # HTML → Meta Schema（必须）
├── listing.py     # 模型列表获取（可选）
└── download.py    # 文件下载（可选）
```

### 注册
在 `packages/downloader/src/downloader/parsers/__init__.py` 中：
```python
from sites.{site} import parsers
register("{site}", parsers)
```

### 站点模块
| 站点 | 模块 | 说明 |
|------|------|------|
| three_dbrute | `sites.three_dbrute` | parsers/listing/download/agent(get_nonce) |
| znzmo | `sites.znzmo` | upload_agent（LLM 分析 + MCP 上传） |
