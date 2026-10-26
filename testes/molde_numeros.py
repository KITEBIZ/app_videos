"""Tipo A (sem IA, sem servidor): o molde números (24/10/2026, "pode fazer o molde números" e "pode fazer o editor do
molde números com o recado"). Liga e desliga pelo pedido dele, as regras e o exemplo existem, a peça tem as casas e está
no tocador, a tela parada é medida por programa e o editor recebe o recado. Calibrado: sem o "numeros" no molde_pedido
os 3 primeiros casos falham; com a tela parada desligada (PARADO_MAX = 99) o caso sintético falha."""
import sys, tempfile
from pathlib import Path
R = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(R), str(R / "ferramentas")]
import servidor, estudio as E, animacao as A, animador_novo as N
casos = [("usa o molde números", "numeros"), ("faz o micro doc em números", "numeros"), ("faz no formato números", "numeros"),
         ("o lucro em números caiu", None), ("tira o molde números", ""), ("faz como micro doc", "microdoc")]
falhas = [f"{t!r} deu {servidor.molde_pedido(t)!r}, esperado {e!r}" for t, e in casos if servidor.molde_pedido(t) != e]
if not (E.RAIZ / "regras" / E.MOLDES.get("numeros", "-")).exists():
    falhas.append("regras/MOLDE-NUMEROS.md não existe")
for f in ("web/pecas/numeros.js", "regras/exemplos/numeros-368.html"):
    if not (E.RAIZ / f).exists():
        falhas.append(f"falta {f}")
peca = (E.RAIZ / "web/pecas/numeros.js").read_text()
for p in ("fundo", "numero", "titulo", "barra", "barras", "regua", "alerta", "troca", "comenta"):
    if f"{p}: comCena({p})" not in peca:
        falhas.append(f"a peça não tem {p}")
toc = (E.RAIZ / "web/tocador.html").read_text()
if "/pecas/numeros.js" not in toc or "Numeros.instalar(tl, T)" not in toc:
    falhas.append("o tocador não liga a peça números")
molde = (E.RAIZ / "regras/MOLDE-NUMEROS.md").read_text()
if "python3" in molde:
    falhas.append("as regras do molde números mandam rodar comando na chamada única")
# a tela parada: 6 s com um quadro igual (só o fundo) e uma troca no meio de outro trecho
from PIL import Image, ImageDraw
with tempfile.TemporaryDirectory() as d:
    feitos = []
    for k in range(13):
        t = k * .5; im = Image.new("RGB", (1080, 1920), (10, 20, 70))
        if t >= 4.0:
            ImageDraw.Draw(im).rectangle([100, 500, 900, 900], fill=(255, 200, 50))
        f = Path(d) / f"t{t:06.2f}.jpg"; im.save(f); feitos.append((t, str(f)))
    par = A.trechos_parados(feitos)
    if par != [{"de": 0.0, "ate": 4.0}]:
        falhas.append(f"a tela parada de 0 a 4 s não foi medida certo: {par}")
# o editor recebe o recado (o Ângulo do INTENCAO.md)
import inspect
if "recado(num)" not in inspect.getsource(N.revisar):
    falhas.append("o editor não recebe o recado do vídeo")
print("passou · molde números liga/desliga, regras, peça, tela parada e recado" if not falhas else "FALHOU · " + " | ".join(falhas))
sys.exit(1 if falhas else 0)
