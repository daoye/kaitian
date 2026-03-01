# KaiTian 快速启动指南

快速启动 KaiTian、MediaCrawler 和 Postiz 的方案，支持从源码直接运行所有服务。

## 📋 要求

### 系统要求
- Python 3.9+ （用于 KaiTian 和 MediaCrawler）
- Node.js 16+ 和 npm/yarn （用于 Postiz）
- Git （用于克隆仓库）

### 检查依赖

```bash
python --version       # 应该是 3.9+
npm --version         # 应该是 8+
node --version        # 应该是 16+
git --version         # 应该是 2.0+
```

## 🚀 快速开始

### 方式 1：Bash 脚本（推荐）

```bash
# 进入 KaiTian 目录
cd /path/to/kaitian

# 启动所有服务
./start.sh

# 或只启动特定服务
./start.sh kaitian
./start.sh kaitian mediacrawler
./start.sh postiz
```

### 方式 2：Python 脚本

```bash
# 启动所有服务
python start.py

# 只启动 KaiTian
python start.py --only kaitian

# 启动多个服务
python start.py --only kaitian,mediacrawler

# 先克隆仓库
python start.py --clone-deps

# 先安装依赖
python start.py --install-deps
```

### 方式 3：手动启动

#### 步骤 1：克隆仓库

```bash
cd /path/to  # KaiTian 的父目录
git clone https://github.com/NanmiCoder/MediaCrawler.git
git clone https://github.com/gitroomhq/postiz-app.git
```

#### 步骤 2：安装依赖

```bash
# KaiTian
cd kaitian
pip install -r requirements.txt

# MediaCrawler
cd ../MediaCrawler
pip install -e .

# Postiz
cd ../postiz-app
npm install
```

#### 步骤 3：启动服务

在不同的终端窗口中运行：

```bash
# 终端 1 - KaiTian
cd kaitian
python main.py

# 终端 2 - MediaCrawler
cd MediaCrawler
python -m media_crawler.main

# 终端 3 - Postiz
cd postiz-app
npm run dev
```

## 📊 服务信息

### KaiTian API 服务
- **端口**: 8000
- **API 地址**: http://localhost:8000/api/v1
- **文档地址**: http://localhost:8000/docs
- **健康检查**: http://localhost:8000/api/v1/health
- **语言**: Python (FastAPI)

### MediaCrawler 爬虫服务
- **端口**: 8888
- **地址**: http://localhost:8888
- **功能**: 社交媒体爬虫（Reddit、Twitter 等）
- **语言**: Python

### Postiz 发布服务
- **端口**: 3000
- **地址**: http://localhost:3000
- **功能**: 社交媒体内容发布管理
- **语言**: Node.js (Next.js)

## 📝 常见命令

### 使用 Bash 脚本

```bash
# 查看帮助
./start.sh --help

# 启动所有服务
./start.sh

# 启动特定服务
./start.sh kaitian
./start.sh mediacrawler
./start.sh postiz

# 启动多个服务
./start.sh kaitian mediacrawler

# 只克隆仓库
./start.sh --clone-deps

# 只安装依赖
./start.sh --install-deps

# 查看日志
tail -f logs/kaitian.log
tail -f logs/mediacrawler.log
tail -f logs/postiz.log

# 停止服务（Ctrl+C）
```

### 使用 Python 脚本

```bash
# 查看帮助
python start.py --help

# 启动所有服务
python start.py

# 启动特定服务
python start.py --only kaitian
python start.py --only kaitian,postiz

# 克隆仓库
python start.py --clone-deps

# 安装依赖
python start.py --install-deps

# 停止服务（Ctrl+C）
```

## 🐛 故障排查

### KaiTian 无法启动

**错误**: `ModuleNotFoundError: No module named 'fastapi'`

**解决**:
```bash
cd kaitian
pip install -r requirements.txt
```

**错误**: `Address already in use: ('0.0.0.0', 8000)`

**解决**: 端口已被占用，关闭其他服务或修改端口：
```bash
# 修改 .env 或直接运行
KAITIAN_PORT=8001 python main.py
```

### MediaCrawler 无法启动

**错误**: `ModuleNotFoundError: No module named 'media_crawler'`

**解决**:
```bash
cd ../MediaCrawler
pip install -e .
```

### Postiz 无法启动

**错误**: `npm: command not found`

**解决**: 安装 Node.js
```bash
# macOS
brew install node

# Ubuntu/Debian
sudo apt-get install nodejs npm

# Windows
# 从 https://nodejs.org 下载安装器
```

**错误**: `Port 3000 already in use`

**解决**: 修改端口
```bash
cd postiz-app
PORT=3001 npm run dev
```

### 依赖安装失败

**针对 MediaCrawler**:
```bash
# 清空缓存重新安装
cd MediaCrawler
pip cache purge
pip install --force-reinstall -e .
```

**针对 Postiz**:
```bash
# 清空 npm 缓存
cd postiz-app
npm cache clean --force
npm install
```

## 🔧 环境变量配置

### KaiTian

在 `.env` 中配置：
```env
# 服务器
KAITIAN_HOST=0.0.0.0
KAITIAN_PORT=8000

# 数据库
DATABASE_URL=sqlite:///./kaitian.db

# Crawl4AI
CRAWL4AI_API_URL=http://localhost:8001

# 搜索关键词
SEARCH_KEYWORDS=python,programming,automation

# Reddit
SUBREDDIT_LIST=python,learnprogramming

# 日志
KAITIAN_LOG_LEVEL=INFO
```

### MediaCrawler

查看 MediaCrawler 的配置文件。

### Postiz

在 `.env.local` 中配置（参考项目文档）。

## 🔗 服务集成示例

### KaiTian + n8n 集成

在 n8n 的 HTTP Request 节点中：

```
URL: http://localhost:8000/api/v1/posts
Method: GET
```

### KaiTian + MediaCrawler 集成

KaiTian 可以调用 MediaCrawler API 获取社交媒体数据：

```python
import httpx

# 调用 MediaCrawler
response = httpx.post("http://localhost:8888/crawl", json={
    "platform": "reddit",
    "keywords": ["python"]
})
```

### KaiTian + Postiz 集成

KaiTian 可以通过 Postiz API 发布内容：

```python
# 调用 Postiz API
response = httpx.post("http://localhost:3000/api/posts", json={
    "content": "Hello World",
    "platforms": ["twitter", "reddit"]
})
```

## 📚 相关文档

- [KaiTian README](./README.md)
- [n8n 集成指南](./docs/N8N_INTEGRATION.md)
- [Docker 部署指南](./docs/DOCKER_DEPLOYMENT.md)
- [MediaCrawler GitHub](https://github.com/NanmiCoder/MediaCrawler)
- [Postiz GitHub](https://github.com/gitroomhq/postiz-app)

## 💡 技巧

### 同时查看多个日志

```bash
# 使用 tmux
tmux new-session -d -s kaitian
tmux send-keys -t kaitian "tail -f logs/kaitian.log" Enter
tmux new-window -t kaitian
tmux send-keys -t kaitian "tail -f logs/mediacrawler.log" Enter
tmux new-window -t kaitian
tmux send-keys -t kaitian "tail -f logs/postiz.log" Enter
tmux attach -t kaitian
```

### 使用 supervisor 管理进程（可选）

创建 `/etc/supervisor/conf.d/kaitian.conf`:

```ini
[group:kaitian-services]
programs=kaitian,mediacrawler,postiz

[program:kaitian]
directory=/path/to/kaitian
command=python main.py
autostart=true
autorestart=true
stdout_logfile=/var/log/kaitian.log

[program:mediacrawler]
directory=/path/to/MediaCrawler
command=python -m media_crawler.main
autostart=true
autorestart=true
stdout_logfile=/var/log/mediacrawler.log

[program:postiz]
directory=/path/to/postiz-app
command=npm run dev
autostart=true
autorestart=true
stdout_logfile=/var/log/postiz.log
```

然后启动:
```bash
supervisord -c /etc/supervisor/supervisord.conf
supervisorctl start kaitian-services:*
```

## 🆘 获取帮助

- 查看脚本帮助: `./start.sh --help` 或 `python start.py --help`
- 查看日志文件: `logs/` 目录
- GitHub Issues: 查看各个项目的 Issue 页面

## 📝 注意事项

1. **端口冲突**: 如果有端口占用，脚本会报错。确保 8000、8888、3000 端口可用。
2. **Python 版本**: KaiTian 需要 Python 3.9+，MediaCrawler 需要 Python 3.8+。
3. **网络连接**: 首次运行会下载依赖包，需要网络连接。
4. **Node.js 版本**: Postiz 需要 Node.js 16+（推荐 18+）。
5. **数据库**: KaiTian 使用 SQLite，数据文件为 `kaitian.db`。

---

**祝使用愉快！** 🎉
