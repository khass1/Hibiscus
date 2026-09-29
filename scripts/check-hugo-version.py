"""Confere o Hugo local contra a versão fixada no workflow de produção."""

from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]


def main() -> int:
    workflow = (ROOT / '.github/workflows/build.yml').read_text()
    expected = re.search(r'^\s+HUGO_VERSION: ([\d.]+)$', workflow, re.MULTILINE)
    if not expected:
        print('HUGO_VERSION ausente no workflow', file=sys.stderr)
        return 1
    try:
        installed = subprocess.check_output(['hugo', 'version'], text=True)
    except (OSError, subprocess.CalledProcessError) as error:
        print(f'Hugo indisponível: {error}', file=sys.stderr)
        return 1
    # Releases oficiais incluem o hash; builds Homebrew podem omiti-lo.
    version = re.search(
        r'^hugo v(\d+\.\d+\.\d+)(?:-[0-9a-f]+)?\+extended(?:\+withdeploy)?(?=\s|$)',
        installed,
    )
    if not version or version.group(1) != expected.group(1):
        print(f'Requer Hugo Extended {expected.group(1)}; instalado: {installed.strip()}', file=sys.stderr)
        return 1
    print(f'Hugo Extended {expected.group(1)}: versão correta.')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
