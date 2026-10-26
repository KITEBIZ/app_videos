"""Simulador do Reels no celular (18/10/2026; ele: "vc consegue simular a tela do iphone ou mobile para ver os erros? e
ajustar a area segura?").

  python3 celular.py <número> <segundo> [<segundo> ...]     → animacao/celular/tNNN.png (como fica no iPhone dele)

Calibrado no print dele (Downloads/IMG_9052.PNG, iPhone, 924 x 2000, reel em colaboração, 18/10 12:04): o vídeo ocupa
a tela do topo até a barra de progresso (y 1800), escala 0,9375; a largura vira 1012 e o celular corta ~44 px de cada
lado. Por cima, o que o Instagram desenha, nas posições medidas no print. Tudo em px da TELA; ZONA_VIDEO converte para o
vídeo (1080 x 1920), que é o que o animador usa.
"""
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

TELA = (924, 2000)
ESCALA = 1800 / 1920                       # 0,9375
CORTE = (1080 * ESCALA - TELA[0]) / 2      # ~44 px de cada lado
# o que o app desenha (px da tela, medido no print): (x0, y0, x1, y1)
APP = {
    # medido pixel a pixel no print (18/10/2026): barra de cima até y 211; borda dos ícones x 817-825; avatar ~1526,
    # texto do nome 1554 (a 1ª versão, no olho, pôs os ícones em 790 e errava)
    "topo": (0, 0, 924, 211),              # hora, "Reels · Amigos"
    "icones": (817, 990, 924, 1760),       # curtir, comentar, repostar, enviar, salvar, menu
    "nome": (30, 1526, 817, 1610),         # avatar(es) + "newsbr360 e alexandremota.digital" (+ "Seguir" de quem não segue)
    "legenda_post": (30, 1625, 790, 1700),
    "curtido": (30, 1705, 790, 1770),
    "comentario": (0, 1810, 924, 2000),    # barra "Faça um comentário..." (fora do vídeo)
}


def tela_para_video(x, y):
    return (x + CORTE) / ESCALA, y / ESCALA


def zona_video(margem=16):
    """A área do vídeo (1080 x 1920) que aparece livre no celular: entre o topo e o nome, sem os ícones à direita,
    dentro do corte lateral. Devolve {x0, x1, y0, y1, icones_x, icones_y0}."""
    x0, _ = tela_para_video(margem, 0)
    x1, _ = tela_para_video(TELA[0] - margem, 0)
    _, y0 = tela_para_video(0, APP["topo"][3])
    _, y1 = tela_para_video(0, APP["nome"][1] - margem)
    ix, iy = tela_para_video(APP["icones"][0] - margem, APP["icones"][1])
    return {"x0": round(x0), "x1": round(x1), "y0": round(y0), "y1": round(y1), "icones_x": round(ix), "icones_y0": round(iy)}


def simular(quadro, saida, zona=True):
    """quadro: PNG/JPG 1080x1920 do vídeo → saida: a tela do celular com o app por cima (e a zona livre tracejada)."""
    v = Image.open(quadro).convert("RGB").resize((round(1080 * ESCALA), 1800))
    t = Image.new("RGB", TELA, (8, 8, 12))
    t.paste(v, (-round(CORTE), 0))
    d = ImageDraw.Draw(t, "RGBA")
    try:
        f = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 34)
        fp = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", 28)
    except Exception:
        f = fp = None
    d.text((205, 160), "Reels   Amigos", fill="white", font=f)
    for k in range(6):
        cy = 1025 + k * 125
        d.ellipse((815, cy, 880, cy + 65), outline="white", width=5)
    d.ellipse((40, 1525, 105, 1590), fill=(160, 180, 220), outline="white", width=3)
    d.text((125, 1540), "newsbr360 e alexandremota.digital", fill="white", font=f)
    d.text((40, 1640), "A única mina de terras raras do Brasil foi ...", fill="white", font=fp)
    d.text((40, 1720), "Curtido por ... e outras pessoas", fill=(220, 220, 220), font=fp)
    d.rectangle((0, 1800, 924, 1806), fill=(200, 200, 200))
    d.rounded_rectangle((40, 1830, 884, 1945), radius=50, fill=(30, 30, 36))
    d.text((90, 1870), "Faça um comentário...", fill=(200, 200, 200), font=f)
    if zona:
        z = APP
        x0, y0, x1, y1 = 16, z["topo"][3], TELA[0] - 16, z["nome"][1] - 16
        for (a, b) in (((x0, y0), (x1, y0)), ((x0, y1), (x1, y1)), ((x0, y0), (x0, y1)), ((x1, y0), (x1, z["icones"][1]))):
            d.line((a, b), fill=(255, 77, 94, 200), width=3)
        d.line((z["icones"][0] - 16, z["icones"][1], z["icones"][0] - 16, y1), fill=(255, 77, 94, 200), width=3)
        d.line((z["icones"][0] - 16, z["icones"][1], x1, z["icones"][1]), fill=(255, 77, 94, 200), width=3)
    Path(saida).parent.mkdir(parents=True, exist_ok=True)
    t.save(saida)
    return saida


if __name__ == "__main__":
    sys.path[:0] = [str(Path(__file__).resolve().parent.parent), str(Path(__file__).resolve().parent)]
    import estudio as E, ver
    num = int(sys.argv[1])
    d = E.pasta(num) / "animacao/celular"
    feitos, erros = ver.quadros(num, [float(x) for x in sys.argv[2:]], saida=d / "video")
    for q in feitos:
        print(simular(q, d / q.name))
    print("zona livre no vídeo (1080x1920):", zona_video())
