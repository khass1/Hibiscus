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


class AuditPagePropertiesTest(unittest.TestCase):
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
