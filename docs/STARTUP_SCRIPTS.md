# 启动脚本说明

本项目包含两个启动脚本，帮助你快速启动 KaiTian、MediaCrawler 和 Postiz 三个服务。

## 📋 脚本概览

| 脚本 | 语言 | 平台 | 优点 |
|------|------|------|------|
| `start.sh` | Bash | macOS/Linux | 原生支持，性能好，集成度高 |
| `start.py` | Python | 跨平台 | 易扩展，Windows 友好，功能丰富 |

## 🚀 快速开始（3 种方式）

### 方式 1：最简单（推荐）

```bash
cd kaitian
./start.sh
```

### 方式 2：Python 脚本

```bash
python start.py
```

### 方式 3：手动启动

```bash
# 在 3 个不同的终端运行
python main.py                              # Terminal 1
cd ../MediaCrawler && python -m media_crawler.main    # Terminal 2
cd ../postiz-app && npm run dev             # Terminal 3
```

## 📝 脚本功能详解

### start.sh（Bash 脚本）

**特性**:
- ✅ 自动创建和使用 Python 虚拟环境
- ✅ 自动克隆仓库（如果不存在）
- ✅ 自动安装依赖（Python + Node.js）
- ✅ 彩色输出，用户体验好
- ✅ 支持仅启动特定服务
- ✅ 自动日志管理
- ✅ 优雅的信号处理（Ctrl+C）

**使用**:

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

# 只克隆仓库（不启动）
./start.sh --clone-deps

# 只安装依赖（不启动）
./start.sh --install-deps
```

**输出示例**:

```
════════════════════════════════════════════════════════════
🎯 KaiTian Service Startup Manager
════════════════════════════════════════════════════════════

ℹ Cloning MediaCrawler from https://github.com/NanmiCoder/MediaCrawler.git...
✓ MediaCrawler cloned successfully

📦 Installing dependencies...
✓ KaiTian dependencies installed

🚀 Starting services...
✓ KaiTian started (PID: 12345)
✓ MediaCrawler started (PID: 12346)

✓ All services started successfully!
```

### start.py（Python 脚本）

**特性**:
- ✅ 自动创建和使用 Python 虚拟环境
- ✅ 跨平台支持（Windows/macOS/Linux）
- ✅ 更灵活的配置管理
- ✅ 易于扩展（添加新服务）
- ✅ 更详细的错误信息
- ✅ 支持自定义基础目录

**使用**:

```bash
# 查看帮助
python start.py --help

# 启动所有服务
python start.py

# 启动特定服务
python start.py --only kaitian
python start.py --only kaitian,postiz

# 自定义基础目录
python start.py --base-dir /custom/path

# 克隆仓库
python start.py --clone-deps

# 安装依赖
python start.py --install-deps
```

## 📂 目录结构

脚本需要以下目录结构：

```
parent_dir/
├── kaitian/                    ← 你在这里运行脚本
│   ├── start.sh
│   ├── start.py
│   ├── main.py
│   ├── requirements.txt
│   └── logs/                   ← 自动创建
├── MediaCrawler/              ← 自动克隆
│   └── ...
└── postiz-app/                ← 自动克隆
    └── ...
```

## 🔍 脚本工作流

### 启动流程

```
1. 验证环境 (Python, npm 等)
   ↓
2. 克隆仓库 (如果不存在)
   ├─ MediaCrawler
   └─ postiz-app
   ↓
3. 安装依赖
   ├─ KaiTian (pip install -r requirements.txt)
   ├─ MediaCrawler (pip install -e .)
   └─ Postiz (npm install)
   ↓
4. 启动服务
   ├─ KaiTian (python main.py)
   ├─ MediaCrawler (python -m media_crawler.main)
   └─ Postiz (npm run dev)
   ↓
5. 监控服务
   ├─ 检查进程状态
   ├─ 输出服务端点
   └─ 保持运行
   ↓
6. 清理资源 (Ctrl+C)
   ├─ 终止进程
   └─ 输出统计信息
```

## 📊 日志和监控

### 日志位置

所有日志保存在 `logs/` 目录：

```bash
logs/
├── kaitian.log
├── mediacrawler.log
├── postiz.log
└── .pids                      # 进程 ID 记录
```

### 查看日志

```bash
# 实时查看 KaiTian 日志
tail -f logs/kaitian.log

# 同时查看所有日志
tail -f logs/*.log

# 查看最后 100 行
tail -100 logs/kaitian.log

# 搜索错误
grep ERROR logs/*.log
```

### 查看进程

```bash
# macOS/Linux
ps aux | grep main.py
ps aux | grep media_crawler
ps aux | grep npm

# 查看占用的端口
lsof -i :8000  # KaiTian
lsof -i :8888  # MediaCrawler
lsof -i :3000  # Postiz
```

## 🔧 环境变量

### 通过 .env 配置 KaiTian

```bash
# 编辑 .env 文件（如果不存在，复制 .env.example）
cp .env.example .env
vim .env
```

可配置项：

```env
# 服务器
KAITIAN_HOST=0.0.0.0
KAITIAN_PORT=8000
KAITIAN_DEBUG=false

# 数据库
DATABASE_URL=sqlite:///./kaitian.db

# 搜索配置
SEARCH_KEYWORDS=python,automation,marketing
SUBREDDIT_LIST=python,learnprogramming

# 日志
KAITIAN_LOG_LEVEL=INFO
```

### 通过脚本启动时设置环境变量

```bash
# Bash
PORT=8001 ./start.sh kaitian

# Python
NODE_ENV=development python start.py
```

## 🆘 常见问题

### Q: 运行脚本时出现 "Permission denied"

**A**: 给脚本执行权限
```bash
chmod +x start.sh start.py
```

### Q: 克隆仓库失败（Network error）

**A**: 检查网络连接或手动克隆
```bash
git clone https://github.com/NanmiCoder/MediaCrawler.git ../MediaCrawler
git clone https://github.com/gitroomhq/postiz-app.git ../postiz-app
```

### Q: 依赖安装失败

**A**: 清空缓存重新安装
```bash
# Python
pip cache purge && pip install --upgrade pip
./start.sh --install-deps

# Node.js
npm cache clean --force
npm install
```

### Q: 端口已被占用

**A**: 修改端口
```bash
# 方式 1：环境变量
KAITIAN_PORT=8001 ./start.sh

# 方式 2：编辑 .env 文件
KAITIAN_PORT=8001
```

### Q: 无法停止服务

**A**: 手动杀死进程
```bash
# 获取 PID
ps aux | grep python | grep main.py
# 杀死进程
kill -9 <PID>
```

### Q: 脚本运行但服务没有启动

**A**: 查看日志文件
```bash
tail -f logs/kaitian.log
tail -f logs/mediacrawler.log
tail -f logs/postiz.log
```

## 💡 高级用法

### 仅启动部分服务

```bash
# 只启动 KaiTian（不启动爬虫和发布）
./start.sh kaitian

# 启动 KaiTian 和 MediaCrawler
./start.sh kaitian mediacrawler
```

### 预检查（不启动）

```bash
./start.sh --clone-deps       # 克隆仓库
./start.sh --install-deps     # 安装依赖
```

### 自定义基础目录（Python 脚本）

```bash
python start.py --base-dir /custom/path
```

### 在后台运行

```bash
# Bash
nohup ./start.sh > startup.log 2>&1 &

# Python
nohup python start.py > startup.log 2>&1 &
```

### 使用 supervisor 管理（生产环境）

```bash
# 创建 supervisor 配置
sudo vim /etc/supervisor/conf.d/kaitian.conf
```

配置内容：

```ini
[program:kaitian]
directory=/path/to/kaitian
command=python main.py
autostart=true
autorestart=true
stdout_logfile=/var/log/kaitian.log
stderr_logfile=/var/log/kaitian.err

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

启动：
```bash
sudo supervisorctl reread
sudo supervisorctl update
sudo supervisorctl start all
```

## 📚 相关文档

- [STARTUP_GUIDE.md](./STARTUP_GUIDE.md) - 详细启动指南
- [QUICK_REFERENCE.md](./QUICK_REFERENCE.md) - 快速参考卡
- [README.md](../README.md) - KaiTian 主文档
- [N8N_INTEGRATION.md](./N8N_INTEGRATION.md) - n8n 集成指南

## 🔗 快速链接

- **KaiTian API**: http://localhost:8000/api/v1
- **KaiTian 文档**: http://localhost:8000/docs
- **MediaCrawler**: http://localhost:8888
- **Postiz**: http://localhost:3000

## 📞 获取帮助

```bash
# 查看脚本帮助
./start.sh --help
python start.py --help

# 查看日志
tail -f logs/*.log

# 检查端口
netstat -an | grep LISTEN

# 检查进程
ps aux | grep python
ps aux | grep npm
```

## 📝 更新日志

### v1.0 (2024-03-01)
- ✅ 首版发布
- ✅ 支持 Bash 和 Python 脚本
- ✅ 自动克隆和依赖安装
- ✅ 完整的文档和指南

---

**需要帮助？** 查看 [STARTUP_GUIDE.md](./STARTUP_GUIDE.md) 获取更详细的信息。
