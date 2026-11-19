"""GTA6-SHORTS — comando simples.

Formas de usar (a partir da pasta do projeto):

  1) Assistente (faz perguntas):          shorts
  2) Pedido em texto livre:               shorts --pedido "Vídeo: C:\\clip.mp4
                                                            Cortes: 8
                                                            Duração: 45 segundos
                                                            Idioma: Português BR
                                                            Estilo: Gaming dinâmico"
  3) Pedido num ficheiro de texto:        shorts --pedido-ficheiro pedido.txt
  4) Opções:                              shorts --video C:\\clip.mp4 --cortes 8 --duracao 45 --idioma pt-BR --estilo gaming
  5) Ver projetos:                        shorts --listar

Correr o mesmo pedido outra vez retoma uma execução interrompida (ou mostra que já está concluída).
Use --refazer para começar essa execução do zero.
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import tomllib
import unicodedata
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))

def refresh_path() -> None:
    """Junta ao PATH do processo o PATH atual do registo (Máquina + Utilizador).
    Assim o FFmpeg/yt-dlp instalados pelo winget são encontrados mesmo num terminal aberto antes da instalação."""
    try:
        import winreg
        parts = []
        for hive, key in ((winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"),
                          (winreg.HKEY_CURRENT_USER, r"Environment")):
            try:
                with winreg.OpenKey(hive, key) as k:
                    parts.append(os.path.expandvars(winreg.QueryValueEx(k, "Path")[0]))
            except OSError:
                pass
        cur = os.environ.get("PATH", "")
        extra = [p for p in ";".join(parts).split(";") if p and p not in cur]
        if extra:
            os.environ["PATH"] = cur + ";" + ";".join(extra)
    except ImportError:
        pass


refresh_path()
os.environ.setdefault("HF_HUB_DISABLE_SYMLINKS_WARNING", "1")
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
os.environ.setdefault("HF_HUB_VERBOSITY", "error")

# ----------------------------------------------------------------------------- interpretação


def _n(s: str) -> str:
    s = unicodedata.normalize("NFKD", s.lower().strip())
    return "".join(c for c in s if not unicodedata.combining(c))


KEYS = {
    "video": ["video", "link", "url", "ficheiro", "arquivo", "fonte", "caminho", "source"],
    "count": ["cortes", "corte", "quantidade", "numero de cortes", "shorts", "clips", "quantos"],
    "duration": ["duracao", "tempo", "duracao de cada corte", "segundos", "duration"],
    "lang": ["idioma", "lingua", "language", "lang"],
    "style": ["estilo", "estilo de edicao", "style", "edicao"],
    "fmt": ["formato", "format", "proporcao", "aspeto", "aspecto"],
    "name": ["nome", "projeto", "name"],
    "rights": ["direitos", "licenca", "rights", "autorizacao"],
    "credit": ["credito", "creditos", "credit"],
    "section": ["trecho", "secao", "intervalo", "parte", "section"],
}


def _ts(s: str) -> float:
    s = s.strip()
    if ":" in s:
        parts = [float(p) for p in s.split(":")]
        sec = 0.0
        for p in parts:
            sec = sec * 60 + p
        return sec
    return float(s.replace(",", "."))


def parse_section(v: str) -> tuple[float, float]:
    """'primeiros 30 minutos' | '10:00-40:00' | '0-1800' | '1:00:00-1:30:00'"""
    s = _n(v)
    m = re.search(r"primeir[oa]s?\s+(\d+(?:[.,]\d+)?)\s*(min|m\b|minutos?|h|horas?|s|seg)", s)
    if m:
        x = float(m.group(1).replace(",", "."))
        unit = m.group(2)
        mult = 3600 if unit.startswith("h") else (1 if unit.startswith("s") else 60)
        return (0.0, x * mult)
    m = re.match(r"^\s*([\d:.,]+)\s*(?:-|a|ate|to)\s*([\d:.,]+)\s*$", s)
    if m:
        a, b = _ts(m.group(1)), _ts(m.group(2))
        if b > a:
            return (a, b)
    raise ValueError(f"não percebi o trecho '{v}' (ex.: primeiros 30 minutos, 10:00-40:00)")


def parse_duration(v: str) -> float:
    s = _n(v)
    m = re.match(r"^(\d+):(\d{1,2})$", s)
    if m:
        return int(m.group(1)) * 60 + int(m.group(2))
    num = re.search(r"(\d+(?:[.,]\d+)?)", s)
    if not num:
        raise ValueError(f"não percebi a duração '{v}' (ex.: 45 segundos, 1 minuto, 1:30)")
    x = float(num.group(1).replace(",", "."))
    if re.search(r"\bmin", s):
        x *= 60
    return x


def parse_lang(v: str) -> str:
    s = _n(v)
    if s in ("auto", "automatico", "detetar", "detectar"):
        return "auto"
    if re.search(r"\b(pt-?pt|portugal|europeu|pt pt)\b", s) or s in ("pt-pt", "ptpt"):
        return "pt-PT"
    if re.search(r"(pt-?br|brasil|br\b|brasileiro)", s):
        return "pt-BR"
    if re.search(r"(ingles|english|^en\b|en-us|en-gb)", s):
        return "en"
    if s.startswith("port") or s == "pt":
        return "pt-BR"
    raise ValueError(f"não percebi o idioma '{v}' (usa Português BR, Português PT, Inglês ou auto)")


def parse_style(v: str) -> str:
    s = _n(v)
    if re.search(r"(gam|jogo|dinamic)", s):
        return "gaming"
    if re.search(r"(minim|limpo|simples|clean)", s):
        return "minimal"
    if re.search(r"(viral|motion|grafic)", s):
        return "viral"
    raise ValueError(f"não percebi o estilo '{v}' (usa Gaming dinâmico, Minimalista ou Viral)")


def parse_format(v: str) -> str:
    s = _n(v).replace(" ", "")
    if s in ("9:16", "9x16", "vertical", "shorts", "tiktok", "reels", "story", "stories"):
        return "9:16"
    if s in ("1:1", "1x1", "quadrado", "square"):
        return "1:1"
    if s in ("4:5", "4x5", "feed", "retrato"):
        return "4:5"
    if s in ("16:9", "16x9", "horizontal", "youtube", "paisagem"):
        return "16:9"
    raise ValueError(f"não percebi o formato '{v}' (usa 9:16, 1:1, 4:5 ou 16:9)")


def parse_count(v: str) -> int:
    m = re.search(r"\d+", v)
    if not m:
        raise ValueError(f"não percebi o número de cortes '{v}'")
    return int(m.group(0))


def parse_yes(v: str) -> bool:
    s = _n(v)
    if re.match(r"^(nao|no|n)\b", s) or "nao " in s:
        return False
    return bool(re.search(r"(sim|confirm|yes|^s$|^y$|tenho|autoriz|propri|cc)", s))


def parse_request_text(text: str) -> dict:
    """Interpreta um bloco 'Chave: valor' (ordem e acentos livres). Linhas sem ':' são ignoradas,
    exceto um caminho/link solto, que é tomado como o vídeo."""
    out: dict = {}
    for raw in text.replace("﻿", "").splitlines():
        line = raw.strip().lstrip("-•* ").strip()
        if not line or line.startswith("/"):
            continue
        if re.match(r'^("?[a-zA-Z]:\\|https?://|\\\\|\.{0,2}[\\/])', line):
            out.setdefault("video", line.strip('"'))
            continue
        if ":" not in line:
            continue
        k, v = line.split(":", 1)
        nk, v = _n(k), v.strip().strip('"')
        for field, names in KEYS.items():
            if nk in names:
                out[field] = v
                break
    return out


# ----------------------------------------------------------------------------- configuração


def load_config() -> dict:
    p = REPO / "config" / "shorts.toml"
    cfg = {"predefinicoes": {}, "saida": {}, "avancado": {}}
    if p.exists():
        try:
            cfg.update(tomllib.loads(p.read_text(encoding="utf-8-sig")))  # tolera BOM (Bloco de Notas)
        except tomllib.TOMLDecodeError as e:
            sys.exit(f"✖ Erro no ficheiro config/shorts.toml: {e}\n  → Corrige a linha indicada (aspas, '=', etc.).")
    return cfg


def build_request(fields: dict, cfg: dict, force: bool):
    from shorts_engine.pipeline import Request
    d = cfg.get("predefinicoes", {})
    errs = []

    def get(field, parser, default):
        if field in fields and str(fields[field]).strip():
            try:
                return parser(str(fields[field]))
            except ValueError as e:
                errs.append(str(e))
        return default

    video = fields.get("video", "").replace("﻿", "").strip().strip('"').strip("'")
    if not video:
        errs.append("falta o vídeo (caminho do ficheiro ou link)")
    req = Request(
        source=video,
        count=get("count", parse_count, int(d.get("cortes", 5))),
        duration=get("duration", parse_duration, float(d.get("duracao", 30))),
        lang=get("lang", parse_lang, parse_lang(str(d.get("idioma", "pt-BR")))),
        style=get("style", parse_style, parse_style(str(d.get("estilo", "gaming")))),
        fmt=get("fmt", parse_format, parse_format(str(d.get("formato", "9:16")))),
        name=fields.get("name") or None,
        rights=get("rights", parse_yes, False),
        credit=fields.get("credit") or None,
        force=force,
        section=get("section", parse_section, None),
    )
    return req, errs


# ----------------------------------------------------------------------------- assistente


def ask(prompt: str, default: str = "") -> str:
    suffix = f" [{default}]" if default else ""
    try:
        v = input(f"{prompt}{suffix}: ").replace("﻿", "").strip().strip('"')
    except EOFError:
        v = ""
    return v or default


def wizard(cfg: dict) -> dict:
    d = cfg.get("predefinicoes", {})
    print("\n=== GTA6-SHORTS — novo pedido ===  (Enter = valor sugerido)\n")
    f = {"video": ask("Vídeo (arrasta o ficheiro para aqui ou cola o link)")}
    f["count"] = ask("Quantos cortes", str(d.get("cortes", 5)))
    f["duration"] = ask("Duração de cada corte (segundos)", str(d.get("duracao", 30)))
    f["lang"] = ask("Idioma (Português BR / Português PT / Inglês / auto)", str(d.get("idioma", "pt-BR")))
    f["style"] = ask("Estilo (Gaming dinâmico / Minimalista / Viral)", str(d.get("estilo", "gaming")))
    f["fmt"] = ask("Formato (9:16 / 1:1 / 4:5 / 16:9)", str(d.get("formato", "9:16")))
    if re.match(r"^https?://", f["video"]):
        print("\nAtenção: só é permitido usar vídeos teus, com licença CC-BY/CC0 ou autorização escrita.")
        f["rights"] = ask("Confirmas que tens direitos de utilização comercial deste vídeo? (sim/não)", "não")
    return f


# ----------------------------------------------------------------------------- main


def list_projects(out_root: Path) -> None:
    from shorts_engine.pipeline import update_index
    if not out_root.exists():
        print("Ainda não há projetos em output/.")
        return
    update_index(out_root)
    print((out_root / "INDEX.md").read_text(encoding="utf-8"))


def main() -> int:
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except Exception:  # noqa: BLE001
            pass
    ap = argparse.ArgumentParser(prog="shorts", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--pedido", help="pedido em texto (linhas 'Chave: valor')")
    ap.add_argument("--pedido-ficheiro", help="ficheiro .txt com o pedido")
    ap.add_argument("--video")
    ap.add_argument("--cortes")
    ap.add_argument("--duracao")
    ap.add_argument("--idioma")
    ap.add_argument("--estilo")
    ap.add_argument("--formato")
    ap.add_argument("--nome")
    ap.add_argument("--credito")
    ap.add_argument("--trecho", help="só para links: parte a descarregar (ex.: 'primeiros 30 minutos', '10:00-40:00')")
    ap.add_argument("--direitos", action="store_true", help="confirmo direitos de utilização comercial (links)")
    ap.add_argument("--refazer", action="store_true", help="recomeçar esta execução do zero")
    ap.add_argument("--listar", action="store_true", help="mostrar projetos e estado")
    ap.add_argument("--simular", action="store_true", help="só mostrar como o pedido foi interpretado")
    a = ap.parse_args()

    cfg = load_config()
    out_root = (REPO / cfg.get("saida", {}).get("pasta", "output")).resolve()
    out_root.mkdir(parents=True, exist_ok=True)
    if a.listar:
        list_projects(out_root)
        return 0

    fields: dict = {}
    if a.pedido_ficheiro:
        fields.update(parse_request_text(Path(a.pedido_ficheiro).read_text(encoding="utf-8-sig")))
    if a.pedido:
        fields.update(parse_request_text(a.pedido))
    for k, v in {"video": a.video, "count": a.cortes, "duration": a.duracao, "lang": a.idioma,
                 "style": a.estilo, "fmt": a.formato, "name": a.nome, "credit": a.credito,
                 "section": a.trecho}.items():
        if v:
            fields[k] = v
    if a.direitos:
        fields["rights"] = "sim"
    if not fields:
        fields = wizard(cfg)

    req, errs = build_request(fields, cfg, a.refazer)
    if errs:
        print("✖ Não consegui perceber o pedido:")
        for e in errs:
            print(f"  - {e}")
        print("\nExemplo:\n  Vídeo: C:\\videos\\gameplay.mp4\n  Cortes: 8\n  Duração: 45 segundos\n"
              "  Idioma: Português BR\n  Estilo: Gaming dinâmico")
        return 2

    from shorts_engine.pipeline import STYLES, Runner, project_slug, run_id
    print("\nPedido:")
    print(f"  Vídeo:    {req.source}")
    print(f"  Cortes:   {req.count} × {req.duration:.0f} s")
    print(f"  Idioma:   {req.lang}   Estilo: {STYLES[req.style]['label']}   Formato: {req.fmt}")
    if req.section:
        print(f"  Trecho:   {req.section[0]:.0f} s – {req.section[1]:.0f} s")
    print(f"  Pasta:    {out_root / project_slug(req) / run_id(req)}\n")
    if a.simular:
        return 0

    # validação antes de criar pastas
    from shorts_engine.pipeline import preflight, UserError
    try:
        preflight(req)
    except UserError as e:
        print(f"✖ {e}")
        if e.hint:
            print(f"  → {e.hint}")
        return e.code

    runner = Runner(req, {**cfg.get("avancado", {}), **cfg.get("saida", {})}, out_root)
    if runner.state.get("status") == "concluido" and not a.refazer:
        print("✔ Este pedido já foi concluído. Resultados em:")
        print(f"  {runner.run / 'export'}")
        print("  (usa --refazer para gerar de novo)")
        return 0
    code = runner.execute()
    n_ok = sum(1 for c in runner.state["clips"].values() if c.get("status") == "concluido")
    print("\n" + "=" * 70)
    if code == 0:
        print(f"✅ Concluído: {n_ok} Shorts prontos (nada foi publicado).")
    elif code == 1:
        print(f"⚠️  Concluído com erros: {n_ok} Shorts prontos; corre o mesmo pedido para tentar de novo os que falharam.")
    elif code == 3:
        print(f"⏸  Interrompido com {n_ok} Shorts prontos. Corre o mesmo pedido para continuar.")
    else:
        print("❌ Não concluído. O progresso foi guardado; corrige o problema acima e corre o mesmo pedido.")
    if n_ok:
        print(f"   Vídeos:     {runner.run / 'export'}")
    print(f"   Relatório:  {runner.run / 'report.md'}")
    print("=" * 70)
    return code


if __name__ == "__main__":
    sys.exit(main())
