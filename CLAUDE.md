# GitHub 应用开发 — AI 全自动流水线项目

## 你是谁，在做什么

你是跨境电商卖家 + AI 重度用户，搭建了一套 GitHub Actions + DeepSeek API 的全自动开发流水线。

**核心理念**：你不需要写代码，只需要在 GitHub Issue 里用中文描述需求，打上 `ai-build` 标签，AI 自动写代码、写测试、提交 PR。

## 当前项目状态

| 项目 | 状态 |
|------|------|
| 流水线 | ✅ 已跑通，Issue #1 → PR #2 成功 |
| 仓库 | https://github.com/jimmy-777-sudo/amazon-review-insight |
| 本地路径 | D:\GitHub应用开发\amazon-review-insight |
| AI 模型 | DeepSeek API (deepseek-chat) |
| Secret | `DEEPSEEK_API_KEY` 已配置 |

## 技术架构

```
用户创建 Issue + 打 ai-build 标签
  │
  ▼
GitHub Actions 触发 (ai-dev.yml)
  │
  ├─ Checkout 代码
  ├─ 运行 python agent.py
  │   ├─ 读取 Issue 内容 (GitHub API)
  │   ├─ 读取仓库文件结构
  │   ├─ 调用 DeepSeek API 分析需求
  │   ├─ 解析 AI 返回的 JSON (文件操作列表)
  │   ├─ 创建/修改/删除文件
  │   ├─ 尝试运行测试
  │   └─ git commit + push -f + gh pr create
  └─ PR 出现在 GitHub → 人工 Review → Merge
```

## 开发能力边界

| 能做的 | 需额外步骤的 |
|--------|------------|
| Python 脚本/自动化 | iOS APP（需 Mac + Xcode 本地编译）|
| Streamlit/Gradio Web 应用 | Windows EXE（需本地 PyInstaller 打包）|
| HTML/CSS/JS 前端 | Android APK（需 Android SDK 本地编译）|
| FastAPI 后端 | 需要 GPU 的程序 |
| Electron 桌面应用 | |
| Chrome 浏览器插件 | |
| Docker 镜像 | |

## 客户交付方式（三级递进）

| Level | 方式 | 客户操作 | 适用场景 |
|-------|------|---------|---------|
| 1 | CLI 命令行 | `python app.py` | 你自己用 |
| 2 | Streamlit Web | 浏览器打开网址 | 发给客户试用 |
| 3 | 独立应用 | 双击 EXE/APP | 商业化产品 |

**推荐起步方式**：AI 生成 Streamlit 界面 → 部署到 Streamlit Cloud（免费）→ 客户打开链接即用。

## 这套流程可以无限复用

需求描述 → Issue → 打标签 → AI 写代码 → PR → Merge。
换项目只要改 README 和 agent.py 里的 prompt。

## 后续待办

- [ ] Review 并 Merge PR #2（第一个 AI 生成的功能）
- [ ] 配置 review.yml 自动代码审查
- [ ] 创建 Issue 模板（.github/ISSUE_TEMPLATE/）
- [ ] 写一篇自媒体文章：跨境电商卖家如何用 AI 自动化开发工具
