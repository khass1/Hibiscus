from __future__ import annotations

import importlib.util
from pathlib import Path
import tempfile
import unittest


SCRIPT = Path(__file__).with_name("audit-build.py")
SPEC = importlib.util.spec_from_file_location("audit_build", SCRIPT)
if SPEC is None or SPEC.loader is None:  # pragma: no cover - import setup guard
    raise RuntimeError(f"cannot load {SCRIPT}")
audit_build = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(audit_build)


VALID_PAGE = """<!doctype html>
<html lang="pt-BR">
<head>
  <title>Página válida</title>
  <meta name="description" content="Descrição válida">
  <meta property="og:title" content="Página válida">
  <meta property="og:description" content="Descrição válida">
  <meta property="og:url" content="https://example.com/">
  <meta property="og:image" content="https://example.com/img.jpg">
  <meta property="og:image:alt" content="Imagem de exemplo">
  <meta property="og:locale" content="pt_BR">
  <meta property="og:site_name" content="Exemplo">
  <link rel="canonical" href="https://example.com/">
</head>
<body>
  <h1>Página <em>válida</em></h1>
  <a href="https://example.org/" target="_blank" rel="noopener">Externo</a>
</body>
</html>
"""


class _PageAudit(unittest.TestCase):
    """Monta uma página isolada e roda audit_pages nela. Sem métodos de
    teste de propósito: quem herda daqui não repete testes alheios."""

    def setUp(self) -> None:
        self._original_public = audit_build.PUBLIC
        self._temporary = tempfile.TemporaryDirectory()
        audit_build.PUBLIC = Path(self._temporary.name) / "public"
        audit_build.PUBLIC.mkdir()

    def tearDown(self) -> None:
        audit_build.PUBLIC = self._original_public
        self._temporary.cleanup()

    def audit(self, source: str) -> list[str]:
        page = (audit_build.PUBLIC / "index.html").resolve()
        parser = audit_build.PageParser()
        parser.feed(source)
        errors: list[str] = []
        audit_build.audit_pages({page: parser}, {page: source}, errors)
        return errors


class AuditPagePropertiesTest(_PageAudit):
    def test_valid_page_satisfies_property_contract(self) -> None:
        self.assertEqual(self.audit(VALID_PAGE), [])

    def test_invalid_accessibility_and_metadata_properties_are_reported(self) -> None:
        invalid = VALID_PAGE.replace(
            '<meta name="description" content="Descrição válida">',
            '<meta name="description" content="">',
        ).replace(
            '<h1>Página <em>válida</em></h1>',
            '<div id="repetido"></div><div id="repetido"></div>',
        ).replace(
            '<a href="https://example.org/" target="_blank" rel="noopener">Externo</a>',
            '<a href="" target="_blank">Sem destino</a>',
        )

        errors = "\n".join(self.audit(invalid))
        self.assertIn("expected one non-empty h1", errors)
        self.assertIn("missing or empty meta description", errors)
        self.assertIn("duplicate id repetido", errors)
        self.assertIn("anchor has missing or empty href", errors)
        self.assertIn("target=_blank link lacks rel=noopener", errors)


if __name__ == "__main__":
    unittest.main()


class _Isolated(unittest.TestCase):
    """Aponta os caminhos globais do script para um diretório temporário e os
    devolve no fim, para cada teste enxergar só o que ele mesmo montou."""

    GLOBALS = ("PUBLIC", "CONTENT", "I18N", "ROOT", "HUGO_CONFIG", "LAYOUTS")

    def setUp(self) -> None:
        self._saved = {name: getattr(audit_build, name) for name in self.GLOBALS}
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        audit_build.ROOT = self.root
        audit_build.PUBLIC = self.root / "public"
        audit_build.CONTENT = self.root / "content"
        audit_build.I18N = self.root / "i18n"
        audit_build.HUGO_CONFIG = self.root / "hugo.toml"
        audit_build.LAYOUTS = self.root / "layouts"
        for folder in ("public", "content", "i18n", "layouts"):
            (self.root / folder).mkdir()

    def tearDown(self) -> None:
        for name, value in self._saved.items():
            setattr(audit_build, name, value)
        self._tmp.cleanup()


class LinkInvariantsTest(_Isolated):
    def links(self, markup: str) -> list[str]:
        page = (audit_build.PUBLIC / "index.html").resolve()
        parser = audit_build.PageParser()
        parser.feed(markup)
        errors: list[str] = []
        audit_build._page_links(Path("index.html"), parser, markup, errors)
        return errors

    def test_wa_me_without_text_is_caught_even_when_unquoted(self) -> None:
        # Regressão: o minificador tira as aspas de um wa.me sem `?text=`, e a
        # versão antiga só procurava href="..." — não via o próprio defeito.
        for markup in (
            '<a href=https://wa.me/5511976591889>x</a>',
            '<a href="https://wa.me/5511976591889">x</a>',
        ):
            with self.subTest(markup=markup):
                self.assertTrue(
                    any("without ?text=" in e for e in self.links(markup))
                )

    def test_wa_me_with_text_passes(self) -> None:
        self.assertEqual(
            self.links('<a href="https://wa.me/5511976591889?text=Ol%C3%A1">x</a>'), []
        )

    def test_double_percent_encoding_is_caught(self) -> None:
        errors = self.links('<a href=mailto:x@y.com?subject=%25C3%25A7>x</a>')
        self.assertTrue(any("double percent-encoded" in e for e in errors))

    def test_legacy_whatsapp_host_is_caught(self) -> None:
        markup = '<a href="https://api.whatsapp.com/send?phone=1&text=x">x</a>'
        self.assertTrue(any("api.whatsapp.com" in e for e in self.links(markup)))


class ContentDatesTest(_Isolated):
    def audit(self, front_matter: str) -> list[str]:
        (audit_build.CONTENT / "p.md").write_text(
            f"---\n{front_matter}\n---\nbody\n", encoding="utf-8"
        )
        errors: list[str] = []
        audit_build.audit_content(errors)
        return errors

    def test_quoted_date_is_valid_yaml_and_accepted(self) -> None:
        # Regressão: `date: "2026-01-01"` é YAML válido e era reportado ilegível.
        errors = self.audit('lastmod: 2026-01-01T00:00:00-03:00\ndate: "2026-01-01"')
        self.assertFalse(any("unparsable" in e for e in errors), errors)

    def test_future_lastmod_is_rejected(self) -> None:
        # O Hugo descarta em silêncio página com data no futuro.
        errors = self.audit("lastmod: 2999-01-01T00:00:00-03:00")
        self.assertTrue(any("in the future" in e for e in errors), errors)

    def test_missing_lastmod_is_rejected(self) -> None:
        errors = self.audit('title: "sem data"')
        self.assertTrue(any("missing or invalid lastmod" in e for e in errors), errors)


class HugoConfigTest(_Isolated):
    BASE = (
        '[params]\n'
        '  contatoEmail = "c@x"\n  rhEmail = "r@x"\n'
        '  googleSiteVerification = ""\n  bingSiteVerification = ""\n'
        '  whatsappPhone = "55"\n  phone = "11"\n'
        '  [params.postal]\n'
        '    street = "s"\n    city = "c"\n'
    )

    def audit(self, toml: str) -> list[str]:
        audit_build.HUGO_CONFIG.write_text(toml, encoding="utf-8")
        errors: list[str] = []
        audit_build.audit_hugo_config(errors)
        return errors

    def test_valid_config_passes_with_empty_verification_strings(self) -> None:
        # "" é o valor correto das verificações de busca (feitas por DNS).
        self.assertEqual(self.audit(self.BASE), [])

    def test_key_written_after_postal_is_caught(self) -> None:
        errors = self.audit(self.BASE + '    novaChave = "vazou"\n')
        self.assertTrue(any("novaChave" in e for e in errors), errors)

    def test_critical_param_swallowed_by_postal_is_caught(self) -> None:
        swallowed = self.BASE.replace('  contatoEmail = "c@x"\n', "")
        swallowed += '    contatoEmail = "c@x"\n'
        errors = self.audit(swallowed)
        self.assertTrue(any("contatoEmail is missing" in e for e in errors), errors)


class StylesheetAssetsTest(_Isolated):
    def test_dead_font_url_in_css_is_caught(self) -> None:
        (audit_build.PUBLIC / "css").mkdir()
        (audit_build.PUBLIC / "css" / "main.css").write_text(
            "@font-face{src:url('/fonts/sumiu.woff2')}", encoding="utf-8"
        )
        errors: list[str] = []
        audit_build.audit_stylesheet_assets(errors)
        self.assertTrue(any("sumiu.woff2" in e for e in errors), errors)


class DescriptionLengthTest(_PageAudit):
    def test_description_over_limit_is_reported(self) -> None:
        long = "x" * (audit_build.DESCRIPTION_MAX + 1)
        page = VALID_PAGE.replace('content="Descrição válida">', f'content="{long}">', 1)
        self.assertTrue(any("search results truncate" in e for e in self.audit(page)))

    def test_description_at_limit_passes(self) -> None:
        exact = "x" * audit_build.DESCRIPTION_MAX
        page = VALID_PAGE.replace('content="Descrição válida">', f'content="{exact}">', 1)
        self.assertFalse(any("truncate" in e for e in self.audit(page)))


class CommercialFactsTest(_Isolated):
    FACTS = "minimum_kg = 20\nsample_days = 30\nproduction_days = 10\n"

    def audit(self, prose: str) -> list[str]:
        (self.root / "data").mkdir(exist_ok=True)
        (self.root / "data" / "commercial.toml").write_text(self.FACTS, encoding="utf-8")
        (audit_build.CONTENT / "p.md").write_text(prose, encoding="utf-8")
        errors: list[str] = []
        audit_build.audit_commercial_facts(errors)
        return errors

    def test_matching_prose_passes(self) -> None:
        self.assertEqual(self.audit(
            "Em geral, até **30 dias** do briefing à primeira amostra; a produção leva "
            "**10 dias úteis**. Mínimo de **20 kg por SKU**, em qualquer formato."), [])

    def test_stale_prose_is_caught(self) -> None:
        # Regressão: a faixa lia os dados, a prosa não, e as duas divergiam em silêncio.
        errors = self.audit("Até 45 dias do briefing à primeira amostra.")
        self.assertTrue(any("sample_days" in e for e in errors), errors)

    def test_unit_count_promise_is_caught(self) -> None:
        # A embalagem é do cliente: o site não promete número de peças.
        for prose in ("Bastão a partir de 500 unidades.", "| 30 g | ~666 unidades |",
                      "Stick from 500 units.", "Barra desde 500 unidades."):
            with self.subTest(prose=prose):
                self.assertTrue(any("unit count" in e for e in self.audit(prose)))

    def test_spf_is_not_a_unit_count(self) -> None:
        self.assertEqual(self.audit("Estudos de FPS 50 para bastão."), [])


class PlaceholderTest(_Isolated):
    def test_dropped_data_placeholder_is_caught(self) -> None:
        base = ('glossary_results = "{count}"\n'
                'trust_num_sample_days = "{{ .sample_days }} dias"\n'
                'trust_num_production_days = "{{ .production_days }} dias"\n'
                )
        (audit_build.I18N / "pt-br.toml").write_text(
            base.replace("{{ .sample_days }} dias", "dias"), encoding="utf-8")
        errors: list[str] = []
        audit_build.audit_content(errors)
        self.assertTrue(any("trust_num_sample_days lacks" in e for e in errors), errors)


class RetractedClaimsTest(_Isolated):
    def audit(self, prose: str) -> list[str]:
        (audit_build.CONTENT / "p.md").write_text(prose, encoding="utf-8")
        errors: list[str] = []
        audit_build.audit_retracted_claims(errors)
        return errors

    def test_each_retracted_claim_is_caught_in_its_known_phrasings(self) -> None:
        # Todas já voltaram ao site depois de corrigidas, em uma destas formas.
        for prose in (
            "Nenhum detalhe técnico é trocado antes do NDA assinado.",
            "NDA assinado desde o primeiro briefing.",
            "Com sigilo absoluto e regulação completa.",
            "Formulações clean beauty e veganas disponíveis.",
            "Any range we produce can be formulated as vegan.",
            "MOQ baixo por unidade.",
            "Per-unit minimums are a starting reference.",
            "Rendimento do lote mínimo de 20 kg.",
            "Qualidade incondicional.",
        ):
            with self.subTest(prose=prose):
                self.assertTrue(self.audit(prose), prose)

    def test_current_wording_passes(self) -> None:
        self.assertEqual(self.audit(
            "O projeto é confidencial desde o primeiro contato; NDA sempre que você pedir. "
            "Versões clean beauty e veganas avaliadas produto a produto. Mínimo de 20 kg "
            "por SKU. Não existe preço por unidade antes de a embalagem ser definida."), [])


class UnusedI18nKeysTest(_Isolated):
    def audit(self, template: str, keys: list[str]) -> list[str]:
        (audit_build.LAYOUTS / "index.html").write_text(template, encoding="utf-8")
        (audit_build.I18N / "pt-br.toml").write_text(
            "".join(f'{k} = "x"\n' for k in keys), encoding="utf-8")
        errors: list[str] = []
        audit_build.audit_unused_i18n_keys(errors)
        return errors

    def test_orphan_key_is_caught(self) -> None:
        errors = self.audit('{{ i18n "usada" }}', ["usada", "orfa"])
        self.assertEqual([e for e in errors if "orfa" in e], errors)
        self.assertEqual(len(errors), 1)

    def test_composed_keys_count_as_used_but_not_siblings(self) -> None:
        # Regressão: o prefixo solto "home_paraquem" deixava passar a órfã _whatsapp.
        template = ('{{ $key := printf "home_paraquem%d" .n }}'
                    '{{ i18n (printf "%s_title" $key) }}{{ i18n (printf "%s_text" $key) }}')
        errors = self.audit(template, ["home_paraquem1_title", "home_paraquem1_text",
                                       "home_paraquem1_whatsapp"])
        self.assertEqual(len(errors), 1)
        self.assertIn("home_paraquem1_whatsapp", errors[0])
