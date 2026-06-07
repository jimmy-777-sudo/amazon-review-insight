# GitHub 应用开发 — AI 全自动流水线项目

## 项目目标

搭建一套 GitHub Actions + AI Agent 的全自动开发流水线：用户在 GitHub Issue 中提需求 → AI 自动写代码、写测试、创建 PR → 用户审核合并。

**核心理念**：你不需要写代码，你只需要提清楚需求。

## 技术栈

| 组件 | 选型 | 原因 |
|------|------|------|
| AI 引擎 | 自研 Python Agent (agent.py) | 直接调用 DeepSeek API，无 CLI 兼容问题 |
| AI 模型 | DeepSeek API (deepseek-chat) | 国产、便宜、OpenAI 兼容协议 |
| CI/CD | GitHub Actions | 免费、与仓库深度绑定 |
| 触发方式 | Issue 标签 `ai-build` | 打标签即触发，直观可控 |
| 代码审查 | review.yml (待实现) | PR 自动触发 AI 审查 |

## 流水线架构

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
  │   ├─ 创建/修改文件
  │   ├─ 尝试运行测试
  │   └─ git commit + push + gh pr create
  └─ PR 出现 → 人工 Review → Merge
```

## 文件结构

```
amazon-review-insight/
├── .github/workflows/
│   ├── ai-dev.yml          # 自动开发流水线
│   └── review.yml          # 自动代码审查 (WIP)
├── agent.py                # AI Agent 核心脚本
├── .gitignore
├── README.md
└── CLAUDE.md               # 项目知识库
```

## 日常操作流程

1. 打开 Issues: https://github.com/jimmy-777-sudo/amazon-review-insight/issues
2. 创建 New Issue，用中文描述需求
3. 右侧 Labels → 打上 `ai-build`
4. 等 2-5 分钟，PR 自动出现
5. Review 代码 → Merge 或评论要求修改

## 新项目复制方法

```bash
cp agent.py .github/workflows/ai-dev.yml .gitignore 新项目/
# 每个新仓库需要：
# Settings → Secrets → Actions → 添加 DEEPSEEK_API_KEY
```

## 调试

查看流水线日志：
```bash
gh run list --limit 5
gh run view <run-id> --log-failed
```

## 已知限制

- DeepSeek 复杂多文件操作不如 Claude Opus
- Agent 目前一轮对话，不支持自动修复测试失败
- 网络不稳定时需重试 push
- JSON 解析依赖 AI 输出格式规范

## 后续优化

- 多轮对话：测试失败自动修复
- 支持多模型切换
- Issue 模板标准化
- 自动更新 CHANGELOG
