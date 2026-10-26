"""pedido-limpo, ensaio real: um pedido do chat numa cópia do #316 pelo caminho novo (maestro, animador, régua, Olhos)."""
import json, shutil, subprocess, sys, threading, time
from pathlib import Path
C = Path("/tmp/ca/limpo/novo"); sys.path[:0] = [str(C), str(C / "ferramentas")]
import estudio as E
T = Path("/tmp/ca/limpo/real"); shutil.rmtree(T, ignore_errors=True); T.mkdir(parents=True)
subprocess.run(["rsync", "-a", "--exclude=animacao/versoes", "--exclude=animacao/chamadas", "--exclude=publicacao",
                "/srv/kitebiz/projetos/conteudo/estudio-v2/videos/316/", f"{T}/316/"], check=True)
E.VIDEOS = T
argv, sys.argv = sys.argv, [sys.argv[0], "4493"]
import servidor as S
sys.argv = argv
from http.server import ThreadingHTTPServer
S.H.log_message = lambda *a: None
srv = ThreadingHTTPServer(("127.0.0.1", 4493), S.H); threading.Thread(target=srv.serve_forever, daemon=True).start()
import ver, capa
ver.URL = "http://127.0.0.1:4493/item/{n}/previa.html?cru=1"; capa.PORTA = 4493
antes = (T / "316/animacao/cena.html").read_text()
msg, _ = E.chat_add(316, "ele", "No bloco 1, deixa o selo CONFIRMADO um pouco maior, sem cobrir o ELE DISSE.", id_msg="ensaio-limpo-1")
E.mexe_ficha(316, etapa="Animação", passo="prévia pronta")
t0 = time.time(); S.maestro_atende(316, msg)
print(f"levou {time.time() - t0:.0f} s; cena mudou: {(T / '316/animacao/cena.html').read_text() != antes}")
for l in (T / "316/historico.jsonl").read_text().splitlines()[-4:]:
    print("histórico:", json.loads(l)["texto"][:220])
r = [m for m in E.chat(316) if m.get("responde") == "ensaio-limpo-1"]
print("RESPOSTA NO CHAT:", r[-1]["texto"] if r else "(nenhuma)")
desde = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(t0 - 2))
g = [x for x in E.gastos(316) if x.get("quando", "")[:19] >= desde]
print("GASTO MEDIDO:", round(sum(x.get("usd") or 0 for x in g), 3), [(x["quem"], round(x.get("usd") or 0, 3)) for x in g])
