"""Faixa preta e conferência do pedido (23/10/2026, "aprovo o plano conferir-o-pedido-e-faixa-preta"; #354: a faixa
preta do vídeo de origem ficou na tela depois de dois ajustes, 182 → 106 → 0 px, e ninguém conferiu). Roda numa CÓPIA
com os vídeos 354, 334, 335, 340, 344 e 356 e os quadros-gabarito em testes/faixa_preta/ (antes-6.7.jpg: 182 px de
faixa; depois-6.7.jpg: 0 px). Sobe um servidor de teste na porta 4495; a IA é fingida.

  .venv/bin/python testes/faixa_preta.py
"""
import os
import json, shutil, sys, threading
from pathlib import Path

RAIZ = Path(sys.argv[0]).resolve().parent.parent
sys.path[:0] = [str(RAIZ), str(RAIZ / "ferramentas")]
import estudio as E
assert "/srv/" not in str(E.RAIZ), "este teste mexe na cena do #354: rode numa cópia"
sys.argv = [sys.argv[0], "4495"]
import servidor as S
import animacao as A, animador_novo as AN, olho_unico as O, ver
from http.server import ThreadingHTTPServer

S.H.log_message = lambda *a: None
ver.URL = "http://127.0.0.1:4495/item/{n}/previa.html?cru=1"
threading.Thread(target=ThreadingHTTPServer(("127.0.0.1", 4495), S.H).serve_forever, daemon=True).start()
O.registra = lambda *a, **k: None
import tempfile
O.CHAVE = Path(tempfile.mkdtemp()) / "DESLIGADO"                # o olho ligado no teste, sem tocar a chave de verdade
G = RAIZ / "testes/faixa_preta"
falhas, ok = [], 0


def caso(nome, certo, detalhe=""):
    global ok
    ok += bool(certo)
    if not certo:
        falhas.append(nome)
    print(("PASSOU" if certo else "FALHOU"), "·", nome, "·", str(detalhe)[:160], flush=True)


def tenta(f, *a):
    try:
        return f(*a)
    except Exception as ex:
        return f"ERRO {type(ex).__name__}: {ex}"


# 1. a tarja do vídeo de origem, medida sem IA
t354 = tenta(lambda: A.tarja_do_video(E.pasta(354) / "referencia/video.mp4", 18.45, 2.07))
caso("1a acha a tarja do #354 no trecho do take dos 6,7 s (~600 px em cima, de 1920)", isinstance(t354, (list, tuple)) and t354[0] > .2, t354)
limpos = {n: tenta(lambda n=n: A.tarja_do_video(E.pasta(n) / "referencia/video.mp4")) for n in (334, 335, 340, 344, 356)}
caso("1b nenhum alarme nos vídeos sem tarja", all(isinstance(v, (list, tuple)) and v[0] == 0 and v[1] == 0 for v in limpos.values()), limpos)

# 2. a faixa preta na tela, medida sem IA (o fundo azul-marinho não é preto)
faixa = lambda q: A.faixa_preta(q)
fa = tenta(faixa, G / "antes-6.7.jpg"); fd = tenta(faixa, G / "depois-6.7.jpg"); ff = tenta(faixa, A.FUNDO_TELA)
caso("2a mede a faixa de 182 px no quadro de antes", isinstance(fa, list) and fa and 150 <= fa[0][1] - fa[0][0] <= 210, fa)
caso("2b nada no quadro consertado nem no fundo azul", fd == [] and ff == [], f"depois={fd} fundo={ff}")

# 3. a régua acusa a faixa como grave
real_perc, real_regua = ver.percorrer, ver.regua
ver.percorrer = lambda num, passo=.5, saida=None, **k: (8.0, [(6.5, G / "antes-6.7.jpg"), (7.0, G / "antes-6.7.jpg")], [])
ver.regua = lambda *a, **k: (0, [])
r = tenta(A._regua_inteira, 354)
ver.percorrer, ver.regua = real_perc, real_regua
fx = [x for x in r if isinstance(x, dict) and x.get("tipo") == "faixa-preta"] if isinstance(r, list) else r
caso("3a a régua acusa faixa preta aos 6,5 s", isinstance(fx, list) and fx and fx[0]["de"] == 6.5, fx)
caso("3b faixa preta é grave (volta sozinha ao animador)", AN.grave({"tipo": "faixa-preta", "msg": ""}))

# 4. o take sem faixa, sem ninguém pedir: a cena das 14:04 (cheia: true, antes dos dois ajustes)
cena = E.pasta(354) / "animacao/cena.html"; guardada = cena.read_text()
shutil.copy(E.pasta(354) / "animacao/versoes/cena-20261023-140405.html", cena)
quadros = tenta(lambda: ver.quadros(354, [6.2, 6.7, 7.2], saida=Path("/tmp/fp/q354"))[0])
cena.write_text(guardada)
med = [tenta(faixa, q) for q in quadros] if isinstance(quadros, list) else quadros
caso("4 a peça de take corta a tarja sozinha (6,2 · 6,7 · 7,2 s sem faixa)", isinstance(med, list) and all(m == [] for m in med), med)

# 5. conferir o pedido depois do conserto
real_q, real_opus = ver.quadros, AN.opus
AN.opus = lambda *a, **k: ('{"atendido": "sim", "faltou": ""}', {"usd": 0})
ver.quadros = lambda num, tempos, saida=None: ([G / "antes-6.7.jpg" for _ in tempos], [])
c1 = tenta(getattr(O, "conferir_pedido", lambda *a: "não existe"), 354, "No segundo 6,7 ainda tem uma faixa preta no topo")
ver.quadros = lambda num, tempos, saida=None: ([G / "depois-6.7.jpg" for _ in tempos], [])
c2 = tenta(getattr(O, "conferir_pedido", lambda *a: "não existe"), 354, "No segundo 6,7 ainda tem uma faixa preta no topo")
c3 = tenta(getattr(O, "conferir_pedido", lambda *a: "não existe"), 354, "sobe o rosto dele")
ver.quadros, AN.opus = real_q, real_opus
caso("5a com a faixa na tela, o programa vence a IA: parcial", isinstance(c1, dict) and c1.get("atendido") == "parcial" and "faixa preta" in str(c1.get("faltou")), c1)
caso("5b sem a faixa e a IA dizendo sim: atendido", isinstance(c2, dict) and c2.get("atendido") == "sim", c2)
caso("5c pedido sem segundo: não confere (nada a medir)", c3 == {}, c3)
fr = tenta(getattr(O, "frase_conferida", lambda *a: "não existe"), "Subi o vídeo do Lula.", {"atendido": "parcial", "faltou": "a faixa preta continua aos 6,7 s"})
caso("5d a resposta começa com 'Parcial:'", isinstance(fr, str) and fr.startswith("Parcial:") and "Subi o vídeo" in fr, fr)

print(f"{ok} de {ok + len(falhas)} · " + ("passou" if not falhas else "FALHOU: " + " | ".join(falhas)))
# 25/10/2026: sai sem esperar o servidor de teste (como o capa_sem_tarja: "11 de 11 · passou" virava erro na saída)
sys.stdout.flush(); sys.stderr.flush()
os._exit(1 if falhas else 0)
