"""Tipo A (sem IA, sem servidor): o olho único em observação não segura o vídeo (23/10/2026, "aprovo o plano
olho-unico-observacao"). Prova que a chave olho/DESLIGADO trava tudo e que o olho que falha ou estoura o tempo devolve
vazio sem erro. Usa uma chave e uma IA fingidas e não refaz caderno: não mexe na chave de verdade nem no vídeo
(consertos-da-revisao: antes gravava olho/DESLIGADO na raiz e extraía quadros no vídeo real):

  .venv/bin/python testes/olho_unico.py <número de um vídeo com prévia>
"""
import sys, tempfile
from pathlib import Path

sys.path.insert(0, str(Path(sys.argv[0]).resolve().parent.parent))
import estudio as E
import olho_unico as O
import animador_novo as AN

num = int(sys.argv[1])
chamadas = []
AN.opus = lambda *a, **k: (chamadas.append(a[2]), ("", {"erro": "passou de 120 s"}))[1]     # a IA fingida: sempre estoura
O.registra = lambda *a, **k: None      # o teste não entra no registro da comparação da semana
O.CHAVE = Path(tempfile.mkdtemp()) / "DESLIGADO"
O.fazer_caderno = lambda n: None
falhas = []

# 1) desligado: nada chama a IA, nada vai ao chat, nada quebra
O.CHAVE.write_text("teste")
antes = len(E.chat(num))
O.na_pauta(num); O.na_previa(num)
r = O.localizar(num, "No segundo 3: sobe a cabeça", Path("/nao/existe.jpg"))
if chamadas or r != [] or len(E.chat(num)) != antes:
    falhas.append(f"desligado ainda agiu: chamadas={chamadas} localizar={r} chat {antes}->{len(E.chat(num))}")
O.CHAVE.unlink()

# 2) ligado, IA estourando o tempo: localizar devolve [] e na_previa não escreve no chat nem levanta erro
chamadas.clear()
folha = next(E.pasta(num).glob("animacao/*.jpg"), None) or next(E.pasta(num).rglob("*.jpg"))
r = O.localizar(num, "sobe a cabeça dele", folha)          # sem segundo citado: não abre navegador
if r != []:
    falhas.append(f"olho com erro devolveu {r}")
if not chamadas:
    falhas.append("ligado e não chamou a IA (o teste não provou nada)")

# 3) a frase do chat: no máximo 5 itens, o segundo com vírgula
txt = O.para_o_chat({"defeitos": [{"t": 3.0, "o_que": f"item {i}"} for i in range(8)]})
if txt.count("\n") != 5 or "3,0 s" not in txt:
    falhas.append("frase do chat fora do combinado: " + txt)
if O.para_o_chat({"defeitos": []}) != "Olho (em teste): não vi problema nesta prévia.":
    falhas.append("prévia sem defeito não diz que não viu problema")

print("FALHOU · " + " | ".join(falhas) if falhas else f"passou · desligado não chama a IA; com a IA estourando, o olho devolve vazio ({len(chamadas)} chamada(s) fingida(s))")
sys.exit(1 if falhas else 0)
