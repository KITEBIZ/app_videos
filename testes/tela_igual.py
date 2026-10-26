"""Tela igual (20/10/2026, "aprovo o plano tela-igual, segunda referência o 305"): confere se uma mudança no tocador
(web/tocador.html) ou nas peças (web/pecas/) mudou o que sai no vídeo. Ideia do HyperFrames (vídeos-modelo a cada
mudança do motor).

  .venv/bin/python testes/tela_igual.py                 refaz os quadros e compara com os modelos
  .venv/bin/python testes/tela_igual.py congelar 304 305    copia a cena e a voz dos vídeos e faz os quadros-modelo
  .venv/bin/python testes/tela_igual.py aceitar         a diferença é de propósito: os quadros de agora viram os modelos

As referências ficam em testes/referencias/<n>/ (cópia do vídeo sem versões, chamadas, fotos de antes/depois e
publicação): editar o vídeo depois não muda a referência. Os quadros saem pelo caminho do vídeo final (?render=1), um a
cada 2 s, por um servidor do estúdio só deste teste (porta 4491, lendo as referências). Só "aceitar" troca os modelos.
"""
import os, shutil, subprocess, sys, threading
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
import estudio as E

REF = RAIZ / "testes/referencias"
SAIDA = RAIZ / "testes/tela_igual"
PORTA = 4491
PASSO = 2.0
FORA = ["animacao/versoes", "animacao/chamadas", "animacao/antes", "animacao/depois", "animacao/folhas-videos",
        "animacao/novo-quadros", "revisao", "publicacao", "anexos", "*.leve.mp4", "gasto.jsonl", "chat.jsonl", "historico.jsonl"]
PIXEL = 32          # diferença por canal acima disto conta como pixel mudado (abaixo é compressão)
QUADRO = 0.001      # mais de 0,1% dos pixels mudados: o quadro mudou


def servidor():
    E.VIDEOS = REF                                  # só neste processo: o estúdio lê as referências
    os.environ.setdefault("GEMINI_API_KEY", "sem-chave-no-teste")      # o import pede; o teste não chama IA nenhuma
    argv, sys.argv = sys.argv, [sys.argv[0], str(PORTA)]                # o servidor lê a porta da linha de comando
    import servidor as S
    sys.argv = argv
    from http.server import ThreadingHTTPServer
    class Srv(ThreadingHTTPServer):
        def handle_error(self, request, client_address):     # o navegador corta pedidos de vídeo ao pular: não é erro
            if not isinstance(sys.exc_info()[1], (ConnectionResetError, BrokenPipeError)):
                super().handle_error(request, client_address)
    S.H.log_message = lambda *a: None
    srv = Srv(("127.0.0.1", PORTA), S.H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    return srv


def quadros(num, pasta):
    """Os quadros a cada PASSO s, como o render.py tira (desenha, espera os trechos chegarem ao tempo, 2 quadros)."""
    from playwright.sync_api import sync_playwright
    shutil.rmtree(pasta, ignore_errors=True); pasta.mkdir(parents=True)
    with sync_playwright() as pw:
        nav = pw.chromium.launch()
        pg = nav.new_page(viewport={"width": 1080, "height": 1920})
        erros = []
        pg.on("pageerror", lambda e: erros.append(str(e)))
        pg.goto(f"http://127.0.0.1:{PORTA}/item/{num}/previa.html?render=1")
        pg.wait_for_function("!!window.__previa && !!window.__sons", timeout=60000, polling=200)
        pg.evaluate("document.fonts.ready.then(() => 0)")
        import render
        render.preparar_trechos(num, pg)              # como o vídeo final: as cópias dos takes prontas antes dos quadros
        fim = float(pg.evaluate("window.__previa.fim"))
        # anda o vídeo inteiro quadro a quadro, como o vídeo final, e fotografa a cada PASSO s. Pulando de 2 em 2 s saía
        # outra coisa: o take mostrava o quadro velho por ~1 s e o plenário do #305 (38 a 46 s) depende do caminho
        # (medido em 20/10: pulo, 0,5 s andando e o vídeo inteiro andando dão três imagens diferentes)
        a_cada = round(PASSO * render.QPS)
        for i in range(int(round(fim * render.QPS))):
            pg.evaluate(render.QUADRO_JS, i / render.QPS)
            if i % a_cada == 0:
                pg.screenshot(path=str(pasta / f"{i / render.QPS:05.1f}.png"), clip={"x": 0, "y": 0, "width": 1080, "height": 1920})
        nav.close()
    return erros


def compara(a, b):
    """Fração dos pixels que mudaram de verdade entre dois quadros."""
    import numpy as np
    from PIL import Image
    x = np.asarray(Image.open(a).convert("RGB"), dtype=np.int16); y = np.asarray(Image.open(b).convert("RGB"), dtype=np.int16)
    if x.shape != y.shape:
        return 1.0
    return float((np.abs(x - y).max(axis=2) > PIXEL).mean())


def lado_a_lado(a, b, saida, rotulo):
    from PIL import Image, ImageDraw
    x, y = Image.open(a).convert("RGB"), Image.open(b).convert("RGB")
    im = Image.new("RGB", (x.width * 2 + 20, x.height + 70), "black"); im.paste(x, (0, 70)); im.paste(y, (x.width + 20, 70))
    d = ImageDraw.Draw(im)
    d.text((20, 20), f"MODELO  ·  {rotulo}", fill="yellow"); d.text((x.width + 40, 20), "AGORA", fill="yellow")
    im.resize((im.width // 3, im.height // 3)).save(saida, quality=85)


def congelar(nums):
    for num in nums:
        orig, dest = E.pasta(num), REF / str(int(num))
        if not (orig / "animacao/cena.html").exists():
            sys.exit(f"#{num} não tem cena")
        shutil.rmtree(dest, ignore_errors=True); dest.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run(["rsync", "-a", *[f"--exclude={f}" for f in FORA], f"{orig}/", f"{dest}/"], check=True)
        print(f"#{num}: referência copiada ({sum(f.stat().st_size for f in dest.rglob('*') if f.is_file()) / 1e6:.0f} MB)")
    servidor()
    for num in nums:
        erros = quadros(num, REF / str(int(num)) / "modelo")
        print(f"#{num}: {len(list((REF / str(int(num)) / 'modelo').glob('*.png')))} quadros-modelo" + (f" · ERROS: {erros}" if erros else ""))


def conferir():
    refs = sorted(p for p in REF.iterdir() if (p / "modelo").is_dir()) if REF.exists() else []
    if not refs:
        sys.exit("sem referências: rode  testes/tela_igual.py congelar 304 305")
    servidor()
    shutil.rmtree(SAIDA, ignore_errors=True); SAIDA.mkdir(parents=True)
    total = mudados = 0
    for r in refs:
        agora = SAIDA / r.name / "agora"
        erros = quadros(r.name, agora)
        for m in sorted((r / "modelo").glob("*.png")):
            total += 1
            a = agora / m.name
            f = compara(m, a) if a.exists() else 1.0
            if f > QUADRO:
                mudados += 1
                lado_a_lado(m, a, SAIDA / f"{r.name}-{m.stem}s.jpg", f"#{r.name} em {m.stem} s · {f:.1%} da tela mudou")
                print(f"MUDOU  #{r.name} em {m.stem} s: {f:.1%} da tela  ->  {SAIDA / f'{r.name}-{m.stem}s.jpg'}")
        if erros:
            print(f"ERRO NA PÁGINA #{r.name}: {'; '.join(erros)[:300]}")
    print(f"\n{'igual' if not mudados else 'DIFERENTE'}: {total - mudados} de {total} quadros iguais")
    return 1 if mudados else 0


def aceitar():
    for r in sorted(p for p in REF.iterdir() if (SAIDA / p.name / "agora").is_dir()):
        shutil.rmtree(r / "modelo"); shutil.copytree(SAIDA / r.name / "agora", r / "modelo")
        print(f"#{r.name}: os quadros de agora viraram os modelos")


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["congelar"]:
        congelar(a[1:] or ["304", "305"])
    elif a[:1] == ["aceitar"]:
        aceitar()
    else:
        sys.exit(conferir())
