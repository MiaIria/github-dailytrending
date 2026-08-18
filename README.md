# github-dailytrending

> A Claude Code Skill that auto-archives GitHub Trending repos into a single mobile HTML, a Markdown knowledge base, and a 500-char daily trend digest.

抓取 GitHub Trending 今日热门仓库，按日期归档为一份**移动端单页 HTML** + 一份**结构化知识库 Markdown** + 一段 **≤500 字符**的趋势速览。

---

## ✨ 核心特性

- 📱 **单页移动端 HTML** — 420px 宽，所有仓库一屏看完，深色 / 浅色主题可切换
- 📚 **合并知识库 Markdown** — 一日一份，仓库按 rank 从高到低统一归档
- ⚡ **Claude 自动跑全流程** — 抓数据、拆 README、生成总结、零手动复制
- 📏 **硬约束：summary ≤500 字符** — 杜绝长篇大论，专注当日信号
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

## 🧩 8 步工作流

| # | 步骤 | 实现 |
|---|---|---|
| 1 | 解析参数 | SKILL 内置 |
| 2 | 抓 trending 页 + README | `scripts/fetch_trending.py` |
| 3 | 校验 JSON 字段 | Claude 自己来 |
| 4 | 拆解每个仓库为 5 个中文字段 | Claude 自己来 |
| 5 | 写入合并 Markdown | Claude 自己来 |
| 6 | 渲染单页 HTML | `scripts/render_outputs.py` |
| 7 | 生成 ≤500 字符总结 | Claude 自己来 |
| 8 | 输出交付清单 | SKILL 内置 |

完整规范见 **[`SKILL.md`](./SKILL.md)**。

---

## 📁 仓库结构

```text
github-dailytrending/
├── SKILL.md                       # Skill 入口（Claude 读它）
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

⚠️ **请保持 summary ≤500 字符的硬约束**——这是 skill 的核心差异化，请勿放宽。

---

## 📜 License

[MIT](./LICENSE) © 2026 MiaIria
