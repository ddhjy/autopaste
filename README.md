# AutoPaste

macOS 菜单栏应用，通过 HTTP 接口接收文本并自动粘贴到当前活跃的输入框中。

## 使用场景

- 从其他设备/脚本远程向 Mac 发送文本并自动粘贴
- 配合自动化工具链，实现跨应用的文本输入
- 搭配 AI 对话工具，将生成内容直接粘贴到目标应用

## 安装

### 从源码运行

```bash
pip install pyobjc
python autopaste.py
```

### 打包为 .app

```bash
pip install py2app
python setup.py py2app
```

生成的应用位于 `dist/AutoPaste.app`，可拖入 `/Applications` 目录使用。

> 注：打包时若遇到递归深度错误，需在构建脚本中设置 `sys.setrecursionlimit(10000)`。

## 使用方法

启动后 AutoPaste 会出现在菜单栏（不会显示 Dock 图标），默认监听 `0.0.0.0:7788`。

### 发送文本

**纯文本：**

```bash
curl -X POST http://localhost:7788 -d '要粘贴的文本'
```

**JSON 格式：**

```bash
curl -X POST http://localhost:7788 \
  -H 'Content-Type: application/json' \
  -d '{"text": "要粘贴的文本"}'
```

### API 说明

| 方法 | 路径 | Content-Type | Body | 说明 |
|------|------|-------------|------|------|
| POST | `/` | `text/plain`（默认） | 原始文本 | 将 body 内容粘贴 |
| POST | `/` | `application/json` | `{"text": "..."}` | 将 `text` 字段内容粘贴 |

**响应：**

| 状态码 | Body | 说明 |
|--------|------|------|
| 200 | `{"ok": true}` | 粘贴成功 |
| 400 | `{"error": "empty text"}` | 文本为空 |
| 400 | `{"error": "invalid json"}` | JSON 解析失败 |
| 500 | `{"error": "..."}` | 粘贴过程出错 |

## 菜单栏功能

| 菜单项 | 说明 |
|--------|------|
| **Port: 7788** | 点击可修改监听端口 |
| **Auto Send** | 开启后粘贴完成会自动按回车发送（Enter + Cmd+Enter） |
| **Server: Running** | 点击可暂停/恢复 HTTP 服务 |
| **Quit** | 退出应用（快捷键 Cmd+Q） |

### 图标状态

- 📋 剪贴板图标 — 正常运行
- 📋 + ↑ 箭头 — Auto Send 已开启
- 📋 + ⏸ 暂停符号 — 服务已暂停

## 权限要求

AutoPaste 需要以下 macOS 权限：

- **辅助功能（Accessibility）** — 用于模拟 Cmd+V 键盘事件
- **Apple Events** — Auto Send 功能需要通过 System Events 发送按键

首次运行时系统会弹窗请求授权，请在 **系统设置 → 隐私与安全性 → 辅助功能** 中允许。

## 技术细节

- 使用 `CGEventPost` 模拟键盘事件（Cmd+V 粘贴）
- 使用 `pbcopy` 将文本写入系统剪贴板
- HTTP 服务运行在独立线程，不阻塞 UI
- 菜单栏图标使用 `NSBezierPath` 程序化绘制，支持自动适配深色/浅色模式
