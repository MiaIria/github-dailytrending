# 数据契约（Data Contract）

`fetch_trending.py` 输出 → Claude 拆解 → `render_outputs.py` 输入，整条链路共用这一个 JSON schema。

## 文件位置

- 抓取产物：`<project_root>/.gdt_cache/github_trending_<YYYY-MM-DD>.json`（Claude 调用时按当日日期构造）
- 渲染输入：同一个 JSON（Claude 在中间填好 5 个拆解字段后再传给渲染脚本）

## 产出结构（合并模式）

调用一次 `render_outputs.py` 仅产出**一份** HTML；Claude 自行写两份文本文件：

```
<project_root>/
├── github-trending-knowledge/<YYYY-MM-DD>/
│   └── github-trending.md          ← Claude 写入；顶部总览 + 索引表 + 按 rank 排列的逐仓库详情
└── github-trending-results/<YYYY-MM-DD>/
    ├── index.html                  ← 脚本生成；单页合并 HTML，按 rank 排列的全量完整卡片
    └── summary.md                  ← Claude 写入；当日趋势总结文案
```

**已弃用**：单个仓库的 `<owner>--<repo>.html` / `<owner>--<repo>.md` / `_index.md`。HTML 与 Markdown 中的仓库必须按 `rank` 从小到大（即热度从高到低）排列。

## JSON 顶层结构

```json
{
  "date": "2026-08-18",
  "since": "daily",
  "language": "",
  "fetched_at": "2026-08-18T08:30:00Z",
  "repos": [ { ...RepoRecord... }, ... ]
}
```

## RepoRecord 字段（每仓库一条）

| 字段 | 类型 | 来源 | 是否 Claude 填 | 说明 |
|---|---|---|---|---|
| `rank` | int | trending 页 | 否 | 当日排名，从 1 开始 |
| `full_name` | string | trending 页 | 否 | `owner/repository` |
| `url` | string | trending 页 | 否 | `https://github.com/owner/repository` |
| `description` | string | trending 页 | 否 | 仓库英文原描述，原样保留 |
| `language` | string | trending 页 | 否 | 主语言（如 `Python`）；缺失则空字符串 |
| `language_color` | string | trending 页 | 否 | 主语言在 GitHub 的代表色（如 `#3572A5`），用于色点 |
| `stars_total` | string | trending 页 | 否 | 总 Star 数（如 `12,345`），原样保留 |
| `forks` | string | trending 页 | 否 | Fork 数（如 `678`），缺失则 `"未提供"` |
| `stars_today` | string | trending 页 | 否 | 今日新增（如 `1,234 stars today`），原样保留 |
| `readme` | string | 抓取 | 否 | raw markdown 文本，前 3000 字；缺失则空字符串 |
| `functionality` | string | **Claude 填** | 是 | 中文一句话描述仓库做什么 |
| `problem_solved` | string | **Claude 填** | 是 | 中文描述它解决什么问题 |
| `target_users` | string | **Claude 填** | 是 | 中文描述适用人群 |
| `application_areas` | string | **Claude 填** | 是 | 中文描述应用领域（多个用 `、`分隔） |
| `one_sentence_summary` | string | **Claude 填** | 是 | 中文一句话总结，用于 HTML callout |
| `sources` | array[string] | 自动 | 否 | 至少包含 `url`；fetch 阶段填好 |

## 字段填写规则

### fetch 阶段（脚本自动）

- `rank` 按 trending 页 DOM 出现顺序递增
- `language` 和 `language_color` 从 trending 页面提取（颜色一般紧邻语言文字的 inline style）
- `readme` 用 `https://raw.githubusercontent.com/{owner}/{repo}/HEAD/README.md`，截前 3000 字符
- `forks` 缺失填 `"未提供"`（不是空字符串），方便 HTML 渲染层判断
- `stars_today` 原样保留 GitHub 显示文本（如 `1,234 stars today`）

### Claude 拆解阶段（必填）

5 个中文字段缺一不可。如果 README 缺失或太短：
- 仍要根据 `description` + 仓库名尽力推断
- 不允许留空字符串
- 字段长度建议：`functionality` 30-80 字，`problem_solved` 20-60 字，`target_users` 15-40 字，`application_areas` 10-30 字，`one_sentence_summary` 15-40 字

### 安全约束

- 所有用户提供的文本在写入 HTML 前必须 `html.escape(..., quote=True)`，防 XSS
- 文件名 `safe_name()`：`owner/repo` → `owner--repo`，过滤非 `[A-Za-z0-9_.-]`
- 路径不允许 `..` 反向穿越

## 示例

```json
{
  "date": "2026-08-18",
  "since": "daily",
  "language": "",
  "fetched_at": "2026-08-18T08:30:00Z",
  "repos": [
    {
      "rank": 1,
      "full_name": "owner/repo",
      "url": "https://github.com/owner/repo",
      "description": "An English description of the repository.",
      "language": "Python",
      "language_color": "#3572A5",
      "stars_total": "12,345",
      "forks": "678",
      "stars_today": "1,234 stars today",
      "readme": "# owner/repo\n\nThis is the README...",
      "functionality": "用 Python 编写张量计算程序，自动编译翻译为多种后端代码",
      "problem_solved": "让张量程序用纯 Python 编写，无需学习领域特定语言，同时保持高性能",
      "target_users": "AI 研究员、深度学习工程师、科学计算开发者",
      "application_areas": "AI/ML 编译器、张量计算、高性能计算",
      "one_sentence_summary": "用 Python 写张量计算，一份代码跑遍所有后端",
      "sources": ["https://github.com/owner/repo"]
    }
  ]
}
```
