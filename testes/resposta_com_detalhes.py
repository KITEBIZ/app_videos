"""Tipo A (sem IA, sem rede): a resposta do animador no chat sai curta e o relatório vai em "detalhes" (24/10/2026, ele:
"pode fazer" a parte B; ACHADOS resposta.3). Pasta de vídeos temporária: não mexe em vídeo de verdade.

  .venv/bin/python testes/resposta_com_detalhes.py
"""
import re, sys, tempfile
from pathlib import Path

sys.path.insert(0, str(Path(sys.argv[0]).resolve().parent.parent))
import estudio as E
E.VIDEOS = Path(tempfile.mkdtemp()) / "videos"
E.LIXEIRA = E.VIDEOS / "_lixeira"
import animador_novo as AN

falhas = []
def caso(nome, ok, visto=""):
    if not ok:
        falhas.append(f"{nome} (visto: {str(visto)[:160]})")

num, _ = E.criar_item("igual", texto="teste")
m, _ = E.chat_add(num, "agente", "Subi o rosto no bloco 2." + E.DETALHES + "Conferência: achou 4 ponto(s) (0 da régua, 4 dos Olhos).")
caso("1 o chat grava só a resposta curta", m["texto"] == "Subi o rosto no bloco 2.", m)
caso("2 o relatório vai no campo detalhes", m.get("detalhes", "").startswith("Conferência: achou 4"), m)
m2, _ = E.chat_add(num, "agente", "Resposta sem relatório.")
caso("3 sem relatório, nada de detalhes", m2["texto"] == "Resposta sem relatório." and "detalhes" not in m2, m2)

AN.ampliados = lambda n, limite=2.5: [(5.8, 3.2), (34.6, 3.2)]
grave = {"de": 3.0, "tipo": next(iter(AN.GRAVES)), "msg": "ELE DISSE encostado"}
txt = AN.pergunta_para_ele(num, [grave], {"atendido": "parcial", "faltou": "y≈165–565 vazio"})
caso("4 take ampliado vira pergunta em segundos redondos", "aos 6 s e aos 35 s" in txt and "Procuro um vídeo mais de perto?" in txt, txt)
caso("5 grave que trava o botão é dito em português", "Aprovar mesmo assim" in txt, txt)
caso("6 pedido parcial é dito sem o relatório técnico", "ainda não ficou inteiro" in txt and "y≈" not in txt, txt)
caso("7 nada de bastidor na parte curta", not re.search(r"px|y≈|\.py|ponto\(s\)|régua|Olhos|`", txt), txt)
AN.ampliados = lambda n, limite=2.5: []
vazio = AN.pergunta_para_ele(num, [], {"atendido": "sim"})
caso("8 sem nada a decidir, parte curta vazia", vazio == "", vazio)

if falhas:
    print("FALHOU · " + " | ".join(falhas)); sys.exit(1)
print("passou · resposta curta no chat, relatório em detalhes, decisões em português (8 casos)")
