"""Pipeline completo com etapas, estado gravado e retoma.

Ingestão → Análise/Transcrição → Seleção → Edição (legendas/efeitos) → Renderização → Exportação → Relatório

Estrutura em output/:
    output/<projeto>/                       um projeto por vídeo de origem
        input/                              ficheiros descarregados de links (+ .info.json)
        analysis/                           transcrição e análise (partilhadas entre execuções)
        <execução>/                         uma pasta por combinação estilo/formato/cortes/duração/idioma
            export/   short-NN.mp4 + .txt (título, descrição, hashtags) + .json
            review/   short-NN.jpg (folhas de contacto)
            work/     ficheiros intermédios regeneráveis
            logs/     run-AAAAMMDD-HHMMSS.log (detalhe técnico)
            state.json                      estado das etapas (permite retomar)
            report.md                       relatório da execução
    output/INDEX.md                         lista de todos os projetos e execuções
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import shutil
import sys
import time
import traceback
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from analyze_video import run_analysis, write_json  # noqa: E402

from . import captions, metadata, render, select, source  # noqa: E402
from .styles import FORMATS, STYLES, TEXT, ui_lang  # noqa: E402

STAGES = ["ingestao", "analise", "selecao", "edicao_render", "relatorio"]
STAGE_LABEL = {"ingestao": "Ingestão", "analise": "Análise e transcrição", "selecao": "Seleção",
               "edicao_render": "Edição, legendas, renderização e exportação", "relatorio": "Relatório"}


class UserError(Exception):
    """Erro com mensagem clara para o utilizador (sem traceback)."""

    def __init__(self, msg: str, hint: str = "", code: int = 2):
        super().__init__(msg)
        self.hint = hint
        self.code = code


@dataclass
class Request:
    source: str
    count: int = 5
    duration: float = 30.0
    lang: str = "pt-BR"
    style: str = "gaming"
    fmt: str = "9:16"
    name: str | None = None
    rights: bool = False
    credit: str | None = None
    force: bool = False


def preflight(req: Request) -> None:
    """Validações rápidas antes de criar pastas: parâmetros, ferramentas, fonte e direitos."""
    if req.style not in STYLES:
        raise UserError(f"Estilo desconhecido: {req.style}", "Usa: Gaming dinâmico, Minimalista ou Viral.")
    if req.fmt not in FORMATS:
        raise UserError(f"Formato desconhecido: {req.fmt}", "Usa: 9:16, 1:1, 4:5 ou 16:9.")
    if not (1 <= req.count <= 30):
        raise UserError(f"Número de cortes inválido: {req.count}", "Escolhe entre 1 e 30.")
    if not (5 <= req.duration <= 180):
        raise UserError(f"Duração inválida: {req.duration:.0f} s", "Escolhe entre 5 e 180 segundos.")
    for tool in ("ffmpeg", "ffprobe"):
        if not shutil.which(tool):
            raise UserError(f"{tool} não encontrado.", "Reinstala com: winget install --id Gyan.FFmpeg -e")
    if source.is_url(req.source):
        if not req.rights:
            raise UserError("Link recusado: falta confirmar os direitos de utilização comercial.",
                            "Só usa conteúdo teu, com licença CC-BY/CC0 ou autorização escrita, e "
                            "acrescenta 'Direitos: confirmados' ao pedido (ou --direitos).")
        if not shutil.which("yt-dlp"):
            raise UserError("yt-dlp não encontrado (necessário para links).",
                            "Reinstala com: winget install --id yt-dlp.yt-dlp -e")
    elif not Path(req.source).expanduser().is_file():
        raise UserError(f"Ficheiro não encontrado: {req.source}",
                        "Confirma o caminho (dica: arrasta o ficheiro para a janela para colar o caminho).")


# ----------------------------------------------------------------------------- utilidades


def slugify(text: str, maxlen: int = 40) -> str:
    import unicodedata
    t = unicodedata.normalize("NFKD", text)
    t = "".join(c for c in t if not unicodedata.combining(c)).lower()
    t = re.sub(r"[^a-z0-9]+", "-", t).strip("-")
    return (t[:maxlen].rstrip("-")) or "video"


def project_slug(req: Request) -> str:
    if req.name:
        return slugify(req.name)
    if source.is_url(req.source):
        return "link-" + hashlib.sha1(req.source.strip().encode()).hexdigest()[:8]
    return slugify(Path(req.source).stem)


def run_id(req: Request) -> str:
    return f"{req.style}_{req.fmt.replace(':', 'x')}_{req.count}x{int(round(req.duration))}s_{req.lang}"


def atomic_json(path: Path, data) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    write_json(tmp, data)
    os.replace(tmp, path)


def fmt_secs(s: float) -> str:
    s = int(round(s))
    return f"{s // 60} min {s % 60:02d} s" if s >= 60 else f"{s} s"


def clip_to_dict(c: select.Clip) -> dict:
    return {"id": c.id, "start": c.start, "end": c.end, "score": c.score, "category": c.category,
            "units": c.units, "peak": c.peak, "hook_text": c.hook_text, "reasons": c.reasons,
            "pieces": [asdict(p) for p in c.pieces]}


def clip_from_dict(d: dict) -> select.Clip:
    c = select.Clip(id=d["id"], start=d["start"], end=d["end"], score=d["score"], category=d["category"],
                    units=d["units"], peak=d["peak"], hook_text=d["hook_text"], reasons=d["reasons"])
    c.pieces = [select.Piece(**p) for p in d["pieces"]]
    return c


# ----------------------------------------------------------------------------- pipeline


class Runner:
    def __init__(self, req: Request, cfg: dict, out_root: Path, console=print):
        self.req, self.cfg, self.say = req, cfg, console
        self.slug = project_slug(req)
        self.proj = out_root / self.slug
        self.run = self.proj / run_id(req)
        for d in ("export", "review", "work", "logs"):
            (self.run / d).mkdir(parents=True, exist_ok=True)
        self.state_path = self.run / "state.json"
        self.state = self._load_state()
        self.log = self._make_logger()
        self.res: dict | None = None
        self.clips: list[select.Clip] = []

    # ---- estado / log
    def _load_state(self) -> dict:
        params = {"source": self.req.source, "count": self.req.count, "duration": self.req.duration,
                  "lang": self.req.lang, "style": self.req.style, "format": self.req.fmt}
        if self.state_path.exists() and not self.req.force:
            st = json.loads(self.state_path.read_text(encoding="utf-8"))
            if st.get("params") == params:
                st["resumed"] = st.get("status") != "concluido"
                return st
        return {"params": params, "status": "novo", "stages": {s: {"status": "pendente"} for s in STAGES},
                "clips": {}, "errors": [], "runs": []}

    def save(self) -> None:
        atomic_json(self.state_path, self.state)

    def _make_logger(self) -> logging.Logger:
        log = logging.getLogger(f"shorts.{self.slug}.{id(self)}")
        log.setLevel(logging.DEBUG)
        stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        self.log_path = self.run / "logs" / f"run-{stamp}.log"
        fh = logging.FileHandler(self.log_path, encoding="utf-8")
        fh.setFormatter(logging.Formatter("%(asctime)s %(levelname)s %(message)s"))
        log.addHandler(fh)
        return log

    def stage(self, name: str, status: str, **extra) -> None:
        st = self.state["stages"][name]
        st["status"] = status
        st.update(extra)
        if status == "a_correr":
            st["started"] = datetime.now().isoformat(timespec="seconds")
        self.save()
        self.log.info("etapa %s -> %s %s", name, status, extra or "")

    def done(self, name: str) -> bool:
        return self.state["stages"][name]["status"] == "concluido"

    # ---- execução
    def execute(self) -> int:
        t0 = time.time()
        self.state["status"] = "a_correr"
        self.state["runs"].append({"started": datetime.now().isoformat(timespec="seconds"),
                                   "log": str(self.log_path.relative_to(self.run))})
        self.save()
        if self.state.get("resumed"):
            pend = [STAGE_LABEL[s] for s in STAGES if not self.done(s)]
            self.say(f"↻ A retomar a execução anterior. Etapas por fazer: {', '.join(pend)}")
        code = 0
        try:
            self._ingest()
            self._analyse()
            self._select()
            code = self._edit_render_export()
            self.state["status"] = "concluido" if code == 0 else "concluido_com_erros"
        except KeyboardInterrupt:
            self.state["status"] = "interrompido"
            self.say("\n⏸  Interrompido. O progresso foi guardado — corre o mesmo pedido para retomar.")
            code = 3
        except UserError as e:
            self.state["status"] = "erro"
            self.state["errors"].append({"when": datetime.now().isoformat(timespec="seconds"), "error": str(e)})
            self.log.error("UserError: %s", e)
            self.say(f"\n✖ {e}")
            if e.hint:
                self.say(f"  → {e.hint}")
            code = e.code
        except Exception as e:  # noqa: BLE001
            self.state["status"] = "erro"
            self.state["errors"].append({"when": datetime.now().isoformat(timespec="seconds"),
                                         "error": f"{type(e).__name__}: {e}"})
            self.log.error("Erro inesperado:\n%s", traceback.format_exc())
            self.say(f"\n✖ Erro inesperado: {type(e).__name__}: {e}")
            self.say(f"  → Detalhes técnicos em: {self.log_path}")
            self.say("  → O progresso foi guardado; corre o mesmo pedido para retomar.")
            code = 4
        finally:
            self.state["runs"][-1]["ended"] = datetime.now().isoformat(timespec="seconds")
            self.state["runs"][-1]["seconds"] = round(time.time() - t0, 1)
            self.save()
            try:
                self._report()
            except Exception:  # noqa: BLE001
                self.log.error("falha no relatório:\n%s", traceback.format_exc())
        return code

    # ---- 1. ingestão
    def _ingest(self) -> None:
        req = self.req
        preflight(req)
        free_gb = shutil.disk_usage(self.proj).free / 1e9
        need = float(self.cfg.get("espaco_minimo_gb", 5))
        if free_gb < need:
            raise UserError(f"Pouco espaço em disco: {free_gb:.1f} GB livres (mínimo {need:.0f} GB).",
                            "Liberta espaço ou apaga projetos antigos em output/.")

        st = self.state["stages"]["ingestao"]
        if self.done("ingestao") and Path(st.get("path", "")).exists():
            self.say(f"✔ Ingestão (já feita): {Path(st['path']).name}")
            self.src, self.prov = Path(st["path"]), st.get("provenance", {})
            return
        self.stage("ingestao", "a_correr")
        self.say("▶ 1/5 Ingestão…")
        try:
            self.src, self.prov = source.fetch(req.source, self.proj / "input", req.rights)
        except SystemExit as e:
            raise UserError(str(e), "Verifica o caminho do ficheiro ou o link.") from None
        from analyze_video import probe
        media = probe(self.src)
        if not media["video"]:
            raise UserError("O ficheiro não tem imagem (vídeo).", "Escolhe um ficheiro de vídeo (mp4, mkv, mov…).")
        if not media["audio"]:
            raise UserError("O vídeo não tem som.", "O sistema precisa do áudio para encontrar os momentos.")
        if media["duration_s"] < req.duration * 0.7:
            raise UserError(f"O vídeo tem só {media['duration_s']:.0f} s — é mais curto do que um corte de "
                            f"{req.duration:.0f} s.", "Reduz a duração dos cortes.")
        self.stage("ingestao", "concluido", path=str(self.src), provenance=self.prov,
                   duration_s=media["duration_s"],
                   resolution=f"{media['video']['width']}x{media['video']['height']}")
        self.say(f"  ✔ {self.src.name} — {fmt_secs(media['duration_s'])}, "
                 f"{media['video']['width']}x{media['video']['height']}")

    # ---- 2. análise + transcrição (com cache)
    def _analyse(self) -> None:
        req = self.req
        was_done = self.done("analise")
        self.stage("analise", "a_correr")
        self.say("✔ Análise (em cache) — a recarregar…" if was_done else
                 "▶ 2/5 Análise e transcrição (a primeira vez pode demorar)…")
        lang = "pt" if req.lang.startswith("pt") else ("en" if req.lang == "en" else "auto")
        variant = req.lang if req.lang != "auto" else "auto"
        self.res = run_analysis(self.src, self.proj / "analysis", model_name=self.cfg.get("modelo", "large-v3-turbo"),
                                device=self.cfg.get("dispositivo", "auto"), lang=lang, variant=variant,
                                use_cache=True)
        a = self.res["analysis"]
        if a["words"] == 0:
            self.say("  ⚠ Não foi detetada fala: a seleção usa apenas volume e cortes de cena.")
        self.stage("analise", "concluido", language=a["language"], words=a["words"],
                   moments=len(self.res["moments"]), device=a["device"],
                   transcribe_s=a["timings"].get("transcribe_s"), cached=bool(a["timings"].get("cache")))
        if not was_done:
            extra = " (transcrição reaproveitada)" if a["timings"].get("cache") else ""
            self.say(f"  ✔ língua {a['language']}, {a['words']} palavras, {len(self.res['moments'])} momentos, "
                     f"{len(self.res['peaks'])} picos de volume, {len(self.res['scenes'])} cortes de cena{extra}")

    # ---- 3. seleção
    def _select(self) -> None:
        req = self.req
        st = self.state["stages"]["selecao"]
        fp = self.res["analysis"]["fingerprint"]
        if self.done("selecao") and st.get("analysis_fingerprint") == fp:
            self.clips = [clip_from_dict(d) for d in st["clips"]]
            self.say(f"✔ Seleção (já feita): {len(self.clips)} cortes")
            return
        self.stage("selecao", "a_correr")
        self.say("▶ 3/5 Seleção dos melhores momentos…")
        style = self._style()
        texts = TEXT[self._ui_lang()]
        min_len = max(5.0, self.cfg.get("duracao_min_fator", 0.7) * req.duration)
        max_len = min(180.0, self.cfg.get("duracao_max_fator", 1.3) * req.duration)
        r = self.res
        self.clips = select.select_clips(r["units"], r["moments"], r["peaks"], r["scenes"],
                                         r["analysis"]["duration_s"], req.count, req.duration, min_len, max_len,
                                         style["teaser"], texts)
        if not self.clips:
            raise UserError("Não foi possível encontrar cortes com esta duração.",
                            "Experimenta uma duração menor ou um vídeo mais longo.")
        self.stage("selecao", "concluido", clips=[clip_to_dict(c) for c in self.clips],
                   analysis_fingerprint=fp, requested=req.count, found=len(self.clips))
        if len(self.clips) < req.count:
            self.say(f"  ⚠ Pediste {req.count} cortes, mas só há {len(self.clips)} momentos distintos "
                     f"com {req.duration:.0f} s neste vídeo.")
        for c in self.clips:
            self.say(f"  • {c.id}: {fmt_secs(c.out_duration)} — {c.hook_text}")

    # ---- 4. edição + render + exportação (por corte, retomável)
    def _edit_render_export(self) -> int:
        req = self.req
        style = self._style()
        W, H = FORMATS[req.fmt]
        L = self._ui_lang()
        texts = TEXT[L]
        r = self.res
        work, export, review = self.run / "work", self.run / "export", self.run / "review"
        self.stage("edicao_render", "a_correr")
        self.say(f"▶ 4/5 Edição, legendas e renderização ({len(self.clips)} cortes)…")
        credit = req.credit or (self.prov.get("uploader") and
                                f"{self.prov.get('uploader')} — {self.prov.get('webpage_url')}")
        failed = 0
        for k, c in enumerate(self.clips, 1):
            cs = self.state["clips"].get(c.id, {})
            mp4 = export / f"{c.id}.mp4"
            if cs.get("status") == "concluido" and mp4.exists():
                self.say(f"  ✔ [{k}/{len(self.clips)}] {c.id} (já exportado)")
                continue
            ts = time.time()
            try:
                flash = [round(c.pieces[0].dur, 3)] if (style["flash"] and len(c.pieces) > 1) else []
                punches = render.emphasis_times(c, r["peaks"], r["moments"], style)
                ass = work / f"{c.id}.ass"
                cap = captions.build_ass(c, r["units"], r["moments"], style, W, H, texts, ass, flash)
                rinfo = render.render_clip(c, str(self.src), r["media"], style, W, H, ass.name, work, mp4,
                                           r["scenes"], punches, self.cfg.get("encoder", "auto"))
                ver = render.verify(mp4, W, H, c.out_duration)
                if not ver["ok"]:
                    raise RuntimeError(f"verificação falhou: {ver}")
                render.contact_sheet(mp4, review / f"{c.id}.jpg", c.out_duration)
                meta = metadata.build(c, texts, L, req.style, credit)
                record = {"id": c.id, "file": mp4.name, "style": req.style, "format": req.fmt, "language": L,
                          "source": self.prov, "source_range": [round(c.start, 3), round(c.end, 3)],
                          "pieces": [asdict(p) for p in c.pieces], "duration_s": round(c.out_duration, 3),
                          "score": c.score, "category": c.category, "selection_reasons": c.reasons,
                          "hook": c.hook_text, "transcript_excerpt": c.text, "captions": cap, "render": rinfo,
                          "verify": ver, "metadata": meta, "published": False}
                write_json(export / f"{c.id}.json", record)
                (export / f"{c.id}.txt").write_text(
                    f"TÍTULO\n{meta['title']}\n\nDESCRIÇÃO\n{meta['description']}\n\n"
                    f"HASHTAGS\n{' '.join(meta['hashtags'])}\n\nTIKTOK\n{meta['captions']['tiktok']}\n\n"
                    f"INSTAGRAM\n{meta['captions']['instagram_reels']}\n", encoding="utf-8")
                self.state["clips"][c.id] = {"status": "concluido", "seconds": round(time.time() - ts, 1),
                                             "title": meta["title"], "duration_s": round(c.out_duration, 2),
                                             "encoder": rinfo["encoder"], "size_mb": ver["size_mb"]}
                self.say(f"  ✔ [{k}/{len(self.clips)}] {c.id} — {fmt_secs(c.out_duration)} — {meta['title']}")
            except KeyboardInterrupt:
                raise
            except Exception as e:  # noqa: BLE001
                failed += 1
                self.log.error("%s falhou:\n%s", c.id, traceback.format_exc())
                self.state["clips"][c.id] = {"status": "erro", "error": f"{type(e).__name__}: {str(e)[:300]}"}
                self.state["errors"].append({"when": datetime.now().isoformat(timespec="seconds"),
                                             "clip": c.id, "error": f"{type(e).__name__}: {str(e)[:300]}"})
                self.say(f"  ✖ [{k}/{len(self.clips)}] {c.id} falhou — os outros cortes continuam "
                         f"(detalhes em logs/{self.log_path.name})")
            self.save()
        self.stage("edicao_render", "concluido" if not failed else "concluido_com_erros", failed=failed)
        return 1 if failed else 0

    def _style(self) -> dict:
        s = dict(STYLES[self.req.style])
        if not self.cfg.get("teaser", True):
            s["teaser"] = False
        return s

    def _ui_lang(self) -> str:
        return ui_lang(self.req.lang, self.res["analysis"]["language"] if self.res else None)

    # ---- 5. relatório
    def _stage_summary(self, s: str) -> str:
        d = self.state["stages"][s]
        if d["status"] == "pendente":
            return ""
        if s == "ingestao":
            return f"{Path(d.get('path', '')).name} · {fmt_secs(d.get('duration_s', 0))} · {d.get('resolution', '')}"
        if s == "analise":
            t = "transcrição reaproveitada" if d.get("cached") else f"transcrição {d.get('transcribe_s') or 0:.1f} s"
            return (f"língua {d.get('language')} · {d.get('words')} palavras · {d.get('moments')} momentos · "
                    f"{d.get('device')} · {t}")
        if s == "selecao":
            return f"{d.get('found', 0)} de {d.get('requested', 0)} cortes pedidos"
        if s == "edicao_render":
            ok = sum(1 for c in self.state["clips"].values() if c.get("status") == "concluido")
            return f"{ok} exportados · {d.get('failed', 0)} falhados"
        return ""

    def _report(self) -> None:
        st, req = self.state, self.req
        st["stages"]["relatorio"]["status"] = "concluido"

        def cell(x) -> str:
            return str(x).replace("|", "\\|").replace("\n", " ")
        ok = [cid for cid, c in st["clips"].items() if c.get("status") == "concluido"]
        status_txt = {"concluido": "✅ Concluído", "concluido_com_erros": "⚠️ Concluído com erros",
                      "interrompido": "⏸ Interrompido (retomável)", "erro": "❌ Erro",
                      "a_correr": "… a correr", "novo": "novo"}.get(st["status"], st["status"])
        lines = [f"# Relatório — {self.slug} / {run_id(req)}", "",
                 f"**Estado:** {status_txt}  ", f"**Fonte:** `{req.source}`  ",
                 f"**Pedido:** {req.count} cortes × {req.duration:.0f} s · {req.lang} · "
                 f"{STYLES.get(req.style, {}).get('label', req.style)} · {req.fmt}  ",
                 f"**Exportados:** {len(ok)} de {len(self.clips) or req.count}  ",
                 "**Publicação:** nenhuma (os ficheiros ficam para revisão e upload manual)", "",
                 "## Etapas", "", "| Etapa | Estado | Detalhes |", "|---|---|---|"]
        for s in STAGES:
            lines.append(f"| {STAGE_LABEL[s]} | {st['stages'][s]['status']} | {cell(self._stage_summary(s))} |")
        lines += ["", "## Cortes", "", "| Corte | Duração | Origem no vídeo | Título | Ficheiro | Estado |",
                  "|---|---:|---|---|---|---|"]
        for c in self.clips:
            cs = st["clips"].get(c.id, {})
            orig = " + ".join(f"{'teaser ' if p.kind == 'teaser' else ''}{fmt_secs(p.src_start)}–{fmt_secs(p.src_end)}"
                              for p in c.pieces)
            lines.append(f"| {c.id} | {fmt_secs(c.out_duration)} | {orig} | {cell(cs.get('title', c.hook_text))} | "
                         f"`export/{c.id}.mp4` | {cs.get('status', 'pendente')}"
                         f"{' — ' + cell(cs['error']) if cs.get('error') else ''} |")
        if st["errors"]:
            lines += ["", "## Erros", ""] + [f"- {e['when']} {e.get('clip', '')} {e['error']}" for e in st["errors"][-10:]]
        lines += ["", "## Execuções", ""] + [
            f"- {r['started']} → {r.get('ended', '…')} ({fmt_secs(r.get('seconds', 0))}) — log `{r['log']}`"
            for r in st["runs"]]
        if source.is_url(req.source) and self.state["stages"]["ingestao"].get("path"):
            lines.insert(4, f"**Ficheiro de origem:** `{self.state['stages']['ingestao']['path']}`  ")
        lines += ["", "## Próximos passos", "",
                  "1. Ver os vídeos em `export/` e as folhas de contacto em `review/`.",
                  "2. Copiar título, descrição e hashtags de `export/short-NN.txt`.",
                  "3. Publicar manualmente em cada plataforma."]
        if st["status"] in ("interrompido", "erro", "concluido_com_erros"):
            lines.append("4. Para retomar ou repetir os cortes que falharam, corre o mesmo pedido outra vez.")
        (self.run / "report.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
        self.save()
        update_index(self.proj.parent)


def update_index(out_root: Path) -> None:
    rows = []
    for stp in sorted(out_root.glob("*/*/state.json")):
        try:
            st = json.loads(stp.read_text(encoding="utf-8"))
        except Exception:  # noqa: BLE001
            continue
        n_ok = sum(1 for c in st.get("clips", {}).values() if c.get("status") == "concluido")
        last = (st.get("runs") or [{}])[-1].get("started", "")
        rel = stp.parent.relative_to(out_root).as_posix()
        rows.append(f"| [{rel}]({rel}/report.md) | {st.get('status')} | {n_ok} | {last} |")
    txt = ("# GTA6-SHORTS — projetos\n\n| Projeto / execução | Estado | Shorts exportados | Última execução |\n"
           "|---|---|---:|---|\n" + "\n".join(rows) + "\n")
    (out_root / "INDEX.md").write_text(txt, encoding="utf-8")
