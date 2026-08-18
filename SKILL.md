---
name: github-dailytrending
description: "抓取 GitHub Trending 全语言/全开发者今日热门仓库，按日期归档到当前项目目录；每日全部仓库合并到一份手机端 HTML（results/<日期>/index.html）和一份知识库 Markdown（knowledge/<日期>/github-trending.md），并产出当日趋势总结文案。仓库在 HTML / Markdown 中均按热度（rank）从上到下排列。Use when user says '/github-trending', '今日 GitHub 热榜', '每日 GitHub 热门', '归档今天的 GitHub trending', 'GitHub 今日热门仓库', 或任何 '抓 GitHub trending 仓库并归档' 的请求。"
argument-hint: "[since=daily|weekly|monthly] [language] [limit=20]"
version: "0.2.0"
user-invocable: true
allowed-tools: Read, Write, Edit, Bash, Glob, Grep, WebFetch
---

# github-dailytrending

抓取 GitHub Trending 今日热门仓库，按日期归档为一份合并的移动端 HTML 报告 + 一份合并的结构化知识库 Markdown，并产出一段当日趋势总结文案。

> **最终交付物**（按日期目录）：
> - `github-trending-knowledge/<YYYY-MM-DD>/github-trending.md`：当日全部仓库的知识库（顶部为总览索引 + 表格，下方按 rank 从高到低逐仓库详情）
> - `github-trending-results/<YYYY-MM-DD>/index.html`：当日全部仓库的单页 HTML 总览（卡片按 rank 从高到低排列，每张卡片为完整详情）
> - `github-trending-results/<YYYY-MM-DD>/summary.md`：当日趋势总结文案

---

## 触发场景

- 用户输入 `/github-dailytrending` 或 `/github-trending`
- 用户说"今日 GitHub 热榜"、"每日 GitHub 热门"、"归档今天的 GitHub trending"、"抓 GitHub trending 仓库"、"GitHub 今日热门仓库"
- 用户给出参数如 `weekly`、`python`、`limit=10`

---

## 参数解析

| 参数 | 默认值 | 说明 |
|---|---|---|
| `since` | `daily` | `daily` / `weekly` / `monthly` |
| `language` | `""`（全部） | GitHub trending 支持的语言 slug，如 `python`、`go`、`rust` |
| `limit` | `20` | 最多保留多少仓库，1-25 |

如果用户没给参数，用默认值。

---

## 工作流（8 步，每步必须执行）

### Step 1 — 解析参数

根据用户输入确定 `since` / `language` / `limit`。如果用户在触发句中已包含时间范围（"今日"/"daily"/"weekly"），优先采用。

### Step 2 — 调用抓取脚本

```bash
python "C:\Users\26250\.claude\skills\github-dailytrending\scripts\fetch_trending.py" \
  --since <since> [--language <lang>] --limit <limit> \
  --output "<project_root>/.gdt_cache/github_trending_<YYYY-MM-DD>.json"
```

`<project_root>` = 当前工作目录（用户调用本 skill 时所在的项目根）。

把脚本 stdout 中的仓库数 + README 命中数记下，后续报告。

### Step 3 — 读取 JSON

用 Read 工具读取上一步生成的 JSON 文件，确认 `repos` 数组非空、每条都有 `full_name` / `url` / `description` / `readme` 等字段。

### Step 4 — 逐仓库拆解（**Claude 自己填 5 个中文字段**）

对 JSON 中每个仓库，根据 `description` 英文原描述 + `readme` 字段（前 3000 字），**Claude 自己生成** 5 个中文字段：

| 字段 | 建议长度 | 写作要求 |
|---|---|---|
| `functionality` | 30-80 字 | 一句话讲清楚仓库做什么，用「用 X 技术做 Y」结构 |
| `problem_solved` | 20-60 字 | 它解决了什么痛点/问题 |
| `target_users` | 15-40 字 | 谁会用（开发者类型、用 `、`分隔） |
| `application_areas` | 10-30 字 | 应用领域（用 `、`分隔，2-4 个） |
| `one_sentence_summary` | 15-40 字 | 一句话总结，用于 HTML callout |

**硬性规则**：
- 不留空字符串——README 缺失或太短时，根据 `description` + 仓库名尽力推断
- 字段值用中文，不要中英混杂
- 不要复述仓库名（如不能说"这是一个叫 X 的仓库"）
- 不允许出现"根据 README 所述"、"该项目是一个"等套话

把填好的字段写回 JSON 同一路径。

### Step 5 — 写合并知识库（Markdown）

在 `<project_root>/github-trending-knowledge/<YYYY-MM-DD>/` 下生成**唯一一份** Markdown 文件：

**`github-trending.md`** —— 文件结构 = 顶部总览 + 索引表 + 下方所有仓库详情（按 rank 从高到低排列）：

```markdown
# GitHub 今日热门 · <YYYY-MM-DD>

- 抓取仓库数：N
- README 命中：N1/N
- 时间范围：<since>
- 语言筛选：<language 或 "全部">

## 仓库清单

| # | 仓库 | 简介 | 一句话总结 |
|---|---|---|---|
| 1 | owner/repo | <description> | <one_sentence_summary> |
| 2 | ... | ... | ... |

---

# owner/repository

- **排名**：#1
- **URL**：https://github.com/owner/repository
- **语言**：Python（#3572A5）
- **总 Star**：12,345
- **今日新增**：1,234 stars today
- **Fork**：678
- **抓取日期**：2026-08-18

## 仓库简介
<description 原样保留>

## 项目拆解

### 🎯 功能
<functionality>

### 🏷️ 应用领域
<application_areas>

### 👥 适用人群
<target_users>

### ❓ 解决问题
<problem_solved>

### 💬 一句话总结
<one_sentence_summary>

## 参考资料
- <url>
- （如有抓取失败需标注"README 未抓取"）

---

# next/repo
...
```

**硬性要求**：
- 仓库详情块之间使用水平分割线 `---` 分隔
- 仓库详情块按 `rank` 从小到大（即热度从高到低）依次排列
- **每个仓库的内部格式（标题层级、字段列表、项目拆解小节、参考资料）必须与旧版单文件 Markdown 完全一致**——只做合并，不改格式
- **不再生成** `_index.md` 和单个仓库的 `<owner>--<repo>.md`

### Step 6 — 调用合并渲染脚本

```bash
python "C:\Users\26250\.claude\skills\github-dailytrending\scripts\render_outputs.py" \
  --input "<含拆解字段的JSON路径>" \
  --project-root "<project_root>" \
  --theme github-blue
```

脚本只生成**唯一一份** HTML 文件 `<project_root>/github-trending-results/<YYYY-MM-DD>/index.html`，其中包含当日所有仓库的完整详情卡片，按 rank 从高到低依次排列。

**硬性要求**：
- 单页 HTML 的样式基线（`THEME_CSS` / `THEME_JS` / SVG / 主题切换按钮）保持不变
- 每个仓库一张 `<article class="card">`，卡片**使用完整详情版**（含 `sec-list` 拆解字段、`oneliner`、`card-link`），与旧版单仓库 HTML 完全一致
- **不再生成**单个仓库的 `<owner>--<repo>.html`，index.html 不再链接到这些子页

### Step 7 — 生成趋势总结文案

Claude 基于当日所有仓库的方向/技术栈/趋势，写一段总结文案，落到：

```
<project_root>/github-trending-results/<YYYY-MM-DD>/summary.md
```

**硬性长度约束（不可违反）**：
- 全文（标题、正文、末尾元信息行）合计 **≤ 500 个字符**（按 `len(text)` 计，标点、空格、换行全部计入，超限直接重写不要交付）
- 默认目标长度 300-450 字符；只有仓库数 ≥ 15 或当日出现明显新趋势主题时才允许逼近 500
- 写入文件前必须自行检查一遍字符数；超过 500 必须删减/重写再交付

文案要求：
- 体现当日技术趋势（如"AI Agent 工具集中爆发"、"系统编程语言复兴"）
- 举一个具体仓库为例（写名 + 一句话点出特色）
- 用中文，行文流畅，不要堆砌套话
- 开头用 `## 今日 GitHub 趋势速览` 标题
- 末尾用 `> 抓取于 YYYY-MM-DD · since=<since> · language=<lang>` 标注元信息

### Step 8 — 输出交付清单

在对话里告诉用户本次产出的所有文件路径，例如：

```
📦 交付清单（YYYY-MM-DD）

知识库（Markdown · 单文件汇总）：
  - ./github-trending-knowledge/YYYY-MM-DD/github-trending.md

结果库（HTML + 文案）：
  - ./github-trending-results/YYYY-MM-DD/index.html       ← 当日全部仓库的单页 HTML（按热度排列）
  - ./github-trending-results/YYYY-MM-DD/summary.md       ← 趋势总结
```

并提示用户在手机宽度浏览器打开 `index.html` 查看。

---

## 质量规则（硬性约束）

1. **不修改原始字段**：`description` / `stars_total` / `stars_today` / `forks` 等 GitHub 原始数据原样保留，禁止估算或四舍五入。
2. **HTML 必须**：独立 UTF-8 文档、移动端优先（max-width 420px）、无外部脚本、无外部字体、SVG 内联。
3. **XSS 防注入**：写入 HTML 的所有用户/RAG 内容必须经过 `html.escape(..., quote=True)`（脚本已做，Claude 写 Markdown 也需避免注入 `<script>` 等危险标签）。
4. **文件名安全**：仓库单文件场景下 `owner/repo` → `owner--repo`；合并场景下固定使用 `github-trending.md` / `index.html`，过滤非 `[A-Za-z0-9_.-]` 字符。
5. **失败兜底**：
   - README 抓取失败：HTML 显示"暂无补充说明"，Markdown 标注"README 未抓取"
   - 整页 trending 抓取失败：报错并停止 skill，不要给半成品
6. **路径不允许 `..` 反向穿越**。
7. **顺序硬约束**：HTML 与 Markdown 中仓库必须按 `rank` 从小到大（即热度从高到低）排列——若 JSON 中顺序异常，需在脚本/写作时显式排序。

---

## 关键文件

| 文件 | 作用 |
|---|---|
| `SKILL.md` | 本文件，skill 入口 |
| `references/data-contract.md` | JSON 字段契约（fetch 产物 ↔ render 输入 ↔ Claude 拆解字段） |
| `references/trending-fetch-spec.md` | GitHub Trending 页面 CSS 选择器 + 解析 fallback |
| `scripts/fetch_trending.py` | 抓 trending 页 + 逐仓库 README，写 JSON（**不变**） |
| `scripts/render_outputs.py` | 读 JSON，生成**单页合并 HTML**（`index.html`） |

---

## 反爬与速率说明

GitHub Trending 公开页面**未观察到**反爬机制，普通 UA 即可。但为礼貌起见：
- README 抓取用 8 线程并发，单请求间隔 100ms
- 若频繁失败，加指数退避；持续失败则中止并报错

---

## 不在本次范围内

- ❌ 定时调度（cron/Windows 计划任务）— 手动调用
- ❌ 邮件 / 飞书 / Slack 推送
- ❌ 历史趋势对比 / 跨日 diff
- ❌ 国际化（i18n）— 当前只生成中文
- ❌ 多个主题切换 UI（仅 github-blue，参数预留）
- ❌ 按仓库拆分的独立 HTML / Markdown 文件 —— 当前产出已全部合并