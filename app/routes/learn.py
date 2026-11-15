import re
from pathlib import Path

import markdown
from flask import Blueprint, abort, render_template
from markupsafe import Markup

learn_bp = Blueprint("learn", __name__)
LEARN_CONTENT_DIR = Path(__file__).resolve().parents[1] / "learn_content"


@learn_bp.route("/<slug>", methods=["GET"])
def learn_page(slug):
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
        abort(404)

    content_path = LEARN_CONTENT_DIR / f"{slug}.md"
    if not content_path.is_file():
        abort(404)

    source = content_path.read_text(encoding="utf-8")
    title = slug.replace("-", " ").title()
    content_html = Markup(markdown.markdown(source, extensions=["fenced_code", "tables"]))
    return render_template("learn-page.html", title=title, content=content_html)


@learn_bp.route("/", methods=["GET"])
def learn_index():
    pages = []
    for content_path in sorted(LEARN_CONTENT_DIR.glob("*.md")):
        slug = content_path.stem
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
            continue

        title = slug.replace("-", " ").title()
        source = content_path.read_text(encoding="utf-8")
        for line in source.splitlines():
            if line.startswith("# "):
                title = line[2:].strip()
                break

        pages.append({
            "slug": slug,
            "title": title,
            "search_text": f"{title} {slug} {source}",
        })

    return render_template("learn-index.html", pages=pages)
