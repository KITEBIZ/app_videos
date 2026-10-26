"""Tipo A (sem IA, sem servidor): porteiro-completo-instalador-e-prova-vps (24/10/2026, "pode fazer tudo isso"). O porteiro
lê a checagem e a memória da página e leva na ordem os detalhes dele; o roteirista e o agente põem a pessoa FALANDO quando
ele pede o vídeo dela; o instalador espera o vídeo que começou a trabalhar antes de religar. Calibrado: sem a espera
(espera_livre devolvendo True direto), o caso 4 falha."""
import inspect, sys
from pathlib import Path
R = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(R), str(R / "ferramentas")]
sys.argv = [sys.argv[0], "4499"]
import maestro, instalar as I
falhas = []
for nome, t in (("PEDIDO", maestro.PEDIDO), ("PEDIDO_ROTEIRO", maestro.PEDIDO_ROTEIRO)):
    if "{checagem}" not in t or "{memoria}" not in t:
        falhas.append(f"1: o porteiro ({nome}) não lê a checagem e a memória")
    if "leve as PALAVRAS dele" not in t:
        falhas.append(f"2: o porteiro ({nome}) não tem a regra de levar os detalhes dele na ordem")
for arq in ("regras/AGENTE.md", "regras/ROTEIRISTA.md"):
    if "Quando ele pede o vídeo de alguém" not in (R / arq).read_text():
        falhas.append(f"3: {arq} sem a regra da pessoa falando com a voz dela")
ciclos = iter([["#373 (baixando o vídeo)"], ["#373 (baixando o vídeo)"], []])
I.ocupados = lambda: next(ciclos, [])
I.time.sleep = lambda s: None
livre = I.espera_livre(maximo=60, passo=0)
I.ocupados = lambda: ["#373 (baixando o vídeo)"]
preso = I.espera_livre(maximo=0, passo=0)
if not livre or preso or "espera_livre()" not in inspect.getsource(I.instalar):
    falhas.append(f"4: o instalador não espera antes de religar (livre={livre}, preso={preso})")
# o modo prova da cópia da VPS: nenhum trabalho começa e a publicação é recusada
import servidor as S
if "if PROVA:" not in inspect.getsource(S.garantir) or 'acao == "publicar" and PROVA' not in (R / "servidor.py").read_text():
    falhas.append("5: o modo prova deixa trabalhar sozinho ou publicar")
if not (R / "ferramentas/prova_vps.sh").exists():
    falhas.append("6: falta ferramentas/prova_vps.sh")
print("passou · porteiro com checagem, memória e os detalhes dele; pessoa falando com a voz dela; instalador espera para religar"
      if not falhas else "FALHOU · " + " | ".join(falhas))
sys.exit(1 if falhas else 0)
