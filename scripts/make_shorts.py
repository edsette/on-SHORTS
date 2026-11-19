"""Motor de produção de Shorts — 100% local, sem publicação automática.

Exemplos (a partir da raiz do repo):
    .venv\\Scripts\\python.exe scripts\\make_shorts.py projects\\gta\\input\\gameplay.mp4 --name gta ^
        --count 3 --duration 30 --lang pt-BR --format 9:16 --style gaming

    .venv\\Scripts\\python.exe scripts\\make_shorts.py "https://..." --name clip --rights-confirmed ^
        --count 2 --duration 45 --style viral

Parâmetros principais:
    --count     quantidade de cortes          --duration  duração alvo de cada corte (s)
    --lang      auto | pt-BR | pt-PT | en     --format    9:16 | 1:1 | 4:5 | 16:9
    --style     gaming | minimal | viral      --dry-run   só analisa e mostra a seleção

Saídas em projects/<name>/:
    input/                  fonte (links descarregados aqui, com .info.json de proveniência)
    analysis/               transcrição, análise e momentos (reutilizados em execuções seguintes)
    shorts/<style>/         short-NN.mp4 + short-NN.json (metadados) + short-NN.txt (copiar/colar)
    review/<style>/         folhas de contacto (short-NN.jpg)
    work/<style>/           .ass, filtergraphs (regeneráveis)
    shorts/<style>/report.md
Nada é publicado: os ficheiros ficam prontos para revisão e upload manual.
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from analyze_video import run_analysis, write_json  # noqa: E402
from shorts_engine import captions, metadata, render, select, source  # noqa: E402
from shorts_engine.styles import FORMATS, STYLES, TEXT, ui_lang  # noqa: E402

REPO = Path(__file__).resolve().parents[1]


def main() -> None:
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:  # noqa: BLE001
        pass
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("source", help="caminho de vídeo local ou URL (com --rights-confirmed)")
    ap.add_argument("--name", required=True, help="nome do projeto (pasta em projects/)")
    ap.add_argument("--count", type=int, default=3)
    ap.add_argument("--duration", type=float, default=30.0, help="duração alvo por corte, em segundos")
    ap.add_argument("--min-duration", type=float)
    ap.add_argument("--max-duration", type=float)
    ap.add_argument("--lang", default="auto", choices=["auto", "pt-BR", "pt-PT", "en"])
    ap.add_argument("--format", default="9:16", choices=list(FORMATS))
    ap.add_argument("--style", default="gaming", choices=list(STYLES))
    ap.add_argument("--model", default="large-v3-turbo")
    ap.add_argument("--device", default="auto", choices=["auto", "cuda", "cpu"])
    ap.add_argument("--encoder", default="auto", choices=["auto", "nvenc", "x264"])
    ap.add_argument("--rights-confirmed", action="store_true",
                    help="obrigatório para links: confirmas direitos de utilização comercial")
    ap.add_argument("--credit", help="texto de crédito/fonte para a descrição")
    ap.add_argument("--no-teaser", action="store_true", help="desativa o cold open com o momento-pico")
    ap.add_argument("--dry-run", action="store_true")
    a = ap.parse_args()

    t0 = time.time()
    proj = REPO / "projects" / a.name
    style = dict(STYLES[a.style])
    if a.no_teaser:
        style["teaser"] = False
    W, H = FORMATS[a.format]
    target = a.duration
    min_len = a.min_duration or max(10.0, 0.7 * target)
    max_len = a.max_duration or min(90.0, 1.3 * target)

    src_path, prov = source.fetch(a.source, proj / "input", a.rights_confirmed)
    print(f"[1/5] fonte: {src_path}")

    lang = "pt" if a.lang.startswith("pt") else ("en" if a.lang == "en" else "auto")
    variant = a.lang if a.lang != "auto" else "auto"
    res = run_analysis(src_path, proj / "analysis", model_name=a.model, device=a.device, lang=lang,
                       variant=variant, use_cache=True)
    an = res["analysis"]
    print(f"[2/5] análise: {an['duration_s']:.1f}s, língua={an['language']}, {an['words']} palavras, "
          f"{len(res['moments'])} momentos, {len(res['peaks'])} picos, {len(res['scenes'])} cortes "
          f"({'cache' if an['timings'].get('cache') else f'{an['timings'].get('transcribe_s', 0)}s transcrição'})")
    if not res["media"]["video"]:
        raise SystemExit("A fonte não tem stream de vídeo.")

    L = ui_lang(a.lang, an["language"])
    texts = TEXT[L]
    clips = select.select_clips(res["units"], res["moments"], res["peaks"], res["scenes"], an["duration_s"],
                                a.count, target, min_len, max_len, style["teaser"], texts)
    print(f"[3/5] seleção: {len(clips)} de {a.count} pedidos")
    for c in clips:
        pcs = " + ".join(f"{p.kind}[{p.src_start:.2f}-{p.src_end:.2f}]" for p in c.pieces)
        print(f"   {c.id}: {c.out_duration:.1f}s score={c.score} cat={c.category} gancho=\"{c.hook_text}\" | {pcs}")
    if a.dry_run or not clips:
        return

    out_dir = proj / "shorts" / a.style
    work = proj / "work" / a.style
    review = proj / "review" / a.style
    for d in (out_dir, work, review):
        d.mkdir(parents=True, exist_ok=True)

    credit = a.credit or (prov.get("uploader") and f"{prov.get('uploader')} — {prov.get('webpage_url')}")
    results = []
    for c in clips:
        ts = time.time()
        flash = []
        if style["flash"] and len(c.pieces) > 1:
            flash.append(round(c.pieces[0].dur, 3))
        punches = render.emphasis_times(c, res["peaks"], res["moments"], style)
        ass = work / f"{c.id}.ass"
        cap_info = captions.build_ass(c, res["units"], res["moments"], style, W, H, texts, ass, flash)
        mp4 = out_dir / f"{c.id}.mp4"
        rinfo = render.render_clip(c, str(src_path), res["media"], style, W, H, ass.name, work, mp4,
                                   res["scenes"], punches, a.encoder)
        ver = render.verify(mp4, W, H, c.out_duration)
        render.contact_sheet(mp4, review / f"{c.id}.jpg", c.out_duration)
        meta = metadata.build(c, texts, L, a.style, credit)
        record = {
            "id": c.id, "file": str(mp4), "style": a.style, "format": a.format, "language": L,
            "source": prov, "source_range": [round(c.start, 3), round(c.end, 3)],
            "pieces": [{"kind": p.kind, "src_start": round(p.src_start, 3), "src_end": round(p.src_end, 3)}
                       for p in c.pieces],
            "duration_s": round(c.out_duration, 3), "score": c.score, "category": c.category,
            "selection_reasons": c.reasons, "hook": c.hook_text, "transcript_excerpt": c.text,
            "captions": cap_info, "render": rinfo, "verify": ver, "metadata": meta,
            "render_seconds": round(time.time() - ts, 1), "published": False,
        }
        write_json(out_dir / f"{c.id}.json", record)
        (out_dir / f"{c.id}.txt").write_text(
            f"TÍTULO\n{meta['title']}\n\nDESCRIÇÃO\n{meta['description']}\n\nHASHTAGS\n{' '.join(meta['hashtags'])}\n\n"
            f"TIKTOK\n{meta['captions']['tiktok']}\n\nINSTAGRAM\n{meta['captions']['instagram_reels']}\n",
            encoding="utf-8")
        results.append(record)
        print(f"[4/5] {c.id}: {ver['duration_s']}s {ver['width']}x{ver['height']} {rinfo['encoder']} "
              f"{'OK' if ver['ok'] else 'FALHOU VERIFICAÇÃO'} ({record['render_seconds']}s) — {meta['title']}")

    lines = [f"# Shorts — {a.name} ({STYLES[a.style]['label']}, {a.format}, {L})", "",
             f"Fonte: `{src_path}` | Gerado em {time.time() - t0:.0f}s | **Não publicado**", "",
             "| Short | Duração | Score | Categoria | Origem | Gancho | Verificação | Título |",
             "|---|---:|---:|---|---|---|---|---|"]
    for r in results:
        orig = " + ".join(f"{p['kind']} {p['src_start']:.1f}-{p['src_end']:.1f}s" for p in r["pieces"])
        lines.append(f"| {r['id']} | {r['duration_s']}s | {r['score']} | {r['category']} | {orig} | "
                     f"{r['hook']} | {'OK' if r['verify']['ok'] else 'FALHOU'} | {r['metadata']['title']} |")
    (out_dir / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(f"[5/5] concluído: {len(results)} shorts em {out_dir} ({time.time() - t0:.0f}s). Nada foi publicado.")


if __name__ == "__main__":
    main()
