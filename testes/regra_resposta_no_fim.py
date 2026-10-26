"""Tipo A (sem IA, sem rede): a regra "Como responder" do regras/AGENTE.md vai no FIM do pedido do agente do chat, depois
da mensagem dele, e não fica repetida no começo (24/10/2026, ele: "tem que responder de forma curta"; o teste com IA que
mediu a regra nova a pôs no fim). Pasta de vídeos temporária: não mexe em vídeo de verdade.

  .venv/bin/python testes/regra_resposta_no_fim.py
"""
import sys, tempfile
from pathlib import Path

sys.path.insert(0, str(Path(sys.argv[0]).resolve().parent.parent))
import estudio as E
E.VIDEOS = Path(tempfile.mkdtemp()) / "videos"
E.LIXEIRA = E.VIDEOS / "_lixeira"
import agente as AG

num, _ = E.criar_item("igual", texto="teste")
msg, _ = E.chat_add(num, "ele", "MENSAGEM-DELE-AQUI", id_msg="t1")
fixo, var = AG.contexto_partes(num, msg)
falhas = []
if "## Como responder" in fixo:
    falhas.append("a regra continua no começo")
if var.count("## Como responder") != 1:
    falhas.append(f"a regra aparece {var.count('## Como responder')} vez(es) no fim")
elif var.index("## Como responder") < var.index("MENSAGEM-DELE-AQUI"):
    falhas.append("a regra vem antes da mensagem dele")
elif "Fato que você afirma" not in var.split("## Como responder")[1]:
    falhas.append("a regra foi cortada")
if "## Botões" not in fixo:
    falhas.append("a seção de antes sumiu do começo")
if falhas:
    print("FALHOU · " + "; ".join(falhas)); sys.exit(1)
print("passou · a regra de como responder vai inteira no fim, depois da mensagem dele")
