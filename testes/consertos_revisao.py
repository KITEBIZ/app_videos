"""Tipo A (sem IA de verdade): os consertos da revisão de 23/10/2026 ("aprovo o plano consertos-da-revisao"). Roda numa
CÓPIA do estúdio que tenha os vídeos 334 (Animação, com T.capa na cena) e 351 (Pauta parada): mexe na ficha e na
conferência deles e sobe um servidor de teste na porta 4497.

  .venv/bin/python testes/consertos_revisao.py
"""
import json, sys, tempfile, threading, time, urllib.request, urllib.error
from pathlib import Path

RAIZ = Path(sys.argv[0]).resolve().parent.parent
sys.path[:0] = [str(RAIZ), str(RAIZ / "ferramentas")]
import estudio as E
assert "/srv/" not in str(E.RAIZ), "este teste mexe nos vídeos: rode numa cópia"
sys.argv = [sys.argv[0], "4497"]
import servidor as S
import olho_unico as O
import animador_novo as AN
from http.server import ThreadingHTTPServer

S.H.log_message = lambda *a: None
S.garantir = lambda n: None                                   # nenhum trabalhador de verdade (nada anima nem grava)
threading.Thread(target=ThreadingHTTPServer(("127.0.0.1", 4497), S.H).serve_forever, daemon=True).start()
O.CHAVE = Path(tempfile.mkdtemp()) / "DESLIGADO"           # o teste nunca toca a chave de verdade
O.registra = lambda *a, **k: None
falhas, ok = [], 0


def caso(nome, certo, detalhe=""):
    global ok
    ok += bool(certo)
    if not certo:
        falhas.append(f"{nome} ({detalhe})")
    print(("PASSOU" if certo else "FALHOU"), "·", nome, "·", str(detalhe)[:140], flush=True)


def post(n, acao, corpo=b"{}"):
    try:
        return urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:4497/api/item/{n}/{acao}", method="POST", data=corpo)).status
    except urllib.error.HTTPError as e:
        return e.code


# 1. erro de código na cena trava a aprovação, também "mesmo assim" (travas.1)
cf = E.pasta(334) / "animacao/conferencia.json"
guardado = cf.read_text() if cf.exists() else None
conf = json.loads(guardado) if guardado else {}
conf["regua"] = [{"tipo": "erro", "msg": "a animação tem erro de código: ReferenceError: x", "de": 0.0, "ate": 0.2}]
cf.write_text(json.dumps(conf))
E.mexe_ficha(334, etapa="Animação", passo="prévia pronta", blocos_regravar=None, ajustar_blocos=None)
cena = E.pasta(334) / "animacao/cena.html"; cena_antes = cena.read_text()
cena.write_text(cena_antes + "\n<!-- T.capa(3) -->\n")           # a capa em número, como manda o ANIMADOR.md
f1, f2 = S.faltas_aprovar(334), S.faltas_aprovar(334, mesmo_assim=True)
cena.write_text(cena_antes)
caso("1a erro na cena (com T.capa) trava a aprovação", any("erro de código" in x for x in f1), f1)
caso("1b nem 'mesmo assim' passa o erro", any("erro de código" in x for x in f2), f2)

# 4. a trava da voz não some quando outro passo vem antes do ajuste do bloco (travas.4)
conf["regua"] = []; cf.write_text(json.dumps(conf))
E.mexe_ficha(334, passo="prévia pronta", blocos_regravar=[3])          # ex.: mudar_capa levou o passo a "prévia pronta"
f = S.faltas_aprovar(334)
caso("4a voz regravada sem ajuste trava a aprovação", any("voz" in x and "3" in x for x in f), f)
E.mexe_ficha(334, passo="voz com problema", esperando=S.VOZ_PROBLEMA, blocos_regravar=[])
st = post(334, "aprovar-voz", b'{"mesmo_assim": true}')
fx = E.ler_ficha(334)
caso("4b 'Ouvi, está ok' sem bloco pede o bloco (não reanima tudo)", st == 409 and fx.get("passo") != S.ANIMANDO, f"status {st} passo {fx.get('passo')}")
E.mexe_ficha(334, passo="prévia pronta", esperando="", blocos_regravar=None)
if guardado is not None:
    cf.write_text(guardado)

# 5a. (a segunda opinião saiu em 26/10/2026; a tela não recebe nada dela)
it = S.item_json(336)
caso("5a sem nada da segunda opinião", "monitor" not in it and "relendo" not in it, str(sorted(it))[:200])

# 5c. tentar-pauta com a mesma conferência do caminho pela mensagem (pauta parada com roteiro não recomeça do zero)
f351 = E.ler_ficha(351)
rot = E.pasta(351) / "ROTEIRO.md"; tinha = rot.exists()
if not tinha:
    rot.write_text("| # | Bloco | Quem | Fala | Tela |\n|---|---|---|---|---|\n| 1 | a | nós | uma fala de teste | x |\n")
st = post(351, "tentar-pauta")
caso("5c tentar-pauta recusa pauta que já tem roteiro", st == 409, f"status {st}")
if not tinha:
    rot.unlink()
E.mexe_ficha(351, passo=f351["passo"], erro=f351.get("erro", ""))

# 5e. segundos ditos de vários jeitos
achados = {t: sorted({float((a or b).replace(",", ".")) for a, b in O.SEGUNDO.findall(t)}) for t in
           ("aos 3 segundos a cabeça", "No segundo 2,3: a cara", "No segundo 11,9:  levantar", "em 12 s e em 14,5s")}
esperado = {"aos 3 segundos a cabeça": [3.0], "No segundo 2,3: a cara": [2.3], "No segundo 11,9:  levantar": [11.9], "em 12 s e em 14,5s": [12.0, 14.5]}
caso("5e segundos reconhecidos", achados == esperado, achados)

# 2. no ajuste o olho não refaz o caderno ali e tem prazo total (olho-unico.13)
feitos = []
O.fazer_caderno = lambda n: (feitos.append((n, threading.current_thread() is threading.main_thread())), time.sleep(30))
(O.pasta(335) / "caderno.json").unlink(missing_ok=True)
AN.opus = lambda *a, **k: (time.sleep(8), ('{"onde": [{"t": 1}], "mudar": "x"}', {"usd": 0}))[1]
O.PRAZO = 3
t0 = time.time(); r = O.localizar(335, "sobe a cabeça dele", next(E.pasta(335).rglob("*.jpg")))
dt = time.time() - t0
caso("2a localizar respeita o prazo total", dt < 6 and r == [], f"{dt:.1f} s, devolveu {r}")
time.sleep(.5)
caso("2b sem caderno: refaz por fora (em thread), não dentro do ajuste", feitos == [(335, False)], f"chamadas de fazer_caderno (vídeo, no fluxo do ajuste?): {feitos}")

# 3. pastas próprias e uma olhada por vídeo, a mais nova (olho-unico.14)
pastas, ao_mesmo, rodando = [], [], [0]
def falso_quadros(num, pasta=None):
    pastas.append(str(pasta)); return [], []
AN.quadros_da_previa = falso_quadros
AN.mosaicos_da_previa = lambda *a, **k: []
O.caderno_atual = lambda n: None
olhadas = []
def falso_olhar(num):
    rodando[0] += 1; ao_mesmo.append(rodando[0]); olhadas.append(time.time()); time.sleep(1.5); rodando[0] -= 1
    return {"defeitos": []}
real_olhar = O.olhar_previa
O.olhar_previa = falso_olhar
th = [threading.Thread(target=O.na_previa, args=(334,)) for _ in range(3)]
for t in th:
    t.start(); time.sleep(.2)
for t in th:
    t.join()
caso("3a uma olhada por vez no mesmo vídeo", max(ao_mesmo) == 1, f"ao mesmo tempo: {max(ao_mesmo)}")
caso("3b três pedidos seguidos dão 2 olhadas (a de agora e a mais nova)", len(olhadas) == 2, f"{len(olhadas)} olhadas")
O.olhar_previa = real_olhar
try:
    O.olhar_previa(334)
except Exception:
    pass
caso("3c o olho usa pasta própria, não a do editor", pastas and all("/olho/" in p for p in pastas) and not any("revisao-" in p for p in pastas), pastas)

print(f"{ok} de {ok + len(falhas)} · " + ("passou" if not falhas else "FALHOU: " + " | ".join(falhas)))
sys.exit(1 if falhas else 0)
