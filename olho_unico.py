"""O olho único, em observação (23/10/2026, "aprovo o plano olho-unico-observacao"; teste em
~/Projetos/KITEBIZ/conteudo/ESTUDIO-V2-OLHO-UNICO-CASOS.md: 5 passou, 2 em parte, 0 falhou nas prévias, contra 4/1/2 do
editor de hoje).

Um olho só acompanha o vídeo: escreve o caderno do material na pauta (videos/<n>/olho/caderno.json), olha cada prévia
pronta e escreve no chat "Olho (em teste)" (só mostra: não conserta nem trava), e nos pedidos de tela localiza o que ele
apontou e passa ao animador. `olho/DESLIGADO` (na raiz do estúdio) desliga na hora, sem reiniciar. Nada aqui pode
segurar o vídeo: todo erro vira evento e o estúdio segue como antes.
"""
import json, re, subprocess, sys, threading, time, traceback
from pathlib import Path

import estudio as E
import animador_novo as AN
from PIL import Image, ImageDraw, ImageFont

if str(E.RAIZ / "ferramentas") not in sys.path:
    sys.path.insert(0, str(E.RAIZ / "ferramentas"))     # ver.py (como em animacao.py)

CHAVE = E.RAIZ / "olho/DESLIGADO"
PRAZO = 90          # s: o máximo que o olho soma a um ajuste (consertos-da-revisao; antes refazia o caderno ali, minutos)
_trava = threading.Lock()
_olhando, _de_novo, _no_caderno = set(), set(), set()     # uma olhada e um caderno por vídeo de cada vez
REGISTRO = E.RAIZ / "olho/registro.jsonl"         # para comparar em uma semana com o editor e com as reclamações dele
MODELO = "sonnet"
FONTE = str(E.RAIZ / "web/fontes/impact.ttf")


def ligado():
    return not CHAVE.exists()


def pasta(num):
    d = E.pasta(num) / "olho"; d.mkdir(exist_ok=True)
    return d


def registra(num, momento, r):
    linha = {"quando": E.agora(), "num": int(num), "momento": momento, **r}
    for arq in (pasta(num) / "historico.jsonl", REGISTRO):
        arq.parent.mkdir(exist_ok=True)
        with open(arq, "a") as h:
            h.write(json.dumps(linha, ensure_ascii=False, default=str) + "\n")


def pedir(num, blocos, quem, limite=300):
    t0 = time.time()
    texto, uso = AN.opus(num, blocos, quem, limite=limite, modelo=MODELO)
    m = re.search(r"\{.*\}", texto or "", re.S)
    try:
        d = json.loads(m.group(0)) if m else {"erro": (uso or {}).get("erro") or "sem resposta"}
    except ValueError:
        d = {"erro": "resposta sem JSON válido", "bruto": (texto or "")[:800]}
    d["_segundos"] = round(time.time() - t0, 1)
    d["_usd"] = (uso or {}).get("usd")
    return d


# ---------- ver ----------

def grade(itens, saida, colunas=10, cel=(180, 320)):
    """[(rótulo, jpg)] numa imagem só, rótulo em amarelo no canto."""
    f = ImageFont.truetype(FONTE, 26)
    folha = Image.new("RGB", (colunas * cel[0], ((len(itens) + colunas - 1) // colunas) * cel[1]), (20, 20, 20))
    for i, (rot, arq) in enumerate(itens):
        im = Image.open(arq).convert("RGB"); im.thumbnail(cel)
        x, y = (i % colunas) * cel[0], (i // colunas) * cel[1]
        folha.paste(im, (x + (cel[0] - im.width) // 2, y + (cel[1] - im.height) // 2))
        ImageDraw.Draw(folha).text((x + 4, y + 2), rot, font=f, fill=(255, 220, 0), stroke_width=2, stroke_fill=(0, 0, 0))
    folha.save(saida, quality=85)
    return saida


def blocos_no_tempo(num):
    bs = E.blocos(num)
    try:
        tempos = json.loads((E.pasta(num) / "narracao/completo.json").read_text())["blocos"]
    except (OSError, KeyError, ValueError):
        tempos = []
    linhas = []
    for i, b in enumerate(bs):
        t = tempos[i] if i < len(tempos) else {}
        quando = f"{t['ini']:.1f}-{t['fim']:.1f} s" if isinstance(t.get("ini"), (int, float)) and isinstance(t.get("fim"), (int, float)) else "?"
        linhas.append(f"- bloco {b['n']} ({quando}) · {'nós' if b['nosso'] else b['quem']} · fala: {b['fala'][:180]} · tela: {b['tela'][:260]}")
    return "\n".join(linhas)


def fala_por_segundo(ws):
    seg = {}
    for w in ws:
        seg.setdefault(int(w[0]), []).append(w[2])
    return "\n".join(f"{s} s: {' '.join(p)}" for s, p in sorted(seg.items()))


def palavras_da_voz(num):
    arq = E.pasta(num) / "narracao/palavras.json"
    return json.loads(arq.read_text()) if arq.exists() else []


def janela(im, y_meio):
    """A faixa de linhas do vídeo (o take) que contém y_meio: linhas onde menos da metade dos pixels é o azul da página."""
    import numpy as np
    a = np.asarray(im.resize((108, 192))).astype(int)
    azul = ((a[..., 2] > a[..., 0] + 40) & (a[..., 2] > a[..., 1] + 20)).mean(axis=1) > .5
    i = min(191, max(0, int(y_meio / 10)))
    if azul[i]:
        return None
    de = i
    while de > 0 and not azul[de - 1]:
        de -= 1
    ate = i
    while ate < 191 and not azul[ate + 1]:
        ate += 1
    return de * 10, (ate + 1) * 10


def medir_rostos(feitos, saida):
    """O programa mede cada rosto grande contra a janela do vídeo em que ele está (a IA, sozinha, descartou o rosto cortado
    da Erika no teste) e desenha a caixa (verde) e a janela (vermelho). Devolve ([(t, quadro marcado)], [medidas])."""
    saida.mkdir(parents=True, exist_ok=True)
    marcados, medidas = [], []
    for t, q in feitos:
        im = Image.open(q).convert("RGB"); dr = ImageDraw.Draw(im)
        for x, y, l, a in AN.rostos(q):
            if l < 140 or t < 1.5:      # rosto pequeno (bolinha, plateia) não é o take; o 1 s de capa corta rosto de propósito
                continue
            dr.rectangle([x, y, x + l, y + a], outline=(0, 255, 0), width=6)
            j = janela(im, y + a / 2)
            if not j:
                continue
            topo, base = j
            dr.rectangle([4, topo, 1076, base], outline=(255, 0, 0), width=4)
            # calibrado em 23/10 no #306 (versão das 20:16, que ele reprovou: 11 avisos; a publicada: 4); "cabeça cortada
            # em cima" acusava a publicada (a faixa azul do título parece borda do vídeo em tela cheia) e saiu
            if y + a > base - 15:
                medidas.append(f"{t:.1f} s: queixo na borda de baixo do vídeo (queixo y {y + a}, vídeo vai de {topo} a {base}): rosto cortado")
            if base - topo > 300 and (y - topo) > .45 * (base - topo):
                medidas.append(f"{t:.1f} s: rosto baixo no vídeo, sobra {y - topo} px de fundo acima da testa (vídeo de {topo} a {base})")
        faixa = imagem_em_faixa(im)
        if faixa and t >= 1.5:
            medidas.append(f"{t:.1f} s: imagem numa faixa: começa em y {faixa[0]} (topo vazio) e ocupa só {faixa[1] - faixa[0]} px "
                           "de 1920: a foto ou o vídeo deve ir ao alto, na largura toda")
        arq = saida / Path(q).name; im.save(arq, quality=85); marcados.append((t, arq))
    return marcados, medidas


def imagem_em_faixa(im):
    """25/10/2026 (#382: Lula e Janones, o ato em BH e os três no SBT ficaram numa faixa de y ~300 a ~1000, com o azul
    da página em cima e meia tela vazia embaixo): (topo, base) da maior faixa de imagem (linhas que não são o azul da
    página) quando ela não encosta no alto, é a maior coisa da tela e não passa de 55% da altura; senão None."""
    import numpy as np
    a = np.asarray(im.resize((108, 192))).astype(int)
    azul = ((a[..., 2] > a[..., 0] + 40) & (a[..., 2] > a[..., 1] + 20)).mean(axis=1) > .5
    faixas, i = [], 0
    while i < 192:
        if azul[i]:
            i += 1
            continue
        de = i
        while i < 192 and not azul[i]:
            i += 1
        faixas.append((de * 10, i * 10))
    if not faixas:
        return None
    topo, base = max(faixas, key=lambda f: f[1] - f[0])
    alto = base - topo
    return (topo, base) if topo >= 150 and 300 <= alto <= .55 * 1920 and topo < 900 else None


# ---------- o caderno ----------

PAPEL = """Você é o OLHO do estúdio da @newsbr360 (reels de checagem, 1080x1920). Você acompanha um vídeo do começo ao fim:
olha o material, olha a edição e responde ao editor. Você só vê e descreve, com o segundo exato; não edita. Seja concreto:
quem aparece (pelo nome, quando der para saber pelo caderno, rótulo ou fala), onde na tela, o que cobre o quê.
Não invente: se não dá para ver, diga que não dá. Responda SÓ o JSON pedido, em português."""

MATERIAL = PAPEL + """

MOMENTO: MATERIAL. Abaixo estão as folhas de quadros do vídeo de referência e do material que o editor mandou (o rótulo em
amarelo diz a fonte e o segundo), de quem é cada vídeo, a fala com o tempo e os dados do post. Escreva o CADERNO deste
vídeo: tudo o que a edição vai querer usar depois.

JSON:
{"resumo": "do que trata o material, 2 frases",
 "pessoas": [{"nome": "...", "como_reconhecer": "roupa, lugar, cabelo", "onde": [{"fonte": "...", "de": s, "ate": s, "enquadramento": "rosto alto/baixo, cortado..."}]}],
 "falas": [{"quem": "...", "fonte": "...", "de": s, "ate": s, "texto": "trecho curto"}],
 "fotos_uteis": [{"fonte": "...", "t": s, "o_que_mostra": "...", "cuidado": "rosto de terceiro, marca, texto por cima..."}],
 "marcas": [{"fonte": "...", "de": s, "ate": s, "o_que": "logo de emissora, marca d'água, legenda queimada"}],
 "cortes_bruscos": [{"fonte": "...", "t": s}]}"""


def de_quem(pasta_fonte):
    """Conta, nome e título do post de onde veio o vídeo (info.json do yt-dlp ou meta.json da pauta). Sem isto o caderno
    chamava Rachel, Freixo e Boulos de "mulher loira", "homem de barba" (teste de 23/10)."""
    for arq in [pasta_fonte / "meta.json"] + sorted(pasta_fonte.glob("*.info.json")):
        try:
            d = json.loads(arq.read_text())
        except (OSError, ValueError):
            continue
        partes = [d.get("quem_postou") or d.get("uploader") or d.get("channel"), d.get("conta") or d.get("uploader_id"),
                  (d.get("title") or "")[:120], (d.get("legenda_do_post") or d.get("description") or "")[:240]]
        texto = " · ".join(str(x) for x in partes if x)
        if texto:
            return texto
    return ""


def fontes_do_material(num):
    p = E.pasta(num)
    fontes = [("referencia", p / "referencia/video.mp4")] if (p / "referencia/video.mp4").exists() else []
    return fontes + [(f"material/{v.parent.name}", v) for v in sorted(p.glob("material/*/video.mp4"))]


def fazer_caderno(num):
    p = E.pasta(num); d = pasta(num) / "material"; d.mkdir(exist_ok=True)
    blocos = [{"type": "text", "text": MATERIAL}]
    for nome, v in fontes_do_material(num):
        dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(v)]))
        passo = 1 if dur <= 60 else 2 if dur <= 120 else max(3, dur / 60)
        q = d / nome.replace("/", "_"); q.mkdir(exist_ok=True)
        for velho in q.glob("q*.jpg"):
            velho.unlink()
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(v), "-vf", f"fps=1/{passo},scale=360:-2", str(q / "q%03d.jpg")], check=True)
        itens = [(f"{nome.split('/')[-1][:8]} {i * passo:.0f}s", f) for i, f in enumerate(sorted(q.glob("q*.jpg")))]
        for k in range(0, len(itens), 30):
            blocos += [{"type": "text", "text": f"Folha de {nome} (a cada {passo:g} s), parte {k // 30 + 1}"},
                       AN.img(grade(itens[k:k + 30], d / f"{nome.replace('/', '_')}-{k // 30 + 1}.jpg"))]
        quem = de_quem(v.parent)
        if quem:
            blocos.append({"type": "text", "text": f"De quem é {nome}: {quem}"})
        pal = v.parent / "palavras.json"
        if pal.exists():
            blocos.append({"type": "text", "text": f"Fala de {nome} por segundo:\n" + fala_por_segundo(json.loads(pal.read_text()))[:5000]})
    soltas = sorted(p.glob("referencia/imagens/*.jpg")) + sorted(x for x in p.glob("material/**/*.jpg") if "quadros" not in x.parts)[:30]
    if soltas:
        blocos += [{"type": "text", "text": "Imagens soltas do material (sem vídeo)"},
                   AN.img(grade([(x.parent.name[:10] + "/" + x.stem[:6], x) for x in soltas[:40]], d / "soltas.jpg"))]
    if not (p / "referencia/video.mp4").exists() and (p / "referencia/palavras.json").exists():
        blocos.append({"type": "text", "text": "Fala da referência por segundo (o vídeo não foi baixado, só o áudio):\n"
                       + fala_por_segundo(json.loads((p / "referencia/palavras.json").read_text()))[:6000]})
    if (p / "referencia/meta.json").exists():
        blocos.append({"type": "text", "text": "Dados do post: " + (p / "referencia/meta.json").read_text()[:1500]})
    if len(blocos) == 1:
        return {"erro": "sem material para olhar"}
    r = pedir(num, blocos, "olho (material)", limite=420)
    if not r.get("erro"):
        (pasta(num) / "caderno.json").write_text(json.dumps({k: v for k, v in r.items() if not k.startswith("_")}, ensure_ascii=False, indent=1))
    registra(num, "material", {k: r.get(k) for k in ("_segundos", "_usd", "erro")})
    return r


def caderno_velho(num):
    """O caderno ainda não existe, ou chegou material novo pelo chat depois dele."""
    arq = pasta(num) / "caderno.json"
    mudou = max((v.stat().st_mtime for _, v in fontes_do_material(num)), default=0)
    return not arq.exists() or mudou > arq.stat().st_mtime


def caderno_atual(num):
    """Refaz o caderno se está velho; um por vídeo de cada vez (dois ao mesmo tempo apagavam os quadros um do outro)."""
    if not caderno_velho(num):
        return
    with _trava:
        if num in _no_caderno:
            return
        _no_caderno.add(num)
    try:
        fazer_caderno(num)
    finally:
        with _trava:
            _no_caderno.discard(num)


def caderno_texto(num):
    arq = pasta(num) / "caderno.json"
    return arq.read_text()[:6000] if arq.exists() else "(sem caderno: o material deste vídeo ainda não foi olhado)"


def na_pauta(num):
    """Chamado em thread pela pauta, depois de transcrever: o caderno fica pronto enquanto o roteiro é escrito."""
    if not ligado():
        return
    try:
        fazer_caderno(num)
    except Exception as ex:
        E.evento(num, f"olho: o caderno não saiu ({str(ex)[:160]})")


# ---------- a prévia ----------

PREVIA = PAPEL + """

MOMENTO: PRÉVIA. Você recebe o roteiro (o que cada bloco tem que mostrar), o seu caderno (quem é quem no material, de
quem é cada vídeo), a fala por segundo, as MEDIDAS DO PROGRAMA e os mosaicos da prévia (1 quadro por segundo e um logo depois
do começo de cada bloco; o segundo e o bloco em amarelo; o rosto que o programa achou em verde e a janela do vídeo em
vermelho).

Ache SOZINHO o que o editor mandaria consertar: pessoa errada ou a mais no take (compare o rosto com o caderno, o rótulo e a
fala: quem fala neste bloco é quem aparece?); imagem por cima de rosto ou de outro vídeo; logo ou marca de outra emissora;
rosto cortado ou baixo demais (o programa mediu os rostos contra a borda do vídeo: cada aviso dele é um lugar onde você
TEM que olhar; é defeito quando boca ou queixo somem na borda ou sob texto, ou quando sobra muito fundo acima da cabeça;
não descarte só porque o quadro pequeno "parece ok"); faixa vazia onde devia ter imagem; algo que o roteiro ou a fala
anunciam e a tela não mostra; picote de edição dentro de um take; nomes ou pessoas sem foto; texto de erro na tela.

ENQUADRAMENTO (25/10/2026, ele: "ele tem que olhar o enquadramento e relatar isso para consertar"). É um Reels do
Instagram, em pé, visto no celular em tela cheia: a tela inteira é da imagem. Olhe cada quadro e aponte, com o segundo:
foto ou vídeo numa faixa no meio com o topo vazio ou meia tela sem imagem (o programa mede: "imagem numa faixa");
pessoa cortada na borda (meio rosto, ombro sem cabeça); rosto com olhos ou boca atrás de texto, faixa, pílula, selo ou
degradê; rosto baixo demais ou cabeça cortada sem necessidade; marca ou logo de outro veículo na imagem (Metrópoles,
Globo, SBT, CNN...). No como_consertar, diga a medida: "subir o vídeo 200 px", "a foto inteira no alto, na largura toda",
"descer a pílula para baixo do queixo".

NÃO são defeito (não liste): transição, fusão ou desfoque de entrada e saída; piscada; boca aberta no meio da fala; letra
miúda de crédito ou rodapé; escolhas de estilo que não atrapalham entender.

No máximo 5 defeitos, os mais graves primeiro. Prefira 2 certos a 5 duvidosos.

JSON:
{"defeitos": [{"t": s, "bloco": n, "o_que": "...", "como_consertar": "...", "certeza": "alta|media"}],
 "esta_bom": ["o que funciona, curto"]}"""


def olhar_previa(num):
    # pastas do olho (consertos-da-revisao: nas do editor, um apagava os quadros do outro e a revisão caía no caminho caro)
    feitos, blocos_v = AN.quadros_da_previa(num, pasta=pasta(num) / "previa/quadros")
    marcados, medidas = medir_rostos(feitos, pasta(num) / "previa/marcados")
    mos = AN.mosaicos_da_previa(num, marcados, blocos_v, pasta=pasta(num) / "previa/mosaicos")
    base = [{"type": "text", "text": PREVIA}, {"type": "text", "text": "Roteiro:\n" + blocos_no_tempo(num)},
            {"type": "text", "text": "Seu caderno:\n" + caderno_texto(num)},
            {"type": "text", "text": "Fala por segundo:\n" + fala_por_segundo(palavras_da_voz(num))[:4000]},
            {"type": "text", "text": "Medidas do programa (rostos grandes):\n" + ("\n".join(medidas[:40]) or "nenhum rosto cortado ou baixo")}]
    for m in mos:
        base += [{"type": "text", "text": m.name}, AN.img(m)]
    r = pedir(num, base, "olho (prévia)")
    r["medidas"] = medidas
    return r


def para_o_chat(r):
    ds = [d for d in r.get("defeitos") or [] if isinstance(d, dict) and d.get("o_que")][:5]
    if not ds:
        return "Olho (em teste): não vi problema nesta prévia."
    linhas = []
    for i, d in enumerate(ds, 1):
        t = d.get("t"); quando = f"{float(t):.1f} s".replace(".", ",") if isinstance(t, (int, float)) else "?"
        # na prova (#332) cada item saiu com um parágrafo inteiro: no celular, duas linhas por item bastam; o resto fica
        # em olho/historico.jsonl
        o_que = d["o_que"] if len(d["o_que"]) <= 200 else d["o_que"][:200].rsplit(" ", 1)[0] + "…"
        linhas.append(f"{i}) {quando}: {o_que}")
    return "Olho (em teste), o que eu vi nesta prévia:\n" + "\n".join(linhas)


def na_previa(num):
    """Chamado em thread quando a prévia fica pronta (primeira animação ou depois de pedido dele). Só mostra no chat.
    Uma olhada por vídeo de cada vez: a prévia que chega no meio vira UMA olhada a mais, na versão mais nova."""
    if not ligado():
        return
    with _trava:
        if num in _olhando:
            _de_novo.add(num)
            return
        _olhando.add(num)
    try:
        while True:
            _olhar_e_mostrar(num)
            with _trava:
                if num not in _de_novo:
                    _olhando.discard(num)
                    return
                _de_novo.discard(num)
    except BaseException:
        with _trava:
            _olhando.discard(num); _de_novo.discard(num)
        raise


def _olhar_e_mostrar(num):
    try:
        caderno_atual(num)
        cena = (E.pasta(num) / "animacao/cena.html").read_bytes()
        import hashlib
        # 25/10/2026: a primeira animação já olha de novo depois do conserto e põe o que viu no chat; esta mesma cena não
        # é olhada (nem paga) outra vez
        try:
            ultima = json.loads((pasta(num) / "historico.jsonl").read_text().splitlines()[-1])
        except (OSError, ValueError, IndexError):
            ultima = {}
        if str(ultima.get("momento", "")).startswith("previa") and ultima.get("cena") == hashlib.md5(cena).hexdigest()[:10]:
            return
        r = olhar_previa(num)
        if r.get("erro"):           # 25/10/2026: a olhada que falhou não entra no registro (a cena seria dada como olhada)
            E.evento(num, f"olho: a prévia não foi olhada ({str(r['erro'])[:160]})")
            return
        registra(num, "previa", {**r, "cena": hashlib.md5(cena).hexdigest()[:10]})
        E.chat_add(num, "sistema", para_o_chat(r))
    except Exception:
        E.evento(num, "olho: parou na prévia: " + traceback.format_exc()[-240:])


# ---------- o pedido ----------

PEDIDO = PAPEL + """

MOMENTO: PEDIDO DO EDITOR. Ele escreveu no chat: "{msg}"
Você recebe o seu caderno, o roteiro, a folha da prévia de agora (1 quadro por segundo, o segundo em amarelo) e os quadros
grandes dos segundos que ele citou. Diga onde está o que ele aponta, quem é, como está hoje e o que mudar, em medidas da tela
(1080x1920) quando der. Só pergunte se for impossível saber.

JSON: {{"onde": [{{"t": s, "quem_ou_o_que": "...", "como_esta": "..."}}], "mudar": "o que o animador deve fazer", "pergunta_para_ele": null}}"""

# "No segundo 2,3", "aos 3 segundos", "11,9 s", "14,5s" (consertos-da-revisao: "aos 3 segundos" não era lido)
SEGUNDO = re.compile(r"segundos?\s+(\d+(?:[.,]\d+)?)|(\d+(?:[.,]\d+)?)\s*(?:s\b|seg)", re.I)


def localizar(num, pedido, folha_arq):
    """Chamado pelo animador antes de ajustar: o olho localiza o que ele apontou. Devolve os blocos para o pedido do
    animador ([] se desligado, sem resposta, com erro ou depois de PRAZO s: o ajuste segue como antes). Usa só o caderno
    que já existe; se está velho, ele é refeito por fora, para a próxima vez (consertos-da-revisao)."""
    if not ligado():
        return []
    if caderno_velho(num):
        threading.Thread(target=caderno_atual, args=(num,), daemon=True).start()
    saida = []
    t = threading.Thread(target=lambda: saida.extend(_localizar(num, pedido, folha_arq)), daemon=True)
    t.start(); t.join(PRAZO)
    if t.is_alive():
        E.evento(num, f"olho: a localização passou de {PRAZO} s; o ajuste seguiu sem ela")
        return []
    return saida


CONFERIR = PAPEL + """

MOMENTO: CONFERIR O PEDIDO. O editor pediu: "{msg}"
O animador já mudou a cena. Abaixo estão os quadros grandes de AGORA nos segundos que ele citou. O pedido foi atendido na
tela? Seja estrito: "sim" só se o que ele pediu está resolvido em todos esses quadros.

JSON: {{"atendido": "sim|parcial|nao", "faltou": "o que ainda falta, curto e com o segundo; vazio se sim"}}"""


def conferir_pedido(num, pedido):
    """23/10/2026 ("aprovo o plano conferir-o-pedido-e-faixa-preta"; #354: o conserto não era olhado de novo e a resposta
    disse "subi" com a faixa preta ainda na tela): depois do ajuste, os segundos que ele citou são conferidos na cena
    final. O programa mede o que dá para medir (a faixa preta) e vale mais que a IA; o olho dá uma olhada curta (se
    ligado). {} sem segundo citado ou sem resposta. Prazo total PRAZO s."""
    if not SEGUNDO.search(pedido or ""):
        return {}
    saida = {}
    t = threading.Thread(target=lambda: saida.update(_conferir(num, pedido)), daemon=True)
    t.start(); t.join(PRAZO)
    return saida


def _conferir(num, pedido):
    try:
        import ver, animacao as A
        citados = sorted({float((a or b).replace(",", ".")) for a, b in SEGUNDO.findall(pedido)})[:3]
        (pasta(num) / "conferir").mkdir(exist_ok=True)
        quadros, _ = ver.quadros(num, citados, saida=pasta(num) / "conferir")
        falta = [f"faixa preta de {y1 - y0} px na tela aos {str(t).replace('.', ',')} s"
                 for t, q in zip(citados, quadros) for y0, y1 in A.faixa_preta(q)]
        r = {}
        if ligado():
            blocos = [{"type": "text", "text": CONFERIR.format(msg=pedido[:1200])}]
            for t, q in zip(citados, quadros):
                g = pasta(num) / "conferir" / f"g{t:06.2f}.jpg"
                im = Image.open(q).convert("RGB"); im.thumbnail((960, 960)); im.save(g, quality=88)
                blocos += [{"type": "text", "text": f"Quadro de agora aos {t:.1f} s"}, AN.img(g)]
            r = pedir(num, blocos, "olho (conferir pedido)", limite=60)
        atendido = r.get("atendido") if r.get("atendido") in ("sim", "parcial", "nao") else None
        if falta:                                   # o programa mediu: vale mais que a impressão da IA
            atendido = "nao" if atendido == "nao" else "parcial"
        if not atendido:
            return {}
        faltou = "; ".join(falta + ([str(r["faltou"])[:300]] if r.get("faltou") and atendido != "sim" else []))
        c = {"atendido": atendido, "faltou": faltou, "medido": falta}
        registra(num, "conferir", {**c, "pedido": pedido[:500], "_segundos": r.get("_segundos"), "_usd": r.get("_usd")})
        return c
    except Exception:
        E.evento(num, "olho: parou na conferência do pedido: " + traceback.format_exc()[-240:])
        return {}


def frase_conferida(frase, conferido):
    """A resposta do ajuste começa dizendo que o pedido ficou só em parte, quando ficou (antes: "subi" com a faixa ainda
    na tela)."""
    if (conferido or {}).get("atendido") == "parcial":
        return f"Parcial: {conferido.get('faltou') or 'o pedido não ficou inteiro na tela'}. " + frase
    if (conferido or {}).get("atendido") == "nao":
        return f"Não ficou: {conferido.get('faltou') or 'o pedido não aparece na tela'}. " + frase
    return frase


def _localizar(num, pedido, folha_arq):
    try:
        import ver
        citados = sorted({float((a or b).replace(",", ".")) for a, b in SEGUNDO.findall(pedido)})[:3]
        blocos = [{"type": "text", "text": PEDIDO.format(msg=pedido[:1500])},
                  {"type": "text", "text": "Seu caderno:\n" + caderno_texto(num)},
                  {"type": "text", "text": "Roteiro:\n" + blocos_no_tempo(num)},
                  {"type": "text", "text": "Folha da prévia de agora"}, AN.img(folha_arq)]
        if citados:
            tempos = sorted({max(0, round(t + dt, 2)) for t in citados for dt in (-.5, 0, .5)})
            quadros, _ = ver.quadros(num, tempos, saida=pasta(num) / "pedido")
            for t, q in zip(tempos, quadros):
                grande = pasta(num) / "pedido" / f"g{t:06.2f}.jpg"
                im = Image.open(q).convert("RGB"); im.thumbnail((960, 960)); im.save(grande, quality=88)
                blocos += [{"type": "text", "text": f"Quadro grande de {t:.1f} s"}, AN.img(grande)]
        r = pedir(num, blocos, "olho (pedido)", limite=120)
        registra(num, "pedido", {**r, "pedido": pedido[:500]})
        if r.get("erro") or not (r.get("onde") or r.get("mudar")):
            return []
        return [{"type": "text", "text": (
            "## O que o OLHO do estúdio localizou neste pedido (ele viu a prévia de agora e o material; use como guia, a "
            "decisão é sua)\n" + json.dumps({k: r.get(k) for k in ("onde", "mudar")}, ensure_ascii=False)[:3000])}]
    except Exception:
        E.evento(num, "olho: parou no pedido: " + traceback.format_exc()[-240:])
        return []
