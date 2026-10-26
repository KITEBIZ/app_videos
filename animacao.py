"""A animação do vídeo (estúdio v2, 16/10/2026, "aprovo o plano v2-parte3-animacao").

  python3 animacao.py <número>                 primeira animação (ou continua a que existe)
  python3 animacao.py <número> "pedido dele"   muda a animação pelo pedido

O animador (claude, regras/ANIMADOR.md) lê o arquivo do vídeo e escreve animacao/cena.html; o tocador
(web/tocador.html) junta a cena, o fundo, a legenda e o áudio na prévia. Ele vê os próprios quadros e mede com a régua
(ferramentas/ver.py). Depois, o estúdio confere sozinho: régua (programa) e os Olhos (conteudo/olhos: só os quadros e a
fala, sem roteiro), com conserto automático do que eles e a medida de tela vazia apontam. Antes de cada mudança, a cena
vai para animacao/versoes/ e os quadros do meio de cada bloco vão para animacao/antes/; depois, para animacao/depois/.
"""
import hashlib, html, json, re, shutil, subprocess, sys, threading, time
from pathlib import Path

import estudio as E
import animador_novo as AN

FERR = E.RAIZ / "ferramentas"
sys.path.insert(0, str(FERR))
CORTE = E.CORTE          # o mesmo do estudio.py (aceita a origem: material/<código>)


def preparar(num):
    """O que a prévia precisa: as palavras ditas no áudio final (legenda e T.palavra) e o vídeo da pauta (trechos)."""
    p = E.pasta(num); nar = p / "narracao"
    from transcrever import palavras
    pal = nar / "palavras.json"
    if not pal.exists() or pal.stat().st_mtime < (nar / "completo.mp3").stat().st_mtime:
        lingua = E.idioma(num)
        if lingua == "pt":
            ws, _ = palavras(nar / "completo.mp3")
        else:
            # 22/10/2026 ("aprovo o plano idioma-do-video"): cada bloco ouvido no idioma dele, a nossa fala no do vídeo e
            # o trecho de outra pessoa em português (o vídeo de origem); um idioma só para o áudio inteiro traduzia o outro
            ws = []
            for t in json.loads((nar / "completo.json").read_text())["blocos"]:
                ws += palavras(nar / "completo.mp3", lingua if t["nosso"] else "pt", t["ini"], t["fim"])[0]
        pal.write_text(json.dumps(ws, ensure_ascii=False))
    traducoes(num)                       # idioma-do-video: a legenda traduzida da fala de outra pessoa (só fora do português)
    tem_trecho = any(not b["nosso"] and (E.corte(b["fala"]) or (0, 0, "referencia"))[2] == "referencia" for b in E.blocos(num))
    ficha = E.ler_ficha(num)
    if tem_trecho and ficha.get("link") and not (p / "referencia/video.mp4").exists():
        import analisar_reel as A
        A.yt([A.ytdlp(), "-q", "--no-warnings", "-S", "res:1080,br", "-f", "bv+ba/b", "--merge-output-format", "mp4",
              "-o", str(p / "referencia/video.%(ext)s"), ficha["link"]], quem="animação (vídeo da pauta)", capture_output=True, timeout=600)
    (p / "animacao").mkdir(exist_ok=True)


PEDIR_TRADUCAO = """Traduza para {nome} a fala abaixo, de uma pessoa num vídeo de checagem. Fiel ao que ela disse: sem
resumir, sem acrescentar, sem corrigir, no tom dela, curta como legenda. Nome próprio fica como está. Responda só a
tradução, sem aspas.

Quem fala: {quem}
Fala: {fala}"""


def traducoes(num, so_guardado=False):
    """{bloco: tradução} da fala de cada outra pessoa, num vídeo que não é em português (22/10/2026, "aprovo o plano
    idioma-do-video"; a fala dela continua a original, em português, e a legenda traduzida vai por baixo). A IA barata
    (haiku) traduz uma vez por fala; guarda em narracao/traducoes.json. so_guardado: só o que já foi traduzido."""
    lg = E.idioma(num)
    if lg == "pt":
        return {}
    arq = E.pasta(num) / "narracao/traducoes.json"
    try:
        cache = json.loads(arq.read_text())
    except (OSError, ValueError):
        cache = {}
    saida, mudou = {}, False
    for b in E.blocos(num):
        if b["nosso"]:
            continue
        fala = CORTE.sub("", b["fala"]).strip()
        # quem fala vai junto: sem isso, "eu sou presidente" do Nazur Garcia (#335) saiu "soy presidenta"
        chave = hashlib.md5(f"{lg}|{b['quem']}|{fala}".encode()).hexdigest()[:12]
        if chave not in cache and not so_guardado:
            import ia                         # 25/10/2026: a chamada de IA de um lugar só (ia.py)
            r, uso = ia.chamar(PEDIR_TRADUCAO.format(nome=E.IDIOMAS[lg], quem=b["quem"], fala=fala), "tradução da legenda",
                               "haiku", num=num, limite=120)
            t = " ".join(r.split()).strip().strip('"“”')
            if t:
                cache[chave] = t; mudou = True
            else:
                E.evento(num, f"a tradução da fala do bloco {b['n']} não saiu: {str(uso['erro'])[:120]}")
        if chave in cache:
            saida[b["n"]] = cache[chave]
    if mudou:
        arq.write_text(json.dumps(cache, ensure_ascii=False, indent=1))
    return saida


def dados(num):
    p = E.pasta(num)
    c = json.loads((p / "narracao/completo.json").read_text())
    ws = json.loads((p / "narracao/palavras.json").read_text()) if (p / "narracao/palavras.json").exists() else []
    bs = {b["n"]: b for b in E.blocos(num)}
    trad = traducoes(num, so_guardado=True)
    blocos = []
    for t in c["blocos"]:
        b = bs.get(t["n"], {})
        cr = E.corte(b.get("fala", ""))      # (17/10: o nome "c" apagava o completo.json e a animação quebrava)
        blocos.append({"n": t["n"], "ini": t["ini"], "fim": t["fim"], "nosso": t["nosso"], "quem": b.get("quem", ""),
                       "fala": CORTE.sub("", b.get("fala", "")), "tela": b.get("tela", ""),
                       "corte": [cr[0], cr[1]] if cr else None, "fonte": cr[2] if cr else None,
                       **({"traducao": trad[t["n"]]} if t["n"] in trad else {})})
    return {"duracao": c["duracao"], "blocos": blocos, "palavras": ws, "legenda": legenda(blocos, ws),
            "idioma": E.idioma(num)}        # idioma-do-video (22/10/2026): os textos fixos das peças (T.t no tocador)


def legenda(blocos, ws):
    """A legenda da v1 (newsbr360.legenda_original, layout 2; RECEITA "Tela": "legenda grande palavra a palavra com
    destaques em amarelo"): o TEXTO do roteiro com o TEMPO da voz (a transcrição erra maiúscula e ponto), em pedaços de
    até 20 letras que não terminam em palavra de ligação (ferramentas/legenda.py), cada pedaço no mínimo 0,35 s.
    16/10/2026 (ele: "a legenda não está aparecendo conforme a pessoa vai falando. tem uma regra [...]")."""
    import difflib
    import legenda as L
    norm = lambda s: re.sub(r"[^\w]", "", __import__("unicodedata").normalize("NFD", str(s).lower()).encode("ascii", "ignore").decode())
    pecas = []
    for b in blocos:
        dentro = [w for w in ws if b["ini"] - .15 <= (w[0] + w[1]) / 2 <= b["fim"] + .15]
        # 19/10/2026 (ele: "pode consertar a legenda"): nos trechos do vídeo dele também o texto do roteiro (que veio da
        # transcrição da pauta, conferida), e não o que o transcritor ouviu na voz final ("Converto" no lugar de "Confesso", #301)
        texto = b["fala"].split() or [w[2] for w in dentro]
        # vídeo em outro idioma (idioma-do-video): na fala de outra pessoa a legenda é a tradução, espalhada no tempo do
        # bloco (as palavras dela não casam com as da tradução)
        if b.get("traducao"):
            texto, dentro = b["traducao"].split(), []
        # 20/10/2026 (#304: a fala do Lula, take de material/, saiu sem legenda; o editor apontou 11 legendas faltando
        # nos #300-#305): sem palavra transcrita no trecho, o texto do roteiro vai distribuído no tempo do bloco
        if not texto or (not dentro and b.get("nosso", True)):
            continue
        # cada palavra do roteiro pega o tempo da palavra dita igual; as outras, por interpolação entre vizinhas
        tempos = [None] * len(texto)
        sm = difflib.SequenceMatcher(None, [norm(t) for t in texto], [norm(w[2]) for w in dentro], autojunk=False)
        for blk in sm.get_matching_blocks():
            for k in range(blk.size):
                tempos[blk.a + k] = (dentro[blk.b + k][0], dentro[blk.b + k][1])
        conhecidos = [i for i, t in enumerate(tempos) if t]
        for i in range(len(texto)):
            if tempos[i]:
                continue
            ant = max([k for k in conhecidos if k < i], default=None); prox = min([k for k in conhecidos if k > i], default=None)
            a0 = tempos[ant][1] if ant is not None else b["ini"]; a1 = tempos[prox][0] if prox is not None else b["fim"]
            n0 = ant if ant is not None else -1; n1 = prox if prox is not None else len(texto)
            passo = (a1 - a0) / max(1, n1 - n0)
            tempos[i] = (a0 + passo * (i - n0 - 1) + .01, a0 + passo * (i - n0))
        palavras = [{"p": t, "ini": round(tempos[i][0], 2), "fim": round(tempos[i][1], 2)} for i, t in enumerate(texto)]
        for p in L.pedacos(palavras, numeros=False, limite=20):
            pecas.append(p)
    saida, ultimo = [], -1.0
    for n, p in enumerate(pecas):
        ini = max(p[0]["ini"] - .08, ultimo + .35 if saida else 0)
        saida.append({"ini": round(ini, 2), "palavras": [{"p": w["p"], "ini": round(max(ini, w["ini"] - .08), 2)} for w in p],
                      "fim_fala": p[-1]["fim"]})
        ultimo = ini
    for n, s in enumerate(saida):
        prox = saida[n + 1]["ini"] if n + 1 < len(saida) else None
        fim = max(s["fim_fala"] + .3, s["ini"] + .35)
        s["fim"] = round(min(fim, prox - .02) if prox is not None else fim, 2)
        del s["fim_fala"]
    return saida


def _legendas_gravadas(arq, quadros=16):
    """Onde ficam as palavras que o canal de origem gravou no vídeo: o alto (no quadro de 540) de cada palavra que o
    leitor de texto (tesseract) acha centrada, com 2 letras ou mais, na metade de baixo, em quadros espalhados pelo vídeo
    inteiro (a legenda aparece e some; 4 quadros de um take só erraram o #335: acharam o "TRENSURB" de baixo e não a
    legenda). Placa de fundo (o "ALSTOM" do trem no #335) fica de fora por estar fora do centro."""
    import cv2, numpy as np
    total = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(arq)]))
    altos = []
    for i in range(quadros):
        png = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-ss", f"{total * (i + .5) / quadros:.2f}", "-i", str(arq), "-frames:v", "1",
                              "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True).stdout
        if not png:
            continue
        alt, larg = cv2.imdecode(np.frombuffer(png, np.uint8), cv2.IMREAD_GRAYSCALE).shape[:2]; e = 540 / larg
        try:
            r = subprocess.run(["tesseract", "stdin", "-", "--psm", "11", "tsv"], input=png, capture_output=True, timeout=30)
        except subprocess.TimeoutExpired:
            continue
        for linha in r.stdout.decode(errors="replace").splitlines()[1:]:
            c = linha.split("\t")
            if len(c) < 12 or float(c[10] or -1) < 60 or sum(ch.isalnum() for ch in c[11]) < 2:
                continue
            x, y, w = int(c[6]), int(c[7]), int(c[8])
            if y > alt / 2 and .15 * larg < x + w / 2 < .85 * larg:
                altos.append(round(y * e, 1))
    return sorted(altos)


def takes_por_texto(cena):
    """Os takes lidos do texto da cena (reserva): só os que escrevem corte com número e src por extenso."""
    out = []
    for m in re.finditer(r"T\.take\(\{(.*?)\}\);", cena, re.S):
        corpo = m.group(1)
        if re.search(r"\bjanela:\s*true|\bcheia:\s*false", corpo):
            continue
        c = re.search(r"\bcorte:\s*([\d.]+)", corpo)
        if c:
            out.append(((re.search(r"\bsrc:\s*['\"]([^'\"]+)['\"]", corpo) or [None, "referencia/video.mp4"])[1], float(c.group(1))))
    return out


def takes_conhecidos(num, cena):
    """A lista de takes que a prévia anotou para ESTA cena (animacao/takes.json), ou None se a cena mudou."""
    import hashlib
    try:
        d = json.loads((E.pasta(num) / "animacao/takes.json").read_text())
    except (OSError, ValueError):
        return None
    return [(x["src"], float(x["corte"])) for x in d["takes"] if not x.get("janela")] \
        if d.get("cena") == hashlib.md5(cena.encode()).hexdigest() else None


def takes_anteriores(num):
    """25/10/2026 (#373, ele: "voltou o erro de enquadramento" depois de tirar o borrão): a lista de takes da cena ANTERIOR
    (takes.json de antes da mudança), com a duração. Mudou a cena, a primeira montagem lia só o texto e perdia o take do
    Lula (corte com conta); somar a lista de antes mantém medido o que continua na cena. Chave a mais não atrapalha."""
    try:
        return [(x["src"], max(0.0, float(x["corte"])), float(x.get("dura") or 2.0), bool(x.get("janela")))
                for x in json.loads((E.pasta(num) / "animacao/takes.json").read_text())["takes"]]
    except (OSError, ValueError, KeyError, TypeError):
        return []


def takes_da_cena(num, cena):
    """24/10/2026 (#373: "porque continua cortando o vídeo e não usando a área toda"; com corte: tCapa - off2 e {...SGT} a
    leitura pelo texto perdia o take do Lula e media o vídeo errado no do sargento): abre a prévia por trás e lê os takes
    de verdade (T._takes, com o vídeo e o corte já calculados). Guarda em animacao/takes.json com a marca da cena."""
    import hashlib, ver
    from playwright.sync_api import sync_playwright
    try:
        with sync_playwright() as pw:
            nav = pw.chromium.launch(); pg = nav.new_page(viewport={"width": 540, "height": 960})
            pg.goto(ver.URL.format(n=num)); pg.wait_for_function("!!window.__previa", timeout=30000, polling=200)
            takes = pg.evaluate("(window.T && window.T._takes) || []")
            nav.close()
    except Exception as ex:
        E.evento(num, f"a lista de takes da prévia não saiu: {str(ex)[:160]}")
        return None
    E._grava(E.pasta(num) / "animacao/takes.json", json.dumps({"cena": hashlib.md5(cena.encode()).hexdigest(), "takes": takes},
                                                             ensure_ascii=False, indent=1))
    return [(x["src"], float(x["corte"])) for x in takes if not x.get("janela")]


def rostos_dos_takes(num, cena, so_guardado=False):
    """22/10/2026 ("aprovo o plano enquadramento-automatico"; ele: "o enquadramento da cabeça de quem fala tem que
    aproveitar bem a área e ficar no topo da área superior" e "isso tem que resolver"; no #335 o animador subiu a cabeça
    três vezes chutando pixels): para cada take em tela cheia da cena, o rosto de quem fala no vídeo de origem, achado pelo
    detector (YuNet, o mesmo do agente de capa) em 4 quadros a partir do corte. Devolve {"<src>@<corte>": [x, y, l, a]}
    em pixels do quadro com 540 de largura (a medida da peça take), mais o alto da legenda gravada no vídeo abaixo do
    boca (o 5º e o 6º números, o alto e o pé da faixa; None se não tem), para a peça embaçar só essa faixa (22/10,
    enquadramento-automatico.1: no #335, com a cabeça no alto, aparecia "no dia 25 no segundo turno" junto do ELE DISSE;
    descer o vídeo até o pé escuro cobrir a legenda escondia a boca, porque ali a legenda encosta no queixo).
    Guarda em animacao/rostos.json (só refaz o que mudou)."""
    import numpy as np, visao
    p = E.pasta(num); cache_arq = p / "animacao/rostos.json"
    try:
        cache = json.loads(cache_arq.read_text())
    except (OSError, ValueError):
        cache = {}
    saida, mudou = {}, False

    def faixa_gravada(arq, marca, boca):
        # a legenda gravada é do vídeo de origem inteiro: lida uma vez por vídeo. O take usa a faixa abaixo da boca (no
        # #335 a legenda encosta no queixo): [alto, pé] da 1ª linha até a 2ª (até 90 px abaixo) mais a altura da letra
        nonlocal mudou
        g = cache.get(f"legendas:{arq.name}")
        if not g or g.get("marca") != marca:
            g = cache[f"legendas:{arq.name}"] = {"marca": marca, "altos": _legendas_gravadas(arq)}; mudou = True
        abaixo = [y for y in g["altos"] if y > boca]
        if len(abaixo) < 2:
            return None, None
        return min(abaixo), max(y for y in abaixo if y <= min(abaixo) + 90) + 35

    lista = takes_conhecidos(num, cena)
    if lista is None:
        if so_guardado:
            saida["_falta"] = True                 # a lista certa vem da prévia, por trás (medir_rostos_por_tras)
            lista = takes_por_texto(cena)
            lista += [(s, c) for s, c, _, j in takes_anteriores(num) if not j and (s, c) not in lista]
        else:
            lista = takes_da_cena(num, cena) or takes_por_texto(cena)
    for src, corte_s in lista:
        c = re.match(r"([\d.]+)", f"{max(0.0, corte_s):.2f}")
        chave = f"{src}@{float(c.group(1)):.2f}"
        arq = (p / src).resolve()
        if not str(arq).startswith(str(p.resolve()) + "/") or not arq.exists():
            continue
        marca = f"{arq.stat().st_mtime:.0f}"
        if chave in cache and cache[chave].get("marca") == marca and cache[chave].get("v") == 6:
            if cache[chave].get("rosto"):
                saida[chave] = cache[chave]["rosto"]
            continue
        if so_guardado:
            saida["_falta"] = True
            continue
        caixas, varios, todos = [], 0, []
        for k in (0.3, 0.9, 1.5, 2.1):
            q = visao.quadro(arq, float(c.group(1)) + k)      # 25/10/2026: quadro e rostos de um lugar só (visao.py)
            if q is None:
                continue
            fs = visao.rostos(q, .7)
            if fs:
                f = fs[0]; e = 540 / q.shape[1]
                # 24/10/2026 (#373, o preso): todos os rostos do quadro, para a peça borrar os que não são de quem fala
                todos += [[round(float(v) * e, 1) for v in g[:4]] for g in fs if g[-1] >= .6]
                caixas.append([float(v) * e for v in f[:4]])
                # 22/10/2026, #340: a montagem do canal tinha a foto do Lula em cima e a apresentadora (quem fala) no
                # meio; o maior rosto era o do Lula e a peça ampliou a foto dele. Dois rostos de tamanho parecido: o
                # detector não sabe quem fala, e o take fica como antes (o animador usa cheia.manual se precisar).
                # Conta o outro rosto só se é firme (nota .85), de bom tamanho (30% do maior) e fora do maior: no #335 o
                # detector achava pedaços do mesmo rosto (nota .71-.73, dentro da caixa dele) e um rosto pequeno num quadro só
                fora = lambda g: g[0] > f[0] + f[2] or g[0] + g[2] < f[0] or g[1] > f[1] + f[3] or g[1] + g[3] < f[1]
                varios += any(g is not f and g[-1] >= .85 and g[2] * g[3] >= .3 * f[2] * f[3] and fora(g) for g in fs)
        varios = bool(caixas) and varios * 2 >= len(caixas)        # em metade dos quadros com rosto, ou mais
        rosto = [round(float(np.median([b[i] for b in caixas])), 1) for i in range(4)] if caixas and not varios else None
        leg = faixa_gravada(arq, marca, rosto[1] + .75 * rosto[3]) if rosto else (None, None)
        cache[chave] = {"marca": marca, "rosto": rosto and rosto + list(leg), "quadros": len(caixas), "varios_rostos": varios,
                        "todos": todos, "v": 6}
        mudou = True
        if rosto:
            saida[chave] = rosto
    if mudou:
        cache_arq.write_text(json.dumps(cache, ensure_ascii=False, indent=1))
    return saida


def rostos_todos(num):
    """{"<src>@<corte>": [[x, y, l, a], ...]}: todos os rostos que o detector viu em cada take (para `borrar: 'outros'`)."""
    try:
        cache = json.loads((E.pasta(num) / "animacao/rostos.json").read_text())
    except (OSError, ValueError):
        return {}
    return {k: v.get("todos") or [] for k, v in cache.items() if isinstance(v, dict) and "@" in k}


_MEDINDO, _MEDINDO_TRAVA = set(), threading.Lock()


def medir_rostos_por_tras(num, cena):
    """Mede os rostos que faltam numa linha só por vídeo, fora do pedido da página; a próxima abertura já usa."""
    with _MEDINDO_TRAVA:
        if num in _MEDINDO:
            return
        _MEDINDO.add(num)

    def medir():
        try:
            rostos_dos_takes(num, cena)
            E.evento(num, "rostos dos takes medidos (enquadramento automático)")
        except Exception as ex:
            E.evento(num, f"o detector de rosto dos takes não rodou: {str(ex)[:160]}")
        finally:
            with _MEDINDO_TRAVA:
                _MEDINDO.discard(num)
    threading.Thread(target=medir, daemon=True).start()


# 25/10/2026 (revisão de segurança): a cena é código escrito pela IA e roda na mesma página do painel, com o login dele
# (e na gravação do vídeo, em 127.0.0.1, sem login). Uma cena só precisa da biblioteca do estúdio (T.*) e do próprio
# desenho; o que sai dela (pedir ao servidor, mexer na janela de cima, cookies, endereço de fora) é o caminho de um
# conteúdo malicioso lido pelo agente apertar botões ou levar dados. Conferido em 119 cenas reais: nenhuma usa isso.
PERIGOS = [
    (r"\bfetch\s*\(", "fetch"), (r"XMLHttpRequest", "XMLHttpRequest"), (r"\bWebSocket\b", "WebSocket"),
    (r"sendBeacon", "sendBeacon"), (r"\beval\s*\(", "eval"), (r"\bFunction\s*\(", "Function()"), (r"\bimport\s*\(", "import()"),
    (r"\b(?:window\s*\.\s*)?(?:parent|top|opener)\s*\.\s*(?:document|fetch|location|postMessage|window|\$|[A-Za-z_]+\s*\()", "a janela de cima"),
    (r"document\s*\.\s*cookie", "cookie"), (r"\b(?:localStorage|sessionStorage|indexedDB)\b", "armazenamento do navegador"),
    (r"\bpostMessage\s*\(", "postMessage"), (r"\b(?:window\s*\.\s*|document\s*\.\s*)?location\s*(?:\.\s*(?:href|assign|replace)|=)", "navegar"),
    (r"<\s*(?:iframe|form|object|embed|base|meta)\b", "elemento proibido"),
    (r"\b(?:src|href|action)\s*=\s*[\"']?\s*(?:https?:)?//", "endereço externo"), (r"url\(\s*[\"']?\s*(?:https?:)?//", "endereço externo"),
]


def codigo_perigoso(cena):
    """O que a cena tem de proibido (lista vazia = nada)."""
    return sorted({nome for p, nome in PERIGOS if re.search(p, cena)})


def tamanhos_das_imagens(num, cena):
    """{caminho na pasta do vídeo: [largura, altura]} das imagens que a cena cita (só o cabeçalho de cada arquivo)."""
    from PIL import Image
    p, out = E.pasta(num), {}
    for rel in set(re.findall(r"""['"]((?:material|anexos|referencia)/[^'"]+?\.(?:jpe?g|png|webp))['"]""", cena, re.I)):
        try:
            with Image.open(p / rel) as im:
                out[rel] = list(im.size)
        except OSError:
            pass
    return out


def pagina(num):
    """A prévia: web/tocador.html com a cena do animador dentro."""
    p = E.pasta(num)
    cena = (p / "animacao/cena.html").read_text() if (p / "animacao/cena.html").exists() else \
        '<svg width="1080" height="1920" style="position:absolute;inset:0"><text x="480" y="900" text-anchor="middle" fill="#9cbcff" font-size="44">a animação ainda não foi feita</text></svg>'
    if codigo_perigoso(cena):                # não roda no navegador dele nem na gravação; a régua manda consertar
        cena = ('<svg width="1080" height="1920" style="position:absolute;inset:0"><text x="480" y="900" text-anchor="middle" '
                'fill="#ff6b7a" font-size="40">cena bloqueada: código que sai da prévia (' + html.escape(", ".join(codigo_perigoso(cena)))
                + ')</text></svg>')
    d = dados(num)
    # a capa escolhida abre a prévia (16/10/2026, "aprovo o plano v2-capa"; o tocador a mostra 1 s antes da fala)
    capa = (p / "animacao/capa.html").read_text() if (p / "animacao/capa.html").exists() else ""
    # capa viva (21/10/2026, "aprovo o plano capa-viva"): o trecho que toca por baixo do texto da capa (T.capa no tocador)
    try:
        d["capa_fundo"] = (json.loads((p / "animacao/capa-fundo.json").read_text())
                           if (p / "animacao/capa-texto.png").exists() else [])
    except (OSError, ValueError):
        d["capa_fundo"] = []
    d["capa_v"] = int((p / "animacao/capa-texto.png").stat().st_mtime) if d["capa_fundo"] else 0
    # enquadramento-automatico: o rosto de cada take em tela cheia (T.rostos no tocador). 22/10/2026, 20:45: medir na hora
    # travou a prévia do #340 (o leitor de legenda gravada leva minutos num vídeo deitado, e cada abertura da página
    # começava outra medida): a página usa só o que já foi medido; o que falta é medido uma vez, por trás
    try:
        d["rostos"] = rostos_dos_takes(num, cena, so_guardado=True)
    except Exception as ex:
        d["rostos"] = {}
        E.evento(num, f"o detector de rosto dos takes não rodou: {str(ex)[:160]}")
    if d["rostos"].pop("_falta", None):
        medir_rostos_por_tras(num, cena)
    d["rostos_todos"] = rostos_todos(num)
    # 25/10/2026 (#382, ele: "continua cortando as imagens [...] e não aproveita o topo"): o tamanho de cada imagem que a
    # cena usa; sem ele a peça de fotos supunha 540x960 (um quadro de vídeo) e a foto deitada de 1200x800 ficava numa
    # faixa no meio da tela
    d["tamanhos"] = tamanhos_das_imagens(num, cena)
    # conferir-o-pedido-e-faixa-preta (23/10/2026): a tarja preta de cada vídeo da cena (T.tarjas); a peça de take a corta
    try:
        d["tarjas"] = tarjas_dos_videos(num, cena)
    except Exception as ex:
        d["tarjas"] = {}
        E.evento(num, f"a tarja dos vídeos não foi medida: {str(ex)[:160]}")
    versao = hashlib.md5(((p / "narracao/completo.json").read_bytes() + cena.encode() + capa.encode())).hexdigest()[:8]
    return ((E.RAIZ / "web/tocador.html").read_text().replace("{{NUM}}", str(int(num))).replace("{{DUR}}", f"{d['duracao']:.2f}")
            .replace("{{VERSAO}}", versao).replace("{{DADOS}}", json.dumps(d, ensure_ascii=False)).replace("{{CAPA}}", capa).replace("{{CENA}}", cena))


def contexto(num, pedido):
    p = E.pasta(num)
    ler = lambda n, lim=10000: (p / n).read_text()[:lim] if (p / n).exists() else "(não existe)"
    material = sorted(str(x.relative_to(p)) for pasta in ("material", "anexos", "referencia") if (p / pasta).exists()
                      for x in (p / pasta).rglob("*") if x.is_file() and x.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp", ".mp4", ".txt"))
    d = dados(num)
    return f"""{(E.RAIZ / 'regras/ANIMADOR.md').read_text().replace('<estúdio>', str(E.RAIZ)).replace('<número>', str(int(num)))}{E.molde(num)}{E.regra_idioma(num)}

## Este vídeo (#{int(num)}), pasta {p}
Formato: {({'checagem': 'Checagem (carimbo = veredito sobre a fala)', 'analise': 'Análise (carimbo = tipo da informação: CONFIRMADO, PREVISÃO, OPINIÃO; selo ANÁLISE na conclusão)'}).get(E.ler_ficha(num).get('formato'), 'não marcado')}. Máximo 4 carimbos.
Duração: {d['duracao']:.1f} s. Blocos no áudio (n · início-fim · quem · Tela pedida no roteiro):
{chr(10).join(f"- {b['n']} · {b['ini']:.1f}-{b['fim']:.1f} s · {'nós' if b['nosso'] else b['quem']}" + (f" · corte {b['corte'][0]} em {b['fonte']}/video.mp4" if b['corte'] else '') + f" · Tela: {b['tela']}" for b in d['blocos'])}

Arquivos de imagem e vídeo na pasta: {', '.join(material[:80]) or '(nenhum)'}

INTENCAO.md:
{ler('INTENCAO.md', 3000)}

ROTEIRO.md:
{ler('ROTEIRO.md')}

O que ele pediu no chat deste vídeo (todas as etapas, as últimas 30; pedido de edição vale para você):
{pedidos_dele(num)}

A cena de agora (animacao/cena.html): {'existe, leia antes de mudar' if (p / 'animacao/cena.html').exists() else 'ainda não existe: faça a primeira animação do vídeo inteiro'}

## O que fazer agora
{pedido or 'Faça a primeira animação do vídeo inteiro, bloco a bloco, seguindo a coluna Tela de cada bloco.'}
"""


def pedidos_dele(num, ultimas=30):
    """16/10/2026 ("aprovo o plano v2-takes"): o pedido "baixa esse vídeo para usar no início" ficou na conversa do
    roteiro e nunca chegou ao animador. Agora ele lê as mensagens dele de todas as etapas."""
    dele = [m for m in E.chat(num) if m.get("quem") == "ele"][-ultimas:]
    return "\n".join(f"- {m.get('quando', '')[:16]}: {m.get('texto', '')[:600]}" for m in dele) or "(nenhuma)"


def fotos_dos_blocos(num, onde):
    """A foto de cada bloco perto do fim (blocoNN.png, a que a tela mostra) e, em mais/, no começo e no meio (17/10/2026:
    a mudança no primeiro meio segundo do bloco 1 do #291 não aparecia na foto do fim e o estúdio achava que nada mudou)."""
    import ver
    from concurrent.futures import ThreadPoolExecutor
    a = E.pasta(num) / "animacao"
    d = a / onde
    # 20/10/2026 (ele: "pode medir e cortar a preparação também"; no #305 as fotos levavam 30 s antes e 30 s depois de
    # cada ajuste): as fotos "antes" de agora são as "depois" da rodada anterior, se nem a cena nem a voz mudaram desde elas
    novas = lambda x: not x.exists() or (a / "depois").stat().st_mtime >= x.stat().st_mtime
    if onde == "antes" and (a / "depois").is_dir() and (a / "cena.html").exists() and any((a / "depois").glob("bloco*.png")) \
            and novas(a / "cena.html") and novas(E.pasta(num) / "narracao/completo.json"):
        shutil.rmtree(d, ignore_errors=True)
        shutil.copytree(a / "depois", d)
        return
    shutil.rmtree(d, ignore_errors=True)

    def uma(onde_no_bloco, sub, sufixo):          # as três passadas ao mesmo tempo, cada uma no seu navegador
        alvo = ver.meios(num, onde_no_bloco)
        dd = d / sub if sub else d
        feitos, _ = ver.quadros(num, [t for _, t in alvo], saida=dd / f".tmp{sufixo}")
        for (n, _), arq in zip(alvo, feitos):
            arq.rename(dd / f"bloco{n:02d}{sufixo}.png")
        shutil.rmtree(dd / f".tmp{sufixo}", ignore_errors=True)

    with ThreadPoolExecutor(max_workers=3) as ex:
        for f in [ex.submit(uma, *x) for x in ((0.85, "", ""), (0.08, "mais", "a"), (0.5, "mais", "b"))]:
            f.result()


def animar(num, pedido=None, msg_id=None, modo=None):
    """25/10/2026 (revisão de solidez): o pedido em andamento fica na ficha (animacao_pendente) até o fim; se o estúdio
    religar no meio, o servidor retoma com ELE (antes, "animando" religava sem pedido e caía no animador antigo inteiro)."""
    E.mexe_ficha(num, animacao_pendente={"pedido": pedido, "modo": modo, "desde": E.agora()})
    try:
        return _animar(num, pedido, msg_id, modo)
    finally:
        E.mexe_ficha(num, animacao_pendente=None)


def _animar(num, pedido=None, msg_id=None, modo=None):
    """Roda o animador; devolve a resposta dele (resumida). Antes e depois, as fotos dos blocos e a conferência.
    modo="revisar": a revisão de edição do vídeo inteiro (o maestro pediu revisar_video; 21/10/2026, "aprovo o plano
    pedido-limpo": antes era a lista de palavras PEDE_REVISAO, e "olha os erros" num ajuste virava revisão completa)."""
    p = E.pasta(num); a = p / "animacao"
    E.mexe_ficha(num, progresso=5, passos=[])       # os passos da rodada anterior saem da tela
    preparar(num)
    cena = a / "cena.html"
    if cena.exists():
        (a / "versoes").mkdir(exist_ok=True)
        shutil.copy2(cena, a / "versoes" / f"cena-{time.strftime('%Y%m%d-%H%M%S')}.html")
        try:
            fotos_dos_blocos(num, "antes")
        except Exception:
            pass
    # 25/10/2026 (ele: "limpa o animador antigo e prepara o novo para fazer quando falha a primeira vez"): só o animador
    # novo. Antes, quando ele falhava, caía no animador antigo (até 36 min e US$ 1 a 2; 5 vezes de 19 a 22/10) e o
    # "roteiro refeito" ia sempre ao antigo. Agora o novo tenta de novo uma vez; falhou as duas, a cena volta como estava
    # e o erro sobe (o servidor conta no chat)
    refeito = bool(pedido) and pedido.startswith("O ROTEIRO FOI REFEITO")
    tinha_cena = cena.exists()
    if refeito and cena.exists():
        cena.unlink()                     # a cena antiga ficou em versoes/; a nova sai inteira para o roteiro de agora
    if not cena.exists():
        rodada = lambda: AN.primeira(num)
    elif modo == "revisar":                                             # 19/10/2026: "revisa a edição"
        rodada = lambda: AN.revisar_e_consertar(num)
    else:
        rodada = lambda: AN.ajustar(num, pedido)
    erros = []
    for tentativa in (1, 2):
        ok, frase = rodada()
        if ok:
            fotos_dos_blocos(num, "depois")
            E.mexe_ficha(num, progresso=None)
            return frase + (f" (Na 1ª tentativa o animador falhou: {erros[0]}; deu certo na 2ª.)" if erros else "")
        erros.append(frase)
        E.evento(num, f"animador novo não deu na {tentativa}ª tentativa: {str(frase)[:200]}")
    # as duas falharam: a cena de antes volta (sem cena antes, a primeira animação fica sem); o roteiro refeito que não
    # ganhou cena nova fica com a de antes até ele pedir de novo
    versoes = sorted((a / "versoes").glob("cena-*.html")) if (a / "versoes").exists() else []
    if tinha_cena and versoes and not cena.exists():
        shutil.copy2(versoes[-1], cena)
    E.mexe_ficha(num, progresso=None)
    raise RuntimeError(f"o animador falhou duas vezes ({erros[-1]})")


def conferir(num):
    """A conferência sem IA (régua e tela vazia) depois de "voltar como estava" (19/10/2026: o servidor já chamava
    animacao.conferir, que não existia, e a conferência ficava a da versão desfeita)."""
    regua = _regua_inteira(num)
    conf = {"quando": E.agora(), "quem": "régua (depois de voltar a versão)", "regua": [{k: x[k] for k in ("de", "tipo", "msg")} for x in regua],
            "opiniao": {}, "vazios": [x for x in regua if x["tipo"] == "vazio"], "consertos": [], "sobrou": [], "fala": [], "custo": []}
    E._grava(E.pasta(num) / "animacao/conferencia.json", json.dumps(conf, ensure_ascii=False, indent=1))
    return conf


RODADAS_REGUA = 2


VAZIO = 4.5      # média de bordas do quadro (270x480); calibrado em 17/10/2026: #204 vazio aos 0 s = 2,4; com conteúdo 7,3 a 11,5


def comeco_vazio(num):
    """Molde curso (17/10/2026): o título fica de 0 a 3 s e nenhum quadro do 1º segundo e meio pode estar vazio.
    Mede as bordas de cada quadro de 0 a 1,5 s (texto e imagem têm bordas; a tela azul vazia quase não tem)."""
    import tempfile, ver
    from PIL import Image, ImageFilter, ImageStat
    ts = [0.0, 0.25, 0.5, 0.75, 1.0, 1.25, 1.5]
    with tempfile.TemporaryDirectory() as d:
        feitos, _ = ver.quadros(num, ts, saida=Path(d))
        vazios = [t for t, f in zip(ts, feitos)
                  if ImageStat.Stat(Image.open(f).convert("L").resize((270, 480)).filter(ImageFilter.FIND_EDGES)).mean[0] < VAZIO]
    return [{"de": t, "ate": t + .25, "tipo": "vazio", "msg": f"tela quase vazia aos {t:.2f} s: no molde curso o título aparece já no 0 s e fica até 3 s"}
            for t in vazios]


TRECHOS_REGUA = 3      # 20/10/2026: a régua mede o vídeo em 3 trechos ao mesmo tempo (a VPS tem 8 núcleos)


def _trechos(num, k=TRECHOS_REGUA):
    """Os trechos da régua, cortados entre blocos: cada um vai do início do 1º bloco ao fim do último + 1,5 s (o selo
    do bloco entra até 1,5 s depois), e o último até o fim do vídeo (a assinatura vem depois da voz)."""
    bs = json.loads((E.pasta(num) / "narracao/completo.json").read_text())["blocos"]
    if len(bs) < 2 * k:
        return [(0.0, None)]
    grupos = [bs[round(i * len(bs) / k):round((i + 1) * len(bs) / k)] for i in range(k)]
    return [(0.0 if i == 0 else g[0]["ini"], None if i == k - 1 else g[-1]["fim"] + 1.5) for i, g in enumerate(grupos)]


MAX_SELOS = 4                # regras/ANIMADOR.md: "Máximo 4 selos por vídeo"


def _regua_inteira(num):
    """A régua, a tela vazia e o começo vazio. 20/10/2026 (ele: "monitora se a velocidade está melhor"; num ajuste do #305,
    de 309 s, a IA levou 132 s e as duas medidas inteiras ~160 s): as medidas rodam ao mesmo tempo, e a régua em trechos."""
    import tempfile, ver
    from concurrent.futures import ThreadPoolExecutor
    cena = E.pasta(num) / "animacao/cena.html"
    proibido = codigo_perigoso(cena.read_text()) if cena.exists() else []
    if proibido:
        return [{"de": 0, "tipo": "erro", "msg": f"a cena usa código que sai da prévia ({', '.join(proibido)}): tire isso; a cena "
                                                 "só usa a biblioteca do estúdio (T.*), GSAP e o próprio desenho"}]
    for f in (E.pasta(num) / "revisao/regua").glob("*.png"):
        f.unlink()

    def regua_trecho(i, de, ate):
        _, probs = ver.regua(num, de, ate, prefixo=f"{i + 1}-", limpar=False)
        return probs

    # 24/10/2026 (editor-molde-numeros-recado): a tela parada nos mesmos quadros; desde consertos-do-369 em todos os vídeos
    # (no #369, aos 28 s, só a multidão de fundo, sem nada nosso por cima)
    mede_parado = True

    def vazio():
        # conferir-o-pedido-e-faixa-preta (23/10/2026): nos mesmos quadros, a faixa preta na tela (a tarja de um vídeo de
        # origem que a peça não cortou); medida aqui porque o arquivo temporário some ao sair
        with tempfile.TemporaryDirectory() as d:
            _, feitos, _ = ver.percorrer(num, .5, d)
            return (trechos_vazios(feitos), [(t, f) for t, q in feitos for f in faixa_preta(q)],
                    trechos_parados(feitos) if mede_parado else [])

    trechos = _trechos(num)
    with ThreadPoolExecutor(max_workers=len(trechos) + 2) as ex:
        fr = [ex.submit(regua_trecho, i, de, ate) for i, (de, ate) in enumerate(trechos)]
        # 17/10/2026 ("aprovo o plano animacao-sem-buraco"): tela vazia no vídeo inteiro, a cada 0,5 s (~21 s no #204)
        fv = ex.submit(vazio)
        fc = ex.submit(comeco_vazio, num) if E.ler_ficha(num).get("molde") in ("curso", "conferir") else None  # título de 0 a 3 s
        try:
            probs = [x for f in fr for x in f.result()]
        except Exception as e:
            return [{"de": 0, "tipo": "erro", "msg": f"a régua não rodou: {str(e)[:120]}"}]
        # o mesmo problema dos dois lados de um corte entre trechos vira um só
        juntos = []
        for x in sorted(probs, key=lambda x: (x["tipo"], x["msg"], x["ini"])):
            y = juntos[-1] if juntos else None
            if y and y["tipo"] == x["tipo"] and y["msg"] == x["msg"] and x["ini"] <= y["fim"] + .5:
                y["fim"] = max(y["fim"], x["fim"])
            else:
                juntos.append(dict(x))
        r = [{"de": round(x["ini"], 1), "ate": round(x["fim"] + .25, 1), "tipo": x["tipo"], "msg": x["msg"]}
             for x in sorted(juntos, key=lambda x: x["ini"])]
        # 21/10/2026 ("aprovo o plano pedido-limpo"): com MAX_SELOS selos pedidos já na tela, o que falta não é cobrado
        # (a regra é no máximo 4, ANIMADOR.md; no #316 a régua cobrou dois a mais e o vídeo foi a 6). Conta no vídeo
        # inteiro: a régua mede em trechos
        import regua as RG
        faltas_selo = [x for x in r if x["tipo"] == "falta-selo"]
        if faltas_selo and len(RG.selos_pedidos(E.pasta(num))) - len(faltas_selo) >= MAX_SELOS:
            r = [x for x in r if x["tipo"] != "falta-selo"]
        try:
            vazios, faixas, parados = fv.result()
            r += [{"de": p["de"], "ate": p["ate"], "tipo": "parado",
                   "msg": f"tela parada de {p['de']:.1f} a {p['ate']:.1f} s (nada muda além do fundo e da legenda): faça algo "
                          f"entrar no meio, na palavra-chave dita ali (o número, a tarja, a barra, um selo)"}
                  for p in parados]
            r += [{"de": v["de"], "ate": v["ate"], "tipo": "vazio",
                   "msg": f"tela vazia de {v['de']:.1f} a {v['ate']:.1f} s (só o fundo, no máximo a legenda): a cena anterior fica ou a seguinte entra antes"}
                  for v in vazios]
            # durante a capa (T.capa(ate)) a faixa é da capa, que o agente de capa faz, não do take: lá o animador não
            # conserta (no #354 a capa tem a tarja do vídeo da Veja atrás dos logos; achado faixa-preta.1)
            mc = re.search(r"T\.capa\(\s*([\d.]+)", (E.pasta(num) / "animacao/cena.html").read_text()) if (E.pasta(num) / "animacao/cena.html").exists() else None
            capa_ate = float(mc.group(1)) if mc else 0
            juntas = []                         # a mesma faixa em quadros seguidos vira um ponto só
            for t, (y0, y1) in faixas:
                if t < capa_ate:
                    continue
                j = next((j for j in juntas if t - j["ate"] <= .51 and abs(j["y"][0] - y0) <= 20), None)
                if j:
                    j["ate"] = t
                else:
                    juntas.append({"de": t, "ate": t, "y": (y0, y1)})
            r += [{"de": j["de"], "ate": round(j["ate"] + .5, 2), "tipo": "faixa-preta",
                   "msg": f"faixa preta de {j['y'][1] - j['y'][0]} px na tela (y {j['y'][0]}-{j['y'][1]}) de {j['de']:.1f} a "
                          f"{j['ate'] + .5:.1f} s: tarja do vídeo de origem; amplie ou suba o vídeo até ela sair da tela"}
                  for j in juntas]
        except Exception as e:
            r.append({"de": 0, "tipo": "erro", "msg": f"a medida de tela vazia não rodou: {str(e)[:120]}"})
        if fc:
            try:
                r = fc.result() + r
            except Exception as e:
                r.append({"de": 0, "tipo": "erro", "msg": f"a medida do começo vazio não rodou: {str(e)[:120]}"})
    return r


def _sem_legenda(png, modo):
    from PIL import Image
    im = Image.open(png).convert(modo)
    sem = Image.new(modo, (1080, 1660)); sem.paste(im.crop((0, 0, 1080, 1200)), (0, 0)); sem.paste(im.crop((0, 1460, 1080, 1920)), (0, 1200))
    return sem.resize((270, 415))


def _vazia(png):
    """Tela sem nada além do fundo (a faixa da legenda, y 1200-1460, não conta: legenda sozinha também é tela vazia):
    poucas bordas e parecida com o fundo puro."""
    from PIL import ImageChops, ImageFilter, ImageStat
    if ImageStat.Stat(_sem_legenda(png, "L").filter(ImageFilter.FIND_EDGES)).mean[0] >= VAZIO_TELA:
        return False
    if not FUNDO_TELA.exists():
        return True
    return ImageStat.Stat(ImageChops.difference(_sem_legenda(png, "RGB"), _sem_legenda(FUNDO_TELA, "RGB")).convert("L")).mean[0] < VAZIO_DIF


TARJA_MIN = .02      # da altura: abaixo disso não é tarja (o #305 tem ~1% de borda escura embaixo; calibrado em 23/10)


def tarja_por_linhas(arq, pontos, alto):
    """24/10/2026 (#373: a faixa preta de cima tem a legenda do canal em letras brancas, e o cropdetect parava na primeira
    linha de letras: mediu 12,5% de uma faixa de ~33%): linha a linha, conta como faixa a linha quase só de preto e de
    branco (letra sobre preto), sem os meios-tons de uma imagem de verdade. Vale a MENOR faixa entre os quadros."""
    import numpy as np, cv2
    cimas, baixos = [], []
    for ini, d in pontos:
        for k in (0.2, d / 2, max(0.2, d - 0.2)):
            png = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-ss", f"{ini + k:.2f}", "-i", str(arq), "-frames:v", "1",
                                  "-vf", "scale=180:-2,format=gray", "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True).stdout
            q = cv2.imdecode(np.frombuffer(png, np.uint8), cv2.IMREAD_GRAYSCALE) if png else None
            if q is None:
                continue
            preto, meio = (q < 28).mean(axis=1), ((q >= 28) & (q <= 170)).mean(axis=1)
            # calibrado no #373 (24/10/2026): linhas de letra sobre preto têm 49-62% de preto e até 29% de meio-tom; a imagem
            # do debate começa com 36-61% de meio-tom. O meio-tom separa faixa de imagem
            faixa = (preto >= .40) & (meio <= .30)
            # do alto para baixo até a primeira linha de imagem (2 linhas seguidas fora da faixa, para pular o serrilhado)
            # e a faixa começa na borda com linhas de preto puro (uma foto escura, como o Senado no alto do #340, não começa)
            puro = (q < 12).mean(axis=1) >= .95

            def corre(linhas, borda):
                if not borda[:3].all():
                    return 0
                n = 0
                for i in range(len(linhas) - 1):
                    if not linhas[i] and not linhas[i + 1]:
                        return n
                    n += 1
                return n
            h = q.shape[0]
            cimas.append(corre(faixa, puro) / h); baixos.append(corre(faixa[::-1], puro[::-1]) / h)
    return (min(cimas) if cimas else 0.0), (min(baixos) if baixos else 0.0)


def tarja_do_video(arq, de=None, dura=None):
    """A tarja preta gravada no próprio vídeo (em cima e embaixo, frações da altura), medida pelo cropdetect do ffmpeg;
    vale a MENOR faixa vista (uma cena escura não vira tarja). Com `de`, mede só o trecho que o take usa (de, de + dura,
    até 4 s): a tarja muda ao longo do vídeo (#354: 140 px no começo, ~600 px no trecho do take dos 18,45 s). Sem `de`, 3
    pontos do vídeo. Calibrado em 23/10/2026 ("aprovo o plano conferir-o-pedido-e-faixa-preta"): 13 vídeos sem tarja,
    0. Devolve [cima, baixo]."""
    arq = str(arq)
    alto = int(subprocess.check_output(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries", "stream=height",
                                        "-of", "csv=p=0", arq], timeout=30))
    if de is not None:
        pontos = [(max(0, de), min(4, max(.5, dura or 2)))]
    else:
        dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", arq], timeout=30))
        pontos = [(dur * p, 1) for p in (.1, .5, .9)]
    cimas, baixos = [], []
    for ini, d in pontos:
        r = subprocess.run(["ffmpeg", "-v", "info", "-ss", f"{ini:.2f}", "-i", arq, "-t", f"{d:.2f}", "-vf", "cropdetect=limit=24:round=2:reset=0",
                            "-f", "null", "-"], capture_output=True, text=True, timeout=60)
        m = re.findall(r"crop=\d+:(\d+):\d+:(\d+)", r.stderr)
        if m:
            h, y = map(int, m[-1])
            cimas.append(y); baixos.append(alto - y - h)
    cima, baixo = (min(cimas) / alto, min(baixos) / alto) if cimas else (0.0, 0.0)
    # 24/10/2026: a faixa com letras (a legenda gravada sobre preto) também é faixa; vale a maior das duas medidas
    try:
        c2, b2 = tarja_por_linhas(arq, pontos, alto)
        cima, baixo = max(cima, c2), max(baixo, b2)
    except Exception:
        pass
    return [round(cima, 4) if cima >= TARJA_MIN else 0, round(baixo, 4) if baixo >= TARJA_MIN else 0]


def tarjas_dos_videos(num, cena):
    """{"<src>@<corte>": [cima, baixo]} de cada take da cena (T.tarjas na peça de take, a mesma chave do rosto), medida no
    trecho que o take usa e guardada em animacao/tarjas.json pela data do arquivo: cada take é medido uma vez (~1 s)."""
    p = E.pasta(num); cache_arq = p / "animacao/tarjas.json"
    try:
        cache = json.loads(cache_arq.read_text())
    except (OSError, ValueError):
        cache = {}
    saida, mudou = {}, False
    # 24/10/2026: a lista de takes que a prévia anotou (o vídeo, o corte e a duração já calculados); sem ela, o texto da cena
    try:
        import hashlib
        d_t = json.loads((p / "animacao/takes.json").read_text())
        reais = d_t["takes"] if d_t.get("cena") == hashlib.md5(cena.encode()).hexdigest() else None
    except (OSError, ValueError, KeyError):
        reais = None
    def _do_texto():
        for m in re.finditer(r"T\.take\(\{(.*?)\}\);", cena, re.S):
            corpo = m.group(1)
            num_de = lambda nome: re.search(rf"\b{nome}:\s*([\d.]+)", corpo)
            yield ((re.search(r"\bsrc:\s*['\"]([^'\"]+)['\"]", corpo) or [None, "referencia/video.mp4"])[1],
                   float(num_de("corte").group(1)) if num_de("corte") else 0.0,
                   float(num_de("fim").group(1)) - float(num_de("ini").group(1)) if num_de("fim") and num_de("ini") else 2.0)
    fontes = [(x["src"], max(0.0, float(x["corte"])), float(x.get("dura") or 2.0)) for x in reais] if reais is not None else \
        list(_do_texto()) + [(s, c, d) for s, c, d, _ in takes_anteriores(num)]
    for src, corte, dura in fontes:
        arq = (p / src).resolve()
        if not str(arq).startswith(str(p.resolve()) + "/") or not arq.exists():
            continue
        chave = f"{src}@{corte:.2f}"
        marca = f"{chave}|{dura:.2f}|{int(arq.stat().st_mtime)}|v2"     # v2 (24/10/2026): a faixa com letras também conta
        if marca not in cache:
            try:
                cache[marca] = tarja_do_video(arq, corte, dura)
            except Exception as ex:
                E.evento(num, f"tarja de {chave} não foi medida: {str(ex)[:120]}")
                cache[marca] = [0, 0]
            mudou = True
        if any(cache[marca]):
            saida[chave] = cache[marca]
    if mudou:
        E._grava(cache_arq, json.dumps(cache, ensure_ascii=False, indent=1))
    return saida


def faixa_preta(q):
    """A faixa preta no topo da tela (quadro da prévia): [(0, y_ate)] em px de 1920, ou []. Linhas com 95% dos pontos
    pretos absolutos (cada cor abaixo de 6), a partir do alto, com 30 px ou mais. Calibrado em 23/10 no #354 (tarja da
    Veja: média 0,03, faixa de 182 px antes e 0 depois do conserto); o fundo azul-marinho e a foto noturna escurecida do
    cartão do #334 (média 5,7) não entram. Só o topo: é onde a tarja aparece com o take em tela cheia; na base, o pé
    escuro do take já cobre, e no meio da tela o preto é desenho (o cartão escuro do #334 tinha 80 px quase pretos)."""
    import numpy as np
    from PIL import Image
    a = np.asarray(Image.open(q).convert("RGB").resize((108, 192))).astype(int)
    preta = (a.max(axis=2) < 6).mean(axis=1) >= .95
    ate = 0
    while ate < len(preta) and preta[ate]:
        ate += 1
    return [(0, ate * 10)] if ate >= 3 else []


PARADO_MIN = .8        # % de pixels que mudam (mais de 40 níveis) para contar como mudança; calibrado no #368 (24/10/2026):
PARADO_VEZES = 2.5     # só a aproximação lenta do fundo dá 0,05 a 0,2 % (3 % em foto cheia de detalhe); o selo entrando, ~1 %
PARADO_MAX = 2.5       # s sem mudança: a regra dos moldes números e micro doc é algo mudar a cada 2 s (a medida é a cada 0,5 s)


def trechos_parados(feitos, de=0.0):
    """24/10/2026 ("pode fazer o editor do molde números com o recado"): a tela parada medida por programa, não por IA
    (no #299 o "parado" da IA deu 6 queixas falsas). [(t, quadro)] a cada 0,5 s → [{de, ate}] com mais de PARADO_MAX s
    sem mudança na área do conteúdo (y 200 a 1270: a legenda embaixo muda sempre e não conta). Mudança = pixels que
    mudaram acima de PARADO_VEZES vezes o quartil de baixo dos ±2 s em volta (o fundo que aproxima devagar; a mediana
    subia com as trocas vizinhas e escondia o selo entrando aos 3 s do #368)."""
    from PIL import Image, ImageChops
    ims = [(t, Image.open(q).convert("L").crop((0, 200, 1080, 1270)).resize((270, 268))) for t, q in feitos]
    frac = []
    for (t0, a), (t1, b) in zip(ims, ims[1:]):
        h = ImageChops.difference(a, b).histogram()
        frac.append((t1, 100 * sum(h[40:]) / max(1, sum(h))))
    mudou = [de]
    for t, f in frac:
        perto = sorted(g for u, g in frac if abs(u - t) <= 2)
        base = perto[len(perto) // 4] if perto else 0
        if f > max(PARADO_MIN, PARADO_VEZES * base):
            mudou.append(t)
    fim = feitos[-1][0] if feitos else de
    mudou.append(fim)
    return [{"de": round(a, 1), "ate": round(b, 1)} for a, b in zip(mudou, mudou[1:]) if b - a > PARADO_MAX]


VAZIO_TELA = 3.5     # média de bordas fora da faixa da legenda; calibrado no #299 em 17/10/2026: só o fundo 1,54 a 1,56
                     # (também com a legenda sozinha); com conteúdo 5,96 a 14,96 (8 quadros)


# 22/10/2026 ("aprovo o plano regua-sem-alarme-falso"; #340: o vídeo do Lula escurecido por baixo do PLACAR, 46,5-48 s,
# deu "tela vazia"; imagem escura e borrada tem poucas bordas): tela vazia é também PARECIDA com o fundo puro
# (ferramentas/modelos/fundo-tela.png, a foto do fundo do tocador sem nada). Diferença média calibrada em 12 quadros
# que a régua acusou em 6 vídeos: vazios de verdade 0,9 a 5,0; com conteúdo 6,8 a 23,2 (o "O NÍVEL DE MALDADE" do #304
# aos 49,5 s tinha 3,4 de bordas e também saía vazio)
VAZIO_DIF = 6.0
FUNDO_TELA = E.RAIZ / "ferramentas/modelos/fundo-tela.png"


def trechos_vazios(feitos):
    """[(t, quadro)] a cada 0,5 s → [{de, ate}] dos trechos de tela vazia. Um quadro só já conta (animacao-sem-buraco:
    no #204 os vazios de um quadro eram todos começo de bloco, a tela só com a legenda)."""
    vazios = []
    for t, q in feitos:
        if not _vazia(q):
            continue
        if vazios and t - vazios[-1]["ultimo"] < .51:
            vazios[-1]["ultimo"] = t
        else:
            vazios.append({"de": t, "ultimo": t})
    return [{"de": v["de"], "ate": round(v["ultimo"] + .5, 2)} for v in vazios]


def pasta_rodada(num, sufixo=""):
    """animacao/assistir/<data_hora>[-sufixo]/ com a cena.html que foi assistida; as rodadas anteriores ficam
    (18/10/2026, "aprovo o plano olhos.10")."""
    a = E.pasta(num) / "animacao"
    d = a / "assistir" / (time.strftime("%Y-%m-%d_%H-%M-%S") + (f"-{sufixo}" if sufixo else ""))
    d.mkdir(parents=True, exist_ok=True)
    if (a / "cena.html").exists():
        shutil.copy2(a / "cena.html", d / "cena.html")
    return d


def assistir_previa(num, modelo="opus", quem="olhos"):
    """A prévia inteira até o fim da assinatura, um quadro a cada 0,5 s em animacao/olhar/todos/ (17/10/2026, "aprovo o
    plano olhos-na-animacao"). Com eles: 1) o programa mede a tela vazia em cada quadro (2 seguidos ou mais = defeito);
    2) os Olhos (conteudo/olhos/opiniao.py) assistem no ritmo deles (0,5 s até 15 s, depois 3,5 s, e o último quadro),
    com a fala de cada instante e nada do roteiro. Devolve {fim, quadros: [(t, png)], vazios: [{de, ate}], olhos}."""
    import ver, olhos_ponte
    from PIL import Image
    p = E.pasta(num); d = p / "animacao/olhar"
    shutil.rmtree(d, ignore_errors=True)
    fim, feitos, _ = ver.percorrer(num, .5, d / "todos")
    vazios = trechos_vazios(feitos)
    escolha = [(t, f) for t, f in feitos if t < 15 or abs((t - 15) / 3.5 - round((t - 15) / 3.5)) < 1e-6]
    if escolha[-1] != feitos[-1]:
        escolha.append(feitos[-1])
    ol = d / "olhos"; (ol / "quadros").mkdir(parents=True)
    ws = json.loads((p / "narracao/palavras.json").read_text()) if (p / "narracao/palavras.json").exists() else []
    folha = []
    for i, (t, png) in enumerate(escolha):
        Image.open(png).convert("RGB").resize((360, 640)).save(ol / f"quadros/t{t:06.2f}.jpg", quality=80)
        ate = escolha[i + 1][0] if i + 1 < len(escolha) else fim
        folha.append({"t": t, "quadro": f"quadros/t{t:06.2f}.jpg", "falado": " ".join(w[2] for w in ws if w[0] < ate and w[1] > t)})
    (ol / "folha.json").write_text(json.dumps({"video": f"prévia do #{int(num)}", "duracao": round(fim, 2), "quadros": len(folha),
                                               "folha": folha, "fala_inteira": " ".join(w[2] for w in ws)}, ensure_ascii=False, indent=1))
    # modelo (18/10/2026, "aprovo o plano olhos-do-animador"): a conferência final usa o Opus; os olhos do animador
    # (ver.py --assistir) usam o Sonnet, para o juiz final não ser o mesmo que o animador consultou
    try:
        op = olhos_ponte.opinar(ol, modelo=modelo)
    except Exception as ex:
        op = {"erro": f"os Olhos não rodaram: {str(ex)[:200]}"}
    if op.get("uso"):
        with open(p / "animacao/gasto.jsonl", "a") as g:
            g.write(json.dumps({"quando": E.agora(), "quem": quem, "modelo": op.get("modelo"), **op["uso"]}) + "\n")
    return {"fim": fim, "quadros": feitos, "vazios": vazios, "olhos": op}


def respostas_do_animador(texto):
    """As linhas FEITO / NAO_E / FALA / CUSTO da resposta do animador no conserto dos Olhos → {tipo: [{t, msg}]}.
    Linha fora do formato é ignorada (testes/olhos_conserta.py)."""
    r = {"FEITO": [], "NAO_E": [], "FALA": [], "CUSTO": []}
    for linha in (texto or "").splitlines():
        # "CUSTO: 3-8 s · …" (uma faixa) vale o começo; antes o "-8 s" ia parar no começo da mensagem (21/10/2026)
        m = re.match(r"\s*[-*]?\s*(FEITO|NAO_E|NÃO_É|FALA|CUSTO)\s*:\s*([\d.,]+)(?:\s*[-–a]\s*[\d.,]+)?\s*s?\s*·?\s*(.*)", linha.strip(), re.I)
        if m:
            tipo = {"NÃO_É": "NAO_E"}.get(m.group(1).upper(), m.group(1).upper())
            r[tipo].append({"t": float(m.group(2).replace(",", ".")), "msg": m.group(3).strip()})
    return r


# só "vazio" a medida confirma; "parado" ela não mede (no #299 o "parad" descartou 6 queixas de tela parada como falsas)
FALA_DE_VAZIO = re.compile(r"vazi|sem nada|só o fundo", re.I)


if __name__ == "__main__":
    print(animar(int(sys.argv[1]), " ".join(sys.argv[2:]) or None))
