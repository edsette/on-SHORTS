"""Entrada: ficheiro local ou link. Links só com confirmação explícita de direitos de uso comercial."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path


def is_url(s: str) -> bool:
    return bool(re.match(r"^https?://", s.strip(), re.I))


def fetch(source: str, input_dir: Path, rights_confirmed: bool) -> tuple[Path, dict]:
    """Devolve (caminho local, info de proveniência)."""
    input_dir.mkdir(parents=True, exist_ok=True)
    if not is_url(source):
        p = Path(source).expanduser().resolve()
        if not p.exists():
            raise SystemExit(f"Ficheiro não encontrado: {p}")
        return p, {"type": "local", "path": str(p)}

    if not rights_confirmed:
        raise SystemExit(
            "Link recusado: confirma que tens direitos de utilização comercial deste conteúdo "
            "(conteúdo próprio, licença CC-BY/CC0 ou autorização escrita) e repete com --rights-confirmed.")
    if not shutil.which("yt-dlp"):
        raise SystemExit("yt-dlp não encontrado no PATH.")
    out_tmpl = str(input_dir / "%(id)s.%(ext)s")
    cmd = ["yt-dlp", "--no-playlist", "--write-info-json", "--no-progress",
           "-f", "bv*[height<=1080]+ba/b[height<=1080]/b", "--merge-output-format", "mp4",
           "-o", out_tmpl, "--print", "after_move:filepath", source]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode:
        raise SystemExit(f"yt-dlp falhou: {r.stderr.strip()[-600:]}")
    path = Path(r.stdout.strip().splitlines()[-1])
    info_path = path.with_suffix(".info.json")
    meta = {}
    if info_path.exists():
        j = json.loads(info_path.read_text(encoding="utf-8"))
        meta = {k: j.get(k) for k in ("title", "uploader", "channel", "webpage_url", "license", "upload_date")}
    return path, {"type": "url", "url": source, "path": str(path), "rights_confirmed": True, **meta}
