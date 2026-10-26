"""Tipo A (sem IA, sem servidor): intencao-viva (24/10/2026, ele: "no passado combinamos de ter uma pasta do video e
tudo ficar nessa pagina inclusive essas decisoes"). A decisão dele entra no INTENCAO.md, não se repete, e fica quando a
pauta reescreve o roteiro; o porteiro e o editor leem o arquivo. Pasta temporária. Calibrado: sem a parte "decisoes" no
pauta.grava, o caso 3 falha."""
import inspect, sys, tempfile
from pathlib import Path
R = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(R), str(R / "ferramentas")]
import estudio as E
E.VIDEOS = Path(tempfile.mkdtemp()) / "videos"; E.LIXEIRA = E.VIDEOS / "_lixeira"
import pauta, maestro, animador_novo as N
falhas = []
num, _ = E.criar_item("igual", link="https://www.instagram.com/reel/T/", texto="sem o trecho do patrimônio")
p = E.pasta(num)
blocos = [{"bloco": "Abertura", "quem": "nós", "fala": "Lula consegue virar?", "tela": "título"}]
R1 = {"angulo": "Lula precisa de tudo junto", "blocos": blocos, "analise_md": "", "checagem_md": ""}
pauta.grava(num, R1, E.ler_ficha(num))
E.anota_decisao(num, "Nunca chamar o Flávio de adversário", "não chama o Flávio de adversário")
E.anota_decisao(num, "Nunca chamar o Flávio de adversário", "de novo")
txt = (p / "INTENCAO.md").read_text()
if txt.count("Nunca chamar o Flávio de adversário") != 1:
    falhas.append(f"1/2: a decisão aparece {txt.count('Nunca chamar o Flávio de adversário')} vez(es), esperado 1")
pauta.grava(num, {**R1, "angulo": "Ângulo novo depois de reescrever"}, E.ler_ficha(num))
txt = (p / "INTENCAO.md").read_text()
if "Ângulo novo" not in txt or "Nunca chamar o Flávio de adversário" not in txt:
    falhas.append("3: ao reescrever o roteiro, a decisão anotada sumiu do INTENCAO.md")
if "{intencao}" not in maestro.PEDIDO or "{intencao}" not in maestro.PEDIDO_ROTEIRO or "anota_decisao" not in inspect.getsource(maestro.decidir):
    falhas.append("4: o porteiro não lê ou não anota no INTENCAO.md")
if "Nunca chamar o Flávio de adversário" not in N.recado(num):
    falhas.append("5: o editor não recebe as decisões dele")
print("passou · a decisão dele entra no INTENCAO.md, não se repete, fica ao reescrever e chega ao porteiro e ao editor"
      if not falhas else "FALHOU · " + " | ".join(falhas))
sys.exit(1 if falhas else 0)
