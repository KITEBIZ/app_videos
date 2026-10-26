"""Tipo B (usa IA, ~US$ 0,02 por pedido): o maestro separa AJUSTE PEQUENO de MUDANÇA DE DIREÇÃO (25/10/2026, ele: "ele tem
que entender o que é uma mudança pequena ou uma mudança de sentido ou direção"). Os 45 pedidos de roteiro que ele fez de
verdade nos chats, marcados um a um (testes/pedidos_direcao.json). Roda numa cópia das pastas dos vídeos (V2_VIDEOS), sem
gravar nada nelas além do gasto.

  V2_VIDEOS=/tmp/copia/videos .venv/bin/python testes/maestro_direcao.py [--so N]
"""
import json, os, sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

RAIZ = Path(sys.argv[0]).resolve().parent.parent
sys.path[:0] = [str(RAIZ)]
import estudio as E
if os.environ.get("V2_VIDEOS"):
    E.VIDEOS = Path(os.environ["V2_VIDEOS"])
import maestro

casos = json.loads((RAIZ / "testes/pedidos_direcao.json").read_text())
if "--so" in sys.argv:
    casos = casos[:int(sys.argv[sys.argv.index("--so") + 1])]
DIRECAO = {"propor_mudanca", "reescrever_roteiro", "aplicar_proposta"}


def um(c):
    f = E.ler_ficha(c["num"])
    if f.get("etapa") not in maestro.ETAPAS_ROTEIRO:     # o pedido foi feito no roteiro: o maestro do roteiro decide
        E.mexe_ficha(c["num"], etapa="Pauta", passo="roteiro pronto", esperando="Aprovar o roteiro", proposta=None)
    d = maestro.decidir(c["num"], c["texto"], conversa="(nenhuma)", gravar=False)
    fs = [a["ferramenta"] for a in d.get("acoes") or []]
    viu = "direcao" if DIRECAO & set(fs) else ("ajuste" if fs else "duvida")
    return c, viu, fs


erros = 0
with ThreadPoolExecutor(6) as ex:
    for c, viu, fs in ex.map(um, casos):
        ok = viu == c["era"]
        erros += not ok
        print(("ok   " if ok else "ERRO ") + f"#{c['num']} era {c['era']}, viu {viu} {fs} · {c['texto'][:90]!r}")
print(f"\n{len(casos) - erros} de {len(casos)} certos")
sys.exit(1 if erros > len(casos) // 15 else 0)
