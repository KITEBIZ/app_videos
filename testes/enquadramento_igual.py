"""enquadramento-igual: o take em tela cheia do #316 no segundo 4,5, com a cópia leve (prévia) e com o original (final)."""
import shutil, subprocess, sys, threading
from pathlib import Path
COD = Path(sys.argv[1]); sys.path[:0] = [str(COD), str(COD / "ferramentas")]
import os; os.environ.setdefault("GEMINI_API_KEY", "teste")
import estudio as E
E.VIDEOS = Path("/srv/kitebiz/projetos/conteudo/estudio-v2/videos")        # só lê
argv, sys.argv = sys.argv, [sys.argv[0], sys.argv[2]]
import servidor as S
sys.argv = argv
from http.server import ThreadingHTTPServer
S.H.log_message = lambda *a: None
srv = ThreadingHTTPServer(("127.0.0.1", int(sys.argv[2])), S.H); threading.Thread(target=srv.serve_forever, daemon=True).start()
import render
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    nav = p.chromium.launch(); r = {}
    for nome, extra in (("final", ""), ("previa", "&leve=1")):
        pg = nav.new_page(viewport={"width": 1080, "height": 1920})
        pg.goto(f"http://127.0.0.1:{sys.argv[2]}/item/316/previa.html?render=1{extra}"); pg.wait_for_function("!!window.__previa", timeout=60000)
        pg.wait_for_function("[...document.querySelectorAll('video.trecho.take')].every(v => v.readyState >= 1)", timeout=60000)
        pg.evaluate(render.QUADRO_JS, 4.5)
        r[nome] = pg.evaluate("""[...document.querySelectorAll('video.trecho.take')].filter(v => v.src.includes('76Yko'))
            .map(v => [v.videoWidth, parseFloat(v.style.width), parseFloat(v.style.left), parseFloat(v.style.top)])""")
        pg.screenshot(path=f"/tmp/ca/enq2-{Path(sys.argv[1]).name}-{nome}.jpg", type="jpeg", quality=80)
    nav.close()
for nome in r: print(nome, "[largura do arquivo, largura na tela, esquerda, alto]:", r[nome][:2])
igual = r["final"] and r["previa"] and all(abs(a[1] - b[1]) < 1 and abs(a[2] - b[2]) < 1 for a, b in zip(r["final"], r["previa"]))
print(("PASSOU" if igual else "FALHOU"), "· o take sai do mesmo tamanho e no mesmo lugar na prévia e no vídeo final")
