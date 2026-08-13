"""Export the latest Markdown daily report as a demo-friendly HTML page."""

from __future__ import annotations

import html
import re
import sys
from pathlib import Path

try:
    import markdown
except ModuleNotFoundError:  # pragma: no cover - exercised only before dependencies are installed.
    markdown = None


REPO_ROOT = Path(__file__).resolve().parents[1]
OUTPUT_DIR = REPO_ROOT / "output"


def find_latest_markdown(output_dir: Path = OUTPUT_DIR) -> Path:
    reports = sorted(
        output_dir.glob("hotspot-daily-*.md"),
        key=lambda path: path.stat().st_mtime,
        reverse=True,
    )
    if not reports:
        raise FileNotFoundError(f"No hotspot-daily-*.md files found in {output_dir}")
    return reports[0]


def render_html(markdown_path: Path, output_path: Path, page_title: str = "内容工作台") -> Path:
    source = markdown_path.read_text(encoding="utf-8")
    if markdown is not None:
        body = markdown.markdown(
            source,
            extensions=["extra", "tables", "fenced_code", "toc"],
            output_format="html5",
        )
    else:
        body = fallback_markdown_to_html(source)
    page = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{html.escape(page_title)}</title>
  <style>
    :root {{
      --ink: #172033;
      --muted: #667085;
      --line: #d8e0ef;
      --paper: #ffffff;
      --wash: #f3f7fb;
      --accent: #0f6b5f;
      --accent-soft: #e3f3ef;
    }}
    * {{ box-sizing: border-box; }}
    body {{
      margin: 0;
      color: var(--ink);
      background:
        linear-gradient(135deg, rgba(15, 107, 95, 0.10), transparent 34%),
        linear-gradient(315deg, rgba(37, 99, 235, 0.08), transparent 40%),
        var(--wash);
      font-family: "Avenir Next", "PingFang SC", "Microsoft YaHei", sans-serif;
      line-height: 1.72;
    }}
    main {{
      width: min(980px, calc(100vw - 32px));
      margin: 32px auto;
      padding: 34px;
      background: var(--paper);
      border: 1px solid rgba(216, 224, 239, 0.9);
      border-radius: 10px;
      box-shadow: 0 22px 70px rgba(23, 32, 51, 0.10);
    }}
    .meta {{
      margin-bottom: 24px;
      padding: 12px 14px;
      color: var(--muted);
      background: var(--accent-soft);
      border-left: 4px solid var(--accent);
      border-radius: 8px;
      font-size: 14px;
    }}
    h1, h2, h3 {{ line-height: 1.25; }}
    h1 {{ margin: 0 0 18px; font-size: clamp(30px, 5vw, 46px); }}
    h2 {{ margin-top: 42px; padding-bottom: 10px; border-bottom: 2px solid var(--line); }}
    h3 {{ margin-top: 28px; }}
    a {{ color: var(--accent); font-weight: 700; text-decoration: none; }}
    a:hover {{ text-decoration: underline; }}
    ul {{ padding-left: 1.35rem; }}
    li {{ margin: 6px 0; }}
    code {{
      padding: 2px 5px;
      background: #edf2f7;
      border-radius: 5px;
    }}
    pre {{
      overflow: auto;
      padding: 16px;
      background: #101828;
      color: #f8fafc;
      border-radius: 8px;
    }}
    pre code {{ padding: 0; background: transparent; color: inherit; }}
    table {{
      width: 100%;
      border-collapse: collapse;
      margin: 18px 0;
      overflow: hidden;
      border-radius: 8px;
    }}
    th, td {{
      padding: 10px 12px;
      border: 1px solid var(--line);
      text-align: left;
      vertical-align: top;
    }}
    th {{ background: #eef6f4; }}
    @media (max-width: 640px) {{
      main {{ margin: 0; width: 100%; min-height: 100vh; padding: 22px; border-radius: 0; }}
    }}
  </style>
</head>
<body>
  <main>
    <div class="meta">内容运营 Agent · 内容工作台<br>作者：靳思嘉</div>
    {body}
  </main>
</body>
</html>
"""
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(page, encoding="utf-8")
    return output_path


def export_latest_report(output_dir: Path = OUTPUT_DIR) -> Path:
    markdown_path = find_latest_markdown(output_dir)
    return render_html(markdown_path, output_dir / "latest-report.html")


def export_latest_workbench(output_dir: Path = OUTPUT_DIR) -> Path:
    markdown_path = output_dir / "latest-workbench.md"
    if not markdown_path.exists():
        raise FileNotFoundError(f"No latest-workbench.md found in {output_dir}")
    return render_html(markdown_path, output_dir / "latest-workbench.html", "内容工作台")


def fallback_markdown_to_html(source: str) -> str:
    lines = source.splitlines()
    html_parts: list[str] = []
    in_list = False
    in_code = False
    code_lines: list[str] = []

    def close_list() -> None:
        nonlocal in_list
        if in_list:
            html_parts.append("</ul>")
            in_list = False

    def flush_code() -> None:
        nonlocal code_lines
        html_parts.append(f"<pre><code>{html.escape(chr(10).join(code_lines))}</code></pre>")
        code_lines = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("```"):
            if in_code:
                flush_code()
                in_code = False
            else:
                close_list()
                in_code = True
            continue
        if in_code:
            code_lines.append(line)
            continue
        if not stripped:
            close_list()
            continue
        if stripped.startswith("#"):
            close_list()
            level = min(len(stripped) - len(stripped.lstrip("#")), 6)
            text = stripped[level:].strip()
            html_parts.append(f"<h{level}>{html.escape(text)}</h{level}>")
            continue
        if stripped.startswith("- "):
            if not in_list:
                html_parts.append("<ul>")
                in_list = True
            html_parts.append(f"<li>{format_inline_markdown(stripped[2:])}</li>")
            continue
        close_list()
        html_parts.append(f"<p>{format_inline_markdown(stripped)}</p>")
    close_list()
    if in_code:
        flush_code()
    return "\n".join(html_parts)


def format_inline_markdown(text: str) -> str:
    escaped = html.escape(text)
    # Match the subset used by generated workbench files before converting links.
    formatted = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", escaped)
    formatted = re.sub(r"(?<!\*)\*([^*]+)\*(?!\*)", r"<em>\1</em>", formatted)
    return re.sub(
        r"\[([^\]]+)\]\(([^)]+)\)",
        lambda match: f'<a href="{html.escape(match.group(2), quote=True)}" target="_blank" rel="noopener noreferrer">{match.group(1)}</a>',
        formatted,
    )


if __name__ == "__main__":
    try:
        print(export_latest_report())
        print(export_latest_workbench())
    except Exception as exc:
        print(f"Failed to export HTML report: {exc}", file=sys.stderr)
        raise
