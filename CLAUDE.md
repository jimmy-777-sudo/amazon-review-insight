# GitHub 应用开发 — AI 全自动流水线项目

## 项目目标

搭建一套 GitHub Actions + AI Agent 的全自动开发流水线：用户在 GitHub Issue 中提需求 → AI 自动写代码、写测试、修复问题、创建 PR → 用户审核合并。

**核心理念**：你不需要写代码，你只需要提清楚需求。

## 技术栈

| 组件 | 选型 | 原因 |
|------|------|------|
| AI 引擎 | OpenCode CLI | 开源、支持 75+ 模型提供商、支持 DeepSeek、有 MCP |
| AI 模型 | DeepSeek API | 国产、便宜、OpenAI 兼容 |
| CI/CD 平台 | GitHub Actions | 免费、与仓库深度绑定 |
| 触发方式 | Issue 标签 `ai-build` | 直观可控 |
| 代码审查 | PR 自动触发 | 每次 PR 自动审核 |

## 流水线架构

```
用户创建 Issue + 打 ai-build 标签
  │
  ▼
GitHub Actions 触发
  │
  ├─ 安装 OpenCode CLI
  ├─ 配置 DeepSeek 连接
  ├─ 读取 Issue 需求
  ├─ 实现代码
  ├─ 编写测试
  ├─ 运行测试 ──→ 失败则自动修复（最多 3 轮）
  ├─ 创建 feature 分支
  └─ 提交 Pull Request（中文描述改动内容）
```

## 文件结构

```
amazon-review-insight/
├── .github/workflows/
│   ├── ai-dev.yml          # 自动开发流水线（Issue 打标签触发）
│   └── review.yml          # 自动代码审查（PR 触发）
├── .gitignore              # 防止泄露 API Key、缓存等
├── README.md               # 项目说明
└── CLAUDE.md               # 本文件 - AI 协作记忆
```

## 日常操作流程

1. 打开 https://github.com/jimmy-777-sudo/amazon-review-insight/issues
2. 创建 New Issue，用中文描述需求
3. 右侧 Labels → 打上 `ai-build`
4. 等 2-5 分钟，PR 自动出现
5. Review 代码 → Merge 或评论要求修改

## 新项目复制方法

```bash
# 复制流水线模板
cp -r amazon-review-insight/.github 新项目目录/

# 每个新仓库需要：
# 1. 创建 GitHub 仓库
# 2. Settings → Secrets → Actions → 添加 DEEPSEEK_API_KEY
# 3. 修改 README.md 为项目内容
```

## 已知限制

- DeepSeek 在复杂多文件操作上不如 Claude Opus
- 网络问题（GitHub 连接可能不稳定，需要重试）
- 每次 Issue 改动不宜过大，小功能或 bug 修复效果最好
- 涉及新依赖安装的场景可能需要手动调整

## 后续优化方向

- 支持多模型切换（DeepSeek / Claude / Qwen 按需选择）
- 添加 e2e 测试自动运行
- Issue 模板标准化
- 自动生成 CHANGELOG
