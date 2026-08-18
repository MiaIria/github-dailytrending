#!/usr/bin/env python
"""根据 fetch_trending.py 的产物 JSON（已含 Claude 填的中文拆解字段），
生成单页合并 HTML：当日所有仓库以完整详情卡片形式堆叠在一份 index.html 中，
按 rank（热度）从高到低依次排列。

样式基线与旧版单仓库 HTML 一致：C:\\Users\\26250\\Desktop\\github-style.html
（GitHub Primer 蓝 + 暗色模式切换 + 手机宽度 420px）。

输出结构（相对 --project-root）：
  github-trending-results/<YYYY-MM-DD>/
      index.html    当日所有仓库的单页 HTML 总览（按 rank 排序）
      summary.md    （由 Claude 写，不由本脚本生成）

依赖：纯 stdlib。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from datetime import datetime
from html import escape
from pathlib import Path
from typing import Any


# ----------------------- 工具 -----------------------

ILLEGAL_FILE_CHARS = re.compile(r"[^A-Za-z0-9_.-]")


def safe_name(full_name: str) -> str:
    """owner/repo -> owner--repo，剔除非法字符（合并模式下仅保留作 util）。"""
    return ILLEGAL_FILE_CHARS.sub("-", full_name.replace("/", "--"))


def e(s: Any) -> str:
    """XSS 防注入的 html.escape。None/空字符串返回 ''。"""
    if s is None:
        return ""
    return escape(str(s), quote=True)


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(content, encoding="utf-8")
    os.replace(tmp, path)


def normalize_color(color: str) -> str:
    """GitHub 的语言色可能是 #3572A5 也可能是简写，统一补 # 与大写。"""
    color = (color or "").strip()
    if not color:
        return "#8b949e"  # GitHub 默认灰
    if not color.startswith("#"):
        color = "#" + color
    return color


def sort_by_rank(repos: list[dict]) -> list[dict]:
    """按 rank 升序排列（rank 1 在最前 = 热度最高在最前）。"""
    return sorted(repos, key=lambda r: r.get("rank", 0) or 0)


# ----------------------- HTML 片段 -----------------------

THEME_CSS = """\
:root {
  --bg: #ffffff; --bg2: #f6f8fa; --bg3: #f3f4f6;
  --border: #d0d7de; --text: #1f2328; --text2: #656d76;
  --link: #0969da; --accent: #0969da; --star: #e3b341;
  --btn-bg: #f6f8fa; --btn-hover: #eaeef2; --card: #ffffff;
}
[data-color-mode="dark"] {
  --bg: #0d1117; --bg2: #161b22; --bg3: #21262d;
  --border: #30363d; --text: #e6edf3; --text2: #8b949e;
  --link: #58a6ff; --accent: #58a6ff;
  --btn-bg: #21262d; --btn-hover: #30363d; --card: #161b22;
}
* { margin: 0; padding: 0; box-sizing: border-box; }
body {
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", "Noto Sans",
               Helvetica, Arial, sans-serif;
  background: #e8eaed; color: var(--text); line-height: 1.5;
  display: flex; justify-content: center; min-height: 100vh;
  -webkit-tap-highlight-color: transparent;
  -webkit-font-smoothing: antialiased;
}
[data-color-mode="dark"] body { background: #010409; }
.phone {
  width: 100%; max-width: 420px; background: var(--bg);
  min-height: 100vh; position: relative;
  box-shadow: 0 0 40px rgba(0,0,0,0.12);
}
.header {
  background: var(--bg2); border-bottom: 1px solid var(--border);
  padding: 10px 14px; position: sticky; top: 0; z-index: 100;
  display: flex; align-items: center; justify-content: space-between;
}
.header-title { font-size: 15px; font-weight: 600; display: flex; align-items: center; gap: 5px; }
.header-title svg { width: 18px; height: 18px; fill: var(--text); }
.header-back {
  font-size: 12px; color: var(--link); text-decoration: none;
  display: inline-flex; align-items: center; gap: 2px;
}
.header-back:active { opacity: 0.6; }
.header-date { font-size: 11px; color: var(--text2); font-weight: 400; }
.theme-btn {
  background: var(--btn-bg); border: 1px solid var(--border);
  color: var(--text); padding: 4px 10px; border-radius: 5px;
  cursor: pointer; font-size: 11px; white-space: nowrap;
}
.container { padding: 10px 10px 20px; }
.subtitle { font-size: 12px; color: var(--text2); margin-bottom: 10px; padding: 0 3px; }
.card {
  border: 1px solid var(--border); border-radius: 7px;
  background: var(--card); padding: 14px; margin-bottom: 10px;
}
.card:active { background: var(--bg3); }
.card-head { display: flex; align-items: flex-start; gap: 7px; margin-bottom: 6px; }
.card-icon { width: 16px; height: 16px; flex-shrink: 0; margin-top: 2px; color: var(--text2); }
.card-head-r { flex: 1; min-width: 0; }
.card-name {
  font-size: 15px; font-weight: 600; color: var(--link); text-decoration: none;
  word-break: break-all; display: block; line-height: 1.25;
}
.card-rank {
  display: inline-block; font-size: 10px; font-weight: 600; color: var(--text2);
  background: var(--bg3); padding: 1px 7px; border-radius: 9px; margin-top: 3px;
}
.card-desc { font-size: 12px; color: var(--text2); margin-bottom: 8px; line-height: 1.5; }
.card-meta { display: flex; flex-wrap: wrap; gap: 4px 10px; font-size: 11px; color: var(--text2); margin-bottom: 10px; }
.card-meta span { display: flex; align-items: center; gap: 2px; }
.lang-dot { width: 9px; height: 9px; border-radius: 50%; flex-shrink: 0; }
.star-clr { color: var(--star); }
.divider { border: none; border-top: 1px solid var(--border); margin: 8px 0; }
.sec-title { font-size: 11px; font-weight: 600; color: var(--text); margin-bottom: 6px; letter-spacing: 0.3px; }
.sec-list { display: flex; flex-direction: column; gap: 4px; }
.sec-row { font-size: 12px; display: flex; gap: 5px; line-height: 1.4; }
.sec-label { color: var(--text2); font-weight: 500; white-space: nowrap; min-width: 48px; flex-shrink: 0; }
.sec-val { color: var(--text); }
.oneliner {
  background: var(--bg3); border-left: 3px solid var(--accent);
  padding: 8px 10px; margin-top: 8px; border-radius: 0 4px 4px 0;
  font-size: 12px; color: var(--text); font-weight: 500; line-height: 1.4;
}
.card-link { font-size: 10px; color: var(--link); margin-top: 8px; display: block; word-break: break-all; }
.footer { text-align: center; padding: 16px; font-size: 10px; color: var(--text2); border-top: 1px solid var(--border); }
"""

THEME_JS = """\
function toggleTheme() {
  const html = document.documentElement;
  const btn = document.querySelector('.theme-btn');
  if (html.getAttribute('data-color-mode') === 'light') {
    html.setAttribute('data-color-mode', 'dark');
    btn.textContent = '☀️ 浅色';
  } else {
    html.setAttribute('data-color-mode', 'light');
    btn.textContent = '🌙 暗色';
  }
}
"""

SVG_REPO = (
    '<svg viewBox="0 0 16 16" width="16" height="16" fill="currentColor" '
    'fill-rule="evenodd"><path d="M2 2.5A2.5 2.5 0 0 1 4.5 0h8.75a.75.75 0 0 1 '
    '.75.75v12.5a.75.75 0 0 1-.75.75h-2.5a.75.75 0 0 1 0-1.5h1.75v-2h-8a1 '
    '1 0 0 0-.714 1.7.75.75 0 1 1-1.072 1.05A2.495 2.495 0 0 1 2 11.5v-9zm'
    '10.5-1V9h-8c-.356 0-.694.074-1 .208V2.5a1 1 0 0 1 1-1h8zM5 12.25v3.25a.25.25 '
    '0 0 0 .4.2l1.45-1.087a.25.25 0 0 1 .3 0L8.6 15.7a.25.25 0 0 0 .4-.2v-3.25a.25.25 '
    '0 0 0-.25-.25h-3.5a.25.25 0 0 0-.25.25z"/></svg>'
)

SVG_OCTOCAT = (
    '<svg viewBox="0 0 16 16"><path d="M8 0c4.42 0 8 3.58 8 8a8.013 8.013 0 0 '
    '1-5.45 7.59c-.4.08-.55-.17-.55-.38 0-.27.01-1.13.01-2.2 0-.75-.25-1.23'
    '-.54-1.48 1.78-.2 3.65-.88 3.65-3.95 0-.88-.31-1.59-.82-2.15.08-.2.36-1'
    '.02-.08-2.12 0 0-.67-.22-2.2.82-.64-.18-1.32-.27-2-.27-.68 0-1.36.09-2'
    '.27-1.53-1.03-2.2-.82-2.2-.82-.44 1.1-.16 1.92-.08 2.12-.51.56-.82 1.28'
    '-.82 2.15 0 3.06 1.86 3.75 3.64 3.95-.23.2-.44.55-.51 1.07-.46.21-1.61'
    '.55-2.33-.66-.15-.24-.6-.83-1.23-.82-.67.01-.27.38.01.53.34.19.73.9.82 '
    '1.13.16.45.68 1.31 2.69.94 0 .67.01 1.3.01 1.49 0 .21-.15.45-.55.38A7'
    '.995 7.995 0 0 1 0 8c0-4.42 3.58-8 8-8Z"/></svg>'
)


# ----------------------- 单仓库卡片 HTML -----------------------

def render_repo_card(repo: dict) -> str:
    """渲染单个仓库的完整详情卡片（与旧版单仓库 HTML 中的 article 一致）。

    返回的字符串是一个独立的 <article class="card">…</article> 块，
    不含 header / container / script 等外层结构。"""
    lang = e(repo.get("language") or "")
    lang_color = normalize_color(repo.get("language_color") or "")
    rank = repo.get("rank", 0)
    name = e(repo.get("full_name") or "")
    url = e(repo.get("url") or "#")
    desc = e(repo.get("description") or "暂无描述")
    stars_total = e(repo.get("stars_total") or "—")
    forks = e(repo.get("forks") or "未提供")
    stars_today = e(repo.get("stars_today") or "—")

    func = e(repo.get("functionality") or "—")
    prob = e(repo.get("problem_solved") or "—")
    users = e(repo.get("target_users") or "—")
    areas = e(repo.get("application_areas") or "—")
    oneliner = e(repo.get("one_sentence_summary") or "—")

    lang_block = (
        f'<span><span class="lang-dot" style="background:{e(lang_color)}"></span> {lang}</span>'
        if lang else ''
    )

    return f"""<article class="card">
      <div class="card-head">
        {SVG_REPO}
        <div class="card-head-r">
          <a class="card-name" href="{url}" target="_blank" rel="noopener">{name}</a>
          <span class="card-rank">🔥 #{rank}</span>
        </div>
      </div>
      <p class="card-desc">{desc}</p>
      <div class="card-meta">
        {lang_block}
        <span>⭐ {stars_total}</span>
        <span><span class="star-clr">★</span> {stars_today}</span>
        <span>🔀 {forks}</span>
      </div>

      <hr class="divider">
      <div class="sec-title">📊 项目拆解</div>
      <div class="sec-list">
        <div class="sec-row"><span class="sec-label">🎯 功能</span><span class="sec-val">{func}</span></div>
        <div class="sec-row"><span class="sec-label">🏷️ 领域</span><span class="sec-val">{areas}</span></div>
        <div class="sec-row"><span class="sec-label">👥 用户</span><span class="sec-val">{users}</span></div>
        <div class="sec-row"><span class="sec-label">❓ 解决</span><span class="sec-val">{prob}</span></div>
      </div>
      <div class="oneliner">💬 {oneliner}</div>
      <a class="card-link" href="{url}" target="_blank" rel="noopener">🔗 {url}</a>
    </article>"""


# ----------------------- 单页合并 HTML -----------------------

def render_index_html(repos: list[dict], date: str) -> str:
    """渲染当日所有仓库的单页 HTML 总览。

    仓库按 rank 升序排列（即热度从高到低），每张卡片为完整详情版。"""
    try:
        dt = datetime.strptime(date, "%Y-%m-%d")
        date_cn = f"{dt.month}月{dt.day}日"
    except ValueError:
        date_cn = date

    ordered = sort_by_rank(repos)
    total = len(ordered)
    cards_html = "\n".join(render_repo_card(r) for r in ordered)

    return f"""<!DOCTYPE html>
<html lang="zh-CN" data-color-mode="light">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>GitHub 今日热门 · {date}</title>
<style>{THEME_CSS}</style>
</head>
<body>
<div class="phone">
  <div class="header">
    <div class="header-title">
      {SVG_OCTOCAT}
      Trending
      <span class="header-date">· {date_cn}</span>
    </div>
    <button class="theme-btn" onclick="toggleTheme()">🌙 暗色</button>
  </div>
  <div class="container">
    <p class="subtitle">今日热门 · {total} 个仓库</p>
{cards_html}
  </div>
  <div class="footer">GitHub Daily Trending · {date}</div>
</div>
<script>{THEME_JS}</script>
</body>
</html>
"""


# ----------------------- Main -----------------------

def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--input", required=True, help="fetch_trending.py 输出的 JSON")
    p.add_argument("--project-root", default=".", help="项目根目录，默认当前")
    p.add_argument(
        "--theme", default="github-blue", help="主题名（预留，目前只支持 github-blue）"
    )
    args = p.parse_args()

    in_path = Path(args.input)
    if not in_path.exists():
        print(f"[ERR] 输入文件不存在：{in_path}", file=sys.stderr)
        return 1

    try:
        data = json.loads(in_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as e:
        print(f"[ERR] JSON 解析失败：{e}", file=sys.stderr)
        return 2

    repos = data.get("repos") or []
    if not repos:
        print("[ERR] JSON 中 repos 为空", file=sys.stderr)
        return 3

    date = data.get("date") or datetime.now().strftime("%Y-%m-%d")
    results_dir = Path(args.project_root) / "github-trending-results" / date
    results_dir.mkdir(parents=True, exist_ok=True)

    # 单页合并 HTML（按 rank 排序的全量卡片）
    atomic_write(results_dir / "index.html", render_index_html(repos, date))

    print(
        f"[OK] {len(repos)} 个仓库合并到单页 HTML → {results_dir / 'index.html'}  "
        f"(theme={args.theme})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())