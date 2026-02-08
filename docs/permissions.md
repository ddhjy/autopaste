# 权限配置指南

AutoPaste 需要 **辅助功能权限** 才能模拟键盘粘贴操作。

## 权限状态检查

打开 AutoPaste 菜单栏图标，会显示当前权限状态：

- ✅ `Accessibility: Granted` — 权限已授予，可正常使用
- ❌ `Accessibility: Not Granted` — 权限未授予，需要配置

## 授权步骤

1. 打开 **系统设置** → **隐私与安全性** → **辅助功能**
2. 点击 **+** 按钮
3. 导航到 `/Applications/AutoPaste.app` 并添加
4. 确保 AutoPaste 旁边的开关**打开**
5. **完全退出** AutoPaste（菜单栏点 Quit）
6. 重新打开 AutoPaste

## 重新编译后权限失效

> [!IMPORTANT]
> 每次重新编译应用后，签名会改变，系统会将其视为"新"应用，之前的权限授权会失效。

**解决方法：**

1. 在辅助功能列表中**删除** AutoPaste（选中后点 `-`）
2. 重新添加 `/Applications/AutoPaste.app`
3. 确保开关打开
4. 重启 AutoPaste

## 快速修复

点击菜单中的 `❌ Accessibility: Not Granted (Click to Fix)` 会：

1. 弹出系统权限请求对话框
2. 自动打开系统设置的辅助功能页面
