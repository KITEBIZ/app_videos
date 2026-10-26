"""Tipo A (sem IA, sem servidor no ar): a mensagem que cria a pauta aparece no chat do vídeo e não vira pedido pendente
(24/10/2026, ele: "tudo que foi falado com o agente deveria aparecer no chat"; no #369 o pedido "no final... eu não
quero" não estava na conversa). Pasta de vídeos temporária. Calibrado: sem o "inicio" no pendentes, o caso 2 falha."""
import json, sys, tempfile, threading
from pathlib import Path
R = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(R), str(R / "ferramentas")]
import estudio as E
E.VIDEOS = Path(tempfile.mkdtemp()) / "videos"; E.LIXEIRA = E.VIDEOS / "_lixeira"
sys.argv = [sys.argv[0], "4498"]
import servidor as S
from http.server import ThreadingHTTPServer
import urllib.request
S.garantir = lambda n: None                              # nada de pauta de verdade
srv = ThreadingHTTPServer(("127.0.0.1", 4498), S.H); threading.Thread(target=srv.serve_forever, daemon=True).start()
falhas = []
texto = "https://www.instagram.com/reel/TESTE/ No final, tira a parte do patrimônio. No lugar: Siga o Instituto br360."
req = urllib.request.Request("http://127.0.0.1:4498/api/pauta", method="POST", headers={"Content-Type": "application/json"},
                             data=json.dumps({"id": "t1", "tipo": "igual", "texto": texto}).encode())
try:
    num = json.load(urllib.request.urlopen(req))["num"]
except urllib.error.HTTPError as e:
    num = None; falhas.append(f"0: a pauta não foi criada ({e.code}: {e.read()[:200]!r})")
if num:
    msgs = E.chat(num)
    if not any(m["quem"] == "ele" and "patrimônio" in m["texto"] for m in msgs):
        falhas.append("1: a mensagem que criou a pauta não está no chat")
    if E.pendentes(num):
        falhas.append(f"2: a mensagem que criou a pauta virou pedido pendente ({[m['id'] for m in E.pendentes(num)]})")
srv.shutdown()
print("passou · a mensagem que cria a pauta aparece no chat, já atendida" if not falhas else "FALHOU · " + " | ".join(falhas))
sys.exit(1 if falhas else 0)
