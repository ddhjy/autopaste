# AutoPaste 编译与安装指南

## 环境要求

- macOS 12.0+
- Xcode 16.0+

## 编译步骤

在项目根目录下执行：

```bash
make release
```

打包产物位于：
```
dist/release/AutoPaste.app
dist/release/AutoPaste-<version>.zip
```

如需仅使用原生 xcodebuild，也可以执行：

```bash
cd AutoPaste
xcodebuild -project AutoPaste.xcodeproj -scheme AutoPaste -configuration Release build
```

编译成功后，产物位于：
```
~/Library/Developer/Xcode/DerivedData/AutoPaste-*/Build/Products/Release/AutoPaste.app
```

## 安装步骤

推荐直接执行：

```bash
make install
```

该命令会自动完成：

1. 编译最新产物并更新 `dist/release/AutoPaste.app`
2. 尝试优雅退出正在运行的 AutoPaste（必要时强制结束）
3. 覆盖安装到 `/Applications/AutoPaste.app`
4. 重新打开应用

## 一键编译安装（完整命令）

```bash
make install
```
