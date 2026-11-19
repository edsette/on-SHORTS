"""Entrada: ficheiro local ou link. Links só com confirmação explícita de direitos de uso comercial."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from pathlib import Path


def is_url(s: str) -> bool:
    return bool(re.match(r"^https?://", s.strip(), re.I))


def already_downloaded(input_dir: Path, section: tuple[float, float] | None) -> bool:
    suffix = f"_{int(section[0])}-{int(section[1])}" if section else ""
    return input_dir.exists() and any(p.stat().st_size > 0 for p in input_dir.glob(f"*{suffix}.mp4"))


def fetch(source: str, input_dir: Path, rights_confirmed: bool,
          section: tuple[float, float] | None = None) -> tuple[Path, dict]:
    """Devolve (caminho local, info de proveniência). `section` (início, fim em s) descarrega só esse trecho."""
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
    suffix = f"_{int(section[0])}-{int(section[1])}" if section else ""
    out_tmpl = str(input_dir / f"%(id)s{suffix}.%(ext)s")
    cmd = ["yt-dlp", "--no-playlist", "--write-info-json", "--no-progress",
           "-f", "bv*[height<=1080][vcodec^=avc1]+ba[ext=m4a]/bv*[height<=1080]+ba/b[height<=1080]/b",
           "--merge-output-format", "mp4", "-o", out_tmpl, "--print", "after_move:filepath"]
    if section:
        cmd += ["--download-sections", f"*{section[0]:.0f}-{section[1]:.0f}"]
    cmd.append(source)
    existing = [p for p in input_dir.glob(f"*{suffix}.mp4") if p.stat().st_size > 0]
    if existing:  # já descarregado numa execução anterior
        path = existing[0]
        info_path = next(input_dir.glob(f"*{suffix}.info.json"), path.with_suffix(".info.json"))
        meta = {}
        if info_path.exists():
            j = json.loads(info_path.read_text(encoding="utf-8"))
            meta = {k: j.get(k) for k in ("title", "uploader", "channel", "webpage_url", "license", "upload_date")}
        return path, {"type": "url", "url": source, "path": str(path), "rights_confirmed": True,
                      "section_s": list(section) if section else None, **meta}
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode:
        raise SystemExit(f"yt-dlp falhou: {r.stderr.strip()[-600:]}")
    path = Path(r.stdout.strip().splitlines()[-1])
    info_path = path.with_suffix(".info.json")
    meta = {}
    if info_path.exists():
        j = json.loads(info_path.read_text(encoding="utf-8"))
        meta = {k: j.get(k) for k in ("title", "uploader", "channel", "webpage_url", "license", "upload_date")}
    return path, {"type": "url", "url": source, "path": str(path), "rights_confirmed": True,
                  "section_s": list(section) if section else None, **meta}
