#!/usr/bin/env python3
"""Audit generated Hugo output using only the Python standard library."""

from __future__ import annotations

import base64
from datetime import datetime
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
HUGO_CONFIG = ROOT / "hugo.toml"

# Únicas chaves legítimas de params.postal (ver hugo.toml e README.md).
# Qualquer coisa além disso é sintoma da armadilha do TOML: uma chave escrita
# depois de [params.postal] vira filha dela em vez de ficar em [params].
POSTAL_KEYS = {
    "street",
    "district",
    "city",
    "region",
    "postalCode",
    "country",
    "latitude",
    "longitude",
}

# Chaves de nível [params] que o README manda ficarem ANTES de [params.postal].
# Servem de canário do sintoma: se [params.postal] "engoliu" o resto do
# arquivo, é exatamente uma dessas que some de params — sem erro de Hugo,
# porque params.postal.contatoEmail é TOML válido, só que ninguém lê de lá.
CRITICAL_PARAMS_KEYS = (
    "contatoEmail",
    "rhEmail",
    "googleSiteVerification",
    "bingSiteVerification",
    "whatsappPhone",
    "phone",
)
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
        self.title: str | None = None
        self._in_title = False

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
        if tag == "title":
            self._in_title = True

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title = (self.title or "") + data


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


def audit_hugo_config(errors: list[str]) -> None:
    config = tomllib.loads(HUGO_CONFIG.read_text(encoding="utf-8"))
    params = config.get("params", {})

    # Chave a mais em params.postal = alguém escreveu algo depois da tabela em
    # hugo.toml e o TOML aceitou em silêncio, sem erro de build. A chave certa
    # mora acima de [params.postal], nunca dentro dela.
    postal = params.get("postal", {})
    if leaked := sorted(set(postal) - POSTAL_KEYS):
        errors.append(
            "hugo.toml: params.postal tem chave(s) inesperada(s) "
            f"{', '.join(leaked)} — provável vazamento de chave escrita depois "
            "de [params.postal]; mova-a para cima da tabela, em [params]"
        )

    # Sintoma direto do vazamento: a chave devia estar em params e sumiu.
    # "" é valor válido para as duas verificações de busca — só ausência conta.
    for key in CRITICAL_PARAMS_KEYS:
        if key not in params:
            errors.append(
                f"hugo.toml: params.{key} ausente — verifique se não foi "
                "escrita depois de [params.postal] e caiu dentro dela"
            )


def audit_content(errors: list[str]) -> None:
    content_files = sorted(CONTENT.glob("*.md"))
    for path in content_files:
        source = path.read_text(encoding="utf-8")
        front_matter = re.match(r"^---\n(.*?)\n---", source, re.DOTALL)
        if not front_matter:
            errors.append(f"{path.relative_to(ROOT)}: missing YAML front matter")
            continue
        block = front_matter.group(1)
        if not LASTMOD_RE.search(block):
            errors.append(f"{path.relative_to(ROOT)}: missing or invalid lastmod")

        # Data no futuro faz o Hugo DESCARTAR a página inteira, em silêncio:
        # sem aviso, sem erro, e `--panicOnWarning` não pega. Foi assim que a
        # home es saiu do build — `lastmod` duas horas à frente do relógio de
        # quem buildou. O arquivo continua em content/, o `hugo list all`
        # continua listando a página, e o HTML simplesmente não existe.
        for key in ("lastmod", "date", "publishDate"):
            value = re.search(rf"^{key}:\s*(\S+)\s*$", block, re.MULTILINE)
            if not value:
                continue
            try:
                when = datetime.fromisoformat(value.group(1))
            except ValueError:
                errors.append(
                    f"{path.relative_to(ROOT)}: unparsable {key} {value.group(1)}"
                )
                continue
            now = datetime.now(when.tzinfo) if when.tzinfo else datetime.now()
            if when > now:
                errors.append(
                    f"{path.relative_to(ROOT)}: {key} is in the future "
                    f"({value.group(1)}) — Hugo drops the page from the build "
                    f"without a warning"
                )

    catalogs = {
        path.stem: tomllib.loads(path.read_text(encoding="utf-8"))
        for path in sorted(I18N.glob("*.toml"))
    }
    all_keys = set().union(*(set(catalog) for catalog in catalogs.values()))
    for language, catalog in catalogs.items():
        if missing := sorted(all_keys - set(catalog)):
            errors.append(f"i18n/{language}.toml: missing keys {', '.join(missing)}")

    # Placeholders que o main.js substitui no navegador. Traduzir a frase e
    # perder `{unidades}` não quebra nada visível: a mensagem sai sem o número,
    # que é justamente o que o estimador existe para mostrar. Mesma classe de
    # falha silenciosa que a contagem de FAQ home:true logo abaixo.
    for language, catalog in catalogs.items():
        for key, tokens in (
            ("est_result", ("{unidades}",)),
            ("est_msg", ("{kg}", "{g}", "{unidades}")),
            ("glossary_results", ("{count}",)),
        ):
            value = catalog.get(key, "")
            missing_tokens = [token for token in tokens if token not in value]
            if missing_tokens:
                errors.append(
                    f"i18n/{language}.toml: {key} lacks {' '.join(missing_tokens)}"
                )


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

        # Invariantes de URL que já quebraram em produção, uma vez cada:
        #
        # 1. `api.whatsapp.com/send?l=..&phone=..` saía com o `&` escapado duas
        #    vezes. O navegador lia `&amp;phone` como NOME de parâmetro, o
        #    número deixava de existir na URL e o WhatsApp abria a lista de
        #    contatos. O build passava: link quebrado não é erro de build.
        # 2. O mesmo duplo escape em qualquer atributo — `%C3%A7` entregue como
        #    `%25C3%25A7` chega ilegível do outro lado.
        # 3. wa.me sem `?text=`: o destino vem no caminho, então falta só a
        #    mensagem — e um CTA sem mensagem volta a ser o genérico que a
        #    revisão pediu para eliminar.
        if "api.whatsapp.com" in source:
            errors.append(f"{relative_page}: legacy WhatsApp host api.whatsapp.com")
        if "&amp;amp;" in source:
            errors.append(f"{relative_page}: double-escaped entity &amp;amp; in markup")
        for wa_link in re.finditer(r'href="(https://wa\.me/[^"]*)"', source):
            if "?text=" not in wa_link.group(1):
                errors.append(f"{relative_page}: wa.me link without ?text=: {wa_link.group(1)}")
        for doubled in re.finditer(r'href="[^"]*%25', source):
            errors.append(
                f"{relative_page}: double percent-encoded href {doubled.group(0)[:100]}"
            )

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

    # Título repetido DENTRO do mesmo idioma é sempre defeito: ou a página
    # duplicada deveria redirecionar, ou a tradução ficou com o título do
    # idioma de origem — foi o caso da home es, idêntica à pt. Entre idiomas
    # repetir é legítimo, e quem resolve isso é o hreflang.
    # O idioma sai do <html lang>, NÃO do caminho: pt-br é o idioma padrão e
    # não tem subdiretório, então `relative.parts[0]` era o slug da própria
    # página e cada página pt caía num balde só dela — a verificação nunca
    # disparava justamente para o idioma com mais páginas. es/en funcionavam
    # porque moram em /es/ e /en/.
    titles: dict[tuple[str, str], list[Path]] = {}
    for page, parser in parsers.items():
        if not parser.title:
            continue
        relative = page.relative_to(PUBLIC.resolve())
        language = parser.html_lang or "sem-lang"
        titles.setdefault((language, parser.title.strip()), []).append(relative)
    for (language, title), pages_with_title in titles.items():
        if len(pages_with_title) > 1:
            listed = ", ".join(str(page) for page in sorted(pages_with_title))
            errors.append(f"duplicate <title> in {language}: {listed} — {title[:60]}")

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


def audit_stylesheet_assets(errors: list[str]) -> None:
    # As referências do HTML já são conferidas em audit_pages (todo href de
    # <a>/<link> vira ref), mas NADA lia o que o CSS pede com url(). É o único
    # ponto cego dos nomes fingerprintados das fontes: trocar um .woff2 na mão
    # em static/fonts/ em vez de rodar scripts/download-fonts.sh deixa o
    # @font-face apontando para um arquivo morto. O navegador cai na fonte de
    # fallback, o layout muda, e o build passa verde — mesma classe de falha
    # silenciosa que o resto deste script existe para pegar.
    for stylesheet in sorted(PUBLIC.rglob("*.css")):
        source = stylesheet.read_text(encoding="utf-8")
        # set(): cada @font-face repete a mesma url() em dois format(), e um
        # arquivo morto não precisa ser reportado duas vezes.
        for reference in sorted(set(re.findall(r"url\(\s*['\"]?([^'\")]+?)['\"]?\s*\)", source))):
            if reference.startswith(("data:", "http:", "https:", "//", "#")):
                continue
            target, _ = local_target(stylesheet.resolve(), reference)
            if target is None:
                continue
            if not target.exists():
                relative = stylesheet.relative_to(PUBLIC.resolve())
                errors.append(f"{relative}: broken url() reference {reference}")


def main() -> int:
    errors: list[str] = []
    audit_hugo_config(errors)
    audit_content(errors)
    parsers, sources = parse_pages(errors)
    inline_hashes = audit_pages(parsers, sources, errors)
    audit_stylesheet_assets(errors)
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
