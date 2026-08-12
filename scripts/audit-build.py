#!/usr/bin/env python3
"""Audit generated Hugo output using only the Python standard library."""

from __future__ import annotations

import base64
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import sys
import tomllib
from urllib.parse import unquote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
PUBLIC = ROOT / "public"
CONTENT = ROOT / "content"
I18N = ROOT / "i18n"
HEADERS = ROOT / "static" / "_headers"
LASTMOD_RE = re.compile(
    r"^lastmod:\s*\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}-\d{2}:\d{2}\s*$",
    re.MULTILINE,
)


class PageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.ids: set[str] = set()
        self.refs: list[tuple[str, str]] = []
        self.images: list[dict[str, str | None]] = []
        self.meta: list[dict[str, str | None]] = []
        self.links: list[dict[str, str | None]] = []
        self.html_lang: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "html":
            self.html_lang = values.get("lang")
        if identifier := values.get("id"):
            self.ids.add(identifier)
        if tag in {"a", "link"} and (href := values.get("href")):
            self.refs.append((tag, href))
        if tag in {"img", "script", "iframe", "source"} and (src := values.get("src")):
            self.refs.append((tag, src))
        if tag == "img":
            self.images.append(values)
        elif tag == "meta":
            self.meta.append(values)
        elif tag == "link":
            self.links.append(values)


def parse_pages(errors: list[str]) -> tuple[dict[Path, PageParser], dict[Path, str]]:
    html_files = sorted(PUBLIC.rglob("*.html"))
    if not html_files:
        errors.append("public/ contains no HTML; run the production build first")
        return {}, {}

    parsers: dict[Path, PageParser] = {}
    sources: dict[Path, str] = {}
    for path in html_files:
        source = path.read_text(encoding="utf-8")
        parser = PageParser()
        parser.feed(source)
        resolved = path.resolve()
        parsers[resolved] = parser
        sources[resolved] = source
    return parsers, sources


def local_target(page: Path, reference: str) -> tuple[Path | None, str]:
    url = urlsplit(reference)
    if url.scheme or reference.startswith("//") or not url.path:
        return None, url.fragment

    if url.path.startswith("/"):
        relative = Path(unquote(url.path.lstrip("/")))
    else:
        relative = page.relative_to(PUBLIC.resolve()).parent / unquote(url.path)

    target = (PUBLIC / relative).resolve()
    if url.path.endswith("/") or target.is_dir() or (not target.exists() and not target.suffix):
        target /= "index.html"
    return target, url.fragment


def audit_content(errors: list[str]) -> None:
    content_files = sorted(CONTENT.glob("*.md"))
    for path in content_files:
        source = path.read_text(encoding="utf-8")
        front_matter = re.match(r"^---\n(.*?)\n---", source, re.DOTALL)
        if not front_matter:
            errors.append(f"{path.relative_to(ROOT)}: missing YAML front matter")
        elif not LASTMOD_RE.search(front_matter.group(1)):
            errors.append(f"{path.relative_to(ROOT)}: missing or invalid lastmod")

    catalogs = {
        path.stem: set(tomllib.loads(path.read_text(encoding="utf-8")))
        for path in sorted(I18N.glob("*.toml"))
    }
    all_keys = set().union(*catalogs.values())
    for language, keys in catalogs.items():
        if missing := sorted(all_keys - keys):
            errors.append(f"i18n/{language}.toml: missing keys {', '.join(missing)}")


def audit_pages(
    parsers: dict[Path, PageParser], sources: dict[Path, str], errors: list[str]
) -> set[str]:
    inline_hashes: set[str] = set()

    for page, parser in parsers.items():
        relative_page = page.relative_to(PUBLIC.resolve())
        source = sources[page]
        is_redirect = any(
            meta.get("http-equiv", "").lower() == "refresh" for meta in parser.meta
        )

        if not is_redirect:
            names = {meta.get("name") for meta in parser.meta}
            properties = {meta.get("property") for meta in parser.meta}
            relations = {link.get("rel") for link in parser.links}
            if not parser.html_lang:
                errors.append(f"{relative_page}: missing html lang")
            if "description" not in names:
                errors.append(f"{relative_page}: missing meta description")
            if "canonical" not in relations:
                errors.append(f"{relative_page}: missing canonical link")
            for required in {"og:title", "og:description", "og:url", "og:image"}:
                if required not in properties:
                    errors.append(f"{relative_page}: missing {required}")

        for image in parser.images:
            if "alt" not in image:
                errors.append(f"{relative_page}: image {image.get('src')} has no alt attribute")

        for _, reference in parser.refs:
            target, fragment = local_target(page, reference)
            if target is None:
                continue
            try:
                target.relative_to(PUBLIC.resolve())
            except ValueError:
                errors.append(f"{relative_page}: reference escapes public/: {reference}")
                continue
            if not target.exists():
                errors.append(f"{relative_page}: broken internal reference {reference}")
            elif fragment and target.suffix == ".html":
                target_parser = parsers.get(target)
                if target_parser and fragment not in target_parser.ids:
                    errors.append(f"{relative_page}: missing fragment target {reference}")

        if re.search(r"<style(?:\s[^>]*)?>", source, re.IGNORECASE):
            errors.append(f"{relative_page}: inline style block violates CSP")
        if re.search(r"\sstyle=", source, re.IGNORECASE):
            errors.append(f"{relative_page}: inline style attribute violates CSP")

        for match in re.finditer(r"<script([^>]*)>(.*?)</script>", source, re.DOTALL | re.IGNORECASE):
            attrs, body = match.groups()
            if re.search(r"\bsrc=", attrs):
                continue
            if not re.search(r"\btype=application/ld\+json\b", attrs, re.IGNORECASE):
                errors.append(f"{relative_page}: executable inline script violates CSP")
                continue
            try:
                json.loads(body)
            except json.JSONDecodeError as error:
                errors.append(f"{relative_page}: invalid JSON-LD: {error}")
            digest = base64.b64encode(hashlib.sha256(body.encode()).digest()).decode()
            inline_hashes.add(digest)

    # A home reaproveita as FAQs marcadas `home: true` no front matter de
    # o-que-fazemos. O número certo é quantas estão marcadas — não uma
    # constante aqui, que ficaria errada assim que alguém marcasse mais uma.
    home_faqs = {
        Path("index.html"): ("o-que-fazemos.md", "/o-que-fazemos/#perguntas-frequentes"),
        Path("es/index.html"): ("o-que-fazemos.es.md", "/es/que-hacemos/#perguntas-frequentes"),
        Path("en/index.html"): ("o-que-fazemos.en.md", "/en/what-we-do/#perguntas-frequentes"),
    }
    for relative, (content_file, faq_href) in home_faqs.items():
        expected = len(
            re.findall(
                r"^\s+home:\s*true\s*$",
                (CONTENT / content_file).read_text(encoding="utf-8"),
                re.MULTILINE,
            )
        )
        page = (PUBLIC / relative).resolve()
        source = sources.get(page, "")
        count = len(re.findall(r"\bclass=faq-item\b", source))
        if not expected:
            errors.append(f"content/{content_file}: no FAQ marked `home: true`")
        elif count != expected:
            errors.append(
                f"{relative}: {expected} FAQs marked `home: true` in "
                f"content/{content_file}, but {count} rendered"
            )
        if f'href={faq_href}' not in source:
            errors.append(f"{relative}: missing localized FAQ link {faq_href}")

    return inline_hashes


def audit_csp(errors: list[str]) -> None:
    headers = HEADERS.read_text(encoding="utf-8")
    match = re.search(r"^\s*Content-Security-Policy:\s*(.+)$", headers, re.MULTILINE)
    if not match:
        errors.append("static/_headers: missing Content-Security-Policy")
        return

    policy = match.group(1)
    if "'unsafe-inline'" in policy:
        errors.append("static/_headers: CSP must not allow unsafe-inline")
    if "frame-src https://maps.google.com https://www.google.com" not in policy:
        errors.append("static/_headers: CSP does not allow both Google Maps frame origins")

    # JSON-LD is a data block, never evaluated, so script-src does not apply to
    # it and hashing it buys nothing. Worse, each block embeds a per-URL @id, so
    # an allowlist would need a new entry for every page ever added. Guard
    # against the hashes creeping back in.
    if re.search(r"'sha256-", policy):
        errors.append(
            "static/_headers: CSP carries script hashes; JSON-LD data blocks are "
            "not subject to script-src and executable JS is a same-origin asset"
        )


def main() -> int:
    errors: list[str] = []
    audit_content(errors)
    parsers, sources = parse_pages(errors)
    inline_hashes = audit_pages(parsers, sources, errors)
    audit_csp(errors)

    if errors:
        print("Generated-site audit failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(
        f"Generated-site audit passed: {len(parsers)} HTML files, "
        f"{len(inline_hashes)} JSON-LD blocks, 3 localized homepages."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
