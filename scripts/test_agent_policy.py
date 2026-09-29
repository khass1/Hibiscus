"""Contrato da política pública de uso por IA; não valida a borda Cloudflare."""

from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
POLICY = {"ai-train": "yes", "search": "yes", "ai-input": "yes"}


class AgentPolicyTest(unittest.TestCase):
    def test_robots_has_one_shared_policy_and_keeps_crawling_open(self) -> None:
        text = (ROOT / "static/robots.txt").read_text(encoding="utf-8")
        directives = [line.strip() for line in text.splitlines()
                      if line.strip() and not line.lstrip().startswith("#")]
        self.assertEqual([line for line in directives if line.startswith("User-agent:")],
                         ["User-agent: *"])
        self.assertIn("Allow: /", directives)
        self.assertFalse(any(line.startswith("Disallow:") for line in directives))
        self.assertIn("Sitemap: https://hibiscus.com.br/sitemap.xml", directives)
        self.assert_policy(text)

    def test_origin_header_matches_policy_on_all_paths(self) -> None:
        text = (ROOT / "static/_headers").read_text(encoding="utf-8")
        route = None
        scopes = []
        for line in text.splitlines():
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            if not line[0].isspace():
                route = line.strip()
            elif line.strip().lower().startswith("content-signal:"):
                scopes.append(route)
        self.assertEqual(scopes, ["/*"])
        self.assert_policy(text)

    def assert_policy(self, text: str) -> None:
        values = re.findall(r"^\s*Content-Signal:\s*([^\n]+)", text, re.MULTILINE)
        self.assertEqual(len(values), 1)
        pairs = [part.strip().split("=") for part in values[0].split(",")]
        self.assertEqual(len(pairs), 3)
        self.assertEqual(dict(pairs), POLICY)
