"""Tipo A (sem IA, sem rede, sem o servidor no ar): o que deixa a tela leve (25/10/2026, "pode fazer do 1 ao 4"; medido
no ar: o funil levava 86 ms e pesava 70 KB, a ficha do vídeo até 37 KB, os dois a cada 2 s, e a VPS gravava de novo
a prévia de vídeos parados). Usa uma pasta de vídeos temporária.

  .venv/bin/python testes/rapidez.py
"""
import io, os, sys, tempfile, time, types
from pathlib import Path

RAIZ = Path(sys.argv[0]).resolve().parent.parent
sys.path[:0] = [str(RAIZ), str(RAIZ / "ferramentas")]
import estudio as E
E.VIDEOS = Path(tempfile.mkdtemp()) / "videos"
E.LIXEIRA = E.VIDEOS / "_lixeira"
sys.argv = [sys.argv[0], "4492"]
import servidor as S

falhas = []
a, _ = E.criar_item("igual", texto="a"); E.mexe_ficha(a, etapa="Pauta")
b, _ = E.criar_item("igual", texto="b"); E.mexe_ficha(b, etapa="Animação")
c, _ = E.criar_item("igual", texto="c"); E.mexe_ficha(c, etapa="Publicado")

# 2. o funil leve: só a etapa pedida; "" (um vídeo aberto) só as contagens; sem etapa, tudo (como antes)
tudo, so_pauta, nenhum = E.funil(), E.funil("Pauta"), E.funil("")
if [i["num"] for i in so_pauta["itens"]] != [a] or nenhum["itens"] or len(tudo["itens"]) != 3:
    falhas.append(f"funil por etapa: Pauta={[i['num'] for i in so_pauta['itens']]}, vazio={len(nenhum['itens'])}, tudo={len(tudo['itens'])}")
if so_pauta["contagem"] != tudo["contagem"]:
    falhas.append("as contagens mudaram com o funil por etapa")

# 3. o cartão guardado: sem mudança, não é refeito; mudou um arquivo do vídeo, é refeito
refeitos = []
original = E.blocos
E.blocos = lambda n, *x, **k: (refeitos.append(n), original(n, *x, **k))[1]
E.funil(); E.funil()
if refeitos:
    falhas.append(f"o cartão foi refeito sem nada mudar: {refeitos}")
time.sleep(.01)
E.mexe_ficha(b, passo="prévia pronta")
E.funil()
if refeitos != [b]:
    falhas.append(f"mudou a ficha do #{b} e foram refeitos {refeitos}")
E.blocos = original

# 1. "nada mudou" custa zero: a 2ª resposta igual é 304 sem corpo, também com a impressão que o Caddy marca
def pede(inm=None):
    h = types.SimpleNamespace(headers={"If-None-Match": inm} if inm else {}, wfile=io.BytesIO(), enviados=[], cabecalhos={})
    h.send_response = lambda cod: h.enviados.append(cod)
    h.send_header = lambda k, v: h.cabecalhos.__setitem__(k, v)
    h.end_headers = lambda: None
    S.H._json(h, 200, {"x": 1}, etag=True)
    return h
p1 = pede()
tag = p1.cabecalhos.get("ETag")
p2, p3, p4 = pede(tag), pede("W/" + tag[:-1] + '-gzip"'), pede('"outro"')
if p1.enviados != [200] or not tag or p2.enviados != [304] or p2.wfile.getvalue() or p3.enviados != [304] or p4.enviados != [200]:
    falhas.append(f"ETag: 1ª {p1.enviados}, igual {p2.enviados} ({len(p2.wfile.getvalue())} bytes), do Caddy {p3.enviados}, outro {p4.enviados}")

# 4. a prévia em vídeo só para os ativos: mexido há 3 dias e não aberto não é ativo; aberto agora é
velho, _ = E.criar_item("igual", texto="velho")
E.mexe_ficha(velho, etapa="Animação")
f = E.ler_ficha(velho); f["atualizado"] = "2026-10-01T10:00:00-03:00"
if S.ativo(velho, f):
    falhas.append("vídeo parado há semanas contou como ativo")
S._vistos[int(velho)] = time.time()
if not S.ativo(velho, f):
    falhas.append("vídeo aberto agora na tela não contou como ativo")
if not S.ativo(b):
    falhas.append("vídeo mexido agora não contou como ativo")

if falhas:
    print("FALHOU · " + "; ".join(falhas))
    sys.exit(1)
print("passou · funil por etapa, cartão guardado e refeito só quando muda, 304 quando nada mudou, prévia em vídeo só dos ativos")
