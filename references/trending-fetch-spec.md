# GitHub Trending 抓取规范

## URL 构造

| 参数 | 格式 | 示例 |
|---|---|---|
| 基础 URL | `https://github.com/trending` | — |
| 时间范围 | `?since=daily\|weekly\|monthly` | `https://github.com/trending?since=daily` |
| 语言过滤 | `/{language}?since=daily`（在 path 里） | `https://github.com/trending/python?since=daily` |

- 默认 `since=daily`
- 默认 `language=`（空 = 全部语言）
- 默认 `limit=20`（GitHub trending 一页最多 25 个）

## 请求头

```
User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36
            (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36
Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8
Accept-Language: en-US,en;q=0.5
```

不传 Cookie、不带 Authorization。GitHub Trending 是公开页面。

## HTML 结构参考

> 字段选择器基于 2026-08 实际页面 DOM。若 GitHub 改版，fallback 到文末策略。

### 仓库卡片容器

```html
<article class="Box-row">
  ...
</article>
```

每个 trending 仓库一个 `<article class="Box-row">`。直接遍历所有 `article.Box-row` 即可。

### 仓库名 + URL

```html
<h2 class="h3 lh-condensed">
  <a href="/owner/repository" class="Link" data-hydro-click="...">
    <span class="text-bold">owner</span> / repository
  </a>
</h2>
```

提取规则：取 `a` 元素的 `href`（去掉前导 `/`），拼接 `https://github.com` 拿到完整 URL。

### 描述

```html
<p class="col-9 color-fg-muted my-1 pr-4">
  The repository description text.
</p>
```

### 主语言 + 颜色

```html
<span itemprop="programmingLanguage">
  Python
</span>
```

或者（带颜色）：

```html
<span class="color-fg-default text-bold mr-1">
  <span style="background-color:#3572A5" class="..."></span>
  Python
</span>
```

颜色一般在 inline style 里，类似 `style="background-color:#3572A5"`。

### 总 Star、Fork、今日新增

通常在一个 `<div class="f6 color-fg-muted mt-2">` 节点下，三个 `<a class="Link--muted ...">`：

```html
<a href="/owner/repo/stargazers" class="Link--muted">
  <svg>...</svg>
  12,345
</a>
<a href="/owner/repo/network/members" class="Link--muted">
  <svg>...</svg>
  678
</a>
<span class="d-inline-block float-sm-right">
  <svg>...</svg>
  1,234 stars today
</span>
```

提取规则：
- 第一个 `Link--muted` → `stars_total`
- 第二个 `Link--muted` → `forks`
- `float-sm-right` 内的文本 → `stars_today`

## HTML 解析策略

### 主方案：`html.parser.HTMLParser` 子类

`beautifulsoup4` / `lxml` 在目标 Python 环境中未安装，使用 stdlib `html.parser.HTMLParser` 自定义子类。

按状态机实现：
1. `handle_starttag`：根据 tag + class 进入不同状态
2. `handle_data`：累积当前状态的文本
3. `handle_endtag`：退出状态时把累积文本写入当前 `RepoRecord` 对应字段

### Fallback：正则

如果 HTML 结构变了无法用 HTMLParser 解析，按以下正则兜底（粗略提取，可能丢失字段）：

```python
RE_ARTICLE = re.compile(r'<article class="Box-row">(.*?)</article>', re.S)
RE_NAME = re.compile(r'<h2[^>]*>\s*<a [^>]*href="/([^"]+)"', re.S)
RE_DESC = re.compile(r'<p class="col-9[^"]*">\s*(.*?)\s*</p>', re.S)
RE_LANG = re.compile(r'programmingLanguage">\s*(\S+?)\s*</span>', re.S)
RE_COLOR = re.compile(r'background-color:(#[0-9A-Fa-f]{6})', re.S)
RE_STARS_TOTAL = re.compile(r'stargazers[^<]*<svg[^/]*?</svg>\s*([\d,]+)', re.S)
RE_STARS_TODAY = re.compile(r'([\d,]+ stars today)', re.S)
```

## README 抓取

对每个仓库单独 GET：

```
https://raw.githubusercontent.com/{owner}/{repo}/HEAD/README.md
```

- 截前 3000 字符（避免某些超大 README 占内存）
- 用 `concurrent.futures.ThreadPoolExecutor` 并发抓取，最多 8 线程
- 单仓库失败不影响整体，记为空字符串

## 失败处理

| 场景 | 处理 |
|---|---|
| trending 页返回非 200 | 抛错给 Claude 终止 skill |
| 某 article 解析不出字段 | 跳过该 article，其余继续 |
| README 404（私有/无 README） | `readme` 留空字符串 |
| README 太大 | 截前 3000 字 |
| 网络超时（>10s） | 重试 1 次，仍失败则该字段留空 |

## 反爬提示

GitHub Trending 公开页面**未观察到**反爬机制（普通 UA 即可，无需登录）。
但若 IP 短时间内大量请求，可能触发 GitHub 的速率限制（一般是 IP 级别的 60 req/h 匿名限制）。
建议：
- 每个仓库的 README 抓取间隔 0.1s（用 `time.sleep(0.1)`）
- 失败重试指数退避（1s, 2s, 4s）
- 若频繁失败，考虑加代理（不在 skill 默认实现里）
