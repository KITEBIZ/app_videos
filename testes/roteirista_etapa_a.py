"""Tipo A (sem IA): Etapa A da revisão do roteirista (26/10/2026, ele: "pode fazer"). Travessão e @ se consertam no texto
sem pedir o roteiro de novo; o @ só nos blocos; o resto do roteiro não muda; o leitor aceita quebra de linha crua.

  .venv/bin/python testes/roteirista_etapa_a.py
"""
import sys
from pathlib import Path
sys.path[:0] = [str(Path(sys.argv[0]).resolve().parent.parent)]
import pauta, ia

falhas = []
R = {"titulo": "Um — dois", "checagem_md": "fonte: contato@site.com — ok",
     "blocos": [{"bloco": "Abertura", "quem": "nós", "fala": "Ele disse — e repetiu — no @newsbr360.", "tela": "SIGA @newsbr360"},
                {"bloco": "A fala", "quem": "Fulano", "trecho": "eu disse isso", "corte": [1, 3]}]}
feitos = pauta.conserta_mecanico(R)
b = R["blocos"][0]
if feitos != ["@", "travessão"] or b["fala"] != "Ele disse, e repetiu, no newsbr360." or b["tela"] != "SIGA newsbr360":
    falhas.append(f"conserto dos blocos: {feitos} {b}")
if "contato@site.com" not in R["checagem_md"] or "—" in R["checagem_md"] or R["titulo"] != "Um, dois":
    falhas.append(f"fora dos blocos: {R['checagem_md']!r} {R['titulo']!r}")
if R["blocos"][1] != {"bloco": "A fala", "quem": "Fulano", "trecho": "eu disse isso", "corte": [1, 3]}:
    falhas.append("mexeu no que não tinha travessão nem @")
if pauta.conserta_mecanico({"blocos": [{"fala": "nada"}]}):
    falhas.append("disse que consertou sem ter o que consertar")
if not ia.json_de('{"checagem_md": "| a |\n| b |"}'):
    falhas.append("o leitor recusou quebra de linha crua (#405)")
# Etapa B (26/10/2026): na reescrita o caderno de fatos só cresce
antes = "| Afirmação | Fonte original | Tipo |\n|---|---|---|\n| A | [x](https://x) | CONFIRMADO |\n"
novo = pauta.junta_fatos(antes, ["| B | [y](https://y) | CONFIRMADO |", "| A | [x](https://x) | CONFIRMADO |", "texto solto"])
if not novo.startswith(antes) or novo.count("| A |") != 1 or "| B |" not in novo or "texto solto" in novo:
    falhas.append(f"caderno de fatos: {novo!r}")
if pauta.junta_fatos("", ["| C | d | e |"]).count("|---|---|---|") != 1:
    falhas.append("caderno vazio sem cabeçalho")
import tempfile, estudio as E
E.VIDEOS = Path(tempfile.mkdtemp()) / "videos"; E.LIXEIRA = E.VIDEOS / "_lixeira"
n, _ = E.criar_item("ideia", texto="t")
p = E.pasta(n); (p / "CHECAGEM.md").write_text(antes); (p / "ANALISE.md").write_text("análise da pauta\n")
pauta.grava(n, {"titulo": "t", "blocos": [{"bloco": "a", "quem": "nós", "fala": "f"}], "checagem_md": "TUDO NOVO",
                "analise_md": "outra", "fatos_novos": ["| B | y | z |"]}, E.ler_ficha(n), reescrita=True)
if (p / "ANALISE.md").read_text() != "análise da pauta\n" or "TUDO NOVO" in (p / "CHECAGEM.md").read_text() \
        or not (p / "CHECAGEM.md").read_text().startswith(antes) or "| B | y | z |" not in (p / "CHECAGEM.md").read_text():
    falhas.append("a reescrita mexeu na análise ou trocou a checagem")
if falhas:
    print("FALHOU · " + "; ".join(falhas)); sys.exit(1)
print("passou · travessão e @ consertados no texto, @ só nos blocos, o resto intacto, quebra de linha crua aceita; na reescrita a checagem só ganha fatos novos e a análise fica")
