"""O vídeo final (estúdio v2, 16/10/2026, "aprovo o plano v2-parte4-publicar").

  python3 render.py <número>

Sai publicacao/final.mp4 (1080x1920, 30 quadros/s, h264 + aac, -14 LUFS) com:
  - 1 s da capa escolhida no começo (v1: capa_no_inicio 1.0), em silêncio;
  - a animação quadro a quadro, tirada da prévia (?render=1: o trecho de vídeo vai ao tempo exato em cada quadro);
  - o som como a prévia toca: a voz, a trilha da v1 (0,45 com rampa; 0,33 sob a fala) e os efeitos (T.som / peças).
Depois confere como a v1 (checagem.py conferir): duração, volume, quadros parados, 9:16, codecs; grava
publicacao/final.json. A porcentagem vai para a ficha (a tela mostra "Gerando o vídeo final… N%").
"""
import json, os, re, shutil, subprocess, sys, tempfile, threading
from pathlib import Path
from urllib.parse import urlparse

import numpy as np

import estudio as E

QPS = 30
SR = 44100
URL = "http://127.0.0.1:4400/item/{n}/previa.html?render=1"
TRILHA = {"base": .45, "sob_a_voz": .33, "sobe": 1.2, "desce": 2.0}     # o mesmo do web/tocador.html
CAPA_S = 1.0
_quadros_trava = threading.Lock()
# desenha o quadro t e espera os trechos que pularam terem o quadro certo pronto para mostrar (até 5 s). 20/10/2026: era
# "até o 'seeked' ou 1,5 s"; o 1º pulo de um take às vezes passava de 1,5 s e o quadro saía com o tempo antigo
# (tela_igual, #304 em 4 s, 2 de 3 rodadas). testes/tela_igual.py usa este mesmo texto.
# Pronto não basta: o vídeo já estava no tempo certo e a foto saía com o quadro anterior na tela (medido: 2,61 s,
# readyState 4); por isso espera também o aviso do vídeo de que mostrou o quadro novo (requestVideoFrameCallback).
QUADRO_JS = """async (t) => {
  const mostrou = new Map();
  for (const v of document.querySelectorAll('video.trecho'))
    if (v.requestVideoFrameCallback) mostrou.set(v, new Promise(r => v.requestVideoFrameCallback(() => r())));
  window.__previa.desenha(t);
  const vs = [...document.querySelectorAll('video.trecho')].filter(v => v.seeking);
  await Promise.all(vs.map(v => new Promise(r => { const ate = performance.now() + 5000;
    (function olha() { if ((!v.seeking && v.readyState >= 2) || performance.now() > ate) r(); else setTimeout(olha, 5); })(); })));
  await Promise.all(vs.map(v => Promise.race([mostrou.get(v) || 0, new Promise(r => setTimeout(r, 1000))])));
  await new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r))); return 0; }"""


def video_quadro(arq):
    """20/10/2026 ("aprovo o plano render-rapido"): o take baixado vem em VP9, pesado para pular quadro a quadro (no #304,
    283 s dos 431 s do vídeo final eram os trechos indo ao tempo certo). O vídeo final lê uma cópia H.264 com um quadro
    inteiro a cada 15 (medido: 105 -> 19 ms por quadro; a imagem final com SSIM 0,997), feita uma vez e guardada ao lado
    (<nome>.quadro.mp4; publicar.limpar apaga depois do post). O original não muda."""
    if arq.name.endswith((".quadro.mp4", ".leve.mp4")):
        return arq
    q = arq.with_name(arq.stem + ".quadro.mp4")
    with _quadros_trava:
        if not q.exists() or q.stat().st_mtime < arq.stat().st_mtime:
            tmp = q.with_name(q.stem + ".tmp.mp4")
            r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(arq), "-an", "-c:v", "libx264", "-preset", "veryfast",
                                "-crf", "16", "-g", "15", "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(tmp)],
                               capture_output=True, timeout=1800)
            if r.returncode or not tmp.exists():
                tmp.unlink(missing_ok=True)
                return arq
            os.replace(tmp, q)
    return q


def preparar_trechos(num, pg):
    """Faz as cópias .quadro.mp4 dos trechos que a página pede antes de começar os quadros, e recarrega a página se
    alguma era nova (o vídeo não fica pela metade enquanto a cópia sai). Devolve quantas cópias foram feitas agora."""
    p = E.pasta(num).resolve(); novas = 0
    for s in pg.evaluate("[...document.querySelectorAll('video.trecho')].map(v => v.getAttribute('src') || '')"):
        caminho = urlparse(s).path                    # o tocador pede "<take>.mp4?quadro=1": o caminho é o do original
        arq = (p / caminho).resolve()
        if not caminho.endswith(".mp4") or not str(arq).startswith(str(p) + "/") or not arq.is_file():
            continue
        leve = "leve=1" in s                           # a prévia em vídeo pede as cópias leves (servidor.video_leve)
        q = arq.with_name(arq.stem + (".leve.mp4" if leve else ".quadro.mp4"))
        if not q.exists() or q.stat().st_mtime < arq.stat().st_mtime:
            if leve:
                import servidor
                servidor.video_leve(arq)
            else:
                video_quadro(arq)
            novas += 1
    if novas:
        pg.reload()
        pg.wait_for_function("!!window.__previa && !!window.__sons", timeout=60000, polling=200)
        pg.evaluate("document.fonts.ready.then(() => 0)")
    # todo trecho aberto (com a duração lida) antes do 1º quadro: sem isso o desenha não leva o vídeo ao tempo e o 1º
    # quadro do take saía com o começo do vídeo (medido no tela_igual, #304 em 4 s)
    pg.evaluate("Promise.all([...document.querySelectorAll('video.trecho')].map(v => v.readyState >= 1 ? 0 : "
                "new Promise(r => { v.preload = 'auto'; v.addEventListener('loadedmetadata', r, {once: true}); v.load(); setTimeout(r, 60000); })))")
    return novas


def _som(arq, dur=None):
    """Decodifica um áudio para mono float32 a 44,1 kHz."""
    cmd = ["ffmpeg", "-v", "error", "-i", str(arq), "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"]
    return np.frombuffer(subprocess.run(cmd, capture_output=True, check=True).stdout, dtype=np.float32).copy()


def mixar(num, fim, sons, palavras, saida, capa_s=None):
    """A mistura como a prévia toca (web/tocador.html: agendarSons e volTrilha), com o silêncio da capa na frente
    (capa_s; sem ele, CAPA_S do vídeo final; a prévia em vídeo usa 0)."""
    capa_s = CAPA_S if capa_s is None else capa_s
    p = E.pasta(num); web = E.RAIZ / "web/sons"
    n = int(round(fim * SR))
    mix = np.zeros(n, dtype=np.float32)
    voz = _som(p / "narracao/completo.mp3"); mix[:min(n, len(voz))] += voz[:n]
    # trilha própria do vídeo (24/10/2026, ele: "a musica no inicio não é uma musica de documentario"); sem ela, a de sempre
    tr = _som(p / "animacao/trilha.mp3") if (p / "animacao/trilha.mp3").exists() else _som(web / "trilha.mp3")
    tr = np.tile(tr, int(np.ceil(n / len(tr))))[:n]
    # envelope da trilha a 100 por segundo: rampa de entrada e saída, e abaixa onde a voz fala
    t = np.arange(0, fim, .01)
    falando = np.zeros_like(t, dtype=bool)
    for w in palavras:
        falando |= (t >= w[0] - .12) & (t <= w[1] + .2)
    rampa = np.minimum(1, np.minimum(t / TRILHA["sobe"], np.maximum(0, (fim - t) / TRILHA["desce"])))
    alvo = TRILHA["base"] * rampa * np.where(falando, TRILHA["sob_a_voz"], 1.0)
    ganho = np.copy(alvo)                      # o tocador suaviza com setTargetAtTime(.08): o mesmo aqui
    k = 1 - np.exp(-.01 / .08)
    for i in range(1, len(ganho)):
        ganho[i] = ganho[i - 1] + (alvo[i] - ganho[i - 1]) * k
    mix += tr * np.interp(np.arange(n) / SR, t, ganho).astype(np.float32)
    cache = {}
    for s in sons:
        if s["som"] not in cache:
            cache[s["som"]] = _som(web / f"{s['som']}.mp3")
        a = cache[s["som"]] * float(s["vol"]); i = int(s["t"] * SR)
        if 0 <= i < n:
            mix[i:i + len(a)] += a[:n - i]
    mix = np.concatenate([np.zeros(int(capa_s * SR), dtype=np.float32), mix])
    bruto = Path(saida).with_suffix(".bruto.wav")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "f32le", "-ar", str(SR), "-ac", "1", "-i", "-", str(bruto)],
                   input=mix.tobytes(), check=True)
    # -14 LUFS (v1), em duas passadas do loudnorm: mede e depois aplica linear
    med = subprocess.run(["ffmpeg", "-hide_banner", "-i", str(bruto), "-af", "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json",
                          "-f", "null", "-"], capture_output=True, text=True).stderr
    m = json.loads(med[med.rfind("{"):med.rfind("}") + 1])
    filtro = (f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={m['input_i']}:measured_TP={m['input_tp']}:"
              f"measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(bruto), "-af", filtro, "-ar", str(SR), str(saida)], check=True)
    bruto.unlink()


FINAL_X264 = ["-vf", "scale=out_range=tv:out_color_matrix=bt709", "-c:v", "libx264", "-preset", "slow", "-crf", "15", "-profile:v",
              "high", "-pix_fmt", "yuv420p", "-color_range", "tv", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709"]
# a prévia em vídeo (21/10/2026, "aprovo o plano previa-em-video"): 720x1280, rápida de fazer, um quadro inteiro a cada
# 15 (pular na barra cai no quadro certo)
PREVIA_X264 = ["-vf", "scale=720:1280:out_range=tv:out_color_matrix=bt709", "-c:v", "libx264", "-preset", "veryfast", "-crf", "23",
               "-g", "15", "-pix_fmt", "yuv420p", "-color_range", "tv", "-colorspace", "bt709", "-color_primaries", "bt709", "-color_trc", "bt709"]
ANTES_S = 2.0          # cada pedaço anda 2 s antes do seu começo sem fotografar: o take chega ao ponto e o plenário ao estado


def _encoder(saida, x264):
    return subprocess.Popen(["ffmpeg", "-v", "error", "-y", "-f", "image2pipe", "-framerate", str(QPS), "-c:v", "mjpeg", "-i", "-",
                             *x264, "-r", str(QPS), str(saida)], stdin=subprocess.PIPE)


def _pedaco(num, de, ate, saida, x264, escala, feitos, erros, url):
    """Um navegador fotografa os quadros [de, ate) e manda ao seu ffmpeg (21/10/2026: o vídeo em pedaços paralelos)."""
    from playwright.sync_api import sync_playwright
    enc = _encoder(saida, x264)
    with sync_playwright() as pw:
        nav = pw.chromium.launch()
        pg = nav.new_page(viewport={"width": 1080, "height": 1920}, device_scale_factor=escala)
        pg.on("pageerror", lambda e: erros.append(str(e)))
        pg.goto(url)
        pg.wait_for_function("!!window.__previa && !!window.__sons", timeout=60000, polling=200)
        pg.evaluate("document.fonts.ready.then(() => 0)")
        preparar_trechos(num, pg)
        for i in range(max(0, de - int(ANTES_S * QPS)), ate):
            pg.evaluate(QUADRO_JS, i / QPS)
            if i >= de:
                enc.stdin.write(pg.screenshot(type="jpeg", quality=96, clip={"x": 0, "y": 0, "width": 1080, "height": 1920}))
                feitos[0] += 1
        nav.close()
    enc.stdin.close(); enc.wait()
    if enc.returncode:
        erros.append(f"o ffmpeg não fechou o pedaço {saida.name}")


def quadros(num, saida, progresso, x264=FINAL_X264, escala=1, capa_jpg=None, capa_s=0.0, navegadores=None, leve=False):
    """A animação quadro a quadro em `saida` (MP4 mudo): a capa parada no começo (capa_s), depois a prévia em modo
    render, em pedaços fotografados por vários navegadores ao mesmo tempo e emendados (21/10/2026; era um navegador só:
    ~148 ms por quadro, 236 s no #304). Devolve (fim, sons, palavras)."""
    from playwright.sync_api import sync_playwright
    url = URL.format(n=num) + ("&leve=1" if leve else "")      # leve: a prévia em vídeo, com as cópias leves dos takes
    with sync_playwright() as pw:               # um navegador lê o fim, os sons e as palavras e prepara as cópias dos takes
        nav = pw.chromium.launch(); pg = nav.new_page(viewport={"width": 1080, "height": 1920})
        pg.goto(url); pg.wait_for_function("!!window.__previa && !!window.__sons", timeout=60000, polling=200)
        erro = pg.evaluate("window.__erroCena || ''")
        if erro:                                # travas-da-verificacao: vídeo com a animação quebrada não sai
            nav.close()
            raise RuntimeError(f"a animação tem erro de código ({erro[:160]}); peça o conserto no chat")
        preparar_trechos(num, pg)
        fim = float(pg.evaluate("window.__previa.fim")); sons = pg.evaluate("window.__sons.lista"); palavras = pg.evaluate("window.T.palavras")
        nav.close()
    total = int(round(fim * QPS))
    k = navegadores or (4 if os.getloadavg()[0] < 3 else 3)
    pasta = Path(saida).parent
    partes = [(total * j // k, total * (j + 1) // k) for j in range(k)]
    segs = [pasta / f"pedaco-{j}.mp4" for j in range(k)]
    feitos, erros = [0], []
    th = [threading.Thread(target=_pedaco, args=(num, de, ate, seg, x264, escala, feitos, erros, url)) for (de, ate), seg in zip(partes, segs)]
    for t in th:
        t.start()
    while any(t.is_alive() for t in th):
        progresso(5 + int(80 * feitos[0] / max(1, total)))
        th[0].join(timeout=2)
    for t in th:
        t.join()
    if erros:
        raise RuntimeError("a prévia deu erro: " + "; ".join(erros)[:300])
    lista = pasta / "pedacos.txt"
    if capa_jpg and capa_s > 0:                 # a capa parada como um pedaço a mais, no começo
        enc = _encoder(pasta / "pedaco-capa.mp4", x264)
        for _ in range(int(capa_s * QPS)):
            enc.stdin.write(capa_jpg)
        enc.stdin.close(); enc.wait()
        segs = [pasta / "pedaco-capa.mp4"] + segs
    lista.write_text("".join(f"file '{s}'\n" for s in segs))
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(lista), "-c", "copy", str(saida)], check=True)
    for s in segs:
        s.unlink(missing_ok=True)
    lista.unlink(missing_ok=True)
    return fim, sons, palavras


def conferir(final, fim):
    """Como a v1 (ferramentas/checagem.py conferir): ok / AVISO / ERRO; ERRO trava a publicação."""
    res = []
    info = json.loads(subprocess.run(["ffprobe", "-v", "error", "-show_entries",
                                      "format=duration,size:stream=codec_type,codec_name,width,height", "-of", "json", str(final)],
                                     capture_output=True, text=True, check=True).stdout)
    dur = float(info["format"]["duration"]); vid = next(s for s in info["streams"] if s["codec_type"] == "video")
    aud = next((s for s in info["streams"] if s["codec_type"] == "audio"), None)
    res.append(("ok" if abs(dur - (fim + CAPA_S)) < .2 else "ERRO", f"duração {dur:.1f} s (esperado {fim + CAPA_S:.1f})"))
    res.append(("ok" if dur <= 70 else "AVISO", f"{dur:.0f} s (a retenção cai acima de 70)"))
    res.append(("ok" if (vid["width"], vid["height"]) == (1080, 1920) else "ERRO", f"{vid['width']}x{vid['height']}"))
    res.append(("ok" if vid["codec_name"] == "h264" and aud and aud["codec_name"] == "aac" else "ERRO",
                f"vídeo {vid['codec_name']}, áudio {aud['codec_name'] if aud else 'nenhum'}"))
    sai = subprocess.run(["ffmpeg", "-i", str(final), "-filter:a", "ebur128=framelog=quiet", "-f", "null", "-"], capture_output=True, text=True).stderr
    m = re.search(r"I:\s+(-?[\d.]+) LUFS", sai[sai.rfind("Summary:"):])
    lufs = float(m.group(1)) if m else None
    res.append(("ok" if lufs is not None and abs(lufs + 14) <= 1 else "ERRO", f"volume {lufs} LUFS (alvo -14 ± 1)"))
    parados = parados_mp4(final, CAPA_S)
    res.append(("ok" if not parados else "AVISO", f"{len(parados)} trecho(s) parado(s) mais de 1 s"
                + (": " + ", ".join(f"{a:.1f} s ({d:.1f})" for a, d in parados[:6]) if parados else "")))
    mb = final.stat().st_size / 1e6
    res.append(("ok" if mb <= 100 else "ERRO", f"{mb:.1f} MB"))
    return {"duracao": round(dur, 2), "lufs": lufs, "mb": round(mb, 1), "itens": [{"nivel": a, "msg": b} for a, b in res],
            "erros": [b for a, b in res if a == "ERRO"]}


def parados_mp4(mp4, depois=0.0):
    """Os trechos parados mais de 1 s de um MP4 ([(início, duração)]), pelo freezedetect do ffmpeg. Os que começam antes
    de `depois` não contam (a capa parada no começo do vídeo final é de propósito). 22/10/2026 (editor-327): a mesma
    medida do vídeo final roda na prévia em vídeo, para ele ver antes de aprovar."""
    fz = subprocess.run(["ffmpeg", "-nostdin", "-v", "info", "-i", str(mp4), "-vf", "freezedetect=n=0.003:d=1", "-map", "0:v:0",
                         "-f", "null", "-"], capture_output=True, text=True).stderr
    ini = [float(x) for x in re.findall(r"freeze_start: ([\d.]+)", fz)]
    dz = [float(x) for x in re.findall(r"freeze_duration: ([\d.]+)", fz)]
    return [(round(a, 1), round(d, 1)) for a, d in zip(ini, dz) if a > depois - .05]


def capa_na_cena(num):
    """19/10/2026 (ele: "o vídeo tem que iniciar na capa, o locutor começa a falar e a capa só troca alguns segundos
    depois"): a cena que abre com T.capa já mostra a capa com a voz; então não vai o 1 s de capa parada e muda antes."""
    cena = E.pasta(num) / "animacao/cena.html"
    return cena.exists() and "T.capa(" in cena.read_text()


def fazer(num):
    global CAPA_S
    CAPA_S = 0.0 if capa_na_cena(num) else 1.0
    p = E.pasta(num); pub = p / "publicacao"; pub.mkdir(exist_ok=True)
    capa = p / "animacao/capa.jpg"
    if not capa.exists():
        raise RuntimeError("sem capa escolhida")
    progresso = lambda v: E.mexe_ficha(num, progresso=v)
    progresso(5)
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp); mudo = tmp / "mudo.mp4"
        # 19/10/2026 (ele: "pode fazer a melhoria de qualidade do vídeo"): mais qualidade na origem (o Instagram comprime
        # de novo) e a marca de cor de vídeo (FINAL_X264). 21/10/2026: em pedaços paralelos, com 1 s da capa na frente
        fim, sons, palavras = quadros(num, mudo, progresso, capa_jpg=capa.read_bytes(), capa_s=CAPA_S)
        progresso(88)
        audio = tmp / "audio.wav"
        mixar(num, fim, sons, palavras, audio)
        progresso(94)
        final = pub / "final.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(mudo), "-i", str(audio), "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                        "-ar", "48000", "-shortest", "-movflags", "+faststart", str(final)], check=True)       # 48 kHz: o do Instagram
    shutil.copy2(capa, pub / "capa.jpg")
    progresso(97)
    conf = conferir(final, fim)
    conf["quando"] = E.agora(); conf["sons"] = len(sons)
    E._grava(pub / "final.json", json.dumps(conf, ensure_ascii=False, indent=1))
    E.evento(num, f"vídeo final: {conf['duracao']} s, {conf['lufs']} LUFS, {conf['mb']} MB, erros: {len(conf['erros'])}")
    return conf


def versao_previa(num):
    """O que a prévia em vídeo depende: a página da prévia como o tocador a monta (cena, voz, capa, tocador) e as peças."""
    import hashlib, animacao
    html = animacao.pagina(num)
    h = hashlib.md5(re.sub(r'\?v=[0-9a-f]{8}"', '"', html).encode())    # o ?v= do áudio também mudava com a capa
    # a capa escolhida entra: a cena a mostra no começo (T.capa, animacao/capa.jpg), também na prévia em vídeo. Tirá-la
    # da versão deixou a prévia do #316 com a capa antiga (21/10/2026, "aprovo o plano previa-com-capa"); com ela, trocar
    # a capa refaz só a prévia, e o nome novo do arquivo impede o navegador de mostrar a de antes
    capa_jpg = E.pasta(num) / "animacao/capa.jpg"
    if capa_jpg.exists():
        h.update(capa_jpg.read_bytes())
    for f in sorted((E.RAIZ / "web/pecas").glob("*.js")):
        h.update(f.read_bytes())
    return h.hexdigest()[:10]


def previa_video(num):
    """A prévia em vídeo (21/10/2026, "aprovo o plano previa-em-video"; ele: "um preview que não dá picos ou pulos, que
    mostra fluido"): o mesmo caminho do vídeo final, em 720x1280 e sem a capa na frente (os segundos batem com os da
    prévia e do roteiro). Grava animacao/previa-<versão>.mp4 e animacao/previa-video.json; apaga as de antes.
    O servidor chama em outro processo, com prioridade baixa (nice), e o mata se a cena mudar no meio."""
    import time
    a = E.pasta(num) / "animacao"; v = versao_previa(num); t0 = time.time()
    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp); mudo = tmp / "mudo.mp4"; audio = tmp / "audio.wav"
        fim, sons, palavras = quadros(num, mudo, lambda p: None, x264=PREVIA_X264, escala=2 / 3, leve=True)
        mixar(num, fim, sons, palavras, audio, capa_s=0.0)
        saida = a / f"previa-{v}.mp4"; tmp_saida = a / f"previa-{v}.tmp.mp4"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(mudo), "-i", str(audio), "-c:v", "copy", "-c:a", "aac", "-b:a", "160k",
                        "-shortest", "-movflags", "+faststart", str(tmp_saida)], check=True)
        os.replace(tmp_saida, saida)
    for velha in a.glob("previa-*.mp4"):
        if velha != saida:
            velha.unlink(missing_ok=True)
    info = {"versao": v, "arquivo": saida.name, "quando": E.agora(), "segundos": round(time.time() - t0, 1), "duracao": round(fim, 2),
            "parados": parados_mp4(saida)}           # editor-327: o "parado mais de 1 s" já na prévia (antes, só no final)
    E._grava(a / "previa-video.json", json.dumps(info, ensure_ascii=False))
    return info


if __name__ == "__main__":
    if sys.argv[1:2] == ["--previa"]:
        print(json.dumps(previa_video(int(sys.argv[2])), ensure_ascii=False))
    else:
        print(json.dumps(fazer(int(sys.argv[1])), ensure_ascii=False, indent=1))
