#!/usr/bin/env python3
"""Build the offline HTML knowledge base for the B-end hardware PM project.

The source of truth remains the Markdown and media already in this repository.
This script deliberately creates a separate ``docs/site`` tree so the existing
podcast and video pipelines keep their own entrypoints and working files.
"""

from __future__ import annotations

import html
import os
import re
import shutil
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "docs"
SITE = DOCS / "site"


@dataclass(frozen=True)
class Document:
    path: Path
    group: str
    title: str
    description: str
    kind: str = "文档"

    @property
    def source(self) -> str:
        return self.path.relative_to(ROOT).as_posix()


def first_heading(markdown: str) -> str | None:
    for line in markdown.splitlines():
        match = re.match(r"^#\s+(.+?)\s*#*$", line.strip())
        if match:
            return match.group(1).strip()
    return None


def intro(markdown: str, fallback: str) -> str:
    """Return a short description without stealing a whole document."""

    lines = markdown.splitlines()
    after_title = False
    for line in lines:
        text = line.strip()
        if not text:
            continue
        if text.startswith("#"):
            after_title = True
            continue
        if not after_title or text.startswith((">", "- ", "* ", "```", "|")):
            continue
        text = re.sub(r"[`*_]", "", text)
        text = re.sub(r"\s+", " ", text)
        return text[:128] + ("…" if len(text) > 128 else "")
    return fallback


def add_document(documents: list[Document], relative: str, group: str, *, title: str | None = None, kind: str = "文档", description: str | None = None) -> None:
    path = ROOT / relative
    if not path.exists() or path.suffix.lower() != ".md":
        return
    markdown = path.read_text(encoding="utf-8")
    resolved_title = title or first_heading(markdown) or path.stem
    resolved_description = description or intro(markdown, f"{group}中的一份可检索资料。")
    documents.append(Document(path, group, resolved_title, resolved_description, kind))


def discover_documents() -> list[Document]:
    documents: list[Document] = []

    # These are the five canonical knowledge-base documents. Their order is
    # intentionally the recommended learning path shown on the home page.
    primary = [
        ("课堂笔记-从零学B端硬件PM.md", "学习路线", "基础课 · 从零学 B 端硬件 PM", "主线课：从智能卡、NFC 和认证一路走到市场、产品、交付和面试。"),
        ("B端产品经理问题集.md", "面试与框架", "问题集 · B 端产品经理高频问答", "把职责、市场、需求、商业、交付和阶段门拆成可练习的回答骨架。"),
        ("工业网关商业论证.md", "商业论证", "案例 · 工业网关商业论证", "用制造与物流场景串起 JTBD、行业选择、商业模式、定价和五年财务模型。"),
        ("B端硬件PM-量产质量与变更闭环面试复习.md", "硬件交付", "交付 · 量产质量与变更闭环", "从 CTQ、EVT/DVT/PVT、良率到 ECN 和批次追溯，建立放行决策闭环。"),
        ("龙杰智能卡-面试PPT素材.md", "案例与面试", "案例 · 龙杰智能卡（ACS）面试素材", "将 ACS 的产品、客户、渠道、竞争和机会点整理为能带进面试的分析素材。"),
    ]
    for relative, group, title, description in primary:
        add_document(documents, relative, group, title=title, description=description, kind="核心资料")

    support = [
        ("video/index.md", "视频课程", "视频课 · B 端硬件 PM 教学视频", "12 节教学视频的播放入口与课程索引。", "媒体入口"),
        ("video/README.md", "视频课程", "视频课 · 生成与维护说明", None, "管道文档"),
        ("video/DESIGN.md", "视频课程", "视频课 · 视觉与动效规范", None, "管道文档"),
        ("podcast/index.md", "播客文稿", "播客 · 双人节目索引", "4 集完整双人播客和音频入口。", "媒体入口"),
        ("podcast/README.md", "播客文稿", "播客 · 写稿、合成与更新说明", None, "管道文档"),
    ]
    for relative, group, title, description, kind in support:
        add_document(documents, relative, group, title=title, description=description, kind=kind)

    # Keep every lesson manuscript searchable from the same documentation
    # shell. Source notes are useful for tracing how a lesson was assembled.
    lesson_root = ROOT / "video" / "lessons"
    for path in sorted(lesson_root.glob("*/script.md")):
        markdown = path.read_text(encoding="utf-8")
        title = first_heading(markdown) or path.parent.name
        add_document(documents, path.relative_to(ROOT).as_posix(), "视频讲稿", title=title, kind="逐字稿")
    for path in sorted(lesson_root.glob("*/source.md")):
        markdown = path.read_text(encoding="utf-8")
        title = first_heading(markdown) or path.parent.name
        add_document(documents, path.relative_to(ROOT).as_posix(), "课程素材", title=f"{title} · 来源笔记", kind="来源笔记")

    episode_root = ROOT / "podcast" / "episodes"
    for path in sorted(episode_root.glob("*/script.md")):
        markdown = path.read_text(encoding="utf-8")
        title = first_heading(markdown) or path.parent.name
        add_document(documents, path.relative_to(ROOT).as_posix(), "播客文稿", title=title, kind="双人稿")

    return documents


def slug(value: str, fallback: str) -> str:
    ascii_value = value.encode("ascii", "ignore").decode("ascii")
    ascii_value = re.sub(r"[^a-zA-Z0-9]+", "-", ascii_value).strip("-").lower()
    return ascii_value or fallback


def split_table_row(line: str) -> list[str]:
    line = line.strip()
    if line.startswith("|"):
        line = line[1:]
    if line.endswith("|"):
        line = line[:-1]
    cells: list[str] = []
    current: list[str] = []
    escaped = False
    for char in line:
        if char == "|" and not escaped:
            cells.append("".join(current).strip())
            current = []
            continue
        if char == "\\" and not escaped:
            escaped = True
            current.append(char)
            continue
        escaped = False
        current.append(char)
    cells.append("".join(current).strip())
    return cells


def is_table_separator(line: str) -> bool:
    cells = split_table_row(line)
    return bool(cells) and all(re.fullmatch(r":?-{3,}:?", cell.replace(" ", "")) for cell in cells)


def source_href(target: str, source_path: Path) -> str:
    """Make local Markdown links point to the source file from docs/site."""

    if target.startswith(("http://", "https://", "mailto:", "#", "javascript:")):
        return target
    clean_target, fragment = (target.split("#", 1) + [""])[:2] if "#" in target else (target, "")
    candidates = [ROOT / clean_target, source_path.parent / clean_target]
    destination = next((candidate.resolve() for candidate in candidates if candidate.exists()), None)
    if destination and destination.is_file():
        result = os.path.relpath(destination, SITE)
        return result + (f"#{fragment}" if fragment else "")
    return target


def inline_markdown(value: str, source_path: Path) -> str:
    """A small, dependency-free inline Markdown renderer for this corpus."""

    escaped = html.escape(value, quote=False)
    placeholders: dict[str, str] = {}

    def protect(content: str) -> str:
        token = f"\x00{len(placeholders)}\x00"
        placeholders[token] = content
        return token

    escaped = re.sub(r"`([^`]+)`", lambda match: protect(f'<code>{html.escape(match.group(1), quote=False)}</code>'), escaped)
    escaped = re.sub(
        r"!\[([^\]]*)\]\(([^)]+)\)",
        lambda match: protect(f'<img src="{html.escape(source_href(match.group(2), source_path), quote=True)}" alt="{html.escape(match.group(1), quote=True)}">'),
        escaped,
    )
    escaped = re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        lambda match: protect(f'<a href="{html.escape(source_href(match.group(2), source_path), quote=True)}">{match.group(1)}</a>'),
        escaped,
    )
    escaped = re.sub(r"\*\*([^*]+)\*\*|__([^_]+)__", lambda match: f"<strong>{match.group(1) or match.group(2)}</strong>", escaped)
    escaped = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)|(?<!_)_([^_]+)_(?!_)", lambda match: f"<em>{match.group(1) or match.group(2)}</em>", escaped)
    escaped = re.sub(r"~~([^~]+)~~", r"<del>\1</del>", escaped)
    escaped = escaped.replace("  ", "<br>")
    for token, content in placeholders.items():
        escaped = escaped.replace(token, content)
    return escaped


def heading_id(text: str, used: set[str], number: int) -> str:
    plain = re.sub(r"[`*_]", "", text)
    value = re.sub(r"[^\w\u4e00-\u9fff-]+", "-", plain.strip().lower()).strip("-")
    value = value or f"section-{number}"
    original = value
    suffix = 2
    while value in used:
        value = f"{original}-{suffix}"
        suffix += 1
    used.add(value)
    return value


def markdown_to_html(markdown: str, source_path: Path) -> tuple[str, list[tuple[str, str, int]]]:
    lines = markdown.replace("\r\n", "\n").split("\n")
    output: list[str] = []
    headings: list[tuple[str, str, int]] = []
    used_ids: set[str] = set()
    i = 0

    def is_special(index: int) -> bool:
        if index >= len(lines):
            return True
        value = lines[index].strip()
        return (
            not value
            or value.startswith("```")
            or re.match(r"^#{1,6}\s+", value) is not None
            or re.match(r"^>\s?", value) is not None
            or re.match(r"^\s*[-*+]\s+", value) is not None
            or re.match(r"^\s*\d+[.)]\s+", value) is not None
            or value.startswith("|")
            or re.fullmatch(r"(?:---+|\*\s*\*\s*\*|___+)", value) is not None
        )

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped:
            i += 1
            continue

        fenced = re.match(r"^\s*```\s*([\w+-]*)\s*$", line)
        if fenced:
            language = fenced.group(1) or "text"
            i += 1
            code_lines: list[str] = []
            while i < len(lines) and not re.match(r"^\s*```\s*$", lines[i]):
                code_lines.append(lines[i])
                i += 1
            if i < len(lines):
                i += 1
            code = html.escape("\n".join(code_lines), quote=False)
            output.append(
                f'<div class="code-block"><div class="code-label"><span>{html.escape(language.upper())}</span>'
                f'<button class="copy-code" type="button" data-copy-code="{html.escape("\n".join(code_lines), quote=True)}">复制</button></div>'
                f"<pre><code>{code}</code></pre></div>"
            )
            continue

        heading = re.match(r"^(#{1,6})\s+(.+?)\s*#*$", stripped)
        if heading:
            level = len(heading.group(1))
            text = heading.group(2).strip()
            # The shell already renders the document title above the source
            # content. Avoid displaying the same Markdown H1 twice.
            if level == 1 and not headings:
                i += 1
                continue
            anchor = heading_id(text, used_ids, len(headings) + 1)
            headings.append((text, anchor, level))
            output.append(f'<h{level} id="{anchor}">{inline_markdown(text, source_path)}</h{level}>')
            i += 1
            continue

        if stripped.startswith("|") and i + 1 < len(lines) and is_table_separator(lines[i + 1]):
            rows: list[list[str]] = [split_table_row(lines[i])]
            i += 2
            while i < len(lines) and lines[i].strip().startswith("|"):
                rows.append(split_table_row(lines[i]))
                i += 1
            header = rows[0]
            body = rows[1:]
            table = ["<div class=\"table-wrap\"><table><thead><tr>"]
            table.extend(f"<th>{inline_markdown(cell, source_path)}</th>" for cell in header)
            table.append("</tr></thead><tbody>")
            for row in body:
                table.append("<tr>")
                for index in range(len(header)):
                    cell = row[index] if index < len(row) else ""
                    table.append(f"<td>{inline_markdown(cell, source_path)}</td>")
                table.append("</tr>")
            table.append("</tbody></table></div>")
            output.append("".join(table))
            continue

        if re.match(r"^\s*[-*+]\s+", line):
            items: list[str] = []
            while i < len(lines):
                match = re.match(r"^\s*[-*+]\s+(.*)$", lines[i])
                if not match:
                    break
                items.append(match.group(1))
                i += 1
            output.append("<ul>" + "".join(f"<li>{inline_markdown(item, source_path)}</li>" for item in items) + "</ul>")
            continue

        if re.match(r"^\s*\d+[.)]\s+", line):
            items = []
            while i < len(lines):
                match = re.match(r"^\s*\d+[.)]\s+(.*)$", lines[i])
                if not match:
                    break
                items.append(match.group(1))
                i += 1
            output.append("<ol>" + "".join(f"<li>{inline_markdown(item, source_path)}</li>" for item in items) + "</ol>")
            continue

        if re.match(r"^>\s?", line):
            quote_lines: list[str] = []
            while i < len(lines) and re.match(r"^>\s?", lines[i]):
                quote_lines.append(re.sub(r"^>\s?", "", lines[i]).strip())
                i += 1
            output.append(f'<blockquote>{inline_markdown(" ".join(quote_lines), source_path)}</blockquote>')
            continue

        if re.fullmatch(r"(?:---+|\*\s*\*\s*\*|___+)", stripped):
            output.append("<hr>")
            i += 1
            continue

        paragraph: list[str] = [stripped]
        i += 1
        while i < len(lines) and not is_special(i):
            paragraph.append(lines[i].strip())
            i += 1
        output.append(f'<p>{inline_markdown(" ".join(paragraph), source_path)}</p>')

    return "\n".join(output), headings


def nav_html(documents: list[Document], active: str | None) -> str:
    groups: list[str] = []
    for document in documents:
        if document.group not in groups:
            groups.append(document.group)
    rendered: list[str] = []
    for group in groups:
        rendered.append(f'<div class="nav-group"><div class="nav-heading">{html.escape(group)}</div>')
        for index, document in enumerate(documents):
            if document.group != group:
                continue
            filename = page_filename(document, documents.index(document))
            active_class = " active" if filename == active else ""
            rendered.append(
                f'<a class="nav-link{active_class}" data-nav-link href="{filename}" title="{html.escape(document.title)}">'
                f'<span class="nav-index">{index + 1:02d}</span><span>{html.escape(document.title)}</span></a>'
            )
        rendered.append("</div>")
    return "".join(rendered)


def page_filename(document: Document, index: int) -> str:
    known = {
        "课堂笔记-从零学B端硬件PM.md": "learning-path",
        "B端产品经理问题集.md": "interview-question-bank",
        "工业网关商业论证.md": "industrial-gateway-case",
        "B端硬件PM-量产质量与变更闭环面试复习.md": "quality-and-change-gate",
        "龙杰智能卡-面试PPT素材.md": "acs-interview-case",
        "video/index.md": "video-index",
        "video/README.md": "video-pipeline",
        "video/DESIGN.md": "video-design",
        "podcast/index.md": "podcast-index",
        "podcast/README.md": "podcast-pipeline",
    }
    stem = known.get(document.source)
    if stem is None and document.source.startswith("video/lessons/"):
        match = re.search(r"video/lessons/(\d+)-", document.source)
        stem = f"video-lesson-{match.group(1)}" if match else "video-lesson"
        stem += "-source" if document.path.name == "source.md" else "-script"
    if stem is None and document.source.startswith("podcast/episodes/"):
        match = re.search(r"podcast/episodes/(\d+)-", document.source)
        stem = f"podcast-{match.group(1)}" if match else "podcast-episode"
        stem += "-script"
    stem = stem or slug(document.title, f"document-{index + 1:02d}")
    return f"{index + 1:02d}-{stem}.html"


def page_shell(*, title: str, description: str, active: str | None, nav: str, body: str, toc: str = "", eyebrow: str = "B 端硬件产品经理知识库") -> str:
    article_class = "article-wrap home-wrap" if "home-hero" in body else "article-wrap"
    return f'''<!doctype html>
<html lang="zh-CN" data-theme="light">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <meta name="description" content="{html.escape(description, quote=True)}">
  <title>{html.escape(title)} · B 端硬件知识库</title>
  <link rel="stylesheet" href="theme.css">
</head>
<body>
  <div class="mobile-backdrop" data-sidebar-close></div>
  <aside class="sidebar" id="sidebar">
    <div class="brand-block">
      <a class="brand" href="index.html"><span class="brand-mark">B<span>×</span>H</span><span><strong>B 端硬件</strong><small>PRODUCT FIELD NOTES</small></span></a>
      <button class="sidebar-close" type="button" data-sidebar-close aria-label="关闭导航">×</button>
    </div>
    <div class="sidebar-intro">把市场判断、硬件交付和面试表达，放进同一条可回看的路径。</div>
    <nav class="sidebar-nav" aria-label="文档导航">
      <a class="nav-home" href="index.html"><span class="home-dot">↗</span><span>知识库首页</span></a>
      {nav}
    </nav>
    <div class="sidebar-footer"><span class="status-dot"></span>本地离线文档站 <span class="footer-version">v1.0</span></div>
  </aside>
  <div class="page-frame">
    <header class="topbar">
      <button class="menu-trigger" type="button" data-sidebar-open aria-label="打开导航"><span></span><span></span><span></span></button>
      <div class="breadcrumb"><a href="index.html">知识库</a><span>/</span><span>{html.escape(eyebrow)}</span></div>
      <label class="search-box"><span class="search-icon">⌕</span><input type="search" data-doc-search placeholder="搜索文档标题…" aria-label="搜索文档标题"><kbd>⌘ K</kbd></label>
      <button class="theme-toggle" type="button" data-theme-toggle aria-label="切换主题"><span class="sun">☼</span><span class="moon">◐</span></button>
    </header>
    <main class="content-layout">
      <article class="{article_class}">{body}</article>
      {toc}
    </main>
  </div>
  <script src="app.js" defer></script>
</body>
</html>'''


def render_toc(headings: list[tuple[str, str, int]]) -> str:
    visible = [(text, anchor, level) for text, anchor, level in headings if level in (2, 3)]
    if not visible:
        return '<aside class="toc"><div class="toc-title">本页内容</div><div class="toc-empty">这是一份短文档，直接阅读即可。</div></aside>'
    items = []
    for text, anchor, level in visible:
        items.append(f'<a class="toc-link level-{level}" href="#{anchor}">{html.escape(text)}</a>')
    return f'<aside class="toc"><div class="toc-title">本页内容</div>{"".join(items)}</aside>'


def article_body(document: Document, documents: list[Document], index: int) -> tuple[str, list[tuple[str, str, int]], str]:
    markdown = document.path.read_text(encoding="utf-8")
    content, headings = markdown_to_html(markdown, document.path)
    filename = page_filename(document, index)
    previous = page_filename(documents[index - 1], index - 1) if index > 0 else "index.html"
    previous_title = documents[index - 1].title if index > 0 else "知识库首页"
    next_page = page_filename(documents[index + 1], index + 1) if index + 1 < len(documents) else "index.html"
    next_title = documents[index + 1].title if index + 1 < len(documents) else "知识库首页"
    source_href_value = os.path.relpath(document.path, SITE)
    return (
        f'<div class="article-meta"><span class="eyebrow">{html.escape(document.group)}</span><span class="meta-separator">·</span><span>{html.escape(document.kind)}</span></div>'
        f'<h1>{html.escape(document.title)}</h1><p class="lede">{html.escape(document.description)}</p>'
        f'<div class="article-rule"></div><div class="prose">{content}</div>'
        f'<footer class="source-footer"><span>源文件</span><a href="{html.escape(source_href_value, quote=True)}">{html.escape(document.source)}</a><span class="source-note">原始 Markdown 保留在项目根目录</span></footer>'
        f'<nav class="page-nav" aria-label="上一篇和下一篇"><a class="page-nav-item prev" href="{previous}"><small>上一份</small><strong>← {html.escape(previous_title)}</strong></a><a class="page-nav-item next" href="{next_page}"><small>下一份</small><strong>{html.escape(next_title)} →</strong></a></nav>'
    ), headings, filename


def render_index(documents: list[Document]) -> str:
    nav = nav_html(documents, None)
    primary = documents[:5]
    cards = []
    card_kickers = ["01 / 学习路线", "02 / 面试训练", "03 / 商业判断", "04 / 量产交付", "05 / 案例拆解"]
    card_colors = ["coral", "teal", "ochre", "blue", "plum"]
    for index, document in enumerate(primary):
        cards.append(
            f'<a class="entry-card {card_colors[index]}" href="{page_filename(document, index)}"><div class="entry-top"><span>{card_kickers[index]}</span><span class="entry-arrow">↗</span></div><h3>{html.escape(document.title.split(" · ", 1)[-1])}</h3><p>{html.escape(document.description)}</p><div class="entry-foot"><span>{html.escape(document.kind)}</span><span>阅读文档</span></div></a>'
        )
    video_index = next((index for index, doc in enumerate(documents) if doc.path.as_posix().endswith("video/index.md")), 0)
    podcast_index = next((index for index, doc in enumerate(documents) if doc.path.as_posix().endswith("podcast/index.md")), 0)
    lesson_count = sum(1 for document in documents if document.group == "视频讲稿")
    episode_count = sum(1 for document in documents if document.group == "播客文稿" and document.path.name == "script.md")
    body = f'''
<section class="home-hero">
  <div class="hero-copy"><div class="hero-kicker"><span class="live-line"></span> FIELD NOTES / 2026</div><h1>把硬件产品经理<br><em>讲明白、做落地。</em></h1><p>一套面向 B 端硬件产品经理的本地知识库：从市场和客户，到产品定义、阶段门、量产质量，再到面试表达。</p><div class="hero-actions"><a class="button button-dark" href="{page_filename(primary[0], 0)}">从学习路线开始 <span>→</span></a><a class="text-link" href="{page_filename(primary[1], 1)}">直接进入问题集 <span>↗</span></a></div></div>
  <div class="hero-visual"><div class="visual-grid"></div><div class="orbit orbit-a"></div><div class="orbit orbit-b"></div><div class="visual-card"><span class="visual-label">PM FIELD MAP</span><strong>市场 → 产品 → 交付</strong><small>把每个决定落到证据</small><div class="visual-bars"><i></i><i></i><i></i><i></i><i></i></div></div><span class="visual-caption">B / H<br>01—05</span></div>
</section>
<section class="stats-strip"><div><strong>{len(documents)}</strong><span>份可检索文档</span></div><div><strong>05</strong><span>核心学习模块</span></div><div><strong>{lesson_count:02d}</strong><span>节视频讲稿</span></div><div><strong>{episode_count:02d}</strong><span>份播客文稿</span></div></section>
<section class="home-section"><div class="section-heading"><div><span class="section-kicker">START HERE</span><h2>核心路径</h2></div><p>不按文件夹找资料，按产品经理真正做决定的顺序阅读。</p></div><div class="entry-grid">{"".join(cards)}</div></section>
<section class="home-section route-section"><div class="section-heading"><div><span class="section-kicker">THE PRODUCT LOOP</span><h2>一条完整的产品闭环</h2></div><p>每一步都对应一类输出物，也对应一类面试证据。</p></div><div class="route-track"><div class="route-step"><span>01</span><strong>看懂场景</strong><small>客户、JTBD、决策链</small></div><div class="route-step"><span>02</span><strong>做出判断</strong><small>行业、竞品、商业模式</small></div><div class="route-step"><span>03</span><strong>定义产品</strong><small>BRD、规格、优先级</small></div><div class="route-step"><span>04</span><strong>推进交付</strong><small>EVT / DVT / PVT / MP</small></div><div class="route-step"><span>05</span><strong>复盘经营</strong><small>质量、RMA、生命周期</small></div></div></section>
<section class="home-section split-section"><div class="mindmap-panel"><div class="panel-heading"><div><span class="section-kicker">SYSTEM MAP</span><h2>知识地图</h2></div><span class="panel-badge">可视化</span></div><p>把“懂技术、懂客户、懂交付”放到一张图里，先建立整体坐标，再回到具体章节。</p><img src="../../diagram/B端硬件产品经理学习思维导图.svg" alt="B端硬件产品经理学习思维导图" loading="lazy"><a class="text-link" href="../../diagram/B端硬件产品经理学习思维导图.svg">查看原图 <span>↗</span></a></div><div class="media-panel"><div class="panel-heading"><div><span class="section-kicker">LISTEN / WATCH</span><h2>媒体与讲稿</h2></div><span class="panel-badge">{lesson_count + episode_count:02d} 项</span></div><a class="media-row" href="{page_filename(documents[video_index], video_index)}"><span class="media-icon video-icon">▶</span><span><strong>视频课程</strong><small>{lesson_count} 节，从智能卡到综合面试</small></span><b>→</b></a><a class="media-row" href="{page_filename(documents[podcast_index], podcast_index)}"><span class="media-icon audio-icon">◖</span><span><strong>双人播客</strong><small>{episode_count} 份脚本，适合通勤复习</small></span><b>→</b></a><div class="media-note"><span class="status-dot"></span>音频与视频仍保留原有播放入口</div></div></section>
<footer class="home-footer"><div><strong>本地知识库</strong><span>源文件可追溯 · HTML 可离线打开 · 适合持续增量整理</span></div><a href="../README.md">项目说明 ↗</a></footer>
'''
    return page_shell(title="B端硬件产品经理知识库", description="B端硬件产品经理学习、商业论证、量产质量与面试文稿的本地 HTML 知识库。", active=None, nav=nav, body=body, eyebrow="知识库首页")


def build() -> list[Document]:
    documents = discover_documents()
    SITE.mkdir(parents=True, exist_ok=True)
    for old in SITE.glob("*.html"):
        old.unlink()
    shutil.copy2(DOCS / "theme.css", SITE / "theme.css")
    shutil.copy2(DOCS / "app.js", SITE / "app.js")
    (SITE / "index.html").write_text(render_index(documents), encoding="utf-8")
    nav = nav_html(documents, None)
    for index, document in enumerate(documents):
        content, headings, filename = article_body(document, documents, index)
        page = page_shell(
            title=document.title,
            description=document.description,
            active=filename,
            nav=nav_html(documents, filename),
            body=content,
            toc=render_toc(headings),
            eyebrow=document.group,
        )
        (SITE / filename).write_text(page, encoding="utf-8")
    return documents


if __name__ == "__main__":
    built = build()
    print(f"built {len(built)} HTML documents in {SITE}")
