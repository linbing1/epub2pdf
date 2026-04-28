# epub2pdf 设计文档

**日期**：2026-04-28
**目标**：把 epub 文件转成"book 形态 + kami 视觉气质"的 PDF。

---

## 1. 背景与目标

把任意 epub 转换成阅读型 PDF：

- **形态**：A5 单栏阅读版式，每章新页起，章标题接正文同页（极简书风格）
- **视觉**：复用 kami 的色板与字体 token —— 暖米羊皮纸底、墨蓝点缀、衬线层级。中文 TsangerJinKai02、英文 Charter、日文 YuMincho（best-effort）
- **使用场景**：在手机/iPad/Kindle 上长时间阅读

**非目标**：

- 不做电子书阅读器（reader3 已存在）
- 不做精装感版式（章扉页、版权页）—— 极简
- v1 不处理"一文件多章"的复杂 epub（按 spine 切，遇到再升级）

---

## 2. 技术栈

| 层 | 选择 | 理由 |
|---|---|---|
| epub 解析 | `ebooklib` + `beautifulsoup4` | 沿用 reader3 同款，已验证 |
| 章节切分 | 按 spine 顺序，但用 TOC 反查过滤+命名（详见 §5.1） | 90% 现代 epub 一文件一章；spine 含 nav/cover 等垃圾项必须剔除，标题必须取自 TOC |
| PDF 渲染 | **WeasyPrint** | 与 kami 同栈，token / 字体 / 元信息逻辑可复用 |
| 环境 | 标准 `python -m venv` + `pip install -r requirements.txt`，**不用 uv** | 用户偏好 |

依赖清单（`requirements.txt`）：

```
ebooklib
beautifulsoup4
lxml
weasyprint
pytest
pypdf
```

---

## 3. 命令行接口

```
python epub2pdf.py <book.epub> [-o output.pdf] [--size a5|6x9|a4] [--keep-html] [-v]
```

| 参数 | 默认 | 说明 |
|---|---|---|
| `<book.epub>` | 必填 | 输入 epub 文件路径 |
| `-o, --output` | `<book>.pdf`（与输入同目录同名） | 输出 PDF 路径；存在则覆盖 |
| `--size` | `a5` | 页面尺寸 |
| `--keep-html` | 否 | 保留中间 HTML 在 `<book>_build/` 供调试/手改 |
| `-v, --verbose` | 否 | 打开 WeasyPrint INFO 级日志（字体/图片解析消息） |

默认一步出 PDF；`--keep-html` 当后门，方便排版翻车时对照 HTML/CSS 调试。

---

## 4. 数据流

```
book.epub
   │
   │ ① ebooklib + reader3 风解析
   ▼
Book {metadata, spine[ChapterContent], toc, images}
   │
   │ ② 拼装单一 HTML（封面 + 目录 + 各章节 body）
   ▼
build.html  +  styles.css  +  fonts/  +  images/
   │
   │ ③ WeasyPrint 渲染（含 bookmark-level、@page、@font-face）
   ▼
output.pdf
```

中间产物默认在临时目录；`--keep-html` 时落盘到 `<book>_build/`。

---

## 5. 模块拆分

### 目录结构（flat 脚本风）

```
epub2pdf/
  epub2pdf.py        # 主入口 + CLI
  parser.py          # epub → Book
  language.py        # 语言识别
  renderer.py        # Book → 单文件 HTML
  pdf.py             # HTML → PDF (WeasyPrint)
  assets/
    styles.css
    fonts/
      TsangerJinKai02-W04.ttf
      TsangerJinKai02-W05.ttf
      Charter.ttf
  tests/
    test_acceptance.py
    fixtures/
      怪屋谜案.epub
  requirements.txt
  README.md
  docs/superpowers/specs/...
```

跑法：`source .venv/bin/activate && python epub2pdf.py book.epub`

### 模块职责

| 模块 | 职责 | 主要 API |
|---|---|---|
| `parser.py` | epub → `Book` dataclass。复用 reader3 的 `ChapterContent` / `BookMetadata` / `parse_toc_recursive` / `clean_html_content` 等结构 | `parse(epub_path) -> Book` |
| `language.py` | 决定字体策略：先读 `dc:language`，缺失或冲突时按正文字符比例兜底（CJK 统一表/平假名/拉丁） | `detect(book) -> "cn"\|"en"\|"ja"` |
| `renderer.py` | 把 `Book` + 字体方案拼成单文件 HTML，挂上 `styles.css` | `render_html(book, lang, out_dir) -> Path` |
| `pdf.py` | 调 WeasyPrint，写入 PDF metadata（title/author/producer="epub2pdf"） | `to_pdf(html_path, pdf_path, book)` |
| `cli.py` | argparse 入口，串起以上四个 | `main()` |
| `assets/styles.css` | 所有版式 token 与 @page / 章节样式 | — |
| `assets/fonts/` | 直接从 kami 复制 `TsangerJinKai02-W04.ttf` / `W05.ttf` + Charter；YuMincho 走 macOS 系统字体（详见 §5.4） | — |

每个模块单一职责、可独立测试。`parser.py` 完全不知道 PDF 存在；`pdf.py` 完全不知道 epub 长什么样；它们靠 `Book` 这个结构体通信。

### 5.1 章节过滤与命名（关键逻辑）

reader3 把 spine 全收（含 `nav.xhtml` 等导航文档），章节标题用 `Section N` 占位。这套在网页阅读器里能靠"侧栏走 TOC、主区不点就不显示"隐藏垃圾，PDF 是线性渲染**没这种偷懒空间**，必须主动处理。

**主路径（有 TOC，绝大多数书）**：

1. 递归 TOC，收集所有条目的 `file_href`（`href` 去掉 `#anchor` 后的部分）成 `valid_files` 集合，同时建 `file_href → toc_title` 映射
2. 遍历 spine，**只保留 href ∈ valid_files 的项**，按 spine 顺序输出
3. 每章的渲染标题 = `toc_title` 映射查到的值
4. 多个 TOC 条目指向同一文件（带不同锚点）时：以**该文件第一次出现的 TOC 条目**作为章标题；锚点级的细分 v1 不处理（在 §10 后续可能里）

**Fallback（TOC 为空或解析失败）**：

1. spine 全收
2. 用文件名启发式剔除：basename 含 `nav` / `cover` / `title` / `copyright` / `colophon` / `toc` 关键字（不区分大小写）的项跳过
3. 章标题：尝试从该文件 HTML 内首个 `<h1>` / `<h2>` 提取；失败则用文件名（去扩展名、下划线转空格）

**为什么不用 EPUB3 `guide` / landmarks 过滤**：实测《怪屋谜案》这种 2020 年代中文出版物 `guide` 字段就是空的，普及度不够，单独依赖会频繁降级，不如直接用更可靠的 TOC 反查。

**reader3 的 `ChapterContent.title` 字段**：仍然保留（方便 fallback 路径下用），但主路径渲染**不读它**——它只是个 `Section N` 占位。

### 5.2 图片资源链路

epub 内的图片是 zip 里的 bytes，HTML 里是相对路径。WeasyPrint 需要能从文件系统读到。

**做法**（沿用 reader3 同款）：

1. `parser.py` 遍历 epub 所有 `ITEM_IMAGE`，写到 `<build_dir>/images/<safe_name>`
2. 重写每章 HTML 的 `<img src>`：用 reader3 的 `image_map` 双索引（完整内部路径 + basename）兜底各种凌乱写法
3. WeasyPrint 渲染时 `base_url=<build_dir>`，HTML 里相对路径 `images/xxx.jpg` 自动解析
4. `<build_dir>` 默认 = `tempfile.mkdtemp()`，渲染完删；`--keep-html` 时 = `<book>_build/`，保留可独立浏览

**否决项**：
- base64 内嵌：长篇带插图的书 HTML 会到 50MB+，WeasyPrint 慢
- WeasyPrint 自定义 url_fetcher：优雅但 `--keep-html` 产物图片链接全死，违背"中间产物可调试"

### 5.3 出版商样式清理（白名单策略）

reader3 的 `clean_html_content` 只剥 `script/style/iframe/form` 等危险标签，**保留**所有 `class` 和内联 `style`。这在 PDF 渲染下会和我们的 styles.css 打架（出版商设的 14px 正文会盖掉 `--body-size: 11pt`、奇怪的 `class="indent2"` 让段落跑偏等等）。

**v1 旗帜鲜明：统一 kami 极简书视觉，不还原各家出版社设计。**

清理规则（在 `parser.py` 的 `clean_html_content` 之后再过一道）：

**保留标签**（语义+结构）：
```
p, h1-h6, em, strong, b, i, u, s, sup, sub,
blockquote, q, br, hr,
ul, ol, li, dl, dt, dd,
table, thead, tbody, tr, td, th,
img, figure, figcaption, a
```

**保留属性**（白名单，其他全删）：
- `<a>`: `href`
- `<img>`: `src`, `alt`
- `<td>/<th>`: `colspan`, `rowspan`

**删属性**：`style`, `class`, `id`, `width`, `height`, `bgcolor`, `align`, `valign`, `lang`（章节级保留在 `<html lang>` 上即可）等所有非白名单属性。

**未在保留列表的标签**：`unwrap`（保留内部内容，去掉外壳），不 `decompose`（不丢内容）。

**例外**：v1 不做 class 白名单。真遇到某本书诗歌/表格特殊版式效果差，再回头加。

### 5.4 字体来源

**这是自用工具**，字体直接复制自本机 kami 安装：

- 中文：`TsangerJinKai02-W04.ttf`（正文）、`TsangerJinKai02-W05.ttf`（章标题），从 `~/.agents/skills/kami/assets/fonts/` 复制到本仓库 `assets/fonts/`
- 英文：Charter（X11 自由许可，可分发），同上路径或 jsDelivr 拉
- 日文：`YuMincho`，走 macOS 系统字体，不 bundle
- `@font-face` 用相对路径 `assets/fonts/...`，WeasyPrint 通过 `base_url` 解析

**字体安装**：仓库初始化时手工执行一次

```bash
cp ~/.agents/skills/kami/assets/fonts/TsangerJinKai02-*.ttf assets/fonts/
```

**TTF 直接 commit 进仓库**（约 38MB），clone 即用，无运行时依赖 kami 路径。`.gitignore` 不屏蔽 `*.ttf`。

**合规说明**：TsangerJinKai 是商业字体，bundle 进仓库是灰色地带。本工具自用，**仓库私有不公开**；如要开源需重新评估或换思源宋体。

### 5.5 语言识别

`<html lang>` 决定段落规则（见 §6 正文）。优先级：

1. **首选 `dc:language`**：epub metadata 里的语言标签（怪屋谜案 = `zh`）
2. **缺失/无法识别时兜底**：取全书前 5000 字符做字符比例统计
   - 平假名/片假名占比 > 5% → `ja`
   - CJK 统一表 + 中日韩标点占比 > 30% → `zh`（阈值低于 50%，因中文文本里西文标点和数字常见）
   - 否则 → `en`
3. 都失败时默认 `zh`（本工具中文为主用例）

### 5.6 其他实现细节

| 项 | 决定 |
|---|---|
| Python 版本 | ≥ 3.10（与 reader3 一致，match-case / 现代 dataclass 可用） |
| WeasyPrint 日志 | 默认静默；`-v` 开启 WeasyPrint INFO 级（字体/图片解析消息） |
| 进度提示 | stderr：`parsing… → N chapters → rendering… → done (X.Ys)` |
| 图片同名冲突 | reader3 的 `image_map` basename 兜底改为：完整内部路径优先 + basename 兜底（防止不同子目录 `cover.jpg` 被覆盖） |
| 空白章节 | 清理后只剩空 `<p>` 的章节跳过，stderr 警告（避免"标题 + 空页"） |
| CJK 长行 | `word-break: break-word; line-break: strict;`（中文按标点断、英文长 URL 按词断） |
| 章节内 `<h1>` | 清理时统一降级为 `<h2>`，避免与封面 `<h1>` 抢书签层级 |

---

## 6. 视觉规范（CSS Token）

```css
:root {
  /* 颜色 — 偷自 kami */
  --paper:   #f5efe1;   /* 暖米底 */
  --ink:     #2a2a2a;   /* 正文墨色 */
  --accent:  #1f3a68;   /* 墨蓝点缀 */
  --rule:    #c9bfa7;   /* 分隔线 */
  --muted:   #6b6357;   /* 页码、副信息 */

  /* 字体 — W04 正文 / W05 章标题与封面 */
  --font-body:     "TsangerJinKai02-W04", "Charter", serif;
  --font-display:  "TsangerJinKai02-W05", "Charter", serif;
  --font-body-en:  "Charter", serif;
  --font-body-ja:  "YuMincho", serif;

  /* 层级 */
  --h1-size: 28pt;       /* 封面书名 */
  --h2-size: 22pt;       /* 章标题 */
  --body-size: 11pt;
  --body-leading: 1.7;
  --caption-size: 9pt;
}
```

### 页面 (`@page`)

- A5 (148×210mm) / 6×9 (152×229mm) / A4 三选一
- 边距：上下 18mm，左右 16mm
- 背景：`--paper`
- 页码：`@bottom-center`，小号 (`--caption-size`)，颜色 `--muted`
- 封面页与目录页：`@page :first` / 命名页，**不渲染页码**

### PDF 书签

WeasyPrint **默认给所有 `h1-h6` 自动加书签**，不写 CSS 也会生效。我们要：

- 章标题 `<h2>` 显式 `bookmark-level: 1; bookmark-label: content(text);` —— 进书签
- 封面 `<h1>` 与目录 `<h1>目录</h1>` 显式 `bookmark-level: none;` —— 否则书签栏会有"封面"和"目录"两条冗余

最终 PDF 大纲只显示正文章节列表（实测验证过）。

### 章节 (`section.chapter`)

- `page-break-before: always` —— 每章新页起
- 章标题：`<h2>`，居中，墨蓝，下方 1px `--rule` 分隔线，下留白 1 行后接正文
- WeasyPrint 书签：`h2 { bookmark-level: 1; bookmark-label: content(text); }`

### 正文

- `<html lang>` 取自 `Book.lang`（详见 §5.5），全书一套段落规则
- `:lang(zh) p { text-indent: 2em; margin: 0; }` —— 中文首行缩进，无段间距
- `:lang(en) p { text-indent: 0; margin: 0 0 0.5em; }` —— 英文段间距，无缩进
- `:lang(ja) p` 同 `zh` 规则
- 中文段落内夹少量英文短语：v1 接受"略别扭"，不做段级语言切换
- `<img>`：`max-width: 100%`，居中，`page-break-inside: avoid`
- `<blockquote>`：左侧 2px `--accent` 竖线，缩进 1em

### 封面

- 上 1/3 留白
- 中部：书名 `--h1-size`，墨蓝
- 下部：作者，`--body-size`，墨色

### 目录

- `<ol>` 章节列表
- 每行：章名 + 引导点 + 页码（用 CSS `target-counter()`）
- 可点击跳转章节

---

## 7. 关键决策与风险

### 决策记录

| 决策 | 选择 | 已否决项 |
|---|---|---|
| 章节切分粒度 | 按 spine 顺序，TOC 反查过滤+命名 | 纯 spine 全收（垃圾页污染）/ TOC 锚点切片（v2）/ EPUB3 guide 过滤（实测普及度差） |
| PDF 引擎 | WeasyPrint | Playwright（kami 用 WP，复用更划算）/ ReportLab（要重写视觉） |
| 视觉风格 | book 形态 + 偷 kami 的 token | kami long-doc 模板（章扉页 + 大留白不适合长篇小说）|
| 前置页面 | 封面 + 目录 + 正文 | 加版权页 / 章扉页（极简优先） |
| 页面尺寸默认 | A5 | A4（太大）/ 6×9（英文向） |
| 包管理 | venv + pip | uv（用户不喜欢） |

### 风险

1. **WeasyPrint 对复杂 CSS 支持有限** — 借鉴 kami 的踩坑清单（无 rgba 背景、CJK 字体显式 fallback、最小 9pt）规避
2. **某些 epub 的 HTML 含奇怪内联样式或脚本** — `clean_html_content`（reader3 同款）剥掉 `script/style/iframe/form`，只保留语义结构，让 `styles.css` 接管
3. **大书 + 大量图片渲染慢/吃内存** — v1 接受，能跑完就行；遇到具体瓶颈再优化
4. **某章 HTML 损坏** — 单章 try/except，stderr 打警告并跳过，不让整本书崩

---

## 8. 错误处理

| 场景 | 行为 |
|---|---|
| epub 文件不存在 / 不是 zip | argparse 层报错，非 0 退出 |
| ebooklib 解析失败 | 打印异常摘要，非 0 退出 |
| spine 为空 | 报错"no readable content"，非 0 退出 |
| 单章 HTML 解析失败 | stderr `warning: chapter X skipped: <reason>`，继续 |
| 字体文件缺失 | stderr 提示路径，fallback 到系统 serif（自用工具，假设字体已 bundle，见 §5.4） |
| WeasyPrint 渲染失败 | 异常向上抛，保留中间 HTML 路径在错误信息里 |
| 输出 PDF 已存在 | 直接覆盖；stderr 打一行 `overwriting <path>` 让用户知情 |

---

## 9. 验收标准

### 9.1 自动化（pytest）

`tests/fixtures/怪屋谜案.epub` 作为固定输入，`tests/test_acceptance.py` 跑下面这些断言：

| 检查 | 工具 | 通过条件 |
|---|---|---|
| 跑得通 | subprocess 调 CLI | 返回码 0，输出 PDF 存在 |
| 字体嵌入 | `pdffonts` 或 pypdf | 嵌入字体名含 `TsangerJinKai` |
| 页数合理 | pypdf `len(reader.pages)` | ≥ 章节数 + 2（封面+目录） |
| 书签数与命名 | pypdf `reader.outline` | 条目数 = 过滤后章节数（怪屋=40），无 `封面`/`目录`/`Section N` 字样 |
| 内部链接可达 | pypdf 抽 `/Annots` 里的 `/Link` | 所有目录链接 dest page ≤ 总页数 |
| 章名都在 PDF 文本里 | pdftotext + grep | TOC 的 40 个章名每个都出现 ≥ 1 次 |
| 没占位文本 | pdftotext | 不含 `Section 1` ~ `Section N` |
| 文件大小 sanity | `os.stat` | < 50MB |

英文书测试：再加一个 `tests/fixtures/dracula.epub`（Project Gutenberg），断言字体含 `Charter`，段落 CSS 用英文规则（间接通过页面布局或不出现中文缩进的视觉特征）。

### 9.2 人工目检（README checklist）

跑完后肉眼确认：

- [ ] 封面：书名/作者居中，墨蓝点缀
- [ ] 暖米色底色渲染对了
- [ ] 章首页留白舒适，章标题样式正确
- [ ] 任意翻 3 章，正文行距、缩进、断行无明显异常
- [ ] `--size a4` / `--size 6x9` 抽样看一遍

---

## 10. 后续可能（不在 v1）

- 按 TOC 切片支持"一文件多章"的旧 epub
- 章扉页 / 版权页 / 多页前言后记的精装版式
- 多层书签（卷 → 章 → 节）
- 自定义主题（不止 kami 暖米）

---

## 11. README 内容（最低限度）

仓库根 `README.md` 至少包含：

1. **安装**：
   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   cp ~/.agents/skills/kami/assets/fonts/TsangerJinKai02-*.ttf assets/fonts/
   ```
2. **跑法**：`python epub2pdf.py book.epub` + 主要参数说明（指向 §3）
3. **人工目检 checklist**（§9.2 内容）
4. **字体合规说明**：本仓库私有不公开，TsangerJinKai 是商业字体（指向 §5.4）
