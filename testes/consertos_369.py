"""Tipo A (sem IA, sem servidor): consertos-do-369 (24/10/2026, "pode fazer os rápidos e as medidas da régua"). A régua
acha o número de um bloco na tela antes da hora (o caso do #369 aos 2 s) e não confunde com br360; a tela parada vale em
todos os vídeos; a assinatura ficou curta; as regras da pesquisa e da capa estão lá. Calibrado: sem o antes_da_hora
somado aos problemas, o caso 2 falha; com br360 contando, o caso 1."""
import inspect, sys
from pathlib import Path
R = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(R), str(R / "ferramentas")]
import regua as RG, animacao as A
falhas = []
blocos = [(1, 0.0, 4.3, set()), (2, 4.7, 11.1, {"56,1", "53,9", "2,2"}), (4, 17.2, 23.9, {"33,5", "21,08"})]
txt = lambda t, s, leg=False: {"tipo": "texto", "txt": s, "op": 1, "b": [0, 0, 10, 10], "leg": leg}
quadros = [(t, [txt(t, "LULA CONSEGUE VIRAR"), txt(t, "33,5 MI"), txt(t, "21%"), txt(t, "INSTITUTO br360"),
                txt(t, "trinta e três 33,5", leg=True)]) for t in (2.5, 2.75, 3.0)] + [(18.0, [txt(18.0, "33,5 MILHÕES")])]
achou = RG.antes_da_hora(quadros, blocos)
nomes = sorted(a["msg"].split("'")[1] for a in achou)
if nomes != ["21%", "33,5 MI"]:
    falhas.append(f"1: antes da hora achou {nomes}, esperado ['21%', '33,5 MI'] (br360, legenda e o bloco certo não contam)")
if "antes_da_hora(quadros, numeros_por_bloco(d))" not in inspect.getsource(RG.medir):
    falhas.append("2: a régua não soma o antes da hora aos problemas")
if "mede_parado = True" not in inspect.getsource(A._regua_inteira):
    falhas.append("3: a tela parada não vale em todos os vídeos")
ass = (R / "web/pecas/assinatura.js").read_text()
if "const DURACAO = 2.6;" not in ass:
    falhas.append("4: a assinatura continua longa")
if "Pesquisa de" not in (R / "regras/ROTEIRISTA.md").read_text() or "**Pesquisa**" not in (R / "regras/ANIMADOR.md").read_text():
    falhas.append("5: falta a regra da pesquisa sem selo")
if "Sem marca de outro canal" not in (R / "regras/CAPA.md").read_text():
    falhas.append("6: falta a regra da capa sem marca de outro canal")
print("passou · antes da hora, tela parada em todos, assinatura curta, pesquisa sem selo, capa sem marca de outro canal"
      if not falhas else "FALHOU · " + " | ".join(falhas))
sys.exit(1 if falhas else 0)
