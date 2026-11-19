"""Interface avançada (opções em inglês) para o mesmo pipeline do comando simples `shorts`.

Os resultados vão para output/ (ver config/shorts.toml). Para uso diário, preferir `shorts.cmd`.

    .venv\\Scripts\\python.exe scripts\\make_shorts.py <vídeo|URL> --count 3 --duration 30 \\
        --lang pt-BR --format 9:16 --style gaming [--name X] [--rights-confirmed] [--force] [--dry-run]
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from shorts_cli import load_config  # noqa: E402
from shorts_engine.pipeline import Request, Runner, UserError, preflight  # noqa: E402
from shorts_engine.styles import FORMATS, STYLES  # noqa: E402

REPO = Path(__file__).resolve().parents[1]


def main() -> int:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source")
    ap.add_argument("--name")
    ap.add_argument("--count", type=int, default=3)
    ap.add_argument("--duration", type=float, default=30.0)
    ap.add_argument("--lang", default="auto", choices=["auto", "pt-BR", "pt-PT", "en"])
    ap.add_argument("--format", default="9:16", choices=list(FORMATS))
    ap.add_argument("--style", default="gaming", choices=list(STYLES))
    ap.add_argument("--rights-confirmed", action="store_true")
    ap.add_argument("--credit")
    ap.add_argument("--force", action="store_true", help="recomeçar a execução do zero")
    ap.add_argument("--dry-run", action="store_true", help="só ingestão, análise e seleção")
    a = ap.parse_args()

    cfg = load_config()
    out_root = (REPO / cfg.get("saida", {}).get("pasta", "output")).resolve()
    req = Request(source=a.source, count=a.count, duration=a.duration, lang=a.lang, style=a.style,
                  fmt=a.format, name=a.name, rights=a.rights_confirmed, credit=a.credit, force=a.force)
    try:
        preflight(req)
    except UserError as e:
        print(f"✖ {e}\n  → {e.hint}")
        return e.code
    runner = Runner(req, {**cfg.get("avancado", {}), **cfg.get("saida", {})}, out_root)
    if a.dry_run:
        runner._ingest()
        runner._analyse()
        runner._select()
        return 0
    return runner.execute()


if __name__ == "__main__":
    sys.exit(main())
