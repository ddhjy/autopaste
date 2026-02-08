# AutoPaste 编译与安装指南

## 环境要求

- macOS 12.0+
- Xcode 16.0+

## 编译步骤

在项目根目录下执行：

```bash
cd AutoPaste
xcodebuild -project AutoPaste.xcodeproj -scheme AutoPaste -configuration Release build
```

编译成功后，产物位于：
```
~/Library/Developer/Xcode/DerivedData/AutoPaste-*/Build/Products/Release/AutoPaste.app
```

## 安装步骤

1. 关闭正在运行的 AutoPaste（如有）
2. 将编译产物复制到 Applications 目录

```bash
# 关闭旧进程
pkill -f AutoPaste.app || true

# 删除旧版本并安装新版本
rm -rf /Applications/AutoPaste.app
cp -R ~/Library/Developer/Xcode/DerivedData/AutoPaste-*/Build/Products/Release/AutoPaste.app /Applications/
```

## 启动应用

```bash
open /Applications/AutoPaste.app
```

## 一键编译安装（完整命令）

```bash
cd AutoPaste && \
xcodebuild -project AutoPaste.xcodeproj -scheme AutoPaste -configuration Release build && \
pkill -f AutoPaste.app 2>/dev/null || true && \
rm -rf /Applications/AutoPaste.app && \
cp -R ~/Library/Developer/Xcode/DerivedData/AutoPaste-*/Build/Products/Release/AutoPaste.app /Applications/ && \
open /Applications/AutoPaste.app
```
