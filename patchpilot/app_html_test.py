"""Static checks of patchpilot/app.html (standard library only, no browser):
every $("id") used by the script exists, static buttons explain themselves, dialogs are labelled."""
import re
from html.parser import HTMLParser
from pathlib import Path

SRC = (Path(__file__).parent / "app.html").read_text(encoding="utf-8")


class P(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids, self.buttons = set(), []

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a:
            self.ids.add(a["id"])
        if tag == "button":
            self.buttons.append(a)


def main():
    p = P()
    p.feed(SRC)
    script = re.search(r"<script>([\s\S]*)</script>", SRC).group(1)
    used = set(re.findall(r'\$\("([A-Za-z0-9_-]+)"\)', script))
    missing = sorted(used - p.ids)
    assert not missing, f"ids used in script but missing in HTML: {missing}"
    bare = [b.get("id") for b in p.buttons if not b.get("title") and not b.get("aria-label")]
    assert not bare, f"static buttons without a title: {bare}"
    for d in ("cmp", "race"):
        assert re.search(r'<div id="%s"[^>]*role="dialog"[^>]*aria-modal="true"' % d, SRC), f"{d}: dialog role missing"
    n = len(re.findall(r'el\("button"', script))
    dyn = len(re.findall(r'el\("button"[^\n]*', script))
    print(f"app_html_test ok: {len(used)} ids, {len(p.buttons)} static buttons, {n} dynamic button sites ({dyn} lines)")


if __name__ == "__main__":
    main()
