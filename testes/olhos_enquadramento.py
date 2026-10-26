"""Tipo A (sem IA, sem rede, sem servidor): os Olhos olham o enquadramento e o que eles relatam chega ao conserto
(25/10/2026, ele: "ele tem que olhar o enquadramento e relatar isso para consertar"; #382: fotos numa faixa com o topo
vazio, a boca do Lula atrás do degradê da capa).

  .venv/bin/python testes/olhos_enquadramento.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(sys.argv[0]).resolve().parent.parent))
from PIL import Image, ImageDraw
import capa_agente as CA, animador_novo as AN, olho_unico as O

falhas = []
AZUL = (24, 52, 150)


def tela(faixa=None):
    """Um quadro 1080x1920 com o azul da página e, se pedido, uma 'foto' (cinza) entre faixa[0] e faixa[1]."""
    im = Image.new("RGB", (1080, 1920), AZUL)
    if faixa:
        ImageDraw.Draw(im).rectangle([0, faixa[0], 1079, faixa[1]], fill=(120, 110, 100))
    return im


# 1. a medida do programa: a foto numa faixa do #382 (y 230 a 840) é acusada; no alto, na largura toda, não
r = O.imagem_em_faixa(tela((230, 840)))
if not r or abs(r[0] - 230) > 10:
    falhas.append(f"a foto numa faixa (230-840) não foi acusada: {r}")
for nome, f in (("a foto no alto", (0, 720)), ("tela cheia", (0, 1919)), ("só o azul", None), ("um selo pequeno", (900, 1100))):
    if O.imagem_em_faixa(tela(f)):
        falhas.append(f"{nome} foi acusada como foto numa faixa")

# 2. a capa: o rosto grande da selfie (#382) fica com o queixo acima do degradê; o ajuste que os Olhos pedem anda a foto
selfie = ("x", 1080, 1920, (344, 381, 451, 582))
x, y, w, h = CA._caixa(selfie, 0, 1080, 1120)
if 381 + 582 + y > CA.CAPA_ROSTO["queixo"]:
    falhas.append(f"o queixo da selfie ficou em {381 + 582 + y}, abaixo do limite {CA.CAPA_ROSTO['queixo']}")
_, y2, _, _ = CA._caixa(selfie, 0, 1080, 1120, -100)
if y2 != y - 100:
    falhas.append(f"o ajuste de -100 px não subiu a foto: {y} -> {y2}")
_, y3, _, _ = CA._caixa(selfie, 0, 1080, 1120, 5000)
if y3 > 0:
    falhas.append("o ajuste para baixo deixou um buraco no alto da capa")
normal = ("x", 1920, 1080, (900, 200, 120, 150))
if CA._caixa(normal, 0, 1080, 1120) != (-1252, -33, 3584, 2016):
    falhas.append(f"o rosto de tamanho normal mudou de lugar: {CA._caixa(normal, 0, 1080, 1120)}")

# 3. o que os Olhos ainda veem depois do conserto conta como aviso grave (a tela mostra "Consertar estes avisos")
if not AN.grave({"tipo": "olhos", "msg": "foto numa faixa"}):
    falhas.append("o tipo 'olhos' não é grave: o aviso não apareceria na tela")

if falhas:
    print("FALHOU · " + "; ".join(falhas))
    sys.exit(1)
print("passou · foto numa faixa acusada (e a do alto não), queixo da capa acima do degradê, ajuste de altura dos Olhos "
      "aplicado sem buraco, o que os Olhos ainda veem vira aviso grave")
