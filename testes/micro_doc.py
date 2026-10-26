"""Tipo A (sem IA, sem servidor): o formato micro documentário (24/10/2026, "pode ensiar esse formato ao agente?").
Liga e desliga pelo pedido dele, o molde existe e vai junto, as ferramentas do animador existem e a peça tem o
vocabulário do exemplo. Calibrado: com o "microdoc" fora do molde_pedido, os 3 primeiros casos falham."""
import sys
from pathlib import Path
R = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(R), str(R / "ferramentas")]
import servidor, estudio as E
casos = [("faz como micro doc", "microdoc"), ("usa o micro documentário nesse", "microdoc"), ("faz em colagem", "microdoc"),
         ("volta ao molde normal", ""), ("tira o micro doc", ""), ("o que é um micro doc?", None), ("usa o fomos conferir", "conferir"),
         ("gostei do micro doc de ontem", None)]
falhas = [f"{t!r} deu {servidor.molde_pedido(t)!r}, esperado {e!r}" for t, e in casos if servidor.molde_pedido(t) != e]
if not (E.RAIZ / "regras" / E.MOLDES.get("microdoc", "-")).exists():
    falhas.append("regras/MOLDE-MICRO-DOC.md não existe")
for f in ("ferramentas/fotos_livres.py", "ferramentas/trilha.py", "regras/exemplos/micro-doc-367.html", "web/sons/trilhas/CATALOGO.md"):
    if not (E.RAIZ / f).exists():
        falhas.append(f"falta {f}")
srv = (E.RAIZ / "servidor.py").read_text()
if 'pede == "microdoc"' not in srv:
    falhas.append("o pedido \"faz como micro doc\" não liga o molde na ficha")
peca = (E.RAIZ / "web/pecas/colagem.js").read_text()
for p in ("capitulo", "faixa", "risco", "seta", "manchete", "painel", "comenta", "recorte", "cartaz", "mapa"):
    if f"{p}: comCena({p})" not in peca:
        falhas.append(f"a peça não tem {p}")
for ruim in ("'marcador'", "'caneta'", "'papel-desliza'"):
    if ruim in peca:
        falhas.append(f"a peça ainda usa o som {ruim} (ele tirou)")
# 24/10/2026 (animador-micro-doc): a chamada única não roda nada; as regras não podem mandar o animador buscar fotos
# ou montar trilha (25/10/2026: o jeito de antes saiu), e o vídeo normal não recebe nada do micro doc
molde = (E.RAIZ / "regras/MOLDE-MICRO-DOC.md").read_text()
if "python3" in molde:
    falhas.append("as regras do micro doc mandam rodar comando na chamada única (o #368 pensou 600 s sem escrever)")
anim = (E.RAIZ / "animador_novo.py").read_text()
if "def pedido_primeira" not in anim or 'if E.ler_ficha(num).get("molde") in ("microdoc", "numeros"):\n        E._ferramentas(); import preparo_microdoc' not in anim:
    falhas.append("o pedido da primeira animação não separa o micro doc dos vídeos normais")
import preparo_microdoc as PM
d = {"blocos": [{"n": 5, "ini": 20.0, "fim": 26.0}], "palavras": [[20.1, 20.4, "Era"], [21.9, 22.1, "Mas,"]]}
if PM._instante(d, 5, "mas") != 21.9 or PM._instante(d, 5, "") != 20.0 or PM._instante(d, 9, "mas") is not None:
    falhas.append("o instante da troca da trilha não sai do tempo da palavra")
print("passou · micro doc liga/desliga, molde, ferramentas e peças" if not falhas else "FALHOU · " + " | ".join(falhas))
sys.exit(1 if falhas else 0)
