#!/usr/bin/env python3
"""Transcrição de fala de terceiros, palavra por palavra, pela Groq (Whisper large-v3), com as bordas acertadas pelo
silêncio (08/10/2026). Alexandre: "isso não podemos colocar na nuvem da groq?" e "pode fazer".

Medido em 08/10 com o reel do Pimenta (115 s de fala): Groq 4,4 s contra ~11 min do whisper-cli local; os dois marcam
o começo de palavra que vem depois de pausa ainda dentro do silêncio (até 1,6 s antes: "mas" em 92,40, real 93,97).
Por isso `borda()` empurra o início para o fim do silêncio e o fim para o começo do próximo.

  from transcrever import palavras, borda
  ws = palavras("audio.m4a")                 # [[ini, fim, palavra], ...] em segundos do arquivo
  a, b = borda("audio.m4a", 92.40, 98.95, a_fim=94.32)   # corte acertado pelo silêncio (a_fim = fim da 1ª palavra)

Chave: GROQ_API_KEY no ambiente (Mac e /etc/kitebiz/newsbr360.env na VPS)."""
import json, os, re, subprocess, tempfile, time, urllib.request, uuid
from pathlib import Path

URL = "https://api.groq.com/openai/v1/audio/transcriptions"


def idioma_ouvido(audio):
    """O idioma que o Whisper ouve, sem dizer qual é ('spanish', 'portuguese', ...). 22/10/2026 (idioma-do-video): a voz
    do #334 lia espanhol com pronúncia de português e a conferência, ouvindo em espanhol, passava."""
    with tempfile.TemporaryDirectory() as d:
        mp3 = Path(d) / "a.mp3"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(audio), "-ac", "1", "-ar", "16000", "-b:a", "64k", str(mp3)], check=True)
        lim = "----" + uuid.uuid4().hex
        campos = {"model": "whisper-large-v3", "response_format": "verbose_json"}
        corpo = b"".join(f'--{lim}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode() for k, v in campos.items())
        corpo += (f'--{lim}\r\nContent-Disposition: form-data; name="file"; filename="a.mp3"\r\nContent-Type: audio/mpeg\r\n\r\n'.encode()
                  + mp3.read_bytes() + f"\r\n--{lim}--\r\n".encode())
        req = urllib.request.Request(URL, data=corpo, method="POST", headers={
            "Authorization": f"Bearer {os.environ['GROQ_API_KEY']}", "Content-Type": f"multipart/form-data; boundary={lim}",
            "User-Agent": "kitebiz-conteudo/1"})
        return (json.load(urllib.request.urlopen(req, timeout=120)).get("language") or "").lower()


MODELO_DITADO = "whisper-large-v3-turbo"


def ditado(audio_bytes, idioma="pt"):
    """O texto do ditado do chat (24/10/2026, "pode ir consertar a parte do chat que envia o audio"). Como o chat do
    kiteprocess: modelo turbo, sem o tempo de cada palavra, e erro vira RuntimeError (não SystemExit, que derrubava a
    conexão da tela sem resposta). Aceita o áudio parcial que a tela manda durante a fala (webm ou mp4 do começo até agora)."""
    with tempfile.TemporaryDirectory() as d:
        bruto, mp3 = Path(d) / "a.bin", Path(d) / "a.mp3"
        bruto.write_bytes(audio_bytes)
        r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(bruto), "-ac", "1", "-ar", "16000", "-b:a", "64k", str(mp3)],
                           capture_output=True, text=True)
        if r.returncode or not mp3.exists() or mp3.stat().st_size == 0:
            raise RuntimeError("o áudio não abriu: " + (r.stderr.strip().splitlines() or ["vazio"])[-1][:160])
        lim = "----" + uuid.uuid4().hex
        campos = {"model": MODELO_DITADO, "language": idioma, "response_format": "json"}
        corpo = b"".join(f'--{lim}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode() for k, v in campos.items())
        corpo += (f'--{lim}\r\nContent-Disposition: form-data; name="file"; filename="a.mp3"\r\nContent-Type: audio/mpeg\r\n\r\n'.encode()
                  + mp3.read_bytes() + f"\r\n--{lim}--\r\n".encode())
        req = urllib.request.Request(URL, data=corpo, method="POST", headers={
            "Authorization": f"Bearer {os.environ['GROQ_API_KEY']}", "Content-Type": f"multipart/form-data; boundary={lim}",
            "User-Agent": "kitebiz-conteudo/1"})
        try:
            return (json.load(urllib.request.urlopen(req, timeout=60)).get("text") or "").strip()
        except urllib.error.HTTPError as e:
            raise RuntimeError(f"a Groq respondeu {e.code}: {e.read().decode()[:200]}")
        except (urllib.error.URLError, TimeoutError) as e:
            raise RuntimeError(f"sem resposta da Groq: {e}")


def palavras(audio, idioma="pt", inicio=0.0, fim=None):
    """Transcreve (opcionalmente só de `inicio` a `fim`) e devolve [[ini, fim, palavra]] no tempo do arquivo original."""
    with tempfile.TemporaryDirectory() as d:
        mp3 = Path(d) / "a.mp3"
        corte = ["-ss", f"{inicio:.3f}"] + (["-to", f"{fim:.3f}"] if fim else [])
        subprocess.run(["ffmpeg", "-v", "error", "-y", *corte, "-i", str(audio), "-ac", "1", "-ar", "16000", "-b:a", "64k", str(mp3)],
                       check=True)
        lim = "----" + uuid.uuid4().hex
        campos = {"model": "whisper-large-v3", "language": idioma, "response_format": "verbose_json",
                  "timestamp_granularities[]": "word"}
        corpo = b"".join(f'--{lim}\r\nContent-Disposition: form-data; name="{k}"\r\n\r\n{v}\r\n'.encode() for k, v in campos.items())
        corpo += (f'--{lim}\r\nContent-Disposition: form-data; name="file"; filename="a.mp3"\r\nContent-Type: audio/mpeg\r\n\r\n'.encode()
                  + mp3.read_bytes() + f"\r\n--{lim}--\r\n".encode())
        req = urllib.request.Request(URL, data=corpo, method="POST", headers={
            "Authorization": f"Bearer {os.environ['GROQ_API_KEY']}", "Content-Type": f"multipart/form-data; boundary={lim}",
            "User-Agent": "kitebiz-conteudo/1"})
        for tentativa in range(3):
            try:
                d = json.load(urllib.request.urlopen(req, timeout=180)); break
            except urllib.error.HTTPError as e:
                if e.code != 429 or tentativa == 2:
                    raise SystemExit(f"Groq respondeu {e.code}: {e.read().decode()[:300]}")
                time.sleep(10)
    return [[round(w["start"] + inicio, 2), round(w["end"] + inicio, 2), w["word"].strip()] for w in d.get("words", [])], d.get("text", "")


def silencios(audio, a, b, db=-32, minimo=0.12):
    """[(ini, fim)] dos silêncios entre a e b (segundos do arquivo)."""
    saida = subprocess.run(["ffmpeg", "-v", "info", "-ss", f"{a:.3f}", "-to", f"{b:.3f}", "-i", str(audio),
                            "-af", f"silencedetect=n={db}dB:d={minimo}", "-f", "null", "-"], capture_output=True, text=True).stderr
    ini = [float(x) + a for x in re.findall(r"silence_start: ([\d.]+)", saida)]
    fim = [float(x) + a for x in re.findall(r"silence_end: ([\d.]+)", saida)]
    return list(zip(ini, fim + [b] * (len(ini) - len(fim))))


def borda(audio, a, b, a_fim=None, b_ini=None, folga=0.08):
    """Acerta um corte [a, b] de palavras da Groq. O erro medido (08/10) é a palavra depois de pausa "engolir" o
    silêncio: "mas" marcado 92,40-94,32 com silêncio 92,94-93,97 dentro, fala real em 93,97. Então: se há silêncio
    dentro da primeira palavra (a .. a_fim), o corte começa no fim do último deles; se há silêncio dentro da última
    (b_ini .. b), termina no começo do primeiro. Silêncio onde o corte já começa/termina também conta."""
    s = silencios(audio, max(0, a - 1), b + 1)
    dentro_ini = [y for x, y in s if a - .02 <= y <= (a_fim if a_fim else a + .4) and x < (a_fim or a + .4)]
    if dentro_ini:
        a = max(dentro_ini) - folga
    dentro_fim = [x for x, y in s if (b_ini if b_ini else b - .4) <= x <= b + .02 and y > (b_ini or b - .4)]
    if dentro_fim:
        b = min(dentro_fim) + folga
    return round(a, 2), round(b, 2)


def texto_com_tempo(ws, pausa=0.6):
    """Frases quebradas nas pausas, com mm:ss, para ler e citar ("0:19 Mais de 50 milhões ...")."""
    linhas, atual, t0, ult = [], [], None, None
    for a, b, p in ws:
        if atual and (a - ult > pausa or atual[-1][-1:] in ".?!"):
            linhas.append(f"{int(t0 // 60)}:{int(t0 % 60):02d}  {' '.join(atual)}"); atual = []
        if not atual:
            t0 = a
        atual.append(p); ult = b
    if atual:
        linhas.append(f"{int(t0 // 60)}:{int(t0 % 60):02d}  {' '.join(atual)}")
    return "\n".join(linhas)
