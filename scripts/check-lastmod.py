#!/usr/bin/env python3
"""Barra commit de conteúdo editado sem `lastmod:` atualizado.

O sitemap usa `lastmod` para dizer ao Google que a página mudou (ver
README.md, seção "lastmod — obrigatório"). Não há automação: quem edita o
corpo de uma página em content/ precisa lembrar de subir a data à mão. Este
script roda antes do commit e reprova quando isso foi esquecido.

Armadilha do jeito ingênuo de checar isso: `lastmod:` costuma ficar na
linha 2 do front matter, logo abaixo de `---`. Um diff comum (3 linhas de
contexto) inclui essa linha como CONTEXTO sempre que qualquer chave vizinha
do front matter é editada — então `"lastmod:" in diff` dá falso negativo
justo no caso mais comum: front matter mexido, lastmod esquecido, e a
string aparece no diff mesmo assim (como contexto, não como mudança).
A defesa é usar diff SEM contexto (`-U0`) e exigir uma linha ADICIONADA
que comece com `+lastmod:` — contexto nunca carrega esse prefixo.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]

ADDED_LASTMOD_RE = re.compile(r"^\+lastmod:\s*\S", re.MULTILINE)


def staged_markdown_files() -> list[str]:
    # :(glob) é necessário para o `**` casar também com .md direto em content/
    # (sem subpasta) — o pathspec `content/**/*.md` sem essa magic exige pelo
    # menos um nível de diretório entre content/ e o arquivo, e hoje TODO
    # arquivo de content/ está no nível raiz. Sem isso o script "passa" sempre,
    # porque a lista de arquivos staged sai vazia — falso negativo silencioso,
    # a mesma classe de bug que o -U0 do diff evita para o `lastmod:` em si.
    result = subprocess.run(
        ["git", "diff", "--cached", "--name-only", "--diff-filter=ACMR", "--", ":(glob)content/**/*.md"],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return [line for line in result.stdout.splitlines() if line]


def staged_diff(path: str) -> str:
    # -U0: zero linhas de contexto. É o que impede uma edição vizinha de
    # arrastar `lastmod:` para dentro do diff como contexto e mascarar que a
    # própria linha do lastmod não mudou.
    result = subprocess.run(
        ["git", "diff", "--cached", "-U0", "--", path],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def has_body_change(diff: str) -> bool:
    for line in diff.splitlines():
        if not line.startswith(("+", "-")):
            continue
        if line.startswith(("+++", "---")):
            continue
        return True
    return False


def main() -> int:
    offenders: list[str] = []
    for path in staged_markdown_files():
        diff = staged_diff(path)
        if not diff:
            continue
        if not has_body_change(diff):
            continue
        if ADDED_LASTMOD_RE.search(diff):
            continue
        offenders.append(path)

    if offenders:
        print(
            "check-lastmod: arquivo(s) editado(s) sem `lastmod:` atualizado:",
            file=sys.stderr,
        )
        for path in offenders:
            print(f"- {path}", file=sys.stderr)
        print(
            "Suba a data de `lastmod:` no front matter para a data de hoje "
            "antes de commitar (ver README.md, seção lastmod).",
            file=sys.stderr,
        )
        return 1

    print("check-lastmod: ok.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
