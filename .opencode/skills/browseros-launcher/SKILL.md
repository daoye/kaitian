---
name: browseros-launcher
description: 当 BrowserOS MCP 连接失败，或有操作需要使用BrowerOS时，用于启动 BrowserOS 浏览器
---

# BrowserOS Launcher

**触发条件：**
1. Agent 报告 BrowserOS MCP 工具无法连接、不可用或超时
2. 用户明确要求"启动 BrowserOS"或"打开浏览器"

## 启动方法

**直接运行以下程序即可：**

```powershell
Start-Process "C:\Users\daoye\AppData\Local\Chromium\Application\chrome.exe"
```

**或双击桌面快捷方式：**
`BrowserOS.lnk`

## 验证启动

```powershell
Get-Process | Where-Object { $_.ProcessName -eq "chrome" -and $_.Path -match "Chromium" }
```

## 故障排查

### MCP 无法连接

如果 Agent 报告 BrowserOS MCP 连接失败：

1. **检查浏览器是否已启动**
   ```powershell
   Get-Process | Where-Object { $_.Path -eq "C:\Users\daoye\AppData\Local\Chromium\Application\chrome.exe" }
   ```

2. **如果没启动，直接运行**
   ```powershell
   Start-Process "C:\Users\daoye\AppData\Local\Chromium\Application\chrome.exe"
   ```

3. **如果已启动但仍然无法连接**
   - 关闭所有 Chromium 进程后重新启动
   - 或重启电脑后再启动

### 多次启动

如果已经启动了多个 Chromium 实例：

```powershell
# 关闭所有 Chromium
Get-Process | Where-Object { $_.Path -match "Chromium" } | Stop-Process -Force

# 重新启动
Start-Process "C:\Users\daoye\AppData\Local\Chromium\Application\chrome.exe"
```
