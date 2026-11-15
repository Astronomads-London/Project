import re
from pathlib import Path

import markdown
from flask import Blueprint, abort, render_template
from markupsafe import Markup

policies_bp = Blueprint("policies", __name__)
POLICIES_DIR = Path(__file__).resolve().parents[1] / "policies"


@policies_bp.route("/<slug>", methods=["GET"])
def learn_page(slug):
    if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", slug):
        abort(404)

    content_path = POLICIES_DIR / f"{slug}.md"
    if not content_path.is_file():
        abort(404)

    source = content_path.read_text(encoding="utf-8")
    title = slug.replace("-", " ").title()
    content_html = Markup(markdown.markdown(source, extensions=["fenced_code", "tables"]))
    return render_template("learn-page.html", title=title, content=content_html)


