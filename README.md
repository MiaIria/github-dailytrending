# github-dailytrending

> A self-evolving Claude Code Skill that auto-archives GitHub Trending repos into a single mobile HTML, a Markdown knowledge base, and a 300-char daily trend digest — **with cross-day comparison that learns from your history**.

抓取 GitHub Trending 今日热门仓库，按日期归档为一份**移动端单页 HTML** + 一份**结构化知识库 Markdown** + 一段 **≤300 字**的趋势速览。**自带自进化机制**：每次执行前先扫描 `./github-trending-knowledge/` 历史归档做跨日对比（窗口为昨日 + 前日 2 天，识别"近 3 天未上榜、今日首次上榜"的真·新面孔仓库），让总结越用越聪明。

---

## ✨ 核心特性

- 🧠 **自进化机制（独有）** — 每次执行前扫描历史归档做跨日对比，`summary.md` 必须包含至少 1 条具体跨日对比事实（如"某某仓库连续两日霸榜后今日被 X 取代"），越用越聪明
- 📱 **单页移动端 HTML** — 420px 宽，所有仓库一屏看完，深色 / 浅色主题可切换
- 📚 **合并知识库 Markdown** — 一日一份，仓库按 rank 从高到低统一归档
- ⚡ **Claude 自动跑全流程** — 抓数据、拆 README、生成总结、零手动复制
- 📏 **硬约束：summary ≤300 字** + 含跨日对比事实 + Top 5 新面孔一句话介绍（≤3 个、同方向合并）— 杜绝空话与长篇大论，专注当日信号
- 🔌 **零外部依赖** — 内联 SVG / 内联主题 CSS，无 CDN、无外部字体、无外部脚本

---

## 🚀 三步上手

### 1. 安装到 Claude Code

```bash
# 推荐方式：直接 clone 到 skills 目录
git clone https://github.com/MiaIria/github-dailytrending.git \
  ~/.claude/skills/github-dailytrending
```

或手动复制：

```bash
cp -r github-dailytrending ~/.claude/skills/
```

### 2. 触发 Skill

在 Claude Code 输入：

```text
/github-trending
```

或自然语言触发：

> "今日 GitHub 热榜"
> "归档今天的 GitHub trending"
> "GitHub 今日热门仓库"

支持参数：

```text
/github-trending since=weekly language=python limit=10
```

| 参数 | 默认 | 可选 |
|---|---|---|
| `since` | `daily` | `daily` / `weekly` / `monthly` |
| `language` | `""`（全部） | `python` / `rust` / `go` / ... |
| `limit` | `20` | 1–25 |

### 3. 拿产物

完成后 Claude 会输出：

```
📦 交付清单（YYYY-MM-DD）
  ./github-trending-knowledge/YYYY-MM-DD/github-trending.md
  ./github-trending-results/YYYY-MM-DD/index.html
  ./github-trending-results/YYYY-MM-DD/summary.md
```

`index.html` 直接拖进手机浏览器即可。

---

## 🧩 9 步工作流（含自进化）

| # | 步骤 | 实现 |
|---|---|---|
| 0 | **跨日对比（自进化机制）** — 扫描 `./github-trending-knowledge/` 昨日 + 前日归档，识别 #1 易主 / 落榜 / 跃迁 + **真·新面孔仓库**（近 3 天未上榜、今日首次上榜；与名次无关） | SKILL 内置 |
| 1 | 解析参数 | SKILL 内置 |
| 2 | 抓 trending 页 + README | `scripts/fetch_trending.py` |
| 3 | 校验 JSON 字段 | Claude 自己来 |
| 4 | 拆解每个仓库为 5 个中文字段 | Claude 自己来 |
| 5 | 写入合并 Markdown | Claude 自己来 |
| 6 | 渲染单页 HTML | `scripts/render_outputs.py` |
| 7 | **生成 ≤300 字总结 + 强制含跨日对比事实 + Top 5 新面孔一句话介绍（≤3 个、同方向合并）** | Claude 自己来 |
| 8 | 输出交付清单 | SKILL 内置 |

完整规范见 **[`SKILL.md`](./SKILL.md)**。

> **自进化闭环**：今日归档 → 落地到 `github-trending-knowledge/<YYYY-MM-DD>/` → 供下次 Step 0 读取 → 形成"读历史 → 写今日 → 沉淀历史 → 供下次读"的反馈环。

---

## 📁 仓库结构

```text
github-dailytrending/
├── SKILL.md                       # Skill 入口（Claude 读它，含 9 步工作流）
├── LICENSE                        # MIT
├── README.md                      # 本文件
├── .gitignore
├── scripts/
│   ├── fetch_trending.py          # 抓 trending 页 + 逐仓库 README
│   └── render_outputs.py          # 渲染单页合并 HTML
└── references/
    ├── data-contract.md           # JSON 字段契约
    └── trending-fetch-spec.md     # GitHub Trending CSS 选择器
```

---

## 🤝 贡献

欢迎 PR / Issue。三条友好扩展路线：

1. **新主题**：`render_outputs.py` 里抽 `THEME_CSS`，fork 一个配色即可
2. **新字段**：在 `references/data-contract.md` 加字段，skill 自动接入
3. **新筛选维度**：`language=javascript?type=repositories` 等 trending 高级参数

⚠️ **请保持以下硬约束**——这是 skill 的核心差异化，请勿放宽：

- summary ≤ **300 字**（含元信息行除外）
- `### 今日新动向` 必须含至少 1 条具体跨日对比事实，且带 `owner/repo` 仓库名
- `### 今日新动向` 必须为今日的"新面孔仓库"（Step 0 严格定义：近 3 天未上榜、今日首次上榜；与名次无关）补一句"作用 + 差异化特征"的一句话介绍；新面孔介绍 ≤3 个、同方向需合并概括（与上方 ≤3 仓库举例配额互不冲突）
- 不得在 final 交付物（含 `summary.md` / `index.html` / `github-trending.md`）中泄露 Step 0 跨日对比备忘

---

## 📜 License

[MIT](./LICENSE) © 2026 MiaIria
