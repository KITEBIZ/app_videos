"""capa-viva (21/10/2026): o vídeo de baixo anda antes de 1,7 s; o quadro 0 é a capa; nenhum corte de cena da edição
original por baixo da capa (no #316 a reportagem cortava para uma cerimônia). Roda numa cópia do estúdio (/tmp/ca/viva/estudio) com uma cópia do #316, sem vigias.
  python3 teste_viva.py medir <mp4>      só mede um vídeo (a calibração: a prévia de hoje tem que FALHAR)
  python3 teste_viva.py                  faz as capas na cópia (agente de capa, ~US$ 0,10), escolhe e mede os dois casos"""
import json, os, shutil, subprocess, sys, threading, time
from pathlib import Path
import numpy as np
from PIL import Image

LIMITE, MEXE = 1.7, 1.5        # o vídeo tem que andar até 1,7 s; "andando" = diferença média entre quadros acima de 1,5


def movimento(mp4, ate=4.0):
    """[(t, diferença média do quadro para o anterior)] em 30 q/s, em tons de cinza 180x320."""
    raw = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-t", str(ate), "-i", str(mp4), "-vf", "scale=180:320,format=gray",
                          "-f", "rawvideo", "-"], capture_output=True).stdout
    q = np.frombuffer(raw, np.uint8).reshape(-1, 320, 180).astype(np.int16)
    return [(i / 30, float(np.abs(q[i] - q[i - 1]).mean())) for i in range(1, len(q))]


def primeiro_movimento(mp4):
    """O primeiro segundo a partir do qual o vídeo anda em pelo menos 5 de 10 quadros seguidos (zoom lento não conta)."""
    m = movimento(mp4)
    for i in range(len(m) - 10):
        if sum(d > MEXE for _, d in m[i:i + 10]) >= 5:
            return round(m[i][0], 2)
    return None


def cortes(mp4, ate):
    """Os segundos com mudança de cena acima de 0,3 entre 0 e `ate` (os mesmos números do capa_agente._no_plano)."""
    import re
    out = subprocess.run(["ffmpeg", "-nostdin", "-v", "info", "-t", f"{ate:.2f}", "-i", str(mp4), "-an", "-vf",
                          "scale=320:-2,select='gt(scene,0.3)',showinfo", "-f", "null", "-"], capture_output=True, text=True).stderr
    return [round(float(x), 2) for x in re.findall(r"pts_time:([0-9.]+)", out)]


def parecido(mp4, jpg):
    """Diferença média (0-255) entre o quadro 0 do vídeo e a capa, ambos 180x320."""
    raw = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-i", str(mp4), "-frames:v", "1", "-vf", "scale=180:320,format=gray",
                          "-f", "rawvideo", "-"], capture_output=True).stdout
    a = np.frombuffer(raw, np.uint8).reshape(320, 180).astype(np.int16)
    b = np.asarray(Image.open(jpg).convert("L").resize((180, 320))).astype(np.int16)
    return float(np.abs(a - b).mean())


if sys.argv[1:2] == ["medir"]:
    t = primeiro_movimento(sys.argv[2])
    print(f"{'PASSOU' if t is not None and t <= LIMITE else 'FALHOU'} · o vídeo anda a partir de {t} s (limite {LIMITE} s): {sys.argv[2]}")
    sys.exit()

C = Path("/tmp/ca/viva/estudio"); sys.path[:0] = [str(C), str(C / "ferramentas"), str(C / "testes")]
os.chdir(C)
import estudio as E
assert str(E.RAIZ) == str(C), E.RAIZ
E.VIDEOS = C / "videos"
PORTA = 4492
argv, sys.argv = sys.argv, [sys.argv[0], str(PORTA)]
import servidor as S
sys.argv = argv
from http.server import ThreadingHTTPServer
S.H.log_message = lambda *a: None
srv = ThreadingHTTPServer(("127.0.0.1", PORTA), S.H); threading.Thread(target=srv.serve_forever, daemon=True).start()
import ver, capa, render, capa_agente
ver.URL = f"http://127.0.0.1:{PORTA}/item/{{n}}/previa.html?cru=1"; capa.PORTA = PORTA
render.URL = f"http://127.0.0.1:{PORTA}/item/{{n}}/previa.html?render=1"
a = E.pasta(316) / "animacao"
print(capa_agente.fazer(316))
print("fundos:", [o.get("fundo") for o in json.loads((a / "capas.json").read_text())])
capa.escolher(316, 1)
ok = []
import re
ate = float(re.search(r"T\.capa\(([0-9.]+)\)", (a / "cena.html").read_text()).group(1))
f = json.load(open(a / "capa-fundo.json"))[0]
# 1. o trecho não atravessa corte da edição original (o detector achou o corte conhecido de 45,1 s no #316)
out = subprocess.run(["ffmpeg", "-nostdin", "-v", "info", "-ss", str(f["seg"]), "-t", str(f["dur"]), "-i", str(E.pasta(316) / f["src"]), "-an",
                      "-vf", "scale=320:-2,select='gt(scene,0.3)',showinfo", "-f", "null", "-"], capture_output=True, text=True).stderr
cs = [round(f["seg"] + float(x), 2) for x in re.findall(r"pts_time:([0-9.]+)", out)]
ok.append((f"o trecho {f['seg']}-{f['seg'] + f['dur']:.2f} s (foto em {f['foto_seg']}) não tem corte da edição: {cs}", not cs))
# 2. na página do vídeo final, o trecho por baixo anda com o tempo desde 0
from playwright.sync_api import sync_playwright
with sync_playwright() as pw:
    nav = pw.chromium.launch(); pg = nav.new_page(viewport={"width": 1080, "height": 1920})
    pg.goto(render.URL.format(n=316)); pg.wait_for_function("!!window.__previa", timeout=60000, polling=200)
    vistos = []
    for t in (0.0, 0.8, 1.6):
        pg.evaluate(render.QUADRO_JS, t)              # o mesmo passo do vídeo final: põe o quadro t e espera os trechos
        vistos.append(pg.evaluate("(() => { const v = document.querySelector('video.capa-trecho'); return v ? +v.currentTime.toFixed(2) : null; })()"))
    nav.close()
esperado = [round(f["seg"] + min(t, f["dur"]), 2) for t in (0.0, 0.8, 1.6)]
ok.append((f"o trecho por baixo anda: tempo do vídeo {vistos}, esperado {esperado}",
           all(v is not None and abs(v - e) < .15 for v, e in zip(vistos, esperado))))
# 3. o quadro 0 do vídeo é a capa (calibrado: 3,7 quando o trecho começava no quadro da foto)
t0 = time.time(); render.previa_video(316)
mp4 = max(a.glob("previa-*.mp4"), key=lambda x: x.stat().st_mtime); shutil.copy(mp4, "/tmp/ca/viva/viva.mp4")
d0 = parecido(mp4, a / "capa.jpg")
ok.append((f"o quadro 0 é a capa (diferença {d0:.1f} de 255; até 12 conta como igual) · prévia em {time.time() - t0:.0f} s", d0 <= 12))
for txt, b in ok:
    print("PASSOU" if b else "FALHOU", "·", txt)
