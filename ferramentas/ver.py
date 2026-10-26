"""Os olhos do animador (estúdio v2, 16/10/2026, "aprovo o plano v2-parte3-animacao").

  python3 ver.py <número> --blocos         um quadro no meio de cada bloco
  python3 ver.py <número> 3.5 12 20.2      quadros nesses segundos
  python3 ver.py <número> --regua          mede a prévia inteira com a régua de layout da v1 e lista os problemas
  python3 ver.py <número> --capa           tira a foto das capas (animacao/capa-N.jpg e o recorte 3:4 capa-N-grade.jpg)
  python3 ver.py <número> --rostos <vídeo> 10 quadros do vídeo (relativo à pasta) em animacao/rostos/, para a capa
  python3 ver.py <número> --fotos <vídeo>  1 quadro por segundo sem os repetidos + folha.jpg, em <pasta do vídeo>/quadros/

Os quadros (1080x1920, como no celular) vão para videos/<número>/animacao/quadros/ e o caminho de cada um é impresso:
o animador abre com Read e vê o que fez. A prévia é a que o estúdio serve (http://127.0.0.1:4400/item/<n>/previa.html).
"""
import json, sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ)); sys.path.insert(0, str(RAIZ / "ferramentas"))
import estudio as E

URL = "http://127.0.0.1:4400/item/{n}/previa.html?cru=1"


def quadros(num, tempos, saida=None):
    from playwright.sync_api import sync_playwright
    d = Path(saida) if saida else E.pasta(num) / "animacao/quadros"
    d.mkdir(parents=True, exist_ok=True)
    feitos = []
    with sync_playwright() as p:
        nav = p.chromium.launch()
        pg = nav.new_page(viewport={"width": 1080, "height": 1920})
        erros = []
        pg.on("pageerror", lambda e: erros.append(str(e)))
        pg.goto(URL.format(n=num))
        pg.wait_for_function("!!window.__previa", timeout=30000, polling=200)
        pg.evaluate("document.fonts.ready")
        for t in tempos:
            pg.evaluate(f"() => {{ window.__previa.desenha({float(t)}); return 0; }}")
            pg.wait_for_timeout(350)
            arq = d / f"t{float(t):05.1f}.png"
            pg.screenshot(path=str(arq), clip={"x": 0, "y": 0, "width": 1080, "height": 1920})
            feitos.append(arq)
        nav.close()
    return feitos, erros


# 21/10/2026 (olhos-enxergam-rosto; o Boulos aos 13 s do #306 saiu como o começo do reel, Flávio e Lula, em 1 de 3
# rodadas): "pronto" não bastava; o take que ainda não tinha carregado não pulava e ficava pronto no começo do arquivo.
# Agora desenha de novo até cada take visível estar no ponto do corte (até 4 s) e espera ele mostrar o quadro novo.
NO_PONTO = """async (t) => {
  const dentro = v => v.dataset.ini !== undefined && t >= +v.dataset.ini && t < +v.dataset.fim;
  const alvo = v => +(v.dataset.corte || 0) + (t - +v.dataset.ini), ate = performance.now() + 4000;
  let vs = [];
  for (;;) {
    window.__previa.desenha(t);
    vs = [...document.querySelectorAll('video.trecho')].filter(dentro);
    if (vs.every(v => !v.seeking && v.readyState >= 2 && Math.abs(v.currentTime - alvo(v)) < .3) || performance.now() > ate) break;
    await new Promise(r => setTimeout(r, 30));
  }
  await Promise.all(vs.map(v => Promise.race([new Promise(r => v.requestVideoFrameCallback ? v.requestVideoFrameCallback(() => r()) : r()),
                                              new Promise(r => setTimeout(r, 150))])));
  return vs.every(v => Math.abs(v.currentTime - alvo(v)) < .3);
}"""


def percorrer(num, passo=.5, saida=None, espera=60, paralelo=3):
    """A prévia inteira, do 0 ao fim de verdade (window.__previa.fim: com a assinatura, que vem depois da voz), um quadro
    a cada `passo` s e o último 0,3 s antes do fim (17/10/2026, "aprovo o plano olhos-na-animacao": a segunda opinião
    parava antes da assinatura e dizia que ela faltava). Em JPG e esperando os takes chegarem ao ponto
    (animacao-sem-buraco: com espera fixa de 150 ms o take saía desbotado ou no quadro errado; PNG com 350 ms levava
    106 s no #204). 20/10/2026 (ele: "pode acelerar a folha de quadros também"; ~50 s antes de cada ajuste): os quadros
    saem de `paralelo` navegadores ao mesmo tempo, cada um com um pedaço do vídeo. Devolve (fim, [(t, jpg)], erros)."""
    from concurrent.futures import ThreadPoolExecutor
    from playwright.sync_api import sync_playwright
    d = Path(saida) if saida else E.pasta(num) / "animacao/quadros"
    d.mkdir(parents=True, exist_ok=True)

    def abre(p, erros):
        nav = p.chromium.launch()
        pg = nav.new_page(viewport={"width": 1080, "height": 1920})
        pg.on("pageerror", lambda e: erros.append(str(e)))
        pg.goto(URL.format(n=num))
        pg.wait_for_function("!!window.__previa", timeout=30000, polling=200)
        pg.evaluate("document.fonts.ready")
        return nav, pg

    def tira(tempos, pg, erros):
        feitos = []
        for t in tempos:
            if not pg.evaluate(NO_PONTO, float(t)):
                erros.append(f"take não chegou ao ponto aos {t:.1f} s")
            pg.wait_for_timeout(espera)
            arq = d / f"t{t:06.2f}.jpg"
            pg.screenshot(path=str(arq), type="jpeg", quality=80, clip={"x": 0, "y": 0, "width": 1080, "height": 1920})
            feitos.append((t, arq))
        return feitos

    def pedaco(tempos):            # cada pedaço no seu navegador (o playwright síncrono é um por thread)
        erros = []
        with sync_playwright() as p:
            nav, pg = abre(p, erros)
            try:
                return tira(tempos, pg, erros), erros
            finally:
                nav.close()

    erros = []
    with sync_playwright() as p:          # o primeiro navegador diz o fim e já tira o primeiro pedaço
        nav, pg = abre(p, erros)
        fim = float(pg.evaluate("window.__previa.fim"))
        tempos = [round(k * passo, 2) for k in range(int((fim - .3) / passo) + 1)]
        if fim - .3 - tempos[-1] > .05:
            tempos.append(round(fim - .3, 2))
        k = max(1, min(paralelo, len(tempos) // 10))
        partes = [tempos[i * len(tempos) // k:(i + 1) * len(tempos) // k] for i in range(k)]
        with ThreadPoolExecutor(max_workers=k) as ex:
            outros = [ex.submit(pedaco, pt) for pt in partes[1:]]
            feitos = tira(partes[0], pg, erros)
            for f in outros:
                fe, er = f.result()
                feitos += fe; erros += er
        nav.close()
    return fim, sorted(feitos), erros


def meios(num, onde=0.5):
    """Um instante por bloco: `onde` = 0,5 é o meio; 0,85 é quando a cena do bloco já se montou (a conferência usa este:
    no meio, o carimbo e o número que entram no fim da fala ainda não aparecem)."""
    c = json.loads((E.pasta(num) / "narracao/completo.json").read_text())
    return [(b["n"], round(b["ini"] + onde * (b["fim"] - b["ini"]), 1)) for b in c["blocos"]]


def rostos(num, video, n=10):
    """10 quadros espalhados pelo vídeo (fora do 5% do começo e do fim), para escolher o rosto da capa."""
    import subprocess
    p = E.pasta(num); arq = (p / video).resolve()
    if not str(arq).startswith(str(p.resolve()) + "/") or not arq.is_file():
        raise SystemExit(f"o vídeo {video} não está na pasta do #{num}")
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(arq)],
                               capture_output=True, text=True).stdout.strip() or 0)
    d = p / "animacao/rostos"; d.mkdir(parents=True, exist_ok=True)
    feitos = []
    for k in range(n):
        t = dur * (.05 + .9 * k / max(1, n - 1))
        saida = d / f"r{k + 1:02d}.jpg"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", f"{t:.2f}", "-i", str(arq), "-frames:v", "1", "-q:v", "2", str(saida)])
        if saida.exists():
            feitos.append(f"{saida} ({t:.1f} s)")
    return feitos


def fotos(num, video, passo=1.0, maximo=90):
    """18/10/2026 (ele: "da permissão para o agente baixar fotos"): as fotos de um vídeo baixado, para o agente do chat
    VER o que ele mandou. Um quadro a cada `passo` s, sem os quase iguais ao anterior (foto parada vira um quadro só),
    em <pasta do vídeo>/quadros/q<seg>.jpg, e uma folha com todos numerados pelo segundo (quadros/folha.jpg)."""
    import subprocess
    from PIL import Image, ImageChops, ImageDraw, ImageStat
    p = E.pasta(num); arq = (p / video).resolve()
    if not str(arq).startswith(str(p.resolve()) + "/") or not arq.is_file():
        raise SystemExit(f"o vídeo {video} não está na pasta do #{num}")
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(arq)],
                               capture_output=True, text=True).stdout.strip() or 0)
    d = arq.parent / "quadros"; d.mkdir(exist_ok=True)
    for velho in d.glob("q*.jpg"):
        velho.unlink()
    # vídeo longo: o passo cresce para cobrir até o fim (no reel de 166 s do #300, 1 por segundo parava em 99 s)
    passo = max(passo, dur / maximo)
    feitos, anterior, t = [], None, passo / 2
    while t < dur and len(feitos) < maximo:
        saida = d / f"q{t:05.1f}.jpg"
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-ss", f"{t:.2f}", "-i", str(arq), "-frames:v", "1",
                        "-vf", "scale=540:-2", "-q:v", "3", str(saida)])
        if saida.exists():
            peq = Image.open(saida).convert("L").resize((48, 85))
            if anterior is not None and ImageStat.Stat(ImageChops.difference(peq, anterior)).mean[0] < 6:
                saida.unlink()                      # igual ao anterior: a mesma foto parada
            else:
                feitos.append((t, saida))
            anterior = peq
        t += passo
    if feitos:
        col, lw = 6, 180
        lh = round(lw * Image.open(feitos[0][1]).height / Image.open(feitos[0][1]).width)
        folha = Image.new("RGB", (col * lw, -(-len(feitos) // col) * (lh + 28)), (16, 16, 20))
        dr = ImageDraw.Draw(folha)
        for k, (t, q) in enumerate(feitos):
            x, y = k % col * lw, k // col * (lh + 28)
            folha.paste(Image.open(q).resize((lw, lh)), (x, y + 28))
            dr.text((x + 6, y + 6), f"{t:.1f} s", fill="white")
        folha.save(d / "folha.jpg", quality=85)
    return [f"{q} ({t:.1f} s)" for t, q in feitos] + ([str(d / "folha.jpg")] if feitos else [])


def sons(num):
    """Os sons que a cena marcou (T.som) e, para cada um, a animação que começa mais perto dele (16/10/2026, v2-som)."""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        nav = p.chromium.launch()
        pg = nav.new_page(viewport={"width": 1080, "height": 1920})
        pg.goto(URL.format(n=num).replace("?cru=1", "?sons=1"))
        pg.wait_for_function("!!window.__previa && !!window.__sons", timeout=30000, polling=200)
        r = pg.evaluate(r"""() => {
          const tl = window.__timelines.main, inicios = [];
          for (const c of tl.getChildren(true, true, false)) {
            const alvo = (c.targets ? c.targets() : []).map(e => e.getAttribute && (e.getAttribute('class') || e.id) || '').filter(Boolean)[0] || '';
            if (/^l[bw]\d/.test(alvo) || alvo === 'fundo-faixas' || !alvo) continue;     // legenda e fundo não contam
            inicios.push([c.startTime(), alvo]);
          }
          return window.__sons.lista.map(s => { let m = null;
            for (const [t, a] of inicios) if (!m || Math.abs(t - s.t) < Math.abs(m[0] - s.t)) m = [t, a];
            return {som: s.som, t: s.t, peca: m ? m[1] : '', dist: m ? Math.abs(m[0] - s.t) : null}; });
        }""")
        nav.close()
    return r


def regua(num, de=0.0, ate=None, **kw):
    """A régua da v1 na prévia; de/ate (segundos) medem só um trecho (17/10/2026, animacao-rapida); kw: prefixo, limpar."""
    import regua as R
    dur, probs = R.medir(str(E.pasta(num)), de=de, ate=ate, url=URL.format(n=num), **kw)
    return dur, probs


def assistir(num):
    """Os olhos do animador (18/10/2026, "aprovo o plano olhos-do-animador"; ele: "a gente poderia dar olhos para o
    animador. separado do analisador para ele poder ver como uma pessoa o que esta sendo criado"): a prévia inteira numa
    folha de contato (1 quadro por segundo, com o segundo e a fala), a tela vazia e a régua medidas, e a opinião dos
    Olhos (chamada própria, Sonnet; a conferência final do estúdio é outra chamada, no Opus). Imprime tudo."""
    import shutil
    import animacao as A
    from PIL import Image, ImageDraw, ImageFont
    p = E.pasta(num)
    olhar = A.assistir_previa(num, modelo="sonnet", quem="olhos do animador")
    ws = json.loads((p / "narracao/palavras.json").read_text()) if (p / "narracao/palavras.json").exists() else []
    import celular            # cada quadro como fica no celular (celular-e-zona-segura, 18/10/2026)
    um_por_seg = [(t, celular.simular(q, q.with_name(q.stem + "-cel.png"), zona=False)) for t, q in olhar["quadros"] if abs(t - round(t)) < 1e-6]
    col, lw, lh, rot = 8, 180, 390, 46
    linhas = (len(um_por_seg) + col - 1) // col
    folha = Image.new("RGB", (col * lw, linhas * (lh + rot)), "white")
    d = ImageDraw.Draw(folha)
    try:
        fonte = ImageFont.truetype(str(E.RAIZ / "web/fontes/impact.ttf"), 15)
    except Exception:
        fonte = None
    for i, (t, q) in enumerate(um_por_seg):
        x, y = (i % col) * lw, (i // col) * (lh + rot)
        folha.paste(Image.open(q).convert("RGB").resize((lw, lh)), (x, y))
        fala = " ".join(w[2] for w in ws if w[0] < t + 1 and w[1] > t)
        d.text((x + 3, y + lh + 2), f"{int(t)} s  {fala[:24]}", fill="black", font=fonte)
        d.text((x + 3, y + lh + 22), fala[24:50], fill="black", font=fonte)
    # cada rodada na sua pasta, sem apagar as anteriores (18/10/2026, "aprovo o plano olhos.10")
    destino = A.pasta_rodada(num)
    folha.save(destino / "folha.jpg", quality=82)
    shutil.rmtree(p / "animacao/olhar", ignore_errors=True)
    _, probs = regua(num)
    op = olhar["olhos"]
    (destino / "rodada.json").write_text(json.dumps({"quando": E.agora(), "quem": "olhos do animador", "fim": round(olhar["fim"], 2),
                                                     "vazios": olhar["vazios"], "regua": probs, "olhos": op}, ensure_ascii=False, indent=1))
    print(f"FOLHA DE CONTATO (1 quadro por segundo, abra com Read): {destino / 'folha.jpg'}")
    print(f"vídeo até {olhar['fim']:.1f} s (com a assinatura)")
    print("TELA VAZIA: " + ("; ".join(f"{v['de']:.1f}-{v['ate']:.1f} s" for v in olhar["vazios"]) or "nenhuma"))
    print(f"RÉGUA: {len(probs)} problema(s)" + "".join(f"\n- {x['ini']:.1f} s · {x['tipo']} · {x['msg']}" for x in probs))
    print(f"OLHOS (um espectador que não sabe nada do roteiro): nota {op.get('nota_para_segurar')}/10 · entendeu: {op.get('entendi', op.get('erro', ''))}")
    print("3 primeiros segundos: " + str(op.get("primeiros_3s", "")))
    for x in op.get("perderia_atencao") or []:
        print(f"- perderia a atenção em {x.get('t')} s: {x.get('porque')}")


if __name__ == "__main__":
    a = sys.argv[1:]
    num = int(a[0])
    if "--capa" in a:                    # 16/10/2026, "aprovo o plano v2-capa"
        import capa
        feitos, erros = capa.fotos(num)
        for arq in feitos:
            print(arq)
        for e in erros:
            print("ERRO NA PÁGINA:", e)
        sys.exit(0)
    if "--rostos" in a:
        print("\n".join(map(str, rostos(num, a[a.index("--rostos") + 1]))))
        sys.exit(0)
    if "--fotos" in a:
        print("\n".join(fotos(num, a[a.index("--fotos") + 1])))
        sys.exit(0)
    if "--sons" in a:
        lista = sons(num)
        print(f"{len(lista)} som(ns)")
        for s in lista:
            print(f"- {s['t']:.2f} s · {s['som']} · peça mais perto: {s['peca']} ({s['dist']:.2f} s)" if s["dist"] is not None else f"- {s['t']:.2f} s · {s['som']} · nenhuma peça")
        sys.exit(0)
    if "--assistir" in a:                # 18/10/2026, "aprovo o plano olhos-do-animador"
        assistir(num)
        sys.exit(0)
    if "--regua" in a:
        dur, probs = regua(num)
        print(f"régua: {len(probs)} problema(s) em {dur:.1f} s")
        for p in probs:
            print(f"- {p['ini']:.2f}-{p['fim'] + 0.25:.2f} s · {p['tipo']} · {p['msg']} · {E.pasta(num) / p['quadro']}")
        sys.exit(0)
    if "--blocos" in a:
        alvo = meios(num)
        feitos, erros = quadros(num, [t for _, t in alvo])
        for (n, t), arq in zip(alvo, feitos):
            print(f"bloco {n} ({t} s): {arq}")
    else:
        feitos, erros = quadros(num, [float(x) for x in a[1:]])
        for arq in feitos:
            print(arq)
    for e in erros:
        print("ERRO NA PÁGINA:", e)
