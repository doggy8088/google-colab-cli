#!/usr/bin/env python3
"""Build a static HTML site from the zh-tw Markdown docs."""
import pathlib
import re
import shutil

import markdown

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "_site"

PAGES = [
    ("README.md", "index.html", "Google Colab CLI 繁體中文文件"),
    ("docs/01_session_management.md", "docs/01_session_management.html", "工作階段管理"),
    ("docs/02_execution_and_interactive.md", "docs/02_execution_and_interactive.html", "執行與互動"),
    ("docs/03_file_management.md", "docs/03_file_management.html", "檔案管理"),
    ("docs/04_automation_and_utility.md", "docs/04_automation_and_utility.html", "自動化與工具"),
    ("docs/05_run_command.md", "docs/05_run_command.html", "colab run 指令"),
    ("docs/06_ssh_access.md", "docs/06_ssh_access.html", "SSH 存取"),
    ("docs/demos.md", "docs/demos.html", "示範導覽"),
    ("docs/public_api_migration_plan.md", "docs/public_api_migration_plan.html", "Public API 遷移計畫"),
    ("CHANGELOG.md", "CHANGELOG.html", "變更記錄"),
    ("CONTRIBUTING.md", "CONTRIBUTING.html", "參與貢獻"),
    ("integration/README.md", "integration/README.html", "整合測試"),
    ("skills/colab-operator/SKILL.md", "skills/colab-operator/SKILL.html", "Colab Operator 技能"),
]

NAV = [
    ("index.html", "首頁"),
    ("docs/01_session_management.html", "工作階段管理"),
    ("docs/02_execution_and_interactive.html", "執行與互動"),
    ("docs/03_file_management.html", "檔案管理"),
    ("docs/04_automation_and_utility.html", "自動化與工具"),
    ("docs/05_run_command.html", "colab run"),
    ("docs/06_ssh_access.html", "SSH 存取"),
    ("docs/demos.html", "示範導覽"),
    ("CHANGELOG.html", "變更記錄"),
]

CSS = """
body{font-family:system-ui,-apple-system,"Segoe UI",sans-serif;max-width:920px;margin:0 auto;padding:24px;line-height:1.7;color:#1f2328}
nav{display:flex;flex-wrap:wrap;gap:12px;padding:12px 0;border-bottom:1px solid #d0d7de;margin-bottom:24px}
nav a{color:#0969da;text-decoration:none} nav a:hover{text-decoration:underline}
code{background:#f6f8fa;padding:2px 5px;border-radius:4px;font-size:.9em}
pre{background:#f6f8fa;padding:16px;border-radius:8px;overflow-x:auto} pre code{background:none;padding:0}
table{border-collapse:collapse} th,td{border:1px solid #d0d7de;padding:6px 12px}
a{color:#0969da} footer{margin-top:48px;padding-top:16px;border-top:1px solid #d0d7de;color:#57606a;font-size:.9em}
img,video{max-width:100%}
"""

TEMPLATE = """<!DOCTYPE html>
<html lang="zh-Hant-TW">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}｜Google Colab CLI 繁體中文文件</title>
<style>{css}</style>
</head>
<body>
<nav>{nav}</nav>
<main>
{body}
</main>
<footer>繁體中文翻譯：<a href="https://www.facebook.com/will.fans/">Will 保哥的技術交流中心</a>｜上游專案：<a href="https://github.com/googlecolab/google-colab-cli">googlecolab/google-colab-cli</a></footer>
</body>
</html>
"""


def nav_html(prefix):
    return "".join(f'<a href="{prefix}{href}">{label}</a>' for href, label in NAV)


def main():
    if OUT.exists():
        shutil.rmtree(OUT)
    OUT.mkdir(parents=True)
    md = markdown.Markdown(extensions=["fenced_code", "tables", "toc", "extra"])
    for src, dst, title in PAGES:
        text = (ROOT / src).read_text(encoding="utf-8")
        # Rewrite internal .md links to .html
        text = re.sub(r"\]\(([^)]+?)\.md(#[^)]*)?\)", r"](\1.html\2)", text)
        md.reset()
        body = md.convert(text)
        depth = dst.count("/")
        prefix = "../" * depth
        html = TEMPLATE.format(title=title, css=CSS, nav=nav_html(prefix), body=body)
        target = OUT / dst
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(html, encoding="utf-8")
        print("built", dst)
    # Copy docs assets (images / videos)
    docs_dir = ROOT / "docs"
    for asset in list(docs_dir.glob("*.png")) + list(docs_dir.glob("*.webm")) + list(docs_dir.glob("*.jpg")):
        shutil.copy(asset, OUT / "docs" / asset.name)
        print("copied", asset.name)


if __name__ == "__main__":
    main()
