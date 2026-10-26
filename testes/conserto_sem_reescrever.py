"""Tipo A (sem IA): roteiro com problema se conserta, não se reescreve (26/10/2026, #408: três reescritas inteiras de 4 min
para trocar "mais da metade" por "maior bancada" e cortar 20 s; ele: "não deveria refazer tudo").

Com a IA fingida: (1) erro da conferência na 1ª versão -> uma chamada de conserto, nenhuma reescrita; (2) roteiro que foge
da proposta -> conserto; depois do conserto, fugir de novo é aviso; (3) conserto que não vem -> uma reescrita inteira.

  .venv/bin/python testes/conserto_sem_reescrever.py
"""
import sys, tempfile
from pathlib import Path
sys.path[:0] = [str(Path(sys.argv[0]).resolve().parent.parent)]
import pauta, estudio as E, ia, fluidez

E.VIDEOS = Path(tempfile.mkdtemp()) / "videos"; E.LIXEIRA = E.VIDEOS / "_lixeira"
falhas = []
BOM = {"titulo": "t", "blocos": [{"bloco": "a", "quem": "nós", "fala": "certo"}]}
RUIM = {"titulo": "t", "blocos": [{"bloco": "a", "quem": "nós", "fala": "errado"}]}


# grava é fingido e para o escrever ali (o resto dele não interessa aqui)
class Parar(Exception):
    pass


def roda(conserto_vem, proposta_foge):
    def grava(num, R, *a, **k):
        roda.R = R
        raise Parar()
    n, _ = E.criar_item("ideia", texto="t")
    ch = {"pedir": 0, "conserto": 0, "proposta": 0}

    def pedir(*a, **k):
        ch["pedir"] += 1
        return {"titulo": "t", "blocos": [dict(RUIM["blocos"][0] if (ch["pedir"] == 1 and not proposta_foge) else BOM["blocos"][0])]}

    def chamar(prompt, quem, *a, **k):
        if quem == "roteirista (conserto)":
            ch["conserto"] += 1
            return ('{"titulo": "t", "blocos": [{"bloco": "a", "quem": "nós", "fala": "certo"}]}' if conserto_vem else "nada"), {}
        if quem == "conferência da proposta":
            ch["proposta"] += 1
            return ('{"segue": false, "faltas": ["x"]}' if ch["proposta"] <= (proposta_foge or 0) else '{"segue": true}'), {}
        raise AssertionError(quem)

    pauta.pedir_roteiro, ia.chamar, pauta.grava = pedir, chamar, grava
    pauta.confere = lambda R, *a, **k: ["fala errada"] if any(b.get("fala") == "errado" for b in R["blocos"]) else []
    fluidez.problemas = lambda *a, **k: []
    roda.R = None
    try:
        pauta.escrever(n, E.ler_ficha(n), {}, "", proposta="P" if proposta_foge else None)
    except Parar:
        pass
    return ch, roda.R, (E.pasta(n) / "historico.jsonl").read_text()


ch, R, hist = roda(conserto_vem=True, proposta_foge=0)
if ch != {"pedir": 1, "conserto": 1, "proposta": 0} or R["blocos"][0]["fala"] != "certo" or "consertando só isso" not in hist:
    falhas.append(f"erro da conferência: {ch} {R}")
ch, R, hist = roda(conserto_vem=True, proposta_foge=2)
if ch["pedir"] != 1 or ch["conserto"] != 1 or "ainda diferente da proposta (aviso)" not in hist or R is None:
    falhas.append(f"fuga da proposta: {ch} {hist[-300:]}")
ch, R, hist = roda(conserto_vem=False, proposta_foge=0)
if ch != {"pedir": 2, "conserto": 1, "proposta": 0} or R["blocos"][0]["fala"] != "certo":
    falhas.append(f"conserto que não veio: {ch} {R}")
if falhas:
    print("FALHOU · " + "; ".join(falhas)); sys.exit(1)
print("passou · erro pontual se conserta sem reescrever (1 chamada leve); fuga da proposta se conserta e depois vira aviso; "
      "sem conserto, uma reescrita")
