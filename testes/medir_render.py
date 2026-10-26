"""Mede o vídeo final por etapa (20/10/2026, ele: "agora vamos para a ideia 4, medir o render"), sem tocar em vídeo de
verdade: gera o final de uma referência congelada do tela_igual (testes/referencias/<n>/publicacao/final.mp4), pelo
servidor de teste (porta 4491).

  .venv/bin/python testes/medir_render.py 304
"""
import sys, time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ)); sys.path.insert(0, str(RAIZ / "testes"))
import tela_igual as TI
import estudio as E

TI.servidor()                                   # E.VIDEOS passa a ser testes/referencias
import render as R
R.URL = f"http://127.0.0.1:{TI.PORTA}/item/{{n}}/previa.html?render=1"

marcas = {}


def cronometra(nome, f):
    def g(*a, **k):
        t = time.time()
        try:
            return f(*a, **k)
        finally:
            marcas[nome] = marcas.get(nome, 0) + time.time() - t
    return g


# dentro dos quadros: quanto é desenhar/esperar os trechos e quanto é fotografar e mandar ao ffmpeg
from playwright.sync_api import Page
Page.evaluate = cronometra("desenhar e esperar os trechos", Page.evaluate)
Page.screenshot = cronometra("fotografar e mandar ao ffmpeg", Page.screenshot)
R.quadros = cronometra("quadros (tudo)", R.quadros)
R.mixar = cronometra("mixar o som", R.mixar)
R.conferir = cronometra("conferir o final", R.conferir)

num = int(sys.argv[1]) if len(sys.argv) > 1 else 304
t0 = time.time()
conf = R.fazer(num)
total = time.time() - t0
print(f"#{num}: vídeo de {conf['duracao']} s, {round(conf['duracao'] * R.QPS)} quadros, {conf['mb']} MB · total {total:.0f} s")
for k in ("quadros (tudo)", "desenhar e esperar os trechos", "fotografar e mandar ao ffmpeg", "mixar o som", "conferir o final"):
    print(f"  {k:32s} {marcas.get(k, 0):6.1f} s")
print(f"  {'resto (fechar o vídeo, juntar o som)':32s} {total - marcas['quadros (tudo)'] - marcas['mixar o som'] - marcas['conferir o final']:6.1f} s")
