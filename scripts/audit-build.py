#!/usr/bin/env python3
"""Audita o HTML gerado pelo Hugo usando só a biblioteca padrão do Python."""

from __future__ import annotations

import base64
from datetime import datetime
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import re
import subprocess
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
        self.duplicate_ids: set[str] = set()
        self.refs: list[tuple[str, str]] = []
        self.anchors: list[dict[str, str | None]] = []
        self.images: list[dict[str, str | None]] = []
        self.meta: list[dict[str, str | None]] = []
        self.links: list[dict[str, str | None]] = []
        self.class_counts: dict[str, int] = {}
        self.h1_texts: list[str] = []
        self.html_lang: str | None = None
        self.title: str | None = None
        self._in_title = False
        self._h1_parts: list[str] | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        if tag == "html":
            self.html_lang = values.get("lang")
        if identifier := values.get("id"):
            if identifier in self.ids:
                self.duplicate_ids.add(identifier)
            self.ids.add(identifier)
        for class_name in (values.get("class") or "").split():
            self.class_counts[class_name] = self.class_counts.get(class_name, 0) + 1
        if tag in {"a", "link"} and (href := values.get("href")):
            self.refs.append((tag, href))
        if tag in {"img", "script", "iframe", "source"} and (src := values.get("src")):
            self.refs.append((tag, src))
        if tag == "img":
            self.images.append(values)
        elif tag == "a":
            self.anchors.append(values)
        elif tag == "meta":
            self.meta.append(values)
        elif tag == "link":
            self.links.append(values)
        if tag == "title":
            self._in_title = True
        elif tag == "h1":
            self._h1_parts = []

    def handle_endtag(self, tag: str) -> None:
        if tag == "title":
            self._in_title = False
        elif tag == "h1" and self._h1_parts is not None:
            self.h1_texts.append("".join(self._h1_parts).strip())
            self._h1_parts = None

    def handle_data(self, data: str) -> None:
        if self._in_title:
            self.title = (self.title or "") + data
        if self._h1_parts is not None:
            self._h1_parts.append(data)


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


# Arquivos que PRECISAM do bit de execução no índice do git. O hook é o caso
# grave: git não executa hook sem +x, só imprime um "hint" e segue — a
# proteção de lastmod some sem erro nenhum. E o próprio hook não tem como
# avisar que perdeu o bit, porque sem o bit ele não roda. Por isso a checagem
# mora aqui, e a CI a executa contra o que foi COMMITADO.
#
# Já aconteceu: o repositório fica numa pasta sincronizada, e o sync tirou o
# +x dos quatro arquivos. Um `git add -A` teria gravado 100644 no índice e
# desligado o hook em todo clone dali em diante.
EXECUTABLE_FILES = (
    ".githooks/pre-commit",
    "scripts/audit-build.py",
    "scripts/check-lastmod.py",
    "scripts/download-fonts.sh",
)


def audit_executable_bits(errors: list[str]) -> None:
    try:
        listing = subprocess.run(
            ["git", "ls-files", "-s", "--", *EXECUTABLE_FILES],
            cwd=ROOT, capture_output=True, text=True, check=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError):
        return  # fora de um checkout git não há índice para conferir
    modes = {line.split()[3]: line.split()[0] for line in listing.splitlines()}
    for path in EXECUTABLE_FILES:
        mode = modes.get(path)
        if mode is None:
            errors.append(f"{path}: not tracked by git")
        elif mode != "100755":
            errors.append(
                f"{path}: committed as {mode}, must be 100755 — "
                "without the executable bit git silently skips the pre-commit hook"
            )


def audit_hugo_config(errors: list[str]) -> None:
    config = tomllib.loads(HUGO_CONFIG.read_text(encoding="utf-8"))
    params = config.get("params", {})

    # Chave a mais em params.postal = alguém escreveu algo depois da tabela em
    # hugo.toml e o TOML aceitou em silêncio, sem erro de build. A chave certa
    # mora acima de [params.postal], nunca dentro dela.
    postal = params.get("postal", {})
    if leaked := sorted(set(postal) - POSTAL_KEYS):
        errors.append(
            f"hugo.toml: unexpected key(s) in params.postal: {', '.join(leaked)} — "
            "likely a key written after [params.postal]; move it above the table"
        )

    # Sintoma direto do vazamento: a chave devia estar em params e sumiu.
    # "" é valor válido para as duas verificações de busca — só ausência conta.
    for key in CRITICAL_PARAMS_KEYS:
        if key not in params:
            errors.append(
                f"hugo.toml: params.{key} is missing — check it was not written "
                "after [params.postal] and swallowed by it"
            )


LAYOUTS = ROOT / "layouts"


def audit_unused_i18n_keys(errors: list[str]) -> None:
    """Chave definida no catálogo e usada em lugar nenhum. A checagem de
    paridade confere que os três idiomas têm as MESMAS chaves, não que elas
    sirvam para algo — e toda remoção de seção deixava chaves órfãs, achadas
    à mão três vezes em setembro de 2026.

    Chaves montadas em tempo de execução (`printf "home_paraquem%d"`) contam
    como usadas pelo prefixo, mas só enquanto algum template ainda monta esse
    prefixo: se o printf sair, a exceção sai junto."""
    templates = " ".join(
        path.read_text(encoding="utf-8") for path in sorted(LAYOUTS.rglob("*.html"))
    )
    # Formatos que começam com letra são a base da chave ("home_paraquem%d");
    # os que começam com %s acrescentam um sufixo a ela ("%s_title"). Compor
    # os dois dá exatamente as chaves montadas: home_paraquem\d+_title e
    # _text — e não home_paraquem1_whatsapp, que um prefixo solto deixaria passar.
    formats = re.findall(r'printf "([^"]*%[ds][^"]*)"', templates)
    as_regex = lambda fmt, base=r"\w+": re.escape(fmt).replace("%d", r"\d+").replace("%s", base)
    bases = [as_regex(f) for f in formats if re.match(r"[a-z]", f)]
    suffixes = [f for f in formats if f.startswith("%s")]
    built = [re.compile(as_regex(sfx, base) + "$") for base in bases for sfx in suffixes]
    built += [re.compile(base + "$") for base in bases]
    catalog = tomllib.loads((I18N / "pt-br.toml").read_text(encoding="utf-8"))
    for key in sorted(catalog):
        if f'"{key}"' in templates:
            continue
        if any(pattern.match(key) for pattern in built):
            continue
        errors.append(f"i18n/*.toml: key {key} is defined but never used by a template")


def audit_content(errors: list[str]) -> None:
    # Hugo aceita leaf/branch bundles em subdiretórios. Auditar só content/*.md
    # deixaria qualquer futura página aninhada fora do contrato de lastmod.
    content_files = sorted(CONTENT.rglob("*.md"))
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
            # Aspas são YAML válido (`date: "2026-01-01"`) e o fromisoformat não
            # as aceita: sem o strip, uma data correta era reportada como ilegível.
            raw = value.group(1).strip("\"'")
            try:
                when = datetime.fromisoformat(raw)
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
    # perder o token não quebra nada visível: a mensagem sai sem o número, que
    # é justamente o que ela existe para mostrar. Falha silenciosa, build
    # verde — daí a checagem.
    for language, catalog in catalogs.items():
        for key, tokens in (
            ("glossary_results", ("{count}",)),
            ("trust_num_sample_days", ("{{ .sample_days }}",)),
            ("trust_num_production_days", ("{{ .production_days }}",)),
        ):
            value = catalog.get(key, "")
            missing_tokens = [token for token in tokens if token not in value]
            if missing_tokens:
                errors.append(
                    f"i18n/{language}.toml: {key} lacks {' '.join(missing_tokens)}"
                )


# O buscador corta a description por largura, por volta de 155–160
# caracteres. Passou disso, o fim vira "…" — e o fim costumava ser justamente
# o sufixo ", Hibiscus Phytocosméticos, São Bernardo do Campo", que só repetia o
# que o <title> e o og:site_name já dizem. 27 páginas estavam acima; a pior,
# com 248. Confere o HTML gerado, então vale para qualquer origem da description.
DESCRIPTION_MAX = 160

REQUIRED_OG = (
    "og:title", "og:description", "og:url", "og:image",
    "og:image:alt", "og:locale", "og:site_name",
)


def _page_metadata(where: Path, parser: PageParser, errors: list[str]) -> None:
    """Cabeçalho que buscador e compartilhamento leem: idioma, título, h1,
    description, canonical e Open Graph. Presença não basta — um atributo
    vazio passa em `in`, por isso tudo é conferido por conteúdo."""
    names = {m.get("name"): m.get("content") for m in parser.meta if m.get("name")}
    properties = {
        m.get("property"): m.get("content") for m in parser.meta if m.get("property")
    }
    canonicals = [
        link for link in parser.links
        if "canonical" in (link.get("rel") or "").split()
    ]
    if not parser.html_lang:
        errors.append(f"{where}: missing html lang")
    if not (parser.title or "").strip():
        errors.append(f"{where}: missing or empty title")
    if len(parser.h1_texts) != 1 or not parser.h1_texts[0]:
        errors.append(
            f"{where}: expected one non-empty h1, found {len(parser.h1_texts)}"
        )
    description = names.get("description")
    if not description:
        errors.append(f"{where}: missing or empty meta description")
    elif len(description) > DESCRIPTION_MAX:
        errors.append(
            f"{where}: meta description is {len(description)} chars, over "
            f"{DESCRIPTION_MAX} — search results truncate it"
        )
    if len(canonicals) != 1 or not canonicals[0].get("href"):
        errors.append(
            f"{where}: expected one non-empty canonical link, found {len(canonicals)}"
        )
    else:
        canonical = urlsplit(canonicals[0]["href"] or "")
        if canonical.scheme != "https" or not canonical.netloc:
            errors.append(f"{where}: canonical must be an absolute HTTPS URL")
    for required in REQUIRED_OG:
        if not properties.get(required):
            errors.append(f"{where}: missing or empty {required}")


def _page_structure(where: Path, parser: PageParser, errors: list[str]) -> None:
    """ids únicos, âncoras com destino, _blank com noopener e img com alt."""
    for identifier in sorted(parser.duplicate_ids):
        errors.append(f"{where}: duplicate id {identifier}")
    for anchor in parser.anchors:
        href = anchor.get("href")
        if href is None or not href.strip():
            errors.append(f"{where}: anchor has missing or empty href")
        if anchor.get("target") == "_blank":
            if "noopener" not in (anchor.get("rel") or "").split():
                errors.append(f"{where}: target=_blank link lacks rel=noopener: {href}")
    for image in parser.images:
        if "alt" not in image:
            errors.append(f"{where}: image {image.get('src')} has no alt attribute")


def _page_references(
    page: Path, where: Path, parser: PageParser,
    parsers: dict[Path, PageParser], errors: list[str],
) -> None:
    """Todo href/src local precisa existir em public/, e todo #fragmento
    precisa bater com um id da página de destino."""
    for _, reference in parser.refs:
        target, fragment = local_target(page, reference)
        if target is None:
            continue
        try:
            target.relative_to(PUBLIC.resolve())
        except ValueError:
            errors.append(f"{where}: reference escapes public/: {reference}")
            continue
        if not target.exists():
            errors.append(f"{where}: broken internal reference {reference}")
        elif fragment and target.suffix == ".html":
            target_parser = parsers.get(target)
            if target_parser and fragment not in target_parser.ids:
                errors.append(f"{where}: missing fragment target {reference}")


def _page_links(where: Path, parser: PageParser, source: str, errors: list[str]) -> None:
    """Invariantes de URL que já quebraram em produção, uma vez cada.

    1. `api.whatsapp.com/send?l=..&phone=..` saía com o `&` escapado duas
       vezes. O navegador lia `&amp;phone` como NOME de parâmetro, o número
       deixava de existir na URL e o WhatsApp abria a lista de contatos. O
       build passava: link quebrado não é erro de build.
    2. O mesmo duplo escape em qualquer atributo — `%C3%A7` entregue como
       `%25C3%25A7` chega ilegível do outro lado.
    3. wa.me sem `?text=`: o destino vem no caminho, então falta só a
       mensagem — e um CTA sem mensagem volta a ser o genérico.

    Os itens 2 e 3 leem o href JÁ PARSEADO, não o HTML cru. O minificador tira
    as aspas de atributo sem caractere especial: um wa.me que perdeu o `?text=`
    sai como `href=https://wa.me/55...`, sem aspas. A versão antiga procurava
    `href="..."` e por isso nunca enxergava justamente o defeito que existia
    para pegar — com o bug plantado, reportava zero erros. O parser devolve o
    valor igual com ou sem aspas.
    """
    if "api.whatsapp.com" in source:
        errors.append(f"{where}: legacy WhatsApp host api.whatsapp.com")
    if "&amp;amp;" in source:
        errors.append(f"{where}: double-escaped entity &amp;amp; in markup")
    for tag, reference in parser.refs:
        if tag not in {"a", "link"}:
            continue
        if reference.startswith("https://wa.me/") and "?text=" not in reference:
            errors.append(f"{where}: wa.me link without ?text=: {reference}")
        if "%25" in reference:
            errors.append(f"{where}: double percent-encoded href {reference[:100]}")


def _page_scripts(
    where: Path, source: str, errors: list[str], inline_hashes: set[str]
) -> None:
    """A CSP não permite script inline executável. JSON-LD é a exceção, e
    precisa ser JSON válido."""
    if re.search(r"<style(?:\s[^>]*)?>", source, re.IGNORECASE):
        errors.append(f"{where}: inline style block violates CSP")
    if re.search(r"\sstyle=", source, re.IGNORECASE):
        errors.append(f"{where}: inline style attribute violates CSP")
    for match in re.finditer(
        r"<script([^>]*)>(.*?)</script>", source, re.DOTALL | re.IGNORECASE
    ):
        attrs, body = match.groups()
        if re.search(r"\bsrc=", attrs):
            continue
        if not re.search(r"\btype=application/ld\+json\b", attrs, re.IGNORECASE):
            errors.append(f"{where}: executable inline script violates CSP")
            continue
        try:
            json.loads(body)
        except json.JSONDecodeError as error:
            errors.append(f"{where}: invalid JSON-LD: {error}")
        inline_hashes.add(
            base64.b64encode(hashlib.sha256(body.encode()).digest()).decode()
        )


def _duplicate_titles(parsers: dict[Path, PageParser], errors: list[str]) -> None:
    """Título repetido DENTRO do mesmo idioma é sempre defeito: ou a página
    duplicada deveria redirecionar, ou a tradução ficou com o título do idioma
    de origem — foi o caso da home es, idêntica à pt. Entre idiomas repetir é
    legítimo, e quem resolve isso é o hreflang.

    O idioma sai do <html lang>, NÃO do caminho: pt-br é o idioma padrão e não
    tem subdiretório, então `relative.parts[0]` era o slug da própria página e
    cada página pt caía num balde só dela — a verificação nunca disparava
    justamente para o idioma com mais páginas."""
    titles: dict[tuple[str, str], list[Path]] = {}
    for page, parser in parsers.items():
        if not parser.title:
            continue
        language = parser.html_lang or "sem-lang"
        titles.setdefault((language, parser.title.strip()), []).append(
            page.relative_to(PUBLIC.resolve())
        )
    for (language, title), pages in titles.items():
        if len(pages) > 1:
            listed = ", ".join(str(page) for page in sorted(pages))
            errors.append(f"duplicate <title> in {language}: {listed} — {title[:60]}")


def audit_pages(
    parsers: dict[Path, PageParser], sources: dict[Path, str], errors: list[str]
) -> set[str]:
    inline_hashes: set[str] = set()
    for page, parser in parsers.items():
        where = page.relative_to(PUBLIC.resolve())
        source = sources[page]
        is_redirect = any(
            m.get("http-equiv", "").lower() == "refresh" for m in parser.meta
        )
        if not is_redirect:
            _page_metadata(where, parser, errors)
        _page_structure(where, parser, errors)
        _page_references(page, where, parser, parsers, errors)
        _page_links(where, parser, source, errors)
        _page_scripts(where, source, errors, inline_hashes)
    _duplicate_titles(parsers, errors)
    return inline_hashes


def audit_reference_layouts(
    parsers: dict[Path, PageParser], errors: list[str]
) -> int:
    """Confere no HTML gerado a composição das famílias de página documentadas
    em docs/reference-layout.md."""
    config = tomllib.loads(HUGO_CONFIG.read_text(encoding="utf-8"))
    default_language = config.get("defaultContentLanguage")
    disabled_languages = set(config.get("disableLanguages", []))
    language_codes = [
        language
        for language in config.get("languages", {})
        if language not in disabled_languages
    ]
    expected_homes = {
        (PUBLIC / "index.html").resolve()
        if language == default_language
        else (PUBLIC / language / "index.html").resolve()
        for language in language_codes
    }

    home_parsers: list[PageParser] = []
    for home in sorted(expected_homes):
        parser = parsers.get(home)
        if parser is None:
            errors.append(f"{home.relative_to(ROOT)}: configured language homepage missing")
            continue
        home_parsers.append(parser)
        required_counts = {
            "hero": 1,
            "servicos-grid": 2,
            # Três públicos + seis serviços: o catálogo mantém a grade 3 x 2.
            "servico-cell": 9,
            "valores-grupo": 4,
        }
        for class_name, expected in required_counts.items():
            actual = parser.class_counts.get(class_name, 0)
            if actual != expected:
                errors.append(
                    f"{home.relative_to(PUBLIC.resolve())}: expected "
                    f"{expected} .{class_name}, found {actual}"
                )
        if parser.class_counts.get("faq-item", 0):
            errors.append(
                f"{home.relative_to(PUBLIC.resolve())}: homepage must not duplicate the FAQ"
            )

    for class_name in ("servico-cell", "valores-grupo"):
        counts = [parser.class_counts.get(class_name, 0) for parser in home_parsers]
        if counts and len(set(counts)) != 1:
            errors.append(
                f"localized homepages disagree on .{class_name} count: {counts}"
            )

    service_pages = [
        (page, parser)
        for page, parser in parsers.items()
        if parser.class_counts.get("servicos-detalhe", 0)
    ]
    if len(service_pages) != len(language_codes):
        errors.append(
            "expected one rendered services-detail page per configured language, "
            f"found {len(service_pages)}"
        )
    for class_name in ("servico-detalhe", "flow-step", "faq-item"):
        counts = [parser.class_counts.get(class_name, 0) for _, parser in service_pages]
        if counts and (not all(counts) or len(set(counts)) != 1):
            errors.append(
                f"localized services pages require matching non-zero .{class_name} "
                f"counts: {counts}"
            )

    return len(home_parsers)


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

    # JSON-LD é bloco de dados, nunca executado, então script-src não se aplica
    # a ele e fazer hash dele não serve para nada. Pior: cada bloco carrega um
    # @id por URL, e uma allowlist precisaria de uma entrada nova para cada
    # página criada. Barra os hashes de voltarem para a CSP.
    if re.search(r"'sha256-", policy):
        errors.append(
            "static/_headers: CSP carries script hashes; JSON-LD data blocks are "
            "not subject to script-src and executable JS is a same-origin asset"
        )


# Cada padrão prende o número ao fato pela GRAMÁTICA da frase, não pela
# distância. "500 unidades para bastão e 800 para pó compacto" põe o 800 mais
# perto de "bastão" do que de "pó compacto" — proximidade erraria. E números
# derivados (a tabela "30 g → ~666 unidades") não casam com nenhum padrão.
FACT_PATTERNS = {
    "minimum_kg": [
        r"(\d+)\s*kg\s+(?:por|per)\s+SKU",
        r"MOQ\s+(?:de\s+)?(\d+)\s*kg",
        r"(\d+)\s*kg\s+MOQ",
        r"(?:lote m[íi]nimo|minimum batch)\s+(?:de\s+|of\s+)?(\d+)\s*kg",
        r"(?:a|an)\s+(\d+)\s*kg\s+minimum",
    ],
    "sample_days": [
        r"(\d+)\s*(?:dias|días|days)(?!\s*(?:[úu]teis|h[áa]biles|working|business))"
        r"(?=[^.\n]{0,45}?(?:amostra|muestra|sample))",
        r"(?:amostra|muestra|sample)[^.\n·;]{0,40}?(\d+)\s*(?:dias|días|days)\b"
        r"(?!\s*(?:[úu]teis|h[áa]biles|working|business))",
    ],
    "production_days": [
        r"(\d+)\s*(?:dias [úu]teis|días h[áa]biles|working days|business days)",
    ],
}


UNIT_PROMISE = (
    r"(?:a partir de|desde|from)\s+\d+\s*(?:unidades|units|un\b|peças|piezas|pieces)"
    r"|~\s*\d+\s*(?:unidades|units|peças|piezas|pieces)"
)


# Afirmações que o site RETIROU por decisão comercial, em pt, es e en. Cada
# uma voltou pelo menos uma vez depois de corrigida — numa frase com a ordem
# das palavras trocada, ou no llms.txt, que nenhuma varredura olhava. Uma
# lista única, conferida em conteúdo, catálogos e llms.txt, impede a volta.
RETRACTED_CLAIMS = {
    "unconditional NDA (confidential by default; NDA only on request)":
        r"NDA (?:assinado|firmado|signed) (?:desde|antes|from|before)"
        r"|antes (?:do|del) NDA|before the NDA",
    "absolute confidentiality":
        r"sigilo (?:absoluto|total)|confidencialidade total"
        r"|(?:total|absoluta) confidencialidad|confidencialidad (?:total|absoluta)"
        r"|(?:absolute|complete|full|total) confidentiality",
    "clean beauty / vegan for any product (assessed product by product)":
        r"(?:clean beauty|veganas?|vegan)[^.\n]{0,25}\b(?:dispon[íi]veis|disponibles|available)\b"
        r"|op[çc][õo]es clean beauty|qualquer linha|cualquier l[íi]nea|any (?:range|line)\b",
    # "custo/preço por unidade" é legítimo (modelos de desenvolvimento): o
    # padrão só pega "por unidade" preso a mínimo ou a número de referência.
    "per-unit minimum (20 kg per SKU in any format)":
        r"(?:MOQ|m[íi]nimos?|minimum)[^.\n]{0,25}(?:por unidade|por unidad|per unit)"
        r"|per-unit (?:minimum|figure)s?|minimum measured in units"
        r"|(?:n[úu]meros|valores|cifras) por unidad(?:e)?",
    "unverifiable quality claim":
        r"qualidade incondicional|calidad incondicional|uncompromising quality",
    "batch yield promise (units depend on customer packaging)":
        r"rendimento do lote|rendimiento del lote|\bbatch yield\b",
}


def audit_retracted_claims(errors: list[str]) -> None:
    sources = sorted(CONTENT.rglob("*.md")) + sorted(I18N.glob("*.toml"))
    llms = ROOT / "static" / "llms.txt"
    if llms.exists():
        sources.append(llms)
    for path in sources:
        text = re.sub(r"\*\*|</?strong>", "", path.read_text(encoding="utf-8"))
        for claim, pattern in RETRACTED_CLAIMS.items():
            for match in re.finditer(pattern, text, re.IGNORECASE):
                line = text.count("\n", 0, match.start()) + 1
                errors.append(
                    f"{path.relative_to(ROOT)}:{line}: retracted claim — {claim}: "
                    f"“{match.group(0).strip()}”"
                )


def audit_commercial_facts(errors: list[str]) -> None:
    """data/commercial.toml alimenta a trust-strip, mas o texto corrido das
    páginas repete os mesmos números à mão. Mudar o arquivo de dados e esquecer
    a prosa deixava o site dizendo "45 dias" na faixa e "até 30 dias" no
    parágrafo ao lado, com build verde. Aqui todo número preso a um fato
    comercial precisa bater com o valor do arquivo."""
    data_file = ROOT / "data" / "commercial.toml"
    if not data_file.exists():
        return
    facts = tomllib.loads(data_file.read_text(encoding="utf-8"))
    sources = sorted(CONTENT.rglob("*.md")) + sorted(I18N.glob("*.toml"))
    llms = ROOT / "static" / "llms.txt"
    if llms.exists():
        sources.append(llms)
    for path in sources:
        text = path.read_text(encoding="utf-8")
        # ênfase atrapalha o casamento e não muda o fato
        text = re.sub(r"\*\*|</?strong>", "", text)
        # A embalagem é fornecida pelo cliente, então o site não promete
        # número de peças: nem mínimo por unidade ("a partir de 500
        # unidades"), nem rendimento ("~666 unidades"). Decisão de 29/09/2026.
        for match in re.finditer(UNIT_PROMISE, text, re.IGNORECASE):
            line = text.count("\n", 0, match.start()) + 1
            errors.append(
                f"{path.relative_to(ROOT)}:{line}: promises a unit count "
                f"(“{match.group(0).strip()}”) — packaging is customer-supplied"
            )
        for fact, patterns in FACT_PATTERNS.items():
            expected = facts.get(fact)
            if expected is None:
                continue
            for pattern in patterns:
                for match in re.finditer(pattern, text, re.IGNORECASE):
                    found = next(g for g in match.groups() if g)
                    if int(found) != int(expected):
                        line = text.count("\n", 0, match.start()) + 1
                        errors.append(
                            f"{path.relative_to(ROOT)}:{line}: says {found} for "
                            f"{fact}, data/commercial.toml says {expected} — "
                            f"“{match.group(0).strip()[:60]}”"
                        )


def audit_stylesheet_assets(errors: list[str]) -> None:
    # As referências do HTML já são conferidas em audit_pages (todo href de
    # <a>/<link> vira ref), mas NADA lia o que o CSS pede com url(). É o único
    # ponto cego dos nomes fingerprintados das fontes: trocar um .woff2 na mão
    # em static/fonts/ em vez de rodar scripts/download-fonts.sh deixa o
    # @font-face apontando para um arquivo morto. O navegador cai na fonte de
    # fallback, o layout muda, e o build passa verde — mesma classe de falha
    # silenciosa que o resto deste script existe para pegar.
    # resolve() dos dois lados: rglob devolve o caminho como foi montado, e
    # relative_to() contra PUBLIC.resolve() quebra se houver symlink no meio
    # (no macOS /var é /private/var). Só funcionava porque ROOT já vinha
    # resolvido — o teste com diretório temporário expôs.
    for stylesheet in sorted(PUBLIC.resolve().rglob("*.css")):
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
    audit_executable_bits(errors)
    audit_hugo_config(errors)
    audit_commercial_facts(errors)
    audit_retracted_claims(errors)
    audit_content(errors)
    audit_unused_i18n_keys(errors)
    parsers, sources = parse_pages(errors)
    inline_hashes = audit_pages(parsers, sources, errors)
    homepage_count = audit_reference_layouts(parsers, errors)
    audit_stylesheet_assets(errors)
    audit_csp(errors)

    if errors:
        print("Generated-site audit failed:", file=sys.stderr)
        for error in errors:
            print(f"- {error}", file=sys.stderr)
        return 1

    print(
        f"Generated-site audit passed: {len(parsers)} HTML files, "
        f"{len(inline_hashes)} JSON-LD blocks, {homepage_count} localized homepages."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
