"""
AI Agent — 读取 GitHub Issue，调用 DeepSeek API 自动实现代码并提交 PR。
在 GitHub Actions 中运行。
"""
import os
import json
import subprocess
import sys
import re
from urllib.request import Request, urlopen
from urllib.error import HTTPError

# === 配置 ===
DEEPSEEK_API_KEY = os.environ["DEEPSEEK_API_KEY"]
GITHUB_TOKEN = os.environ["GITHUB_TOKEN"]
GITHUB_REPOSITORY = os.environ["GITHUB_REPOSITORY"]
GITHUB_EVENT_PATH = os.environ["GITHUB_EVENT_PATH"]

DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"


def read_github_event():
    """读取 GitHub Actions 事件数据"""
    with open(GITHUB_EVENT_PATH, "r", encoding="utf-8") as f:
        return json.load(f)


def read_issue(issue_number):
    """通过 GitHub API 读取 Issue 内容"""
    url = f"https://api.github.com/repos/{GITHUB_REPOSITORY}/issues/{issue_number}"
    req = Request(url, headers={
        "Authorization": f"Bearer {GITHUB_TOKEN}",
        "Accept": "application/vnd.github+json",
        "User-Agent": "AI-Agent",
    })
    with urlopen(req) as resp:
        data = json.loads(resp.read().decode())
    return data["title"], data["body"]


def list_files():
    """列出仓库所有文件"""
    result = subprocess.run(
        ["git", "ls-files"], capture_output=True, text=True
    )
    return result.stdout.strip().split("\n")


def read_file(path, max_lines=200):
    """读取仓库中的文件"""
    try:
        with open(path, "r", encoding="utf-8") as f:
            lines = f.readlines()
        if len(lines) > max_lines:
            return "".join(lines[:max_lines]) + f"\n... (共 {len(lines)} 行，只显示前 {max_lines} 行)"
        return "".join(lines)
    except FileNotFoundError:
        return f"[文件不存在] {path}"
    except Exception as e:
        return f"[读取失败] {path}: {e}"


def call_deepseek(messages, max_tokens=8000):
    """调用 DeepSeek API"""
    payload = json.dumps({
        "model": "deepseek-chat",
        "messages": messages,
        "max_tokens": max_tokens,
        "temperature": 0.3,
    }).encode("utf-8")

    req = Request(DEEPSEEK_URL, data=payload, headers={
        "Authorization": f"Bearer {DEEPSEEK_API_KEY}",
        "Content-Type": "application/json",
    })
    with urlopen(req) as resp:
        result = json.loads(resp.read().decode())
    return result["choices"][0]["message"]["content"]


def run_cmd(cmd, cwd=".", timeout=120):
    """运行命令并返回结果"""
    result = subprocess.run(
        cmd, shell=True, capture_output=True, text=True, cwd=cwd, timeout=timeout
    )
    return result.returncode, result.stdout, result.stderr


def create_branch_pr(branch_name, title, body):
    """创建分支并提交 PR"""
    # 配置 git
    run_cmd('git config user.name "AI Agent"')
    run_cmd('git config user.email "ai-agent@github.com"')

    # 删除可能存在的同名远程分支
    run_cmd(f"git push origin --delete {branch_name} 2>/dev/null || true")

    # 创建新分支（从 main 开始）
    run_cmd(f"git checkout -B {branch_name}")

    # 添加所有改动
    run_cmd("git add -A")

    # 提交
    rc, out, err = run_cmd(f'git commit -m "{title}"')
    if rc != 0 and "nothing to commit" not in err:
        print(f"commit failed: {err}")
        return None

    # 强制推送（覆盖远程旧分支）
    rc, out, err = run_cmd(f"git push -f origin {branch_name}")
    if rc != 0:
        print(f"push failed: {err}")
        return None

    # 创建 PR (用 gh CLI)
    pr_body = body.replace('"', '\\"').replace('\n', '\\n')[:60000]
    rc, out, err = run_cmd(
        f'gh pr create --title "{title}" --body "{pr_body}" --base main --head {branch_name}'
    )
    if rc != 0:
        print(f"PR creation failed: {err}")
        return None

    # 提取 PR URL
    match = re.search(r'https://github\.com/[^\s]+/pull/\d+', out)
    return match.group(0) if match else out


def main():
    print("=== AI Agent 启动 ===")

    # 1. 读取事件
    event = read_github_event()
    issue_number = event["issue"]["number"]
    print(f"Issue: #{issue_number}")

    # 2. 读取 Issue 内容
    title, body = read_issue(issue_number)
    print(f"标题: {title}")

    # 3. 读取仓库结构
    files = list_files()
    repo_info = "仓库文件:\n" + "\n".join(files)
    print(repo_info)

    # 4. 读取 README 了解项目
    readme = read_file("README.md")

    # 5. 构建 Prompt 给 DeepSeek
    system_prompt = """你是一个全栈开发 AI 助手，在 GitHub Actions 中运行。
你的任务是读取 GitHub Issue 的需求，然后生成完整的代码实现。

你必须输出一个 JSON 数组，每个元素描述一个文件的操作：
[
  {"action": "create", "path": "文件路径", "content": "文件完整内容"},
  {"action": "delete", "path": "要删除的文件路径"}
]

注意：
- 代码要完整可运行，不要省略
- 包含适当的错误处理
- 遵循项目已有技术栈
- 如果是 Python 项目，记得更新 requirements.txt
- content 中的双引号需要转义为 \\"
- 只输出 JSON，不要输出其他内容"""

    user_prompt = f"""## Issue 信息
标题: {title}
内容: {body}

## 当前项目结构
{repo_info}

## README.md
{readme}

请根据 Issue 需求，输出需要创建/修改的文件列表（JSON 格式）。
每个 create 操作要包含文件的完整内容。"""

    print("\n=== 调用 DeepSeek API ===")
    response = call_deepseek([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ])
    print(f"响应 ({len(response)} 字符):\n{response[:500]}...\n")

    # 6. 解析 AI 返回的 JSON
    # 提取 JSON 部分（可能被 markdown 代码块包裹）
    json_match = re.search(r'```(?:json)?\s*([\s\S]*?)```', response)
    if json_match:
        json_str = json_match.group(1)
    else:
        json_str = response

    try:
        file_ops = json.loads(json_str)
    except json.JSONDecodeError as e:
        print(f"JSON 解析失败: {e}")
        print(f"原始响应:\n{response}")
        sys.exit(1)

    if not isinstance(file_ops, list):
        print("AI 返回的不是数组格式，尝试修复...")
        # 尝试找到包含文件操作的任何 list
        sys.exit(1)

    # 7. 执行文件操作
    print(f"\n=== 执行 {len(file_ops)} 个文件操作 ===")
    for op in file_ops:
        action = op.get("action")
        path = op.get("path", "")
        content = op.get("content", "")

        if action == "create":
            os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(content)
            print(f"✓ 创建: {path} ({len(content)} 字符)")
        elif action == "delete":
            if os.path.exists(path):
                os.remove(path)
                print(f"✓ 删除: {path}")

    # 8. 尝试运行测试
    print("\n=== 测试 ===")
    test_files = [f for f in files if f.startswith("test_") or f.startswith("tests/")]
    for test_file in test_files:
        rc, out, err = run_cmd(f"python -m pytest {test_file} -v")
        print(out[-500:])
        if rc != 0 and err:
            print(f"⚠ 测试失败:\n{err[-500:]}")

    # 9. 创建分支和 PR
    branch_name = f"feature/{issue_number}-auto"
    pr_title = f"[#{issue_number}] {title}"
    pr_body = f"""## 变更说明
根据 Issue #{issue_number} 自动实现。

## Issue 需求
{body[:2000]}

## 改动文件
{chr(10).join(f'- {op["path"]}' for op in file_ops)}

---
🤖 由 AI Agent 自动生成 | 请人工审核后合并
"""

    print(f"\n=== 创建 PR ===")
    pr_url = create_branch_pr(branch_name, pr_title, pr_body)

    if pr_url:
        print(f"\n✅ PR 已创建: {pr_url}")
    else:
        print("\n❌ PR 创建失败")
        sys.exit(1)


if __name__ == "__main__":
    main()
