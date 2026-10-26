"""Tipo A (sem IA): Etapa C da revisão do roteirista (26/10/2026, ele: "pode seguir"). O ajuste do agente do chat passa
pela conferência do roteirista: travessão e @ consertados no texto; defeito NOVO de texto (corte no meio da frase) volta
ao agente uma vez; duração e o resto viram aviso; defeito que já existia antes não é culpa do ajuste.

  .venv/bin/python testes/ajuste_mesmas_regras.py
"""
import sys, tempfile
from pathlib import Path
sys.path[:0] = [str(Path(sys.argv[0]).resolve().parent.parent)]
import estudio as E
E.VIDEOS = Path(tempfile.mkdtemp()) / "videos"; E.LIXEIRA = E.VIDEOS / "_lixeira"
import pauta, agente

falhas = []
n, _ = E.criar_item("ideia", texto="t")
p = E.pasta(n)
CAB = "# Roteiro v1\n\n| # | Bloco | Quem | Fala | Tela |\n|---|---|---|---|---|\n"
antes = CAB + "| 1 | A | nós | um dois | x |\n"
(p / "ROTEIRO.md").write_text(CAB + "| 1 | A | nós | um — dois no @perfil | SIGA @perfil |\n")
chamadas = []
agente.trabalhar = lambda num, txt, **k: chamadas.append(txt) or ("ok", 0)

# 1) só travessão e @: consertado no texto, sem chamar o agente
pauta.regras_quebradas = lambda num, texto=None: []
r = agente._mesmas_regras(n, antes, "Feito.", "", "opus")
if "—" in (p / "ROTEIRO.md").read_text() or "@" in (p / "ROTEIRO.md").read_text() or chamadas or r != "Feito.":
    falhas.append(f"conserto no texto: {(p / 'ROTEIRO.md').read_text()!r} {chamadas} {r!r}")

# 2) defeito novo de texto: volta ao agente uma vez; se ficar, aviso
pauta.regras_quebradas = lambda num, texto=None: [] if texto else ['o trecho termina no meio da frase ("...x")']
r = agente._mesmas_regras(n, antes, "Feito.", "", "opus")
if len(chamadas) != 1 or "meio da frase" not in chamadas[0] or "Atenção" not in r:
    falhas.append(f"defeito novo: {chamadas} {r!r}")

# 3) duração passou: aviso, sem chamar o agente (pode ser o que ele pediu)
chamadas.clear()
pauta.regras_quebradas = lambda num, texto=None: [] if texto else ["o roteiro tem uns 80 s e o alvo é até 60 s"]
r = agente._mesmas_regras(n, antes, "Feito.", "", "opus")
if chamadas or "80 s" not in r:
    falhas.append(f"duração: {chamadas} {r!r}")

# 4) defeito que já existia antes (mesmo tipo, outro número): não é culpa do ajuste
pauta.regras_quebradas = lambda num, texto=None: ["o roteiro tem uns 72 s"] if texto else ["o roteiro tem uns 75 s"]
r = agente._mesmas_regras(n, antes, "Feito.", "", "opus")
if chamadas or r != "Feito.":
    falhas.append(f"defeito antigo virou culpa do ajuste: {r!r}")

if falhas:
    print("FALHOU · " + "; ".join(falhas)); sys.exit(1)
print("passou · travessão e @ no texto, defeito novo volta ao agente uma vez, duração é aviso, defeito antigo não conta")
