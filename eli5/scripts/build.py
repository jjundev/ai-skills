"""Build an ELI5 explainer HTML from a body fragment and the note template.

The template (assets/note-template.html) is a verbatim copy of the
bio-review-pack note template. This script only fills its {{PLACEHOLDERS}}:

    python build.py --title "DNS" --subtitle "인터넷의 전화번호부" \
        --slug dns --sections body.html --out ELI5_dns.html

<script> blocks inside the fragment are moved to {{SCRIPTS}} (before </body>),
the left TOC is generated from <section id> + <h2>, and the result is checked
for leftover placeholders, missing topics, and duplicate ids.
"""
from __future__ import annotations

import argparse
import html
import re
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
TEMPLATE = SKILL_DIR / "assets" / "note-template.html"

PLACEHOLDER_RE = re.compile(r"\{\{([A-Z_]+)\}\}")
SCRIPT_RE = re.compile(r"<script\b[^>]*>.*?</script>", re.S | re.I)
SECTION_RE = re.compile(r"<section\b[^>]*\bid=\"([^\"]+)\"[^>]*>\s*<h2\b[^>]*>(.*?)</h2>", re.S | re.I)
TOPIC_RE = re.compile(r"<article\b[^>]*\bclass=\"[^\"]*\btopic\b[^\"]*\"[^>]*>", re.I)
ID_RE = re.compile(r"\bid=\"([^\"]+)\"")
TAG_RE = re.compile(r"<[^>]+>")
SLUG_RE = re.compile(r"[a-z0-9][a-z0-9-]*")


class BuildError(Exception):
    pass


def esc(text: str) -> str:
    return html.escape(text, quote=True)


def build(title: str, subtitle: str, slug: str, fragment: str,
          brand: str = "ELI5", footer: str = "", template: str | None = None) -> str:
    if not SLUG_RE.fullmatch(slug):
        raise BuildError(f"slug는 영소문자·숫자·하이픈만 씁니다: {slug!r}")
    if template is None:
        template = TEMPLATE.read_text(encoding="utf-8")

    body = SCRIPT_RE.sub("", fragment)
    scripts = SCRIPT_RE.findall(fragment)

    sections = SECTION_RE.findall(body)
    if not sections:
        raise BuildError("<section id=…><h2>…</h2> 형태의 섹션이 없습니다")
    if not TOPIC_RE.search(body):
        raise BuildError('<article class="topic"> 가 하나도 없습니다')
    ids = ID_RE.findall(body)
    dupes = sorted({i for i in ids if ids.count(i) > 1})
    if dupes:
        raise BuildError(f"id 중복: {', '.join(dupes)}")
    reserved = sorted(set(ids) & set(ID_RE.findall(template)))
    if reserved:
        raise BuildError(f"템플릿이 쓰는 id와 겹칩니다: {', '.join(reserved)}")
    left = PLACEHOLDER_RE.findall(body)
    if left:
        raise BuildError(f"조각에 자리표시자가 남아 있습니다: {sorted(set(left))}")

    toc = "".join(
        f'<a href="#{sid}">{esc(TAG_RE.sub("", h2).strip())}</a>' for sid, h2 in sections
    )
    values = {
        "PAGE_TITLE": esc(f"ELI5: {title}"),
        "DESCRIPTION": esc(subtitle),
        "RANGE": esc(f"eli5-{slug}"),
        "BRAND": esc(brand),
        "TITLE": esc(title),
        "SUBTITLE": esc(subtitle),
        "TOC": toc,
        "SECTIONS": body.strip("\n"),
        "FOOTER": esc(footer),
        "SCRIPTS": "\n".join(f"  {s}" for s in scripts),
    }

    missing = sorted(set(PLACEHOLDER_RE.findall(template)) - values.keys())
    if missing:
        raise BuildError(f"채울 값이 없는 자리표시자: {missing}")
    # 한 번에 치환해 본문 속 텍스트가 다시 치환되지 않게 한다
    return PLACEHOLDER_RE.sub(lambda m: values[m.group(1)], template)


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(description="ELI5 정리노트 양식 HTML 빌드")
    p.add_argument("--title", required=True)
    p.add_argument("--subtitle", required=True, help="비유를 담은 한 줄 요약")
    p.add_argument("--slug", required=True, help="영소문자·숫자·하이픈 (읽음 기록 키)")
    p.add_argument("--sections", required=True, type=Path, help="본문 조각 HTML 파일")
    p.add_argument("--out", required=True, type=Path)
    p.add_argument("--brand", default="ELI5")
    p.add_argument("--footer", default="")
    a = p.parse_args(argv)

    try:
        out = build(a.title, a.subtitle, a.slug, a.sections.read_text(encoding="utf-8"),
                    brand=a.brand, footer=a.footer)
    except (BuildError, OSError) as e:
        print(f"FAIL: {e}", file=sys.stderr)
        return 1
    a.out.parent.mkdir(parents=True, exist_ok=True)
    a.out.write_text(out, encoding="utf-8")
    print(f"OK: {a.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
