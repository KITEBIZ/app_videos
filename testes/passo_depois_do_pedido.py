"""Tipo A (sem IA, sem rede, sem servidor): depois de atender um pedido com link, o vídeo volta ao passo em que estava
(23/10/2026, o #354 em Aguardando ficou com o passo "roteiro pronto": o material() marcava "baixando e transcrevendo o
vídeo que você mandou" antes de o responder() guardar o passo de antes, e esse passo provisório virava "roteiro pronto").
Usa uma pasta de vídeos temporária, o download e o agente fingidos: não mexe em nenhum vídeo de verdade.

  .venv/bin/python testes/passo_depois_do_pedido.py
"""
import json, sys, tempfile
from pathlib import Path

sys.path.insert(0, str(Path(sys.argv[0]).resolve().parent.parent))
import estudio as E
E.VIDEOS = Path(tempfile.mkdtemp()) / "videos"
E.LIXEIRA = E.VIDEOS / "_lixeira"
import agente as AG


def baixa_fingido(num, msg):                  # o que o material() de verdade faz com um link de vídeo, sem baixar
    E.mexe_ficha(num, passo="baixando e transcrevendo o vídeo que você mandou", passo_desde=E.agora())
    return "Link: vídeo baixado (fingido)."


AG.material = baixa_fingido
AG.contexto_partes = lambda num, msg, extra, modo=None: ("", "")
AG.trabalhar = lambda num, var, **k: ("feito (fingido)", 0)

falhas = []
# a espera de cada passo como na vida real (mapa-de-passos, 24/10/2026: sem ela a ficha de mentira ficava fora do mapa)
for etapa, passo, espera in [("Aguardando", "vídeo final pronto", "Publicar"), ("Animação", "prévia pronta", ""),
                             ("Pauta", "roteiro pronto", "Aprovar o roteiro")]:
    num, _ = E.criar_item("igual", texto="teste")
    E.mexe_ficha(num, etapa=etapa, passo=passo, esperando=espera)
    msg, _ = E.chat_add(num, "ele", "https://www.instagram.com/reel/TESTE/ baixa os prints deste vídeo", id_msg=f"t{num}")
    AG.responder(num, msg, modelo="sonnet")
    fim = E.ler_ficha(num)["passo"]
    if fim != passo:
        falhas.append(f"{etapa}: o passo era {passo!r} e ficou {fim!r}")

# 25/10/2026 (#375): o porteiro (servidor.roteiro_atende) já marcou "trabalhando no seu pedido" e guardou o passo de
# antes; a pesquisa pedida com a voz pronta volta a "voz pronta", não a "roteiro pronto"
num, _ = E.criar_item("igual", texto="teste")
E.mexe_ficha(num, etapa="Roteiro e voz", passo="trabalhando no seu pedido", esperando="Aprovar a voz", passo_antes="voz pronta")
(E.pasta(num) / "ROTEIRO.md").write_text("roteiro")
msg, _ = E.chat_add(num, "ele", "pesquisa melhor esse caso antes de alterar o script", id_msg=f"t{num}")
AG.responder(num, msg, modelo="sonnet")
fim = E.ler_ficha(num)["passo"]
if fim != "voz pronta":
    falhas.append(f"Roteiro e voz pelo porteiro: o passo era 'voz pronta' e ficou {fim!r}")

if falhas:
    print("FALHOU · " + "; ".join(falhas))
    sys.exit(1)
print("passou · com link no pedido, o vídeo volta ao passo de antes (Aguardando, Animação e Pauta) e o pedido pelo porteiro com a voz pronta")
