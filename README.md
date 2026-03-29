# 智能计薪系统 - Android App

基于 Python + Kivy 构建的 Android 应用，复刻原 Flask Web 版计薪系统功能。

## 功能特性

- ✅ 用户注册/登录
- ✅ 打卡签到（支持多时段）
- ✅ 工时录入（正常/加班/周末/节假日）
- ✅ 月薪自动计算
- ✅ 日历视图
- ✅ 工资明细统计

## 自动构建 APK

本项目配置了 GitHub Actions，自动构建 Android APK：

### 步骤 1：创建 GitHub 仓库

```bash
# 在 GitHub 上创建新仓库 (salary-app)
# 然后克隆到本地：
git clone https://github.com/你的用户名/salary-app.git
cd salary-app
```

### 步骤 2：复制项目文件

将本目录下的所有文件复制到克隆的仓库中：

```bash
# 复制以下文件到 Git 仓库根目录：
# - main.py
# - buildozer.spec
# - .github/workflows/build.yml
```

### 步骤 3：推送代码

```bash
git add .
git commit -m "Initial commit: 智能计薪系统"
git push -u origin main
```

### 步骤 4：获取 APK

1. 访问你的 GitHub 仓库
2. 点击 **Actions** 标签
3. 查看 **Build Android APK** workflow
4. 等待构建完成（约 15-20 分钟）
5. 点击构建产物下载 `salary-app-apk` 文件

## 本地构建（可选）

如果你想本地构建：

### 环境要求
- Ubuntu 20.04+ 或 macOS
- Python 3.8-3.10
- JDK 8+
- Android SDK / NDK

### 构建命令

```bash
# 安装依赖
pip install buildozer cython

# 安装 Android SDK（如果没有）
# 设置环境变量
export ANDROID_HOME=/path/to/android-sdk
export ANDROIDNDK=/path/to/android-ndk

# 构建
buildozer android debug
```

APK 输出位置：`.buildozer/android/platform/build-*/dists/salaryapp/bin/`

## 应用截图

（待添加）

## 技术栈

- **前端**: Kivy (Python)
- **后端**: SQLite
- **构建工具**: Buildozer
- **CI/CD**: GitHub Actions
