#!/usr/bin/env python
"""抓取 GitHub Trending 全语言/全开发者今日热门仓库，并并发下载每个仓库的 README。

输出 JSON 符合 references/data-contract.md：
  {
    "date": "2026-08-18",
    "since": "daily",
    "language": "",
    "fetched_at": "2026-08-18T08:30:00Z",
    "repos": [ {rank, full_name, url, description, language, language_color,
                 stars_total, forks, stars_today, readme, ...}, ... ]
  }

抓取规范见 references/trending-fetch-spec.md。Python 3.10+。
依赖：requests（已装）。html.parser / re / json / argparse / datetime / concurrent.futures / pathlib 全是 stdlib。
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Optional
from urllib.parse import urljoin

import requests

GITHUB_TRENDING_BASE = "https://github.com/trending"
RAW_README_URL = "https://raw.githubusercontent.com/{owner}/{repo}/HEAD/README.md"
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)
README_MAX_CHARS = 3000
README_WORKERS = 8
HTTP_TIMEOUT = 10  # seconds
README_THROTTLE = 0.1  # seconds between requests


# ----------------------- HTMLParser 子类 -----------------------

class _TrendingParser(HTMLParser):
    """状态机式解析 GitHub Trending 页面，遍历每个 <article class="Box-row">。

    每进入一个 Box-row 开始累积一个仓库记录；遇到 </article> 提交。"""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.records: list[dict] = []
        self._cur: Optional[dict] = None
        self._depth_in_article = 0
        # 文本累积的"目标字段"——当处于某个关键元素内时，把 handle_data 写到这里
        self._field_target: Optional[str] = None
        self._buf: list[str] = []
        # 用于在 <a class="Link--muted"> 之间区分顺序（star / fork / today）
        self._muted_link_idx = 0
        # 用于在 <h2.h3> 内的 <a href> 上识别仓库名/URL
        self._h2_seen = False

    # ---- helpers ----

    def _start_field(self, name: str) -> None:
        self._field_target = name
        self._buf = []

    def _flush_field(self) -> None:
        if self._field_target and self._cur is not None:
            value = "".join(self._buf).strip()
            if value:
                self._cur[self._field_target] = value
        self._field_target = None
        self._buf = []

    def _class_attr(self, attrs: list[tuple[str, Optional[str]]]) -> str:
        for k, v in attrs:
            if k == "class" and v:
                return v
        return ""

    def _style_attr(self, attrs: list[tuple[str, Optional[str]]]) -> str:
        for k, v in attrs:
            if k == "style" and v:
                return v
        return ""

    def _href_attr(self, attrs: list[tuple[str, Optional[str]]]) -> Optional[str]:
        for k, v in attrs:
            if k == "href" and v:
                return v
        return None

    # ---- tag handlers ----

    def handle_starttag(self, tag: str, attrs: list[tuple[str, Optional[str]]]) -> None:
        cls = self._class_attr(attrs)

        # 进入 article 卡片
        if tag == "article" and "Box-row" in cls.split():
            self._cur = {
                "rank": len(self.records) + 1,
                "full_name": "",
                "url": "",
                "description": "",
                "language": "",
                "language_color": "",
                "stars_total": "",
                "forks": "",
                "stars_today": "",
                "readme": "",
                "functionality": "",
                "problem_solved": "",
                "target_users": "",
                "application_areas": "",
                "one_sentence_summary": "",
                "sources": [],
            }
            self._depth_in_article = 1
            self._muted_link_idx = 0
            self._h2_seen = False
            return

        if self._cur is None:
            return
        self._depth_in_article += 1

        # 仓库名 + URL（在 h2.h3 内的 a.Link）
        if tag == "h2" and "h3" in cls.split():
            self._h2_seen = True
            return
        if tag == "a" and self._h2_seen:
            href = self._href_attr(attrs)
            if href and href.startswith("/"):
                full = urljoin("https://github.com", href)
                self._cur["url"] = full
                # owner/repo
                path = href.lstrip("/").split("?")[0].split("#")[0]
                self._cur["full_name"] = path
                self._h2_seen = False  # 只取第一个有效 a
            return

        # 描述 <p class="col-9 ...">
        if tag == "p" and "col-9" in cls.split():
            self._start_field("description")
            return

        # 顺序：先匹配更具体的 class，避免被通用 span 分支 early-return 短路
        # 今日新增 <span class="d-inline-block float-sm-right">
        if tag == "span" and "float-sm-right" in cls.split():
            self._start_field("stars_today")
            return

        # 主语言 <span itemprop="programmingLanguage">...</span>
        if tag == "span":
            itemprop = None
            for k, v in attrs:
                if k == "itemprop" and v == "programmingLanguage":
                    itemprop = v
                    break
            if itemprop:
                self._start_field("language")
                return
            # 主语言旁边的色块 <span style="background-color:#xxx"></span>
            style = self._style_attr(attrs)
            m = re.search(r"background-color\s*:\s*(#[0-9A-Fa-f]{6})", style)
            if m and not self._cur.get("language_color"):
                self._cur["language_color"] = m.group(1)
            return

        # 总 Star / Fork（两个 Link--muted 顺序）
        if tag == "a" and "Link--muted" in cls.split():
            self._muted_link_idx += 1
            if self._muted_link_idx == 1:
                self._start_field("stars_total")
            elif self._muted_link_idx == 2:
                self._start_field("forks")
            return

    def handle_data(self, data: str) -> None:
        if self._cur is None or not self._field_target:
            return
        # 累积，handle_endtag 时 flush
        self._buf.append(data)

    def handle_endtag(self, tag: str) -> None:
        if self._cur is None:
            return
        self._depth_in_article -= 1

        if self._field_target:
            # 描述 / stars_total / forks / stars_today / language 都在闭合时 flush
            # 对应标签：p / a / a / span / span
            target_tags = {
                "description": "p",
                "language": "span",
                "stars_total": "a",
                "forks": "a",
                "stars_today": "span",
            }
            if target_tags.get(self._field_target) == tag:
                self._flush_field()
                return

        # 提交整张卡片
        if tag == "article" and self._depth_in_article <= 0:
            # 兜底：stars_today 可能在浮点数 span 内嵌套了 svg 后才闭合，
            # 万一没刷成功，留个最后补救
            if self._field_target:
                self._flush_field()
            if self._cur.get("full_name"):
                if not self._cur.get("sources"):
                    self._cur["sources"] = [self._cur.get("url", "")]
                self.records.append(self._cur)
            self._cur = None
            self._h2_seen = False


def parse_trending_html(html: str) -> list[dict]:
    parser = _TrendingParser()
    parser.feed(html)
    return parser.records


# ----------------------- Fetch README -----------------------

def fetch_one_readme(session: requests.Session, full_name: str) -> str:
    """抓单个仓库 README，截前 README_MAX_CHARS 字符。失败返回空字符串。"""
    if "/" not in full_name:
        return ""
    owner, repo = full_name.split("/", 1)
    url = RAW_README_URL.format(owner=owner, repo=repo)
    try:
        resp = session.get(url, timeout=HTTP_TIMEOUT, allow_redirects=True)
        if resp.status_code == 200:
            return resp.text[:README_MAX_CHARS]
        return ""
    except requests.RequestException:
        return ""


def fetch_all_readmes(
    full_names: list[str], max_workers: int = README_WORKERS
) -> dict[str, str]:
    """并发抓 README，返回 {full_name: readme_text} 映射。"""
    out: dict[str, str] = {}
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept": "*/*"})
    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        futures = {
            pool.submit(fetch_one_readme, session, fn): fn for fn in full_names
        }
        for fut in as_completed(futures):
            fn = futures[fut]
            try:
                out[fn] = fut.result()
            except Exception:
                out[fn] = ""
            time.sleep(README_THROTTLE)  # 简单节流
    return out


# ----------------------- IO & atomic write -----------------------

def atomic_write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, path)


# ----------------------- Main -----------------------

def main() -> int:
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--since", choices=["daily", "weekly", "monthly"], default="daily")
    p.add_argument("--language", default="", help="留空 = 全部语言；如 python / go / rust")
    p.add_argument("--limit", type=int, default=20, help="最多保留多少仓库，1-25")
    p.add_argument(
        "--output",
        required=True,
        help="输出 JSON 路径，如 /tmp/github_trending_2026-08-18.json",
    )
    p.add_argument("--skip-readme", action="store_true", help="跳过 README 抓取（调试用）")
    args = p.parse_args()

    # 1. 构造 URL
    if args.language:
        url = f"{GITHUB_TRENDING_BASE}/{args.language}?since={args.since}"
    else:
        url = f"{GITHUB_TRENDING_BASE}?since={args.since}"

    # 2. GET trending 页
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }
    )
    try:
        resp = session.get(url, timeout=HTTP_TIMEOUT)
        resp.raise_for_status()
    except requests.RequestException as e:
        print(f"[ERR] 抓 trending 失败：{e}", file=sys.stderr)
        return 1

    # 3. 解析 HTML
    records = parse_trending_html(resp.text)
    if not records:
        print("[ERR] 解析出 0 条仓库，HTML 结构可能已变化", file=sys.stderr)
        return 2
    records = records[: max(1, min(args.limit, len(records)))]

    # 4. 抓 README（可选）
    if not args.skip_readme:
        full_names = [r["full_name"] for r in records if r.get("full_name")]
        readmes = fetch_all_readmes(full_names)
        for r in records:
            r["readme"] = readmes.get(r["full_name"], "")

    # 5. 组装顶层（用本地时间作 date，避免 UTC 与本地日期错位）
    local_now = datetime.now()
    payload = {
        "date": local_now.strftime("%Y-%m-%d"),
        "since": args.since,
        "language": args.language,
        "fetched_at": local_now.strftime("%Y-%m-%dT%H:%M:%S"),
        "repos": records,
    }

    # 6. 写 JSON
    out_path = Path(args.output)
    atomic_write_json(out_path, payload)

    # 7. 摘要
    readme_hits = sum(1 for r in records if r.get("readme"))
    print(
        f"[OK] {len(records)} 个仓库 → {out_path}  "
        f"(README 命中 {readme_hits}/{len(records)})"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
