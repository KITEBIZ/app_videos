#!/usr/bin/env python3
"""Narração do vídeo do Método VTA com a voz replicada do Alexandre no Gemini TTS. v2 (29/09/2026).
Guia da voz: /caminho/local/Projetos/voice/COMO-USAR-VOZ-GEMINI.md.

O que mudou da v1 (a v1 levou mais de 10 min e deixou passar um erro):
  - frases geradas e conferidas em PARALELO (4 de cada vez), não em fila;
  - conferência palavra por palavra (src/conferir_voz.py, calibrada em testes/): Whisper small primeiro, large só
    para confirmar reprovação; números e marcas normalizados, então "12" e "Kitbis" não reprovam mais à toa;
  - cada frase aprovada fica guardada em narracao/frases-voz/ junto com o texto; rodar de novo só refaz o que
    mudou ou reprovou. --refazer 5 7 força frases.
Depois emenda com respiro de 0,35 s e entrega ao narrar.py do modelo da Deliver IT (nível, alinhamento, JSON).
Rodar: python3 src/voz_alexandre.py [--refazer 5 ...]"""
import argparse, base64, json, os, subprocess, sys, tempfile, time, urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(Path(__file__).resolve().parent))   # 08/10/2026: dependências copiadas para ferramentas/voz
import metodo              # ROTEIRO e SLUG
import narrar as n         # nível, alinhamento e JSON
import conferir_voz as cv

VOZ = "voice_2nzcocppuzhc"
MODELO = "gemini-3.8-flash-tts"
ESTILO = "narração natural, no tom da voz de referência, sem exagero"
PAUSA, TENTATIVAS, PARALELO = 0.35, 3, 4
# pronúncia: o TTS lê ao pé da letra. Alexandre, 29/09: "a pronuncia da kitebiz esta errada. é kaitibiz."
# Só o texto que vai para a voz muda; tela, roteiro e alinhamento continuam com KITEBIZ.
# "Kaitbiz" aprovado de ouvido na frase 6 (versão C, 29/09: "C eta bom"); com "Kaitibiz" uma variação saiu "keiteweb".
PRONUNCIA = {"KITEBIZ": "Kaitbiz", "kitebiz": "kaitbiz"}
CACHE = ROOT / "narracao" / "frases-voz"


def tts(texto, estilo=None):
    """estilo (22/10/2026, idioma-do-video): a instrução de estilo; sem ela, ESTILO (a de sempre, em português)."""
    corpo = {"model": MODELO,
             "input": [{"type": "user_input", "content": [{"type": "text", "text": texto,
                        "annotations": [{"type": "speech_metadata", "style": estilo or ESTILO}]}]}],
             "response_format": {"type": "audio"}, "generation_config": {"speech_config": [{"voice": VOZ}]}}
    req = urllib.request.Request("https://generativelanguage.googleapis.com/v1beta/interactions", data=json.dumps(corpo).encode(),
                                 headers={"x-goog-api-key": os.environ["GEMINI_API_KEY"], "Content-Type": "application/json"})
    d = json.load(urllib.request.urlopen(req, timeout=300))
    for s in d.get("steps", []):
        for c in s.get("content", []):
            if c.get("data"):
                return base64.b64decode(c["data"])
    raise RuntimeError("sem áudio: " + json.dumps(d)[:300])


def falado(texto):
    for a, b in PRONUNCIA.items():
        texto = texto.replace(a, b)
    return texto


def limpar(bruto, saida):
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(bruto), "-af",
                    "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.03,areverse,"
                    "silenceremove=start_periods=1:start_threshold=-45dB:start_silence=0.05,areverse,"
                    "loudnorm=I=-20:TP=-3", "-ar", "24000", "-ac", "1", str(saida)], check=True)


def frase(i, texto, refazer):
    wav, meta = CACHE / f"f{i:02d}.wav", CACHE / f"f{i:02d}.json"
    if wav.exists() and meta.exists() and not refazer:
        m = json.loads(meta.read_text())
        if m.get("texto") == texto and m.get("ok"):
            return {"i": i, "ok": True, "tentativas": 0, "nota": "guardada", "ouvido": m.get("ouvido", "")}
        if m.get("texto") == texto and "diferencas" not in m:     # gravação herdada, nunca conferida pela v2
            ok, ds, ouvido, modelo = cv.conferir(wav, texto)
            meta.write_text(json.dumps({**m, "ok": ok, "ouvido": ouvido, "diferencas": ds, "modelo": modelo},
                                       ensure_ascii=False, indent=1))
            if ok:
                return {"i": i, "ok": True, "tentativas": 0, "nota": f"herdada, conferida ({modelo})", "ouvido": ouvido}
    for t in range(1, TENTATIVAS + 1):
        with tempfile.TemporaryDirectory() as d:
            bruto = Path(d) / "b.wav"; bruto.write_bytes(tts(falado(texto))); limpar(bruto, wav)
        ok, ds, ouvido, modelo = cv.conferir(wav, texto)
        meta.write_text(json.dumps({"texto": texto, "ok": ok, "ouvido": ouvido, "diferencas": ds, "modelo": modelo,
                                    "quando": time.strftime("%Y-%m-%d %H:%M")}, ensure_ascii=False, indent=1))
        if ok:
            return {"i": i, "ok": True, "tentativas": t, "nota": modelo, "ouvido": ouvido}
    return {"i": i, "ok": False, "tentativas": TENTATIVAS, "nota": "; ".join(ds), "ouvido": ouvido}


def main():
    ap = argparse.ArgumentParser(); ap.add_argument("--refazer", nargs="*", type=int, default=[])
    a = ap.parse_args()
    CACHE.mkdir(parents=True, exist_ok=True); t0 = time.time()
    with ThreadPoolExecutor(PARALELO) as ex:
        res = list(ex.map(lambda p: frase(p[0], p[1], p[0] in a.refazer), enumerate(metodo.ROTEIRO, 1)))
    for r in res:
        print(f"  {r['i']:2d}  {'ok ' if r['ok'] else 'RUIM'}  tentativas {r['tentativas']}  {r['nota']}")
    ruins = [r["i"] for r in res if not r["ok"]]
    if ruins:
        sys.exit(f"frases que não passaram na conferência: {ruins}. Nada foi emendado.")
    with tempfile.TemporaryDirectory() as d:
        pausa = Path(d) / "pausa.wav"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t", str(PAUSA), str(pausa)], check=True)
        partes = []
        for i in range(1, len(metodo.ROTEIRO) + 1):
            partes += [CACHE / f"f{i:02d}.wav", pausa]
        lista = Path(d) / "lista.txt"; lista.write_text("".join(f"file '{p}'\n" for p in partes[:-1]))
        junto = Path(d) / "junto.wav"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lista), "-c", "copy", str(junto)], check=True)
        n.ROOT = ROOT; n.ROTEIROS = {metodo.SLUG: metodo.ROTEIRO}; n.VOZ = f"{VOZ}, voz replicada do Alexandre,"
        dados = junto.read_bytes(); n.gemini_tts = lambda _t: dados
        n.narrar(metodo.SLUG)
    print(f"\npronto em {time.time() - t0:.0f} s")


if __name__ == "__main__":
    main()
