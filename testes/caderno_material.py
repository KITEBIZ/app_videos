"""Tipo A (sem IA): o caderno de material (26/10/2026, ele: "pode seguir"). Cada material vira uma ficha uma vez (a mesma
origem não repete), o PDF tem o texto tirado, a ficha que veio com chamada de ferramenta não vale, e o caderno entra no
pedido do roteirista e do agente.

  .venv/bin/python testes/caderno_material.py
"""
import sys, tempfile, shutil, subprocess
from pathlib import Path
sys.path[:0] = [str(Path(sys.argv[0]).resolve().parent.parent)]
import estudio as E
E.VIDEOS = Path(tempfile.mkdtemp()) / "videos"; E.LIXEIRA = E.VIDEOS / "_lixeira"
import ia, caderno, agente

falhas, pedidos = [], []
resp = {"txt": "Fato: a nota confirma a investigação."}
ia.chamar = lambda pedido, quem, *a, **k: (pedidos.append(pedido) or resp["txt"], {"erro": ""})
n, _ = E.criar_item("ideia", texto="t")
x = caderno.registrar(n, "https://site/a", "página", "texto da página")
y = caderno.registrar(n, "https://site/a", "página", "outra vez")
if x["id"] != "M1" or y["id"] != "M1" or len(caderno.itens(n)) != 1 or len(pedidos) != 1:
    falhas.append("a mesma origem virou duas fichas")
if (E.pasta(n) / x["texto"]).read_text() != "texto da página" or not (E.pasta(n) / "MATERIAL.md").exists():
    falhas.append("o texto inteiro ou o MATERIAL.md não foi guardado")
resp["txt"] = 'Vou abrir.\n<invoke name="Glob"><parameter name="pattern">x</parameter></invoke>'
z = caderno.registrar(n, "https://site/b", "página", "b")
if "<invoke" in z["util"] or "não saiu" not in z["util"]:
    falhas.append(f"ficha com chamada de ferramenta valeu: {z['util']!r}")
if shutil.which("pdftotext") and shutil.which("cupsfilter"):
    (E.pasta(n) / "anexos").mkdir()
    t = Path(tempfile.mkdtemp()) / "n.txt"; t.write_text("NOTA OFICIAL da PF sobre a investigação\n")
    (E.pasta(n) / "anexos/nota.pdf").write_bytes(subprocess.run(["cupsfilter", str(t)], capture_output=True).stdout)
    resp["txt"] = "ok"
    w = caderno.anexo(n, "nota.pdf")
    if w["tipo"] != "PDF" or "NOTA OFICIAL" not in (E.pasta(n) / w["texto"]).read_text():
        falhas.append("o texto do PDF não foi tirado")
if "MATERIAL COMPLEMENTAR" not in caderno.para_pedido(n) or "M1" not in caderno.para_pedido(n):
    falhas.append("o caderno não entra no pedido")
fixo, var = agente.contexto_partes(n, {"id": "x", "texto": "oi"})
if "MATERIAL COMPLEMENTAR" not in var:
    falhas.append("o agente não recebe o caderno")
if falhas:
    print("FALHOU · " + "; ".join(falhas)); sys.exit(1)
print("passou · uma ficha por material, texto inteiro guardado, PDF lido, ficha falsa recusada, caderno no pedido do agente")
