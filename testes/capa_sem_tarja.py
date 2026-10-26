"""Capa sem tarja (23/10/2026, "aprovo o plano capa-sem-tarja"; a capa do #354 saiu com a tarja preta da Veja no alto).
Sem IA: a foto da capa e a capa viva do agente de capa. Roda numa CÓPIA com os vídeos 354 (tarja), 334, 335 e 340 (sem
tarja); sobe um servidor de teste na porta 4497.

  .venv/bin/python testes/capa_sem_tarja.py
"""
import os, sys, tempfile, threading
from pathlib import Path

RAIZ = Path(sys.argv[0]).resolve().parent.parent
sys.path[:0] = [str(RAIZ), str(RAIZ / "ferramentas")]
import estudio as E
assert "/srv/" not in str(E.RAIZ), "rode numa cópia"
sys.argv = [sys.argv[0], "4497"]
import servidor as S
import capa_agente as CA, animacao as A, ver
from http.server import ThreadingHTTPServer
from PIL import Image

S.H.log_message = lambda *a: None
ver.URL = "http://127.0.0.1:4497/item/{n}/previa.html?cru=1"
threading.Thread(target=ThreadingHTTPServer(("127.0.0.1", 4497), S.H).serve_forever, daemon=True).start()
falhas, ok = [], 0
def d(n):                                  # a foto tem que ficar na pasta do vídeo (foto() devolve o caminho relativo)
    p = E.pasta(n) / "animacao/teste-capa"; p.mkdir(parents=True, exist_ok=True); return p


def caso(nome, certo, detalhe=""):
    global ok
    ok += bool(certo)
    if not certo:
        falhas.append(nome)
    print(("PASSOU" if certo else "FALHOU"), "·", nome, "·", str(detalhe)[:170], flush=True)


# 1. a foto da capa do #354 (o Lula do take dos 6 s, o vídeo da Veja com tarja) sai sem a faixa preta
tk354 = CA._takes(354)
f = CA.foto(354, {"t": 6.7, "quem": "Lula"}, tk354, d(354) / "f354.jpg")
fx = A.faixa_preta(d(354) / "f354.jpg") if f else "sem foto"
caso("1 a foto da capa do #354 sai sem tarja", f and fx == [], f"faixa={fx} foto={f and f[1:4]}")

# 2. a capa viva casa com a foto: o vídeo por baixo começa a parte sem tarja no mesmo y da foto
if f:
    fu = CA.fundo({"desenho": "um_rosto"}, [f], E.pasta(354))
    x, y, w, h = CA._caixa(f, 0, 1080, 1120)
    tj = (f[5] or {}).get("tarja") or [0, 0]
    v = fu[0] if fu else {}
    topo_util = v.get("y", 0) + tj[0] * v.get("h", 0)
    caso("2 a capa viva começa a parte sem tarja onde começa a foto", fu and abs(topo_util - y) <= 2 and abs(v.get("h", 0) * (1 - tj[0] - tj[1]) - h) <= 2,
         f"foto y={y} h={h} · vídeo y={v.get('y')} h={v.get('h')} tarja={tj}")

# 3. vídeos sem tarja: a foto é o quadro inteiro, como hoje
for n in (334, 335, 340):
    tk = CA._takes(n)
    if not tk:
        caso(f"3 #{n} igual a hoje", True, "sem take (nada a comparar)"); continue
    t = (tk[0][0] + tk[0][1]) / 2
    r = CA._rosto(E.pasta(n) / tk[0][3], tk[0][2] + (t - tk[0][0]))
    g = CA.foto(n, {"t": t, "quem": ""}, tk, d(n) / f"f{n}.jpg")
    igual = bool(r and g) and (g[1], g[2], tuple(g[3])) == (r[0].shape[1], r[0].shape[0], tuple(r[1]))
    caso(f"3 #{n} sem tarja: a foto é o quadro inteiro, como hoje", igual or not r, f"foto={g and g[1:4]} quadro={r and (r[0].shape[1], r[0].shape[0], r[1])}")

print(f"{ok} de {ok + len(falhas)} · " + ("passou" if not falhas else "FALHOU: " + " | ".join(falhas)))
# 25/10/2026: sai sem esperar o servidor de teste (a linha dele, mandando um vídeo no fim, dava "Broken pipe" e às
# vezes a saída virava erro com "5 de 5 · passou"; a instalação na VPS voltou duas vezes por isso)
sys.stdout.flush(); sys.stderr.flush()
os._exit(1 if falhas else 0)
