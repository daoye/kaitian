# KaiTian 快速参考卡

## 🚀 一行命令启动

```bash
# Bash 脚本（自动创建和使用虚拟环境）
./start.sh

# Python 脚本（自动创建和使用虚拟环境）
python start.py

# 手动启动（3 个不同的终端）
python main.py                    # Terminal 1: KaiTian
cd ../MediaCrawler && python -m media_crawler.main  # Terminal 2
cd ../postiz-app && npm run dev   # Terminal 3
```

## 💡 虚拟环境说明

- 启动脚本自动创建虚拟环境在 `./venv` 目录
- 无需手动激活虚拟环境
- 所有依赖自动安装到虚拟环境中
- 支持多 Python 版本隔离

## 📍 服务端点

| 服务 | 地址 | 说明 |
|------|------|------|
| KaiTian API | http://localhost:8000/api/v1 | REST API |
| KaiTian Docs | http://localhost:8000/docs | API 文档（Swagger） |
| KaiTian Health | http://localhost:8000/api/v1/health | 健康检查 |
| MediaCrawler | http://localhost:8888 | 爬虫服务 |
| Postiz | http://localhost:3000 | 发布服务 |

## 🔧 常用命令

```bash
# 启动脚本选项
./start.sh --help              # 显示帮助
./start.sh --install-deps      # 安装依赖
./start.sh --clone-deps        # 克隆仓库
./start.sh kaitian             # 只启动 KaiTian
./start.sh kaitian postiz      # 启动指定服务

# 查看日志
tail -f logs/kaitian.log
tail -f logs/mediacrawler.log
tail -f logs/postiz.log

# 查看运行的进程
ps aux | grep "main.py"        # KaiTian
ps aux | grep "media_crawler"  # MediaCrawler
ps aux | grep "npm"            # Postiz

# 停止服务（从脚本启动）
Ctrl+C

# 停止服务（手动启动）
kill -9 <PID>
```

## 📦 依赖检查

```bash
# 检查 Python
python --version               # 需要 3.9+

# 检查 Node.js
node --version                 # 需要 16+
npm --version                  # 需要 8+

# 检查 Git
git --version                  # 需要 2.0+
```

## 🔌 API 快速测试

```bash
# 健康检查
curl http://localhost:8000/api/v1/health

# 列出所有帖子
curl http://localhost:8000/api/v1/posts

# 爬取 URL
curl -X POST "http://localhost:8000/api/v1/crawl/url?url=https://example.com&store_to_db=false"

# 查看 API 文档
open http://localhost:8000/docs
```

## 🐛 快速排查

| 问题 | 解决方案 |
|------|---------|
| 端口占用 | 更改环境变量中的端口号 |
| 模块未找到 | 运行 `./start.sh --install-deps` |
| 仓库不存在 | 运行 `./start.sh --clone-deps` |
| Node.js 未找到 | 安装 Node.js（https://nodejs.org） |
| Python 版本太低 | 升级到 3.9 或更高 |

## 📚 文件位置

```
kaitian/
├── start.sh                    # Bash 启动脚本
├── start.py                    # Python 启动脚本
├── main.py                     # KaiTian 入口
├── requirements.txt            # Python 依赖
├── .env.example               # 环境配置示例
├── .env.startup               # 启动脚本配置
├── logs/                      # 日志目录
├── kaitian.db                 # SQLite 数据库
└── docs/
    ├── STARTUP_GUIDE.md       # 本启动指南
    ├── N8N_INTEGRATION.md     # n8n 集成
    └── DOCKER_DEPLOYMENT.md   # Docker 部署

../MediaCrawler/              # 爬虫项目
../postiz-app/                # 发布项目
```

## 🎯 典型工作流

### 第一次运行
```bash
cd kaitian
python start.py --clone-deps      # 克隆仓库
python start.py --install-deps    # 安装依赖
python start.py                   # 启动所有服务
```

### 日常运行
```bash
cd kaitian
./start.sh                        # 或 python start.py
```

### 开发模式
```bash
# Terminal 1 - KaiTian（支持自动重载）
cd kaitian
python main.py

# Terminal 2 - MediaCrawler
cd ../MediaCrawler
python -m media_crawler.main

# Terminal 3 - Postiz
cd ../postiz-app
npm run dev
```

## 💻 跨平台说明

### macOS
```bash
# 安装依赖
brew install python@3.11 node git

# 启动
./start.sh
```

### Linux (Ubuntu/Debian)
```bash
# 安装依赖
sudo apt-get install python3 python3-pip nodejs npm git

# 启动
./start.sh
```

### Windows
```bash
# 使用 PowerShell 或 Git Bash
python start.py

# 或用 WSL 使用 bash
bash start.sh
```

## 🔗 相关链接

- [KaiTian GitHub](.)
- [MediaCrawler GitHub](https://github.com/NanmiCoder/MediaCrawler)
- [Postiz GitHub](https://github.com/gitroomhq/postiz-app)
- [n8n 官网](https://n8n.io)

## 📞 获取帮助

1. **查看日志**: `tail -f logs/*.log`
2. **检查端口**: `lsof -i :8000` (macOS/Linux)
3. **查看脚本帮助**: `./start.sh --help`
4. **阅读完整指南**: `docs/STARTUP_GUIDE.md`

---

**版本**: 1.0  
**更新**: 2024-03-01
