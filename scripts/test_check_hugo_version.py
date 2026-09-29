"""Verifica os formatos oficiais e Homebrew sem depender do Hugo instalado."""

import contextlib
import importlib.util
import io
from pathlib import Path
import unittest
from unittest.mock import patch


SPEC = importlib.util.spec_from_file_location(
    "check_hugo_version", Path(__file__).with_name("check-hugo-version.py")
)
checker = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(checker)


class HugoVersionTest(unittest.TestCase):
    def check(self, output):
        with patch.object(Path, "read_text", return_value="      HUGO_VERSION: 0.167.0\n"), \
             patch.object(checker.subprocess, "check_output", return_value=output), \
             contextlib.redirect_stdout(io.StringIO()), \
             contextlib.redirect_stderr(io.StringIO()):
            return checker.main()

    def test_supported_release_formats(self):
        for output in (
            "hugo v0.167.0-3fff6fb5c267dacb26280c78dbe8c344054249c8+extended linux/amd64",
            "hugo v0.167.0+extended+withdeploy darwin/arm64",
            "hugo v0.167.0+extended linux/amd64",
        ):
            with self.subTest(output=output):
                self.assertEqual(self.check(output), 0)

    def test_wrong_version_edition_and_prerelease_rejected(self):
        for output in (
            "hugo v0.166.0+extended linux/amd64",
            "hugo v0.167.0-3fff6fb linux/amd64",
            "hugo v0.167.0 linux/amd64",
            "hugo v0.167.0-rc.1+extended linux/amd64",
            "hugo v0.167.0+extended-invalid linux/amd64",
            "not a version",
        ):
            with self.subTest(output=output):
                self.assertEqual(self.check(output), 1)

    def test_missing_binary_fails_cleanly(self):
        with patch.object(Path, "read_text", return_value="      HUGO_VERSION: 0.167.0\n"), \
             patch.object(checker.subprocess, "check_output", side_effect=FileNotFoundError), \
             contextlib.redirect_stderr(io.StringIO()):
            self.assertEqual(checker.main(), 1)
