"""travas-da-verificacao numa cópia (porta 4494). Voz, animador e vídeo final trocados por falsos: nada grava, anima nem
publica. Cada caso diz PASSOU/FALHOU pelo que tem que acontecer."""
import json, subprocess, sys, threading, time, urllib.request, urllib.error
from pathlib import Path
C = Path(sys.argv[1]).resolve(); sys.path[:0] = [str(C), str(C / "ferramentas")]   # resolve: no Mac /var é atalho de /private/var
import estudio as E
assert str(E.RAIZ) == str(C)
sys.argv = [sys.argv[0], "4494"]
import servidor as S
from http.server import ThreadingHTTPServer
erros_log = []
_orig = S.H.log_message
S.H.log_message = lambda self, fmt, *a: erros_log.append(fmt % a)
srv = ThreadingHTTPServer(("127.0.0.1", 4494), S.H); threading.Thread(target=srv.serve_forever, daemon=True).start()
import ver, render, animacao as A
ver.URL = "http://127.0.0.1:4494/item/{n}/previa.html?cru=1"; render.URL = "http://127.0.0.1:4494/item/{n}/previa.html?render=1"
ok = tot = 0
def caso(nome, certo, detalhe=""):
    global ok, tot
    tot += 1; ok += bool(certo); print(("PASSOU" if certo else "FALHOU"), "·", nome, "·", detalhe, flush=True)
def post(n, acao, corpo=b""):
    try:
        r = urllib.request.urlopen(urllib.request.Request(f"http://127.0.0.1:4494/api/item/{n}/{acao}", method="POST", data=corpo)); return r.status
    except urllib.error.HTTPError as e:
        return e.code
def espera(cond, s=20):
    t0 = time.time()
    while time.time() - t0 < s and not cond(): time.sleep(.3)
    return cond()
# 1. erro de código na cena
cena = E.pasta(334) / "animacao/cena.html"; bom = cena.read_text()
cena.write_text(bom.replace("const seguro = f =>", "const seguro_nao = f =>", 1))
_, probs = ver.regua(334, 0, 5)
caso("1a cena com erro vira problema 'erro' na régua", any(p["tipo"] == "erro" and "seguro" in p["msg"] for p in probs), str([(p["tipo"], p["msg"][:60]) for p in probs][:2]))
try:
    render.quadros(334, Path("/tmp/x.mp4"), lambda p: None); caso("1b vídeo final recusa a cena com erro", False)
except RuntimeError as e:
    caso("1b vídeo final recusa a cena com erro", "erro de código" in str(e), str(e)[:90])
cena.write_text(bom)
# 5. capa: o 'centro vazio aos 0 s' sumiu
_, probs = ver.regua(334, 0, 8)
caso("5 régua ignora o tempo da capa (T.capa com variável)", not any(p["tipo"] == "centro-vazio" and p["ini"] < 1 for p in probs), str([(p["tipo"], p["ini"]) for p in probs][:4]))
# 2. Gravar a voz na Animação regrava só o bloco
chamou = {}
S.voz.gravar = lambda num: chamou.setdefault("voz", num) and {"duracao": 46.0, "problemas": [], "novas": [3]}
S.animacao.animar = lambda num, pedido=None, **k: chamou.setdefault("animar", pedido) and "ok"
E.mexe_ficha(344, etapa="Animação", passo="voz parou", esperando="Gravar a voz", erro="bloco 3: ...", blocos_regravar=[3])
st = post(344, "gravar-voz-de-novo")
espera(lambda: "animar" in chamou)
caso("2 Gravar a voz na Animação regrava e ajusta só o bloco", st == 200 and chamou.get("voz") == 344 and "SÓ o bloco 3" in (chamou.get("animar") or ""),
     f"status {st} · animar: {(chamou.get('animar') or '')[:70]}")
# 3. voz com problema na Animação: aviso, trava de aprovação, Ouvi está ok ajusta o bloco
espera(lambda: E.ler_ficha(344)["passo"] == "prévia pronta")
chamou.clear()
S.voz.gravar = lambda num: {"duracao": 46.0, "problemas": ["bloco 3: a voz disse ..."], "novas": [3]}
S.refazer_bloco(344, [3])
f = E.ler_ficha(344)
caso("3a voz com problema na Animação espera ele", f["esperando"] == "Voz com problema", f"esperando={f['esperando']}")
caso("3b aprovação trava com a voz com aviso", any("voz tem aviso" in x for x in S.faltas_aprovar(344)), str(S.faltas_aprovar(344))[:120])
st = post(344, "aprovar-voz", json.dumps({"mesmo_assim": True}).encode())
espera(lambda: "animar" in chamou)
caso("3c Ouvi, está ok ajusta só o bloco", st == 200 and "SÓ o bloco 3" in (chamou.get("animar") or ""), f"status {st}")
# 4. becos
S.gerar_final = lambda num: chamou.setdefault("final", num) or E.mexe_ficha(num, passo="vídeo final pronto")
E.mexe_ficha(340, etapa="Aguardando", passo="o vídeo final parou", esperando="", erro="teste")
st = post(340, "gerar-final-de-novo"); espera(lambda: "final" in chamou)
caso("4a Gerar o vídeo final de novo", st == 200 and chamou.get("final") == 340, f"status {st}")
S.pauta.rodar = lambda num: chamou.setdefault("pauta", num) or E.mexe_ficha(num, passo="parou")
E.mexe_ficha(351, etapa="Pauta", passo="parou")
st = post(351, "tentar-pauta"); espera(lambda: "pauta" in chamou)
caso("4b Tentar a pauta de novo", st == 200 and chamou.get("pauta") == 351, f"status {st}")
caso("4c recusa fora do caso", post(336, "tentar-pauta") == 409 and post(336, "gerar-final-de-novo") == 409)
# 6. HEAD
n0 = len(erros_log)
r = subprocess.run(["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", "-I", "http://127.0.0.1:4494/"], capture_output=True, text=True).stdout
caso("6 HEAD responde 200 e o registro não quebra", r == "200", f"HEAD {r} · linhas novas no registro: {erros_log[n0:]}")
print(f"{ok}/{tot} casos")
