"""Tipo A (sem IA, sem rede, sem servidor): a conferência das fontes lê o link solto (25/10/2026, "faz"; o #383
escreveu "https://..." na tabela, sem [nome](link), e a conferência leu 0 fontes, como se estivesse tudo certo) e avisa
quando a checagem não tem link nenhum. Usa uma pasta de vídeos temporária: não mexe em nenhum vídeo de verdade.

  .venv/bin/python testes/fontes_link_solto.py
"""
import sys, tempfile
from pathlib import Path

sys.path.insert(0, str(Path(sys.argv[0]).resolve().parent.parent))
import estudio as E
E.VIDEOS = Path(tempfile.mkdtemp()) / "videos"
E.LIXEIRA = E.VIDEOS / "_lixeira"
import fontes as F

falhas = []
casos = {
    # o #383: links soltos, um deles com parênteses de texto depois e um ponto no fim
    "solto": ("| Afirmação | Fonte original | Veredito |\n|---|---|---|\n"
              "| Eleito com mais de 60% | Discurso: https://www.funag.gov.br/loja/download/505-discursos.pdf | CONFIRMADO |\n"
              "| STF condenou Dirceu | STF, AP 470: https://www.congressoemfoco.com.br/noticia/67766/stf-dirceu (a quadrilha caiu em 2014) | CONFIRMADO |\n"
              "| Preso 580 dias | Correio: https://www.correio24horas.com.br/brasil/lula-e-libertado-1119. | CONFIRMADO |\n",
              ["https://www.funag.gov.br/loja/download/505-discursos.pdf", "https://www.congressoemfoco.com.br/noticia/67766/stf-dirceu",
               "https://www.correio24horas.com.br/brasil/lula-e-libertado-1119"]),
    # o formato de antes, [nome](link): continua igual, sem link repetido
    "markdown": ("| # | Afirmação | Fonte original | Veredito |\n|---|---|---|---|\n"
                 "| 1 | O TSE proibiu a live | [TSE, 24/09/2022](https://www.tse.jus.br/decisao-123) | CONFIRMADO |\n",
                 ["https://www.tse.jus.br/decisao-123"]),
    "sem link": ("| Afirmação | Fonte original | Veredito |\n|---|---|---|\n"
                 "| Lula disse X | Discurso de posse, 2003 | CONFIRMADO |\n| Y aconteceu | TSE | CONFIRMADO |\n", []),
}
for nome, (md, esperado) in casos.items():
    num, _ = E.criar_item("igual", texto="teste")
    (E.pasta(num) / "CHECAGEM.md").write_text(md)
    achados = [u for *_, ls in F.linhas_da_checagem(num) for u in ls]
    if achados != esperado:
        falhas.append(f"{nome}: os links lidos foram {achados}, esperava {esperado}")
    if nome == "sem link":
        sem = sum(1 for *_, ls in F.linhas_da_checagem(num, sem_link=True) if not ls)
        frase = F.aviso({"fontes": [], "linhas_sem_link": sem})
        if sem != 2 or "Não achei link nenhum" not in frase:
            falhas.append(f"sem link: {sem} linha(s) sem link e o aviso {frase!r}")
# com fontes conferidas e tudo confirmado, o aviso continua calado
if F.aviso({"fontes": [{"afirmacao": "a", "confirma": "sim", "url": "https://x", "obs": ""}], "linhas_sem_link": 1}):
    falhas.append("com fonte confirmada, o aviso de 'sem link' apareceu")

if falhas:
    print("FALHOU · " + "; ".join(falhas))
    sys.exit(1)
print("passou · a conferência lê link solto e [nome](link), e avisa quando a checagem não tem link nenhum")
