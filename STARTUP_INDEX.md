# 🚀 KaiTian 启动脚本快速索引

## 一句话开始

```bash
cd kaitian && ./start.sh
```

## 📍 快速导航

### 我想...

| 目标 | 命令 | 文档 |
|------|------|------|
| 快速启动所有服务 | `./start.sh` | [快速参考](docs/QUICK_REFERENCE.md) |
| 启动特定服务 | `./start.sh kaitian` | [快速参考](docs/QUICK_REFERENCE.md) |
| 查看脚本帮助 | `./start.sh --help` | [脚本说明](docs/STARTUP_SCRIPTS.md) |
| 仅克隆仓库 | `./start.sh --clone-deps` | [启动指南](docs/STARTUP_GUIDE.md) |
| 仅安装依赖 | `./start.sh --install-deps` | [启动指南](docs/STARTUP_GUIDE.md) |
| 查看日志 | `tail -f logs/*.log` | [脚本说明](docs/STARTUP_SCRIPTS.md) |
| 使用 Python 脚本 | `python start.py` | [脚本说明](docs/STARTUP_SCRIPTS.md) |
| 解决问题 | 查看日志 | [故障排查](docs/STARTUP_GUIDE.md) |
| 学习高级用法 | 阅读文档 | [脚本说明](docs/STARTUP_SCRIPTS.md) |

## 📚 文档指南

### 🟢 初级用户（快速开始）

1. **[快速参考卡](docs/QUICK_REFERENCE.md)** (4 分钟阅读)
   - 一行命令启动
   - 服务端点表格
   - 常用命令速查
   - 快速排查

2. **[详细启动指南](docs/STARTUP_GUIDE.md)** (10 分钟阅读)
   - 系统要求检查
   - 3 种启动方式
   - 常见问题解答
   - 环境配置

### 🔵 高级用户（深入学习）

3. **[脚本说明书](docs/STARTUP_SCRIPTS.md)** (15 分钟阅读)
   - 脚本工作流详解
   - 日志和监控
   - supervisor 配置
   - 故障排查进阶

## 🎯 典型场景

### 场景 1：第一次运行

```bash
# 进入目录
cd kaitian

# 启动所有服务（自动克隆 + 安装 + 启动）
./start.sh

# 等待输出显示所有端点
# 打开浏览器访问 http://localhost:8000/docs
```

**预期输出**:
```
✓ KaiTian started (PID: xxxx)
✓ MediaCrawler started (PID: xxxx)
✓ Postiz started (PID: xxxx)

✓ All services started successfully!
```

### 场景 2：仅启动 KaiTian

```bash
./start.sh kaitian

# 打开另外的终端启动其他服务
cd ../MediaCrawler && python -m media_crawler.main
```

### 场景 3：查看日志

```bash
# 实时查看 KaiTian 日志
tail -f logs/kaitian.log

# 同时查看所有日志
tail -f logs/*.log

# 搜索错误
grep ERROR logs/*.log
```

### 场景 4：预检查（不启动）

```bash
# 只克隆仓库
./start.sh --clone-deps

# 只安装依赖
./start.sh --install-deps

# 然后再启动
./start.sh
```

### 场景 5：故障排查

```bash
# 1. 查看实时日志
tail -f logs/*.log

# 2. 检查进程
ps aux | grep python
ps aux | grep npm

# 3. 检查端口占用
lsof -i :8000
lsof -i :8888
lsof -i :3000

# 4. 手动启动单个服务
python main.py  # KaiTian
```

## 🔧 脚本选择

### 选择 start.sh (Bash)

**适合**: Linux/macOS 用户，更熟悉 Shell

```bash
# 优点
✓ 原生支持，无额外依赖
✓ 性能更好
✓ Shell 集成度高
✓ 彩色输出漂亮

# 缺点
✗ Windows 需要 WSL 或 Git Bash
```

### 选择 start.py (Python)

**适合**: Windows 用户，或希望跨平台

```bash
# 优点
✓ 完全跨平台 (Windows/macOS/Linux)
✓ 更灵活的配置
✓ 易于扩展
✓ 更详细的错误信息

# 缺点
✗ 需要 Python 3.6+
```

## 📍 服务端点速查

```
KaiTian API     http://localhost:8000/api/v1
KaiTian Docs    http://localhost:8000/docs
KaiTian Health  http://localhost:8000/api/v1/health

MediaCrawler    http://localhost:8888

Postiz          http://localhost:3000
```

## 🔗 相关文档

| 文档 | 用途 | 位置 |
|------|------|------|
| 快速参考 | 速查常用命令 | [docs/QUICK_REFERENCE.md](docs/QUICK_REFERENCE.md) |
| 启动指南 | 详细启动说明 | [docs/STARTUP_GUIDE.md](docs/STARTUP_GUIDE.md) |
| 脚本说明 | 脚本工作原理 | [docs/STARTUP_SCRIPTS.md](docs/STARTUP_SCRIPTS.md) |
| 主文档 | 项目概述 | [README.md](README.md) |
| n8n 集成 | 与 n8n 集成 | [docs/N8N_INTEGRATION.md](docs/N8N_INTEGRATION.md) |
| Docker 部署 | Docker 方案 | [docs/DOCKER_DEPLOYMENT.md](docs/DOCKER_DEPLOYMENT.md) |

## ❓ 常见问题快速答案

**Q: 脚本无法执行？**
```bash
chmod +x start.sh start.py
```

**Q: 端口被占用？**
修改环境变量或编辑 .env 文件

**Q: 网络连接失败？**
检查网络，或手动克隆仓库

**Q: 依赖安装失败？**
```bash
./start.sh --install-deps  # 重新安装
```

**Q: 如何停止服务？**
```bash
Ctrl+C  # 或手动 kill <PID>
```

更多问题见 [故障排查](docs/STARTUP_GUIDE.md#%EF%B8%8F-故障排查)

## 🎁 额外资源

- **源代码**: `start.sh` (Bash) 和 `start.py` (Python)
- **配置模板**: `.env.startup`
- **日志目录**: `logs/` (自动创建)
- **API 文档**: http://localhost:8000/docs (启动后访问)

## 🚀 立即开始

```bash
# 1. 进入项目目录
cd /path/to/kaitian

# 2. 运行启动脚本
./start.sh

# 3. 等待服务启动完成
# 输出会显示所有端点和 PID

# 4. 访问 API 文档
# 打开浏览器: http://localhost:8000/docs

# 5. 开始使用
# 查看 docs/N8N_INTEGRATION.md 了解如何集成 n8n
```

## 📞 需要帮助？

- 🔍 快速查找: `docs/QUICK_REFERENCE.md`
- 📖 详细说明: `docs/STARTUP_GUIDE.md`
- 🔧 高级用法: `docs/STARTUP_SCRIPTS.md`
- 💬 脚本帮助: `./start.sh --help`
- 📋 查看日志: `tail -f logs/*.log`

---

**版本**: 1.0  
**最后更新**: 2024-03-01  
**状态**: ✅ 完全就绪
