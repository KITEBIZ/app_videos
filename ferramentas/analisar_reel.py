#!/usr/bin/env python3
"""Primeiro passo para analisar um vídeo de referência (08/10/2026). Alexandre: "quando eu mandar um vídeo para analisar,
primeiro escuta o áudio para pegar a transcrição sem baixar o vídeo ainda [...] se for o caso baixamos para pegar os
exemplos. vai ter vídeo que não vamos precisar baixar".

  python3 ferramentas/analisar_reel.py LINK            só o áudio + transcrição (medido no reel do Pimenta: 1 MB em 3 s,
                                                       contra 30 MB do vídeo; transcrição na Groq em 4 s)
  python3 ferramentas/analisar_reel.py LINK --video    baixa também o vídeo (para a bolinha e os quadros), depois de validar

Sai em referencias/<código>/: audio.m4a, palavras.json ([[ini, fim, palavra]]), transcricao.txt (frases com mm:ss),
meta.json (quem postou, data, duração, link). Reel público do Instagram baixa sem login (yt-dlp atualizado)."""
import argparse, datetime, json, re, shutil, subprocess, sys, time
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI))
from transcrever import palavras, texto_com_tempo

RAIZ = AQUI.parent / "referencias"


def ytdlp():
    for c in (shutil.which("yt-dlp"), str(Path.home() / ".local/bin/yt-dlp")):
        if c and Path(c).exists():
            return c
    sys.exit("yt-dlp não encontrado (instalar o binário oficial em ~/.local/bin)")


def yt(cmd, quem="v2", **kw):
    """20/10/2026 ("aprovo o plano v2-baixa-pela-casa"): todo yt-dlp do v2 passa por aqui, saindo pela casa (o Pi), pela
    IPRoyal ou direto (ferramentas/saida_casa.py). Mesmos argumentos de subprocess.run."""
    import saida_casa
    return saida_casa.yt(cmd, quem=quem, **kw)


def codigo(link):
    m = re.search(r"/(?:reels?|p|shorts)/([\w-]+)", link) or re.search(r"[?&]v=([\w-]+)", link)
    return m.group(1) if m else re.sub(r"\W+", "-", link)[-24:]


def extrai_quadros(video, pasta_imagens, dur, n=6):
    """n quadros espalhados pelo vídeo em <pasta>/imagens/quadroK.jpg. Devolve quantos saíram."""
    pasta_imagens.mkdir(parents=True, exist_ok=True)
    if not dur:                                   # sem duração, os 6 quadros saíam todos no segundo 0
        try:
            dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(video)]))
        except (subprocess.CalledProcessError, ValueError):
            return 0
    feitos = 0
    for k in range(n):
        arq = pasta_imagens / f"quadro{k + 1}.jpg"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{(dur or 0) * (k + .5) / n:.2f}", "-i", str(video), "-frames:v", "1",
                        "-vf", "scale=540:-2", str(arq)], capture_output=True, timeout=120)
        feitos += arq.exists()
    return feitos


def quadros(link, pasta, dur):
    """15/10/2026 ("aprova o plano quem-fala"): 6 quadros para a análise ver QUEM FALA (no #119 a conta era da Renata
    Simoso e quem falava era o Eduardo Oinegue, que só a tela mostrava: estúdio da BandNews FM). Baixa a versão leve do
    vídeo (até 480p), tira os quadros e apaga o vídeo: a regra de não baixar o vídeo antes de decidir continua."""
    for velho in pasta.glob("quadros-tmp.*"):
        velho.unlink()
    try:
        r = yt([ytdlp(), "-q", "--no-warnings", "-f", "bv*[height<=480]/wv*/b[height<=480]/w", "-o",
                str(pasta / "quadros-tmp.%(ext)s"), link], quem="reel (quadros)", capture_output=True, text=True, timeout=300)
        erro = "" if r.returncode == 0 else (r.stderr or "").strip()[-160:]
    except subprocess.TimeoutExpired:
        erro = "o download do vídeo leve passou de 5 min"
    video = next((p for p in pasta.glob("quadros-tmp.*") if p.suffix not in (".part", ".json")), None)
    if erro or not video:
        print(f"sem quadros (a análise segue só com o áudio): {erro}", file=sys.stderr)
        for velho in pasta.glob("quadros-tmp.*"):
            velho.unlink()
        return 0
    n = extrai_quadros(video, pasta / "imagens", dur)
    video.unlink()
    return n


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("link"); ap.add_argument("--video", action="store_true")
    a = ap.parse_args()
    pasta = RAIZ / codigo(a.link); pasta.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    audio = pasta / "audio.m4a"
    if not audio.exists():   # uma chamada só (áudio + ficha); o -J separado e o -x custavam 50 s no Mac
        yt([ytdlp(), "-q", "--no-warnings", "-f", "ba[ext=m4a]/ba/b", "--write-info-json", "-o", str(pasta / "audio.%(ext)s"), a.link],
           quem="reel (áudio)", check=True)
        baixado = next(p for p in pasta.glob("audio.*") if p.suffix not in (".json",))
        if baixado != audio:
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(baixado), "-vn", "-c:a", "aac", str(audio)], check=True); baixado.unlink()
    info = json.loads((pasta / "audio.info.json").read_text())
    t_baixa = time.time() - t0
    ws, txt = palavras(audio)
    (pasta / "palavras.json").write_text(json.dumps(ws, ensure_ascii=False))
    (pasta / "transcricao.txt").write_text(texto_com_tempo(ws) + "\n")
    ts = info.get("timestamp")
    meta = {"link": a.link, "quem": info.get("uploader") or info.get("channel"), "conta": info.get("channel") or info.get("uploader_id"),
            "postado": datetime.datetime.fromtimestamp(ts, datetime.timezone(datetime.timedelta(hours=-3))).isoformat() if ts else info.get("upload_date"),
            "duracao": info.get("duration") or round(float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries",
                        "format=duration", "-of", "csv=p=0", str(audio)])), 1), "legenda": (info.get("description") or "")[:2000]}
    (pasta / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1))
    n_quadros = quadros(a.link, pasta, meta["duracao"])
    if a.video and not (pasta / "original.mp4").exists():
        yt([ytdlp(), "-q", "--no-warnings", "-f", "bv*+ba/b", "--merge-output-format", "mp4", "-o", str(pasta / "original.%(ext)s"), a.link],
           quem="reel (vídeo)", check=True)
    print(f"{pasta.relative_to(AQUI.parent)} · {meta['quem']} · postado {meta['postado']} · {meta['duracao']} s · "
          f"áudio em {t_baixa:.1f} s · {n_quadros} quadros · total {time.time() - t0:.1f} s" + (" · vídeo baixado" if a.video else ""))
    print((pasta / "transcricao.txt").read_text())


if __name__ == "__main__":
    main()
