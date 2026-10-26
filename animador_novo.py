"""Animador novo, só para os AJUSTES dele (19/10/2026; ele: "isso esta gastando muito" e "pode fazer", sobre o plano: o
novo animador no app só nos ajustes, com rede de segurança). Testado 4 vezes no #300 (testes/caminho_novo.py e
caminho_novo2.py): um ajuste custou de US$ 0,04 a 0,90 eq., contra US$ 5,36 do animador em passos.

Numa chamada só do Opus, sem ferramentas e com as imagens dentro do pedido:
  - a parte que não muda no vídeo vem primeiro e fica no cache por 1 hora (regras, roteiro, palavras de cada bloco, os
    mosaicos das pastas de material que o roteiro ou o pedido citam, como responder);
  - depois o chat, a cena de agora, a folha da prévia (1 quadro por segundo) e o pedido;
  - ele devolve só as trocas na cena (@@ANTES / @@DEPOIS / @@FIM) e uma linha RESUMO para o chat;
  - a trava: troca que some com texto da tela sem pedido nem linha TIRADO é recusada;
  - a régua e a tela vazia medem (programa); se acharem algo, UM conserto do mesmo jeito; os Olhos não entram aqui
    (ele: "os olhos só na aprovação").
Rede de segurança: se passar de LIMITE_S, vier sem resposta, ou nenhuma troca entrar, a cena volta como estava e
animacao.animar tenta de novo uma vez e, se falhar outra vez, a cena volta como estava e o chat recebe o erro (25/10/2026:
o animador antigo, "o jeito de antes", saiu; a primeira animação e o "roteiro refeito" também vêm para cá).
"""
import base64, json, re, shutil, subprocess, time
from pathlib import Path

import estudio as E

LIMITE_S = 300          # tempo máximo de uma chamada (medido nos testes: 13 a 40 s; uma vez travou 48 min)
TROCA = re.compile(r"@@ANTES\n(.*?)\n@@DEPOIS\n(.*?)\n?@@FIM", re.S)
TIRADO = re.compile(r"^TIRADO:\s*(.+?)\s*(?:·.*)?$", re.M)
RESUMO = re.compile(r"^RESUMO:\s*(.+)$", re.M)
# link ou "baixa esse vídeo": precisa de ferramenta. 21/10/2026 (#306): era "\bbaix", e "metade de baixo" ia ao animador antigo

COMO = """

## Como trabalhar (vale para todo pedido deste vídeo)
Você não abre arquivos nem roda nada: tudo vem neste pedido. Acima, os mosaicos do material (10 fotos por imagem, o
caminho de cada foto em amarelo; para usar uma foto, use esse caminho). No fim vêm o chat, a cena de agora
(animacao/cena.html) inteira, a folha da prévia de agora (1 quadro por segundo, o segundo em amarelo) e o pedido.
Responda SÓ as trocas na cena, uma por trecho mudado, neste formato (o ANTES copiado exatamente da cena de agora, com um
pedaço que aparece uma vez só; o DEPOIS é o trecho novo):
@@ANTES
<trecho de agora>
@@DEPOIS
<trecho novo>
@@FIM
Não tire da tela nenhum texto que o pedido não mande tirar: troca que some com texto sem pedido é recusada pelo estúdio.
Se tirar ou trocar um texto de propósito, escreva depois das trocas uma linha TIRADO: <o texto que sai> · <por quê>.
Quando o pedido trouxer pontos para conferir, escreva depois das trocas uma linha por ponto:
FEITO: <segundos> · <o que mudou, até 12 palavras>
NAO_E: <segundos> · <por que não é defeito>
FALA: <segundos> · <o que na fala atrapalha>
CUSTO: <segundos> · <o que precisaria e o preço>
No fim, uma linha RESUMO: <o que você mudou, em até 2 frases curtas, para ele ler no chat do celular: português simples,
começando pelo resultado, sem pixel, coordenada, nome de arquivo nem de peça (T.alguma_coisa); tempo em segundos>.
Sem cercas de código.
"""


def serve(pedido):
    """O caminho novo vale para este pedido? (ajuste em cena que já existe, sem link e sem pedido de baixar)"""
    # 21/10/2026 ("aprovo o plano pedido-limpo"): saiu a lista de palavras (link, "baixa o vídeo") que mandava o pedido ao
    # animador antigo; quem decide o que o pedido é agora é o maestro (link e download vão para o agente do chat)
    return bool(pedido) and not pedido.startswith("O ROTEIRO FOI REFEITO")


# ---- preparar (programa, sem IA) ---------------------------------------------------------------------------------

def folha(num, saida, grandes=None):
    """1 quadro por segundo da prévia numa imagem só (12 colunas), com o segundo em amarelo. grandes={segundo: caminho}:
    guarda esses quadros em 540x960 ao lado da folha (os Olhos do ajuste, olhos-enxergam-rosto)."""
    import ver
    from PIL import Image, ImageDraw, ImageFont
    d = saida.parent / "novo-quadros"
    shutil.rmtree(d, ignore_errors=True)
    _, feitos, erros = ver.percorrer(num, 1.0, d)
    for t, q in feitos:
        if grandes is not None and round(t) in grandes:
            Image.open(q).convert("RGB").resize((540, 960)).save(grandes[round(t)], quality=88)
    f = ImageFont.truetype(str(E.RAIZ / "web/fontes/impact.ttf"), 26)
    col, lw, lh = 12, 200, 356
    im = Image.new("RGB", (col * lw, ((len(feitos) + col - 1) // col) * lh), "black"); dr = ImageDraw.Draw(im)
    for i, (t, q) in enumerate(feitos):
        x, y = (i % col) * lw, (i // col) * lh
        im.paste(Image.open(q).convert("RGB").resize((lw, lh)), (x, y)); dr.rectangle([x, y, x + 52, y + 32], fill="black")
        dr.text((x + 4, y + 1), f"{t:.0f}", fill="yellow", font=f)
    im.save(saida, quality=85)
    shutil.rmtree(d, ignore_errors=True)
    return erros


def mosaicos(num, pastas):
    """Os quadros de cada pasta de material, 10 por imagem com o caminho em amarelo, em animacao/mosaicos/. Refaz só
    a pasta cujo material mudou depois do mosaico."""
    from PIL import Image, ImageDraw, ImageFont
    p = E.pasta(num); dest = p / "animacao/mosaicos"; dest.mkdir(parents=True, exist_ok=True)
    try:
        fonte = ImageFont.truetype("/Library/Fonts/Arial Unicode.ttf", 20)
    except OSError:
        fonte = ImageFont.load_default()
    feitos = []
    for nome in pastas:
        arqs = sorted((p / "material" / nome / "quadros").glob("q*.jpg"))
        prontos = sorted(dest.glob(f"{nome}-*.jpg"))
        if prontos and arqs and min(x.stat().st_mtime for x in prontos) >= max(a.stat().st_mtime for a in arqs):
            feitos += prontos; continue
        for velho in prontos:
            velho.unlink()
        for k in range(0, len(arqs), 10):
            grupo, lw, lh, col = arqs[k:k + 10], 360, 640, 5
            im = Image.new("RGB", (col * lw, ((len(grupo) + col - 1) // col) * lh), "black"); dr = ImageDraw.Draw(im)
            for i, a in enumerate(grupo):
                q = Image.open(a).convert("RGB"); q.thumbnail((lw, lh))
                x, y = (i % col) * lw + (lw - q.width) // 2, (i // col) * lh + (lh - q.height) // 2
                im.paste(q, (x, y)); dr.rectangle([x, y, x + lw, y + 28], fill="black")
                dr.text((x + 4, y + 3), str(a.relative_to(p)), fill="yellow", font=fonte)
            m = dest / f"{nome}-{k // 10 + 1}.jpg"; im.save(m, quality=85); feitos.append(m)
    return feitos


FOTO_PEDIDO = re.compile(r"foto|enquadr|recort|rosto|cortad|cabe[cç]a|imagem|zoom|prova", re.I)
MAX_FOTOS = 18


def fotos_da_cena(num):
    """As fotos que a cena usa e os recortes de cada uma: {caminho: ['x y l a', ...]}. Entende o jeito de escrever das
    cenas: const D = 'material/X/quadros/' e [D + 'q000.9.jpg', '28 122 477 588', ...], ou o caminho inteiro."""
    cena = (E.pasta(num) / "animacao/cena.html").read_text()
    pastas = dict(re.findall(r"\b(\w+)\s*=\s*'(material/[^']+/)'", cena))
    achadas = {}
    for var, arq, resto in re.findall(r"\[\s*(\w+)\s*\+\s*'(q[\w.]+\.jpg)'([^\]]*)\]", cena):
        if var in pastas:
            achadas.setdefault(pastas[var] + arq, []).extend(re.findall(r"'(\d+ \d+ \d+ \d+)'", resto))
    for arq in re.findall(r"'(material/[^']+\.(?:jpg|jpeg|png))'", cena):
        achadas.setdefault(arq, [])
    return {a: sorted(set(r)) for a, r in achadas.items() if (E.pasta(num) / a).exists()}


def rostos(arq):
    """Os rostos da foto pelo YuNet (programa, sem IA; ferramentas/modelos/yunet.onnx): [(x, y, l, a), ...]."""
    try:
        import cv2, visao                    # 25/10/2026: o detector de rosto é um só (visao.py)
        return [tuple(int(v) for v in r[:4]) for r in visao.rostos(cv2.imread(str(arq)), .6)]
    except Exception:
        return []


def fotos_com_grade(num):
    """19/10/2026 (ele: "porque não aumenta o tamanho da foto para ele ver melhor?" e "prepara as fotos grandes com
    grade e o yunet"): nos pedidos de foto e enquadramento, cada foto que a cena usa vai em tamanho cheio, com a grade
    de 50 em 50 px (números a cada 100), o rosto que o YuNet achou (verde) e o recorte de agora (amarelo). O animador lê
    as coordenadas na grade em vez de estimar pelas miniaturas. Devolve [(caminho, imagem, rostos, recortes)]."""
    from PIL import Image, ImageDraw, ImageFont
    p = E.pasta(num); dest = p / "animacao/fotos-grade"; shutil.rmtree(dest, ignore_errors=True); dest.mkdir(parents=True)
    try:
        f = ImageFont.truetype("/Library/Fonts/Arial Unicode.ttf", 15)
    except OSError:
        f = ImageFont.load_default()
    feitas = []
    for k, (arq, recortes) in enumerate(list(fotos_da_cena(num).items())[:MAX_FOTOS]):
        im = Image.open(p / arq).convert("RGB"); W, H = im.size
        fs = rostos(p / arq)
        cam = Image.new("RGBA", im.size, (0, 0, 0, 0)); d = ImageDraw.Draw(cam)
        for x in range(0, W, 50):
            d.line([(x, 0), (x, H)], fill=(255, 255, 255, 110 if x % 100 == 0 else 50), width=1)
        for y in range(0, H, 50):
            d.line([(0, y), (W, y)], fill=(255, 255, 255, 110 if y % 100 == 0 else 50), width=1)
        for r in recortes:
            x, y, w, h = map(int, r.split()); d.rectangle([x, y, x + w, y + h], outline=(255, 201, 51, 255), width=3)
        for x, y, w, h in fs:
            d.rectangle([x, y, x + w, y + h], outline=(61, 220, 132, 255), width=3)
        im = Image.alpha_composite(im.convert("RGBA"), cam).convert("RGB"); d = ImageDraw.Draw(im)
        for x in range(100, W, 100):
            d.rectangle([x - 16, 0, x + 16, 17], fill="black"); d.text((x - 13, 1), str(x), fill="white", font=f)
        for y in range(100, H, 100):
            d.rectangle([0, y - 9, 34, y + 9], fill="black"); d.text((2, y - 8), str(y), fill="white", font=f)
        saida = dest / f"foto-{k + 1:02d}.jpg"; im.save(saida, quality=88)
        feitas.append((arq, saida, fs, recortes))
    return feitas


def palavras_por_bloco(num):
    import animacao as A
    d = A.dados(num)
    return "\n".join(f"- bloco {b['n']} ({b['ini']:.2f}-{b['fim']:.2f} s): " +
                     " ".join(f"{w[2]}@{w[0]:.2f}" for w in d["palavras"] if b["ini"] - .15 <= w[0] <= b["fim"] + .15)
                     for b in d["blocos"])


def img(arq):
    return {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": base64.b64encode(Path(arq).read_bytes()).decode()}}


def pastas_citadas(num, *textos):
    p = E.pasta(num); nomes = set()
    for t in textos:
        nomes |= set(re.findall(r"material/([^/\s'\"]+)/", t or ""))
    return sorted(n for n in nomes if (p / "material" / n / "quadros").is_dir())


def parte_fixa(num, citadas):
    import animacao as A
    p = E.pasta(num)
    fixo = A.contexto(num, "").split("O que ele pediu no chat deste vídeo")[0]
    fixo += f"\n\n## As palavras de cada bloco, com o segundo em que são ditas\n{palavras_por_bloco(num)}"
    outras = sorted(x.name for x in (p / "material").iterdir() if x.is_dir() and x.name not in citadas) if (p / "material").exists() else []
    fixo += (f"\n\n## Material em mosaico: as pastas que o roteiro cita ({', '.join(citadas) or 'nenhuma'})\n"
             f"As outras pastas de material ({', '.join(outras) or 'nenhuma'}) não vêm em imagem: use pelo tempo do vídeo (takes).")
    blocos = [{"type": "text", "text": fixo}]
    for m in mosaicos(num, citadas):
        blocos += [{"type": "text", "text": f"Mosaico {m.name}"}, img(m)]
    # sem esta marca o claude só guarda no cache o pedido inteiro e o 2º pedido pagava tudo de novo (teste no Haiku:
    # com ela, a 2ª chamada custou 12x menos; no #300, o 2º ajuste custou US$ 0,035 contra 0,68)
    blocos.append({"type": "text", "text": COMO, "cache_control": {"type": "ephemeral", "ttl": "1h"}})
    return blocos


def parte_variavel(num, pedido, folha_arq, quadros=(), fotos=(), olho=()):
    import animacao as A
    ctx = A.contexto(num, pedido)
    var = "O que ele pediu no chat deste vídeo" + ctx.split("O que ele pediu no chat deste vídeo", 1)[1]
    var += f"\n\n## A cena de agora (animacao/cena.html), inteira\n{(E.pasta(num) / 'animacao/cena.html').read_text()}"
    blocos = [{"type": "text", "text": var}]
    if fotos:
        blocos.append({"type": "text", "text": (
            "## As fotos que a cena usa, em tamanho cheio\nCada uma no tamanho do quadro original (as coordenadas do recorte "
            "'x y largura altura' são nesta mesma escala). Grade de 50 em 50 px, com os números a cada 100 na borda. Verde: "
            "rosto achado pelo programa (YuNet, confiável para rosto de frente; de perfil ou pequeno pode faltar). Amarelo: o "
            "recorte de agora. Para enquadrar, leia as coordenadas na grade: o recorte deve pegar a foto de verdade (sem a "
            "tela do Instagram, tarja, marca ou texto queimado), com os rostos inteiros e no terço de cima.")})
        for arq, im, fs, recs in fotos:
            desc = f"Foto {arq}: rostos (x y l a) {'; '.join(' '.join(map(str, r)) for r in fs) or 'nenhum achado'}; recorte de agora {'; '.join(recs) or 'nenhum'}"
            blocos += [{"type": "text", "text": desc}, img(im)]
    blocos += list(olho)
    blocos += [{"type": "text", "text": "A folha da prévia de agora:"}, img(folha_arq)]
    for t, q in quadros:
        blocos += [{"type": "text", "text": f"Quadro aos {t:.1f} s:"}, img(q)]
    return blocos + [{"type": "text", "text": "Responda agora: só as trocas, as linhas (se houver pontos) e o RESUMO."}]


# ---- a chamada, a trava, a régua ---------------------------------------------------------------------------------

def opus(num, blocos, quem, limite=None, modelo="opus"):
    """Uma chamada, imagens dentro do pedido, sem ferramentas, com tempo máximo. Guarda o que o claude respondeu em
    animacao/chamadas/ e o gasto no gasto do vídeo. Devolve (texto, uso); texto vazio = falhou (uso['erro'] diz por quê).
    modelo: os Olhos dos ajustes usam o Sonnet (20/10/2026, olhos-nos-ajustes)."""
    import ia                                 # 25/10/2026: a chamada de IA de um lugar só (ia.py)
    p = E.pasta(num)
    registro = p / "animacao/chamadas" / f"{time.strftime('%Y%m%d-%H%M%S')}-{re.sub(r'[^a-z0-9]+', '-', quem)}.jsonl"
    texto, uso = ia.chamar(blocos, quem, modelo, num=num, limite=limite or LIMITE_S, cwd=p, registro=registro)
    uso.pop("s", None)
    return texto, uso


def textos(trecho):
    """Os textos que aparecem na tela: o que está entre > e < no SVG e as frases entre aspas no script (com espaço ou 3
    maiúsculas seguidas; nomes de classe, caminhos e números sozinhos não contam)."""
    # o <b> das peças é só o amarelo; o que tem cara de código ({ } ( ) = ;) não é texto de tela
    achados = [x.strip() for x in re.findall(r">([^<>]*[A-Za-zÀ-ú][^<>]*)<", re.sub(r"</?b>", "", trecho))
               if not set(x) & set("{}()=;")]
    for x in re.findall(r"'([^'\n]{3,})'|\"([^\"\n]{3,})\"", trecho):
        s = re.sub(r"</?b>", "", x[0] or x[1]).strip()          # 'O QUE <b>FOTOS</b>' é texto de tela (o <b> é o amarelo)
        if s[:1] not in ".#" and not set(s) & set("/<>=") and re.search(r"[A-ZÀ-Ú]{3}|[A-Za-zÀ-ú] [A-Za-zÀ-ú]", s):
            achados.append(s)
    return {x for x in achados if re.search(r"[A-Za-zÀ-ú]{3}", x)}


_PECAS = []


def textos_das_pecas():
    """Os textos fixos que as peças prontas escrevem sozinhas (RESPONDE NOS COMENTÁRIOS, PLACAR...): quando a cena passa
    a usar a peça, eles saem da cena mas continuam na tela (19/10/2026, teste do T.fecho: a trava recusou a troca)."""
    if not _PECAS:
        # só o código: os comentários das peças têm exemplos ('O PLANALTO <b>REPETIU</b>') que não são texto fixo
        sem_coment = lambda js: re.sub(r"(?<![:'\"])//[^\n]*", "", re.sub(r"/\*.*?\*/", "", js, flags=re.S))
        _PECAS.append(set().union(*(textos(sem_coment(a.read_text())) for a in (E.RAIZ / "web/pecas").glob("*.js"))))
    return _PECAS[0]


USA_PECA = re.compile(r"\bT\.(fecho|fotos|documento|carimbos|selo|take|seguir|assinatura)\b|\bpeça", re.I)


def some_sem_pedido(antes, depois, pedido, declarados):
    """Texto que some da tela só passa se o animador declarou (TIRADO) ou se o pedido cita uma palavra dele (no 1º
    teste o conserto desceu a nota e apagou "O PLANALTO REPETIU" sem ninguém pedir)."""
    pede = pedido.lower(); falta = []
    # 19/10/2026 (#302: "AS FAMÍLIAS" e ", informa" recusados porque a frase só foi quebrada em outras linhas ao
    # aumentar a letra): texto cujas palavras continuam todas na cena não sumiu, só mudou de linha
    tudo_depois = set(re.findall(r"[a-zà-ú0-9]{3,}", " ".join(textos(depois)).lower()))
    for t in textos(antes) - textos(depois) - textos_das_pecas():
        palavras = [w.lower() for w in re.findall(r"[A-Za-zÀ-ú]{4,}", t)]
        if any(d.lower() in t.lower() or t.lower() in d.lower() for d in declarados) or any(w in pede for w in palavras):
            continue
        minhas = re.findall(r"[a-zà-ú0-9]{3,}", t.lower())
        if minhas and all(w in tudo_depois for w in minhas):
            continue
        falta.append(t)
    return falta


def aplica(num, resposta, pedido):
    """Aplica as trocas e compara a cena inteira antes e depois: texto que só mudou de lugar passa; o que sumiu sem
    pedido recusa a troca que o tirou. Devolve (feitas, recusadas, erros)."""
    cena = E.pasta(num) / "animacao/cena.html"
    inicial = cena.read_text()
    declarados = TIRADO.findall(TROCA.sub("", resposta))
    trocas, erros = [], []
    for antes, depois in TROCA.findall(resposta):
        n = inicial.count(antes)
        if n != 1:
            erros.append(f"o trecho a trocar aparece {n} vez(es) na cena")
        else:
            trocas.append((antes, depois))

    def monta(lista):
        t = inicial
        for a, d in lista:
            t = t.replace(a, d)
        return t
    texto, recusadas = monta(trocas), 0
    falta = some_sem_pedido(inicial, texto, pedido, declarados)
    if falta and USA_PECA.search(pedido or ""):
        # o pedido manda usar uma peça: o texto que ela substitui pode sair; a trava só avisa (19/10/2026)
        erros.append("saiu da tela, trocado pela peça que você pediu: " + "; ".join(f"\"{f}\"" for f in falta[:4]))
        falta = []
    if falta:
        culpadas = [(a, d) for a, d in trocas if any(f in textos(a) and f not in textos(d) for f in falta)]
        if culpadas:
            trocas = [x for x in trocas if x not in culpadas]; recusadas = len(culpadas)
            erros.append(f"recusei {recusadas} troca(s) que tiravam da tela, sem você pedir: " + "; ".join(f"\"{f}\"" for f in falta[:4]))
            texto = monta(trocas)
    if trocas:
        cena.write_text(texto)
    return len(trocas), recusadas, erros


def gasto_da_animacao(num, t0):
    """O peso deste pedido: tudo o que rodou desde o começo dele (o maestro marca pedido_desde na ficha; sem ele, desde
    t0), menos capas e legenda, que rodam ao mesmo tempo na primeira animação (19/10/2026: o #301 dizia US$ 2,04 com
    elas; a animação em si foi 1,08). 21/10/2026 ("aprovo o plano pedido-limpo"): antes só somava animador e prévia, e o
    chat mostrava ~10% menos que o real (faltavam o maestro e os Olhos)."""
    desde = time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(t0 - 1))
    pd = str(E.ler_ficha(num).get("pedido_desde") or "")[:19]
    if pd and pd < desde and pd >= time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(t0 - 1800)):
        desde = pd
    return sum(g.get("usd") or 0 for g in E.gastos(num)
               if g.get("quando", "")[:19] >= desde and not str(g.get("quem") or "").startswith(("capa", "legenda")))


def respondidos(num):
    a = E.pasta(num) / "animacao/respondidos.json"
    return json.loads(a.read_text()) if a.exists() else []


def assunto(texto):
    comuns = set("porque quando depois antes ainda sobre entre muito pouco tela video vídeo fala falou mostra aparece "
                 "bloco segundos texto parte agora coisa sempre outra outro mesmo mesma isso esse essa este esta".split())
    return {w for w in re.findall(r"[a-zà-ú]{5,}", texto.lower()) if w not in comuns}


def tempos(num):
    """A versão dos tempos da voz: quando a voz muda (fala regravada, roteiro refeito), as respostas antigas não valem."""
    import hashlib
    c = E.pasta(num) / "narracao/completo.json"
    return hashlib.md5(c.read_bytes()).hexdigest()[:10] if c.exists() else ""


def ja_respondido(q, lista, versao):
    """O ponto já foi dispensado pelo animador como "não é defeito" (NAO_E)? Só se for o MESMO ponto: mesmo tipo, até
    1,5 s de distância, 2 palavras do problema em comum, e a mesma voz (versao = tempos()).
    21/10/2026 ("aprovo o plano pedido-limpo"): antes bastava estar a menos de 1 s de QUALQUER resposta guardada (também
    "custa demais" e "é da fala"), e a lista nunca zerava: no #316 o "ELE DISSE" coberto aos 3,5 s sumiu por causa de
    respostas em 3,0 e 3,2 s sobre a nitidez do vídeo antigo, e o chat disse "Conferência: ok"."""
    a = assunto(q["msg"])
    return any(r.get("tipo") == "NAO_E" and r.get("tempos") == versao and r.get("ponto_tipo") == q["tipo"]
               and abs(q["t"] - r["t"]) <= 1.5 and len(a & assunto(r.get("ponto_msg", ""))) >= 2 for r in lista)


def aviso_para_ele(num, regua, avisos):
    """O fim da mensagem do ajuste (21/10/2026, "aprovo o plano pedido-limpo"): os avisos do animador, take ampliado
    demais e o grave que sobrou, pelo nome (antes: "Régua: 1 problema(s)" logo depois de "Conferência: ok", #316 16:21)."""
    out, vistos = "", set()
    for k, x in avisos:
        if x["msg"] and x["msg"] not in vistos and len(vistos) < 4:
            vistos.add(x["msg"])
            out += f" O animador avisa ({x['t']:.0f} s): {x['msg']}"
    for t, vezes in ampliados(num):
        out += (f" O take de {t:.1f} s está ampliado {vezes:.1f} vezes: a imagem fica mole. Quer que eu procure outro vídeo "
                "do mesmo momento, em close?")
    graves = [x for x in regua if grave(x)]
    if graves:
        out += (" Sobrou na régua: " + "; ".join(f"{x['de']:.1f} s · {x['tipo']} · {x['msg']}" for x in graves[:3])
                + ". O botão de aprovar fica travado até consertar (peça aqui) ou você tocar em \"Aprovar mesmo assim\".")
    leves = len(regua) - len(graves)
    return out + (f" Régua: {leves} aviso(s) leve(s)." if leves else " Régua: nada a apontar.") if not graves else out


def pergunta_para_ele(num, regua, conferido=None):
    """24/10/2026 (ele: "pode fazer" a parte B): o pedaço do relatório que pede decisão dele, em português de chat; o
    resto (conferência, avisos, régua leve, tempo, custo) vai para os detalhes recolhidos (aviso_para_ele)."""
    partes = []
    if (conferido or {}).get("atendido") in ("parcial", "nao"):
        partes.append("Conferi depois e o pedido ainda não ficou inteiro na tela (o que falta está nos detalhes).")
    amp = [t for t, _ in ampliados(num)]
    if amp:
        quando = " e ".join(f"aos {t:.0f} s" for t in amp[:3])
        partes.append(f"A imagem {quando} ficou ampliada demais e fica mole. Procuro um vídeo mais de perto?")
    if any(grave(x) for x in regua):
        partes.append('Sobrou um problema de tela que trava o botão de aprovar: peça o conserto aqui ou toque em "Aprovar mesmo assim".')
    return " ".join(partes)


LEVE = 540                   # a largura da cópia leve (servidor.video_leve): a medida em que o animador e a prévia veem


def ampliados(num, limite=2.5):
    """Takes ampliados mais de `limite` vezes sobre o vídeo ORIGINAL: a imagem fica mole e vale outro vídeo do mesmo
    momento. 21/10/2026 (ele: "a edição procura outro video do mesmo assunto, esse não está bom e o agente deveria ter
    detectado isso"; #316: o Lula de um plano aberto da Cultura, ~3 vezes). cheia {s} conta sobre a cópia leve (540 de
    largura, a da prévia): 540 x s / largura do original. zoom: a faixa de 1080 x zoom / largura do original.
    [(início em s, vezes)]"""
    p = E.pasta(num); cena = (p / "animacao/cena.html").read_text() if (p / "animacao/cena.html").exists() else ""
    larg = {}
    def largura(src):
        if src not in larg:
            r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v", "-show_entries", "stream=width", "-of", "csv=p=0",
                                str(p / src)], capture_output=True, text=True)
            larg[src] = int(r.stdout.strip().splitlines()[0]) if r.stdout.strip() else 0
        return larg[src]
    padrao = (re.findall(r"\bsrc:\s*'([^']+)'", cena) or ["referencia/video.mp4"])[0]
    out = []
    for m in re.finditer(r"T\.take\(\{(.*?)\}\s*\)", cena, re.S):
        corpo = m.group(1)
        src = (re.findall(r"\bsrc:\s*'([^']+)'", corpo) or [padrao])[0]
        w = largura(src)
        s_ = re.search(r"cheia:\s*\{[^}]*?\bs:\s*([\d.]+)", corpo)
        z = re.search(r"\bzoom:\s*([\d.]+)", corpo)
        vezes = LEVE * float(s_.group(1)) / w if s_ and w else 1080 * float(z.group(1)) / w if z and w else 0
        ini = re.search(r"\bini:\s*([\d.]+)", corpo)
        if vezes > limite:
            out.append((float(ini.group(1)) if ini else 0.0, round(vezes, 1)))
    return out


# ---- o ajuste ------------------------------------------------------------------------------------------------------

GRAVES = {"sobreposto", "escondido", "fora", "estourado", "pedaço", "encavalado", "erro",
          "invisivel", "take-longo", "centro-vazio",      # 22/10/2026, editor-327: o que o #327 mostrou que faltava
          "faixa-preta",                                  # 23/10/2026, conferir-o-pedido-e-faixa-preta (#354)
          "olhos"}                                        # 25/10/2026: o que os Olhos ainda viram depois do conserto


def grave(x):
    """O que volta sozinho ao animador depois de um ajuste. 20/10/2026 (ele: "pode fazer assim"): também o texto encostado
    na LEGENDA das falas (#305: os anos embaixo do plenário colados na legenda, 15 avisos que ninguém consertou); o
    "falta-selo" fica só aviso, porque há vídeo que ele quer sem selo."""
    return x["tipo"] in GRAVES or (x["tipo"] == "encostado" and str(x.get("msg", "")).startswith("legenda"))


TIRA_SELO = re.compile(r"\bsem\s+(?:os?\s+)?selos?\b|\b(?:tir\w*|remov\w*|apag\w*|n[aã]o\s+(?:quero|coloc\w*|p[oõ]e|ponh\w*|"
                       r"us[ae]\w*|precis\w*))\b[^.?!]{0,40}?\bselos?\b", re.I)
SELO_NA_TELA = re.compile(r"\s*(?:[·;,]\s*)?\bselo\s+(?:[A-ZÁÉÍÓÚÂÊÔÃÕÇ][A-ZÁÉÍÓÚÂÊÔÃÕÇ-]*\s?)+")


def tira_selos_da_tela(num, pedido):
    """20/10/2026 (ele: "vai ter vídeos que vai ter selos e vídeos que não vai ter. se eu pedir lá no chat [...] para não
    ter aí ele retira"): o pedido de tirar os selos tira também o "selo X" da coluna Tela do roteiro (de todos os blocos,
    ou só dos blocos citados), para a régua (falta-selo) não cobrar o que ele não quer. Devolve os blocos mudados."""
    if not TIRA_SELO.search(pedido or ""):
        return []
    alvo = {int(n) for n in re.findall(r"blocos?\s+(\d+)", pedido, re.I)}
    arq = E.pasta(num) / "ROTEIRO.md"
    if not arq.exists():
        return []
    linhas, mudou = arq.read_text().split("\n"), []
    for i, l in enumerate(linhas):
        m = E.LINHA.match(l.strip())
        if not m or (alvo and int(m.group(1)) not in alvo):
            continue
        c = m.group(2).split("|")
        if len(c) < 4 or not SELO_NA_TELA.search(c[3]):
            continue
        nova = re.sub(r"\s{2,}", " ", re.sub(r"^\s*[·;,]\s*", "", SELO_NA_TELA.sub(" ", c[3]))).strip()
        c[3] = f" {nova} "
        linhas[i] = f"| {m.group(1)} |" + "|".join(c) + "|"
        mudou.append(int(m.group(1)))
    if mudou:
        E.foto_roteiro(num)
        arq.write_text("\n".join(linhas))
        E.evento(num, f"pedido de tirar selo: tirei o selo da coluna Tela dos blocos {mudou}")
    return mudou


OLHOS_AJUSTE = """Você é os Olhos do estúdio: olha a prévia de um vídeo curto DEPOIS de um ajuste e diz se o ajuste deu certo.
A imagem é a folha da prévia: 1 quadro por segundo, o segundo em amarelo no canto.
O editor pediu: {pedido}
O animador diz que fez: {resumo}
Responda SÓ um JSON, sem cercas: {{"pedido_na_tela": "sim" | "nao" | "parcial", "faltou": "<o que do pedido não aparece, ou vazio>",
"defeitos": [{{"t": <segundo>, "o_que": "<até 15 palavras>"}}],
"quadros": [{{"t": <segundo do quadro grande>, "pessoa_maior": "<nome de quem ocupa o quadro, comparando com as fotos de referência; 'desconhecida' se não souber>",
"rosto_inteiro": true | false, "o_que_cobre": "<o que esconde ou corta o rosto, ou vazio>"}}]}}
Preencha "quadros" com UMA linha para CADA quadro grande, sem pular nenhum.
Defeito é só o que se VÊ e é objetivo, perto do que mudou: texto cortado, encavalado ou ilegível; take de outra pessoa
ou do trecho errado; foto ou rosto que não apareceu; tela vazia; algo que o pedido mandou tirar e continua, ou mandou pôr
e não está. Gosto, ritmo e sugestão não são defeito. Na dúvida, não aponte.
Depois da folha vêm QUADROS GRANDES dos takes (o segundo e o rótulo do take escritos antes de cada um) e, se houver, FOTOS DE
REFERÊNCIA com o nome de cada pessoa. Em todo quadro grande de take, confira SEMPRE, mesmo que o pedido não fale disso:
- ROSTO: olhos, boca e queixo da pessoa do take aparecem inteiros, fora do escurecido do pé, do título e da legenda; a
  cabeça não está cortada no alto; o vídeo preenche a largura (sem faixa azul ou preta do lado). Rosto escondido ou cortado
  é defeito.
- QUEM FALA: olhe a pessoa MAIOR e mais no centro do quadro grande e compare com a foto de referência do nome do rótulo.
  Se a pessoa maior não for a do rótulo (rótulo GUILHERME BOULOS e a maior é o Lula, ou outra pessoa), é defeito: escreva
  "aparece <quem aparece> em vez de <nome do rótulo>". O take pode ser um vídeo com duas pessoas, uma em cima e outra
  embaixo: a do rótulo tem que ser a que ocupa o quadro."""


def takes_na_tela(num):
    """[(ini, fim, rótulo)] dos takes da cena, lidos na prévia (o que o take.js montou)."""
    import ver
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        nav = p.chromium.launch(); pg = nav.new_page(viewport={"width": 1080, "height": 1920})
        pg.goto(ver.URL.format(n=num)); pg.wait_for_function("!!window.__previa", timeout=30000, polling=200)
        r = pg.evaluate("""[...document.querySelectorAll('video.trecho')].map(v => { const c = v.closest('.peca-take');
            const r = c && c.querySelector('.take-rotulo'); return [+v.dataset.ini, +v.dataset.fim, r ? r.textContent.trim() : '']; })""")
        nav.close()
    return sorted((a, b, c) for a, b, c in r if b > a)


def segundos_para_olhar(num, pedido, maximo=6):
    """Os segundos dos quadros grandes: primeiro os que ele citou no pedido; depois, 1 s depois do começo de cada take.
    Devolve {segundo: rótulo do take nesse segundo}."""
    takes = takes_na_tela(num)
    rotulo = lambda s: next((r for a, b, r in takes if a <= s < b), "")
    citados = []
    for depois_da_palavra, antes_do_s in re.findall(r"(?:segundos?|aos?|no|em)\s+(\d{1,3}(?:[.,]\d)?)|(\d{1,3}(?:[.,]\d)?)\s*s\b", pedido):
        citados.append(round(float((depois_da_palavra or antes_do_s).replace(",", "."))))
    escolha = []
    for s in citados + [min(int(a) + 1, int(b - .01)) for a, b, _ in takes]:
        if s not in escolha:
            escolha.append(s)
    return {s: rotulo(s) for s in escolha[:maximo]}


def olhos_do_ajuste(num, pedido, resumo, folha_arq, grandes=None):
    """20/10/2026 ("aprovo o plano olhos-nos-ajustes"; ele: "os olhos tem que ver os ajustes para poder ajustar
    corretamente"): depois do ajuste, os Olhos (Sonnet, ~US$ 0,10 e ~10 s) olham a folha da prévia nova com uma pergunta
    fechada. 21/10/2026 ("aprovo o plano olhos-enxergam-rosto"; ele: "na fala do boulos aparece o lula"): também os
    quadros grandes dos takes ({segundo: (caminho, rótulo)}) e as fotos de referência de animacao/rostos/rosto-<nome>.jpg,
    com a regra de rosto e de quem fala. Devolve {"pedido_na_tela", "faltou", "defeitos"} ou {} se não responderam."""
    blocos = [{"type": "text", "text": OLHOS_AJUSTE.format(pedido=pedido.strip()[:1500], resumo=(resumo or "(sem resumo)")[:800])},
              img(folha_arq)]
    for s, (arq, rot) in sorted((grandes or {}).items()):
        if Path(arq).exists():
            blocos += [{"type": "text", "text": f"Quadro grande de {s} s · take: {rot or '(sem rótulo)'}"}, img(arq)]
    for ref in sorted((E.pasta(num) / "animacao/rostos").glob("rosto-*.jpg"))[:6]:
        blocos += [{"type": "text", "text": f"Foto de referência: {ref.stem.replace('rosto-', '').upper()}"}, img(ref)]
    texto, _ = opus(num, blocos, "Olhos (ajuste)", limite=180, modelo="sonnet")
    m = re.search(r"\{.*\}", texto or "", re.S)
    try:
        d = json.loads(m.group(0)) if m else {}
    except ValueError:
        return {}
    d["defeitos"] = [x for x in d.get("defeitos") or [] if isinstance(x, dict) and x.get("o_que")]
    # 21/10/2026: a decisão do quadro grande é do programa, não da IA (a mesma imagem do Boulos aos 13 s foi acusada numa
    # rodada e passou na outra): rosto não inteiro, ou pessoa maior que não é a do rótulo, vira defeito
    norm = lambda s: set(re.findall(r"[a-zà-ú]{3,}", (s or "").lower())) - {"desconhecida", "pedido", "deputada", "federal", "video"}
    rotulos = {int(s): r for s, (_, r) in (grandes or {}).items()}
    for q in d.get("quadros") or []:
        try:
            t = int(round(float(q.get("t"))))
        except (TypeError, ValueError):
            continue
        quem, rot = str(q.get("pessoa_maior") or ""), rotulos.get(t, "")
        if q.get("rosto_inteiro") is False:
            d["defeitos"].append({"t": t, "o_que": f"rosto de {quem or 'quem fala'} não está inteiro: {q.get('o_que_cobre') or 'cortado ou coberto'}"})
        if rot and norm(quem) and "desconhecida" not in quem.lower() and not (norm(quem) & norm(rot)):
            d["defeitos"].append({"t": t, "o_que": f"aparece {quem} em vez de {rot.split('·')[0].strip().title()}"})
    return d


def ajustar(num, pedido):
    """Devolve (ok, frase para o chat). ok=False: a cena está como estava e animacao.animar tenta de novo."""
    import animacao as A
    p = E.pasta(num); a = p / "animacao"; t0 = time.time()
    copia = a / "cena-antes-do-ajuste.html"; shutil.copy2(a / "cena.html", copia)
    try:
        E.mexe_ficha(num, progresso=15, passos=[{"quando": E.agora(), "texto": "olhando a prévia de agora"}])
        f1 = a / "folha-ajuste.jpg"; folha(num, f1)
        citadas = pastas_citadas(num, (p / "ROTEIRO.md").read_text() if (p / "ROTEIRO.md").exists() else "", pedido,
                                 (a / "cena.html").read_text())
        fixo = parte_fixa(num, citadas)
        E.mexe_ficha(num, progresso=35, passos=[{"quando": E.agora(), "texto": "animador mudando a cena (uma chamada só)"}])
        fotos = fotos_com_grade(num) if FOTO_PEDIDO.search(pedido) else []
        if fotos:
            E.mexe_ficha(num, passos=[{"quando": E.agora(), "texto": f"{len(fotos)} foto(s) em tamanho cheio, com grade e os rostos medidos"}])
        # 23/10/2026 ("aprovo o plano olho-unico-observacao"): o olho único localiza o que ele apontou antes do animador mudar
        import olho_unico
        olho = olho_unico.localizar(num, pedido, f1)
        resposta, uso = opus(num, fixo + parte_variavel(num, pedido, f1, fotos=fotos, olho=olho), "animador novo (ajuste)")
        if not resposta:
            raise RuntimeError(uso["erro"] or "o animador não respondeu")
        feitas, recusadas, erros = aplica(num, resposta, pedido)
        if not feitas and TROCA.search(resposta):
            raise RuntimeError("nenhuma troca entrou na cena (" + "; ".join(erros)[:200] + ")")
        resumo = (RESUMO.findall(resposta) or [""])[-1]
        # o que o animador avisa (custa demais, é da fala) chega ao chat (21/10/2026, pedido-limpo: ficava só no arquivo)
        avisos = [(k, x) for k in ("CUSTO", "FALA") for x in A.respostas_do_animador(TROCA.sub("", resposta))[k]]
        sem_selo = tira_selos_da_tela(num, pedido)
        if sem_selo:
            resumo = (resumo or "Ajustei a cena.") + f" Tirei também o selo da coluna Tela do roteiro (bloco(s) {', '.join(map(str, sem_selo))})."
        # 20/10/2026 ("aprovo o plano conferencia-unica"): a régua (programa) e os Olhos (Sonnet) olham a MESMA prévia nova
        # ao mesmo tempo; o que acharem vira uma lista e UM conserto; depois a régua mede de novo e os Olhos não olham de novo
        E.mexe_ficha(num, progresso=70, passos=[{"quando": E.agora(), "texto": "conferência: régua e Olhos olhando a prévia nova"}])
        from concurrent.futures import ThreadPoolExecutor
        f3 = a / "folha-ajuste.jpg"
        with ThreadPoolExecutor(max_workers=2) as ex:
            fr = ex.submit(A._regua_inteira, num)
            def olhar():                            # olhos-enxergam-rosto: a folha e os quadros grandes dos takes
                try:
                    secs = segundos_para_olhar(num, pedido)
                except Exception:
                    secs = {}
                caminhos = {s: a / f"olhos-{s}.jpg" for s in secs}
                folha(num, f3, grandes=caminhos)
                return olhos_do_ajuste(num, pedido, resumo, f3, grandes={s: (caminhos[s], secs[s]) for s in secs})
            fo = ex.submit(olhar)
            regua = fr.result()
            try:
                olhos = fo.result()
            except Exception:
                olhos = {}
        consertou = ""
        if not any(x["tipo"] == "erro" for x in regua):
            # da régua, só o grave volta ao animador (19/10/2026, ele: "pode fazer o 3"; letra pequena, rótulos empilhados e
            # meio segundo vazio viram aviso no chat); da régua e dos Olhos, só não volta o MESMO ponto que o animador já
            # disse não ser defeito, com a mesma voz (ja_respondido, 21/10/2026)
            versao, ditos = tempos(num), respondidos(num)
            pontos = [{"t": x["de"], "tipo": "régua · " + x["tipo"], "msg": x["msg"]} for x in regua if grave(x)]
            n_dispensados = len(pontos)
            pontos = [q for q in pontos if not ja_respondido(q, ditos, versao)]
            n_regua = len(pontos); n_dispensados -= n_regua
            if olhos.get("pedido_na_tela") in ("nao", "parcial") and olhos.get("faltou"):
                pontos.append({"t": 0.0, "tipo": "Olhos", "msg": "o pedido não aparece inteiro na tela: " + str(olhos["faltou"])[:200]})
            for x in olhos.get("defeitos") or []:
                try:
                    q = {"t": float(x.get("t") or 0), "tipo": "Olhos", "msg": str(x["o_que"])[:200]}
                except (TypeError, ValueError):
                    continue
                if ja_respondido(q, ditos, versao):
                    n_dispensados += 1
                else:
                    pontos.append(q)
            n_olhos = len(pontos) - n_regua
            if pontos:
                E.mexe_ficha(num, progresso=82, passos=[{"quando": E.agora(), "texto": f"consertando {len(pontos)} ponto(s) da conferência"}])
                lista = "\n".join(f"- {q['t']:.1f} s · {q['tipo']} · {q['msg']}" for q in pontos)
                ped2 = (f"A conferência da prévia DEPOIS do seu ajuste (pedido dele: \"{pedido.strip()[:600]}\") achou:\n{lista}\n"
                        "A régua é programa (mede posição e tela vazia); os Olhos olham a folha como uma pessoa. Conserte só "
                        "isto na TELA, mexendo o mínimo (posição, tamanho, margem, instantes de entrada e saída); nunca mude o "
                        "que é dito nem o que já está bom. Se um ponto não for defeito, uma linha NAO_E: <segundo> · <por quê>.")
                r2, _ = opus(num, fixo + parte_variavel(num, ped2, f3), "animador novo (conserto da conferência)")
                f = 0
                if r2:
                    f, _, e2 = aplica(num, r2, ped2); erros += e2
                    linhas = A.respostas_do_animador(TROCA.sub("", r2))
                    avisos += [(k, x) for k in ("CUSTO", "FALA") for x in linhas[k]]

                    def ponto_de(t):         # a resposta do animador fala de qual ponto (o mais perto no tempo)
                        q = min(pontos, key=lambda q: abs(q["t"] - t), default=None)
                        return q if q and abs(q["t"] - t) <= 1.5 else {"tipo": "", "msg": ""}
                    guardar = [r for r in ditos if r.get("tempos") == versao] + [
                        {"t": x["t"], "tipo": k, "msg": x["msg"], "tempos": versao,
                         "ponto_tipo": ponto_de(x["t"])["tipo"], "ponto_msg": ponto_de(x["t"])["msg"]}
                        for k in ("FALA", "NAO_E", "CUSTO") for x in linhas[k]]
                    (a / "respondidos.json").write_text(json.dumps(guardar, ensure_ascii=False, indent=1))
                    regua = A._regua_inteira(num)
                consertou = (f" Conferência: achou {len(pontos)} ponto(s) ({n_regua} da régua, {n_olhos} dos Olhos); "
                             + (f"consertei {f} troca(s)." if f else "não consegui consertar."))
            else:
                consertou = " Conferência: ok" + (", os Olhos viram o pedido na tela." if olhos else " (os Olhos não responderam).")
            if n_dispensados:
                consertou += f" ({n_dispensados} ponto(s) que você ou o animador já tinham dispensado ficaram de fora.)"
        # 23/10/2026 ("aprovo o plano conferir-o-pedido-e-faixa-preta"; #354: os Olhos viram "parcial", o conserto não foi
        # olhado de novo e a resposta disse "subi"): os segundos que ele citou são conferidos de novo, na cena final
        E.mexe_ficha(num, progresso=92, passos=[{"quando": E.agora(), "texto": "conferindo o pedido na prévia final"}])
        conferido = olho_unico.conferir_pedido(num, pedido)
        conf = {"quando": E.agora(), "quem": "régua e Olhos (ajuste pelo animador novo)", "olhos_ajuste": olhos, "regua": [{k: x[k] for k in ("de", "tipo", "msg")} for x in regua],
                "opiniao": {}, "vazios": [x for x in regua if x["tipo"] == "vazio"], "consertos": [], "sobrou": [], "fala": [], "custo": [],
                "pedido_conferido": conferido}
        E._grava(a / "conferencia.json", json.dumps(conf, ensure_ascii=False, indent=1))
        gasto = gasto_da_animacao(num, t0)
        # 24/10/2026 (parte B): no chat, o resumo e o que pede decisão dele; o relatório vai nos detalhes, fechado
        detalhes = olho_unico.frase_conferida(consertou.strip(), conferido)
        if erros:
            detalhes += " " + " ".join(dict.fromkeys(erros))        # a mesma recusa saía duas vezes (#316, 15:55)
        detalhes += aviso_para_ele(num, regua, avisos) + f" ({time.time() - t0:.0f} s, US$ {gasto:.2f})"
        frase = " ".join(x for x in ((resumo or "Ajustei a cena."), pergunta_para_ele(num, regua, conferido)) if x)
        frase += E.DETALHES + detalhes.strip()
        E.evento(num, f"ajuste pelo animador novo em {time.time() - t0:.0f} s, US$ {gasto:.2f}, régua {len(regua)}")
        copia.unlink(missing_ok=True)
        return True, frase
    except Exception as ex:
        shutil.copy2(copia, a / "cena.html"); copia.unlink(missing_ok=True)       # a cena volta como estava
        E.evento(num, f"animador novo não deu ({str(ex)[:200]})")
        return False, str(ex)[:200]


# ---- a primeira animação ---------------------------------------------------------------------------------------------

LIMITE_PRIMEIRA = 600        # a cena inteira sai numa resposta só: mais texto para escrever que num ajuste
PRIMEIRA = """

## Como trabalhar NESTA rodada: a PRIMEIRA animação do vídeo, numa resposta só
Você não abre arquivos nem roda nada: tudo vem neste pedido (as regras acima, o roteiro com o tempo de cada palavra, os
mosaicos do material e as folhas de quadros dos vídeos, com o segundo de cada quadro). Escreva a cena INTEIRA do zero,
bloco a bloco, seguindo a coluna Tela, com as PEÇAS PRONTAS das regras (T.take, T.selo ou T.carimbos, T.documento,
T.fotos, T.locutor, T.seguir, T.fecho ou T.assinatura, T.som, T.bloco, T.palavra); só desenhe à mão o que nenhuma peça faz.
Os takes saem do vídeo pelo segundo: use as folhas de quadros para escolher o trecho e o enquadramento.
Responda SÓ o conteúdo completo do animacao/cena.html (o <svg> com o que for desenhado à mão e o <script> com
window.DESTAQUE e function montar(tl, T) { ... }), sem explicação e sem cercas de código. Na ÚLTIMA linha, fora do
HTML, uma linha RESUMO: <o que a animação mostra, em até 2 frases, para ele ler no chat do celular: português simples,
sem pixel, coordenada, nome de arquivo nem de peça>.
"""


def folhas_dos_videos(num):
    """Uma folha de quadros por vídeo da pauta e do material (o segundo em amarelo), para ele escolher os takes sem
    abrir o vídeo. Até 2 min: 1 quadro a cada 2 s; mais longo: a cada 5 s, no máximo 60 quadros."""
    from PIL import Image, ImageDraw, ImageFont
    p = E.pasta(num); dest = p / "animacao/folhas-videos"; shutil.rmtree(dest, ignore_errors=True); dest.mkdir(parents=True)
    videos = [p / "referencia/video.mp4"] + sorted(p.glob("material/*/video.mp4"))
    f = ImageFont.truetype(str(E.RAIZ / "web/fontes/impact.ttf"), 22)
    feitas = []
    for v in [v for v in videos if v.exists()]:
        try:
            dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(v)]))
        except Exception:
            continue
        passo = 2 if dur <= 120 else max(5, dur / 60)
        ts = [round(t * passo, 1) for t in range(int(dur / passo) + 1)][:60]
        quadros = []
        for t in ts:
            png = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(t), "-i", str(v), "-frames:v", "1", "-vf", "scale=240:-2",
                                  "-f", "image2pipe", "-vcodec", "mjpeg", "-"], capture_output=True).stdout
            if png:
                import io
                quadros.append((t, Image.open(io.BytesIO(png)).convert("RGB")))
        if not quadros:
            continue
        lw, lh = quadros[0][1].size; col = 8
        im = Image.new("RGB", (col * lw, ((len(quadros) + col - 1) // col) * lh), "black"); d = ImageDraw.Draw(im)
        for i, (t, q) in enumerate(quadros):
            x, y = (i % col) * lw, (i // col) * lh
            im.paste(q.resize((lw, lh)), (x, y)); d.rectangle([x, y, x + 64, y + 26], fill="black")
            d.text((x + 4, y + 1), f"{t:.0f} s", fill="yellow", font=f)
        saida = dest / f"{v.parent.name}.jpg"; im.save(saida, quality=85)
        feitas.append((str(v.relative_to(p)), saida, dur))
    return feitas


TELA_PESADA = 2600       # caracteres da coluna Tela: #368 (2.364, micro doc) e #369 (3.019) estouraram os 600 s; na VPS o
                         # maior que coube foi o #334 (2.478, 373 s). Micro doc e molde números contam como pesados
LIMITE_PLANO = 300
# 24/10/2026 (prova no #369): com o plano pronto em 190 s, a escrita pensou os 600 s de novo e não escreveu nada; o plano só
# somava ~3 min. Desligado até a prova da escrita com esforço menor ("pode" dele para a prova)
PLANO_LIGADO = False


def tela_pesada(num):
    f = E.ler_ficha(num)
    if f.get("molde") in ("microdoc", "numeros"):
        return True
    return sum(len(b.get("tela") or "") for b in E.blocos(num)) > TELA_PESADA


PLANO = """
## Como trabalhar NESTA rodada: só o PLANO da cena (a escrita vem na próxima, seguindo este plano)
Tudo vem neste pedido. NÃO escreva código. Para cada bloco, em até 3 linhas curtas: as peças prontas que usa (T.take,
T.selo, T.numeros..., ou "desenho" só quando nenhuma peça faz), o que cada uma mostra (texto, número, foto, take e o
segundo do vídeo), em que palavra entra (T.palavra) e quando sai, e onde fica (topo, centro, embaixo). Resolva aqui as
escolhas difíceis (qual take, qual foto, o que vai em cada camada) para a escrita não precisar repensar. Seja curto:
no máximo 1.500 palavras, sem explicação.
"""


def pedido_primeira(num):
    """O pedido da primeira animação (o mesmo da VPS para os vídeos normais; testes/micro_doc.py confere). No micro doc
    e no molde números entram antes da instrução final as fotos e a trilha já prontas, a peça e o exemplo. Devolve
    (blocos, fixo, extra): o conserto reusa fixo (a parte em cache) e extra (a peça do molde; vazio no vídeo normal)."""
    import animacao as A
    p = E.pasta(num)
    citadas = pastas_citadas(num, (p / "ROTEIRO.md").read_text() if (p / "ROTEIRO.md").exists() else "",
                             " ".join(f"material/{x.name}/" for x in (p / "material").iterdir()) if (p / "material").exists() else "")
    fixo = parte_fixa(num, citadas)
    folhas = folhas_dos_videos(num)
    blocos = list(fixo)
    if folhas:
        blocos.append({"type": "text", "text": "## As folhas de quadros dos vídeos (o segundo de cada quadro em amarelo)"})
        for rel, im, dur in folhas:
            blocos += [{"type": "text", "text": f"Vídeo {rel} ({dur:.0f} s)"}, img(im)]
    extra = []
    if E.ler_ficha(num).get("molde") in ("microdoc", "numeros"):
        E._ferramentas(); import preparo_microdoc as PM
        extra = PM.pedido(num)
    blocos += extra
    blocos.append({"type": "text", "text": A.contexto(num, None).split("O que ele pediu no chat deste vídeo")[1][:6000] + PRIMEIRA})
    return blocos, fixo, extra


def primeira(num):
    """A primeira animação no caminho novo (19/10/2026; ele: "vamos resolver primeiro o gasto?"; no #300 ela custou
    ~5 a 10 de peso no animador em passos). Devolve (ok, frase). ok=False: não fica cena nenhuma e animacao.animar
    tenta de novo."""
    import animacao as A
    p = E.pasta(num); a = p / "animacao"; a.mkdir(exist_ok=True); t0 = time.time(); cena = a / "cena.html"
    try:
        E.mexe_ficha(num, progresso=10, passos=[{"quando": E.agora(), "texto": "preparando o material e as folhas dos vídeos"}])
        if E.ler_ficha(num).get("molde") in ("microdoc", "numeros"):
            # 24/10/2026 (ele: "porque o micro doc não pode usar a mesma logica dos outros videos?"): fotos e trilha
            # prontas antes, como os mosaicos; no #368 o animador pensou 600 s sem escrever, porque tinha de buscá-las
            E.mexe_ficha(num, passos=[{"quando": E.agora(), "texto": "micro doc: escolhendo e baixando as fotos e montando a trilha"}])
            E._ferramentas(); import preparo_microdoc as PM
            feito = PM.preparar(num, opus)
            E.mexe_ficha(num, progresso=20, passos=[{"quando": E.agora(), "texto": f"micro doc: {len([f for f in feito['fotos'] if not f.get('erro')])} foto(s) e trilha em {len(feito['trilha'])} parte(s), em {feito['segundos']:.0f} s"}])
        blocos, fixo, extra = pedido_primeira(num)
        if PLANO_LIGADO and tela_pesada(num):
            # 24/10/2026 (animacao-mais-rapida-e-certa): na Tela pesada a chamada única pensava 600 s e não escrevia (#368,
            # #369: 10 min perdidos e o jeito de antes, ~16 min); aqui ele decide a cena num plano curto e escreve seguindo-o
            E.mexe_ficha(num, progresso=25, passos=[{"quando": E.agora(), "texto": "Tela pesada: o animador planeja a cena antes de escrever"}])
            pedido_plano = blocos[:-1] + [{"type": "text", "text": blocos[-1]["text"].replace(PRIMEIRA, PLANO)}]
            plano, _ = opus(num, pedido_plano, "animador novo (plano da cena)", limite=LIMITE_PLANO)
            if plano:
                blocos[-1] = {"type": "text", "text": blocos[-1]["text"] + "\n\n## O PLANO DA CENA (já decidido nesta mesma rodada: "
                              "siga-o bloco a bloco e escreva direto, sem repensar)\n" + plano.strip()[:12000]}
        E.mexe_ficha(num, progresso=30, passos=[{"quando": E.agora(), "texto": "animador escrevendo a cena inteira (uma chamada só)"}])
        resposta, uso = opus(num, blocos, "animador novo (primeira animação)", limite=LIMITE_PRIMEIRA)
        if not resposta:
            raise RuntimeError(uso["erro"] or "o animador não respondeu")
        resumo = (RESUMO.findall(resposta) or [""])[-1]
        html_ = RESUMO.sub("", resposta).strip()
        html_ = re.sub(r"^```\w*\n|\n```\s*$", "", html_).strip()
        if "function montar" not in html_:
            raise RuntimeError("a resposta não trouxe a cena (sem function montar)")
        cena.write_text(html_)
        # régua e tela vazia; os Olhos (Opus em mosaico) uma vez; um conserto só com tudo
        E.mexe_ficha(num, progresso=60, passos=[{"quando": E.agora(), "texto": "régua, tela vazia e os Olhos conferindo"}])
        regua = A._regua_inteira(num)
        if any(x["tipo"] == "erro" for x in regua):
            pontos = [{"t": 0, "tipo": "erro", "msg": "; ".join(x["msg"] for x in regua if x["tipo"] == "erro")}]
            op = {}
        else:
            # 24/10/2026 (animacao-mais-rapida-e-certa): os Olhos, o editor e o olho único olham AO MESMO TEMPO (antes um
            # depois do outro, ~63 s no #370), e o que o olho único vê entra no conserto (no #370 ele viu o rosto cortado e
            # a pessoa errada, mas só depois do conserto, no chat)
            from concurrent.futures import ThreadPoolExecutor
            import olho_unico
            with ThreadPoolExecutor(3) as ex:
                f_olhos = ex.submit(A.assistir_previa, num, "opus")
                f_editor = ex.submit(revisar, num)
                f_olho = ex.submit(olho_unico.olhar_previa, num) if olho_unico.ligado() else None
            op = f_olhos.result()["olhos"]
            pontos = [{"t": x["de"], "tipo": x["tipo"], "msg": x["msg"]} for x in regua]
            try:                                     # 19/10/2026: o olho de editor (erros de edição), além do espectador
                erros_ed, _ = f_editor.result()
                pontos += [{"t": float(e["t"]), "tipo": f"edição ({e.get('gravidade', '')})", "msg": f"{e.get('problema', '')} → {e.get('conserto', '')}"} for e in erros_ed]
            except Exception:
                pass
            try:
                r_olho = f_olho.result() if f_olho else {}
                pontos += [{"t": float(d["t"]), "tipo": "olho único", "msg": f"{d.get('o_que', '')} → {d.get('como_consertar', '')}"}
                           for d in r_olho.get("defeitos") or [] if isinstance(d, dict) and d.get("o_que") and isinstance(d.get("t"), (int, float))]
            except Exception:
                pass
            for x in op.get("perderia_atencao") or []:
                try:
                    pontos.append({"t": float(x.get("t")), "tipo": "olhos", "msg": str(x.get("porque", ""))})
                except (TypeError, ValueError):
                    pass
        consertou = ""
        if pontos:
            E.mexe_ficha(num, progresso=75, passos=[{"quando": E.agora(), "texto": f"consertando {len(pontos)} ponto(s)"}])
            f2 = a / "folha-ajuste.jpg"; folha(num, f2)
            lista = "\n".join(f"- {q['t']:.1f} s · {q['tipo']} · {q['msg']}" for q in pontos)
            ped2 = (f"Pontos para conferir (régua e tela vazia são programa; os Olhos, um espectador que não sabe nada do roteiro; "
                    f"erro é a cena quebrada):\n{lista}\nConserte o que for defeito na TELA mexendo o mínimo, fiel à coluna Tela; "
                    "nunca mude o que é dito. Para cada ponto, uma linha FEITO, NAO_E, FALA ou CUSTO.")
            # 24/10/2026: "fixo" voltou a vir do pedido_primeira (na mudança do micro doc ele sumiu daqui e o conserto
            # quebrava com "name 'fixo' is not defined", prova do #367); extra = a peça do molde, vazio no vídeo normal
            r2, _ = opus(num, fixo + extra + parte_variavel(num, ped2, f2), "animador novo (conserto da primeira)")
            if r2:
                feitas, _, _ = aplica(num, r2, ped2)
                linhas = A.respostas_do_animador(TROCA.sub("", r2))
                versao = tempos(num)
                perto = lambda t: min(pontos, key=lambda q: abs(q["t"] - t)) if pontos and min(abs(q["t"] - t) for q in pontos) <= 1.5 \
                    else {"tipo": "", "msg": ""}
                (a / "respondidos.json").write_text(json.dumps([{"t": x["t"], "tipo": k, "msg": x["msg"], "tempos": versao,
                                                                 "ponto_tipo": perto(x["t"])["tipo"], "ponto_msg": perto(x["t"])["msg"]}
                                                                for k in ("FALA", "NAO_E", "CUSTO") for x in linhas[k]], ensure_ascii=False, indent=1))
                consertou = f" Conferi e consertei {feitas} ponto(s)."
            regua = A._regua_inteira(num)
            # 25/10/2026 (ele: "ele tem que olhar o enquadramento e relatar isso para consertar"; #382: o olho único viu o
            # rosto do Lula baixo e a foto cortando um homem, o conserto mexeu na cena e ninguém olhou de novo; o chat disse
            # só "Primeira animação pronta"): depois do conserto o olho único olha DE NOVO; o que ele ainda vê entra na
            # conferência como aviso grave (tipo "olhos": a tela mostra, com "Consertar estes avisos" e "Aprovar mesmo
            # assim") e vai ao chat
            import olho_unico
            if olho_unico.ligado() and not any(x["tipo"] == "erro" for x in regua):
                E.mexe_ficha(num, progresso=88, passos=[{"quando": E.agora(), "texto": "os Olhos olhando de novo depois do conserto"}])
                try:
                    import hashlib
                    r3 = olho_unico.olhar_previa(num)
                    if r3.get("erro"):
                        # 25/10/2026 (revisão de solidez): olhada que falhou não é "não veem mais problema"
                        raise RuntimeError(f"os Olhos não responderam ({str(r3['erro'])[:120]})")
                    olho_unico.registra(num, "previa (depois do conserto)", {**r3, "cena": hashlib.md5(cena.read_bytes()).hexdigest()[:10]})
                    for d in r3.get("defeitos") or []:
                        if isinstance(d, dict) and d.get("o_que") and isinstance(d.get("t"), (int, float)):
                            regua.append({"de": float(d["t"]), "ate": float(d["t"]), "tipo": "olhos",
                                          "msg": f"{d['o_que']} → {d.get('como_consertar', '')}".strip(" →")})
                    sobrou = [x for x in regua if x["tipo"] == "olhos"]
                    consertou += (f" Os Olhos olharam de novo e ainda veem {len(sobrou)} ponto(s): "
                                  + "; ".join(f"{x['de']:.1f} s: {x['msg'][:140]}" for x in sobrou[:3])
                                  + ". Toque em Consertar estes avisos, ou aprove assim." if sobrou
                                  else " Os Olhos olharam de novo e não veem mais problema.")
                except Exception as ex:
                    E.evento(num, f"olho: a segunda olhada parou ({str(ex)[:160]})")
                    consertou += " Não consegui olhar de novo depois do conserto (os Olhos falharam): confira a prévia."
        if any(x["tipo"] == "erro" for x in regua):
            raise RuntimeError("a cena continua com erro depois do conserto: " + "; ".join(x["msg"] for x in regua if x["tipo"] == "erro")[:200])
        conf = {"quando": E.agora(), "quem": "animador novo (primeira animação)", "regua": [{k: x[k] for k in ("de", "tipo", "msg")} for x in regua],
                "opiniao": op, "vazios": [x for x in regua if x["tipo"] == "vazio"],
                "consertos": [{"t": q["t"], "tipo": q["tipo"], "msg": q["msg"][:300]} for q in pontos],
                "sobrou": [{"t": x["de"], "msg": x["msg"]} for x in regua if x["tipo"] == "olhos"], "fala": [], "custo": []}
        E._grava(a / "conferencia.json", json.dumps(conf, ensure_ascii=False, indent=1))
        gasto = gasto_da_animacao(num, t0)
        E.evento(num, f"primeira animação pelo animador novo em {time.time() - t0:.0f} s, US$ {gasto:.2f}, régua {len(regua)}")
        return True, ((resumo or "Fiz a primeira animação.") + E.DETALHES + consertou.strip()
                      + f" Régua: {len(regua)} problema(s). ({time.time() - t0:.0f} s, US$ {gasto:.2f})")
    except Exception as ex:
        cena.unlink(missing_ok=True)          # a 2ª tentativa começa do zero
        E.evento(num, f"primeira animação pelo animador novo não deu ({str(ex)[:200]})")
        return False, str(ex)[:200]


# ---- a revisão de edição (olho de editor) ----------------------------------------------------------------------------

EDITOR = """Você é o editor-chefe de vídeos curtos da @newsbr360 (checagem, formato vertical 1080x1920). Abaixo estão os quadros
da prévia (o segundo de cada um em amarelo, e o bloco do roteiro) e o roteiro com a coluna Tela de cada bloco. Procure
ERROS DE EDIÇÃO, não de conteúdo:
- dois elementos um por cima do outro (gráfico, documento ou texto em cima de um take, de um rosto ou de outro texto);
- um elemento que entra antes do anterior sair, ou some antes da hora;
- take borrado por zoom demais, rosto cortado, pessoa errada na tela para o que está sendo dito;
- ENQUADRAMENTO de Reels (tela em pé, vista inteira no celular; 25/10/2026, ele: "ele tem que olhar o enquadramento e
  relatar isso para consertar"): foto ou vídeo numa faixa com o topo vazio ou meia tela sem imagem; pessoa cortada na
  borda; olhos ou boca atrás de texto, pílula, selo ou degradê; marca ou logo de outro veículo na imagem;
- texto cortado na borda, letra pequena demais para ler no celular, crédito ou rótulo faltando;
- tela parada mais de 3 s sem nada mudar, ou tela vazia;
- o que está na tela não bate com a coluna Tela do bloco, ou com o que está sendo dito naquele segundo;
- legenda (embaixo) com palavra errada em relação ao roteiro.
Não aponte gosto pessoal nem coisa que o roteiro pediu. Responda SÓ um JSON com até 12 itens, do mais grave ao menos:
[{"t": segundos, "bloco": n, "gravidade": "alta" | "media" | "baixa", "problema": "<até 20 palavras>", "conserto": "<até 20 palavras>"}]"""


def quadros_da_previa(num, pasta=None):
    """Quadros da prévia: 1 por segundo e mais um 0,4 s depois do começo de cada bloco (onde as trocas acontecem).
    pasta: o olho único usa a dele (consertos-da-revisao: na mesma pasta, um apagava os quadros do outro)."""
    import ver, animacao as A
    d = Path(pasta) if pasta else E.pasta(num) / "animacao/revisao-quadros"; shutil.rmtree(d, ignore_errors=True)
    blocos = A.dados(num)["blocos"]
    fim, feitos, _ = ver.percorrer(num, 1.0, d)
    extra = sorted({round(b["ini"] + .4, 2) for b in blocos} - {round(t, 2) for t, _ in feitos})
    if extra:
        mais, _ = ver.quadros(num, extra, saida=d / "extra")
        feitos += list(zip(extra, mais))
    return sorted(feitos), blocos


def mosaicos_da_previa(num, feitos, blocos, pasta=None):
    from PIL import Image, ImageDraw, ImageFont
    dest = Path(pasta) if pasta else E.pasta(num) / "animacao/revisao-mosaicos"
    shutil.rmtree(dest, ignore_errors=True); dest.mkdir(parents=True)
    f = ImageFont.truetype(str(E.RAIZ / "web/fontes/impact.ttf"), 24)
    bloco_em = lambda t: next((b["n"] for b in blocos if b["ini"] - .05 <= t < b["fim"] + .3), "")
    saidas, por = [], 16
    for k in range(0, len(feitos), por):
        g = feitos[k:k + por]; lw, lh, col = 270, 480, 4
        im = Image.new("RGB", (col * lw, ((len(g) + col - 1) // col) * lh), "black"); d = ImageDraw.Draw(im)
        for i, (t, q) in enumerate(g):
            x, y = (i % col) * lw, (i // col) * lh
            im.paste(Image.open(q).convert("RGB").resize((lw, lh)), (x, y)); d.rectangle([x, y, x + 150, y + 30], fill="black")
            d.text((x + 4, y + 2), f"{t:.1f} s · b{bloco_em(t)}", fill="yellow", font=f)
        s = dest / f"previa-{k // por + 1}.jpg"; im.save(s, quality=85); saidas.append(s)
    return saidas


def recado(num):
    """24/10/2026 (ele: "eu pensei que o editor tinha visão do todo, estava ciente do que estava produzindo"; "pode fazer o
    editor do molde números com o recado"): o editor recebe o Ângulo do vídeo (a ideia em uma frase, INTENCAO.md) e o
    que os Olhos entenderam assistindo (se a opinião deles é desta cena), e diz se o recado chegou à tela."""
    p = E.pasta(num)
    m = re.search(r"^Ângulo:\s*(.+)$", (p / "INTENCAO.md").read_text() if (p / "INTENCAO.md").exists() else "", re.M)
    if not m:
        return ""
    txt = f"\n\nO RECADO do vídeo (o Ângulo, a ideia em uma frase): {m.group(1).strip()}"
    # intencao-viva (24/10/2026): as decisões dele para o vídeo inteiro também (o editor confere se a tela as respeita)
    intencao = (p / "INTENCAO.md").read_text()
    if E.DECISOES in intencao:
        txt += "\nAs decisões dele para este vídeo (a tela tem de respeitar):\n" + intencao[intencao.index(E.DECISOES) + len(E.DECISOES):].strip()[:2000]
    op, cena = p / "animacao/olhar/olhos/opiniao.json", p / "animacao/cena.html"
    try:
        if op.exists() and cena.exists() and op.stat().st_mtime >= cena.stat().st_mtime:
            entendi = json.loads(op.read_text()).get("entendi")
            if entendi:
                txt += f"\nO que um espectador entendeu assistindo a esta prévia: {entendi}"
    except (OSError, ValueError):
        pass
    return txt + ("\nAlém dos erros de edição, veja o recado: se o espectador não saiu com ele, ou se a conclusão não mostra o "
                  "recado NA TELA (quem assiste sem som tem de sair com ele), aponte UM item com \"problema\" começando por "
                  "\"recado:\" e o conserto na tela (no segundo da conclusão). Recado que chegou não é item.")


def revisar(num):
    """19/10/2026 (ele: "tem vários erros de edição. consegue colocar a visão para olhar e resolver?"): o olho de editor
    sobre a prévia inteira (Opus, numa chamada, com os quadros em mosaico e o roteiro). Devolve a lista de erros."""
    import animacao as A
    feitos, blocos = quadros_da_previa(num)
    mos = mosaicos_da_previa(num, feitos, blocos)
    rot = "\n".join(f"- bloco {b['n']} ({b['ini']:.1f}-{b['fim']:.1f} s) · {'nós' if b['nosso'] else b['quem']} · fala: {b['fala'][:200]} · Tela: {b['tela'][:300]}" for b in blocos)
    conteudo = [{"type": "text", "text": EDITOR + recado(num) + "\n\nRoteiro:\n" + rot}]
    for m in mos:
        conteudo += [{"type": "text", "text": m.name}, img(m)]
    texto, uso = opus(num, conteudo, "editor (revisão de edição)")
    m = re.search(r"\[.*\]", texto or "", re.S)
    try:
        erros = json.loads(m.group(0)) if m else []
    except ValueError:
        erros = []
    perto = lambda t: min(feitos, key=lambda q: abs(q[0] - t))
    return [e for e in erros if isinstance(e, dict) and "t" in e], perto


def revisar_e_consertar(num):
    """A revisão de edição e UM conserto com tudo o que ela achou (e a régua). Devolve (ok, frase)."""
    import animacao as A
    a = E.pasta(num) / "animacao"; t0 = time.time()
    copia = a / "cena-antes-da-revisao.html"; shutil.copy2(a / "cena.html", copia)
    try:
        E.mexe_ficha(num, progresso=20, passos=[{"quando": E.agora(), "texto": "o editor olhando a prévia inteira"}])
        erros, perto = revisar(num)
        regua = A._regua_inteira(num)
        pontos = [{"t": float(e["t"]), "tipo": f"edição ({e.get('gravidade', '')})", "msg": f"{e.get('problema', '')} → {e.get('conserto', '')}"} for e in erros]
        pontos += [{"t": x["de"], "tipo": x["tipo"], "msg": x["msg"]} for x in regua]
        if not pontos:
            copia.unlink(missing_ok=True)
            return True, "O editor olhou a prévia inteira e não achou erro de edição. Régua: 0."
        E.mexe_ficha(num, progresso=60, passos=[{"quando": E.agora(), "texto": f"consertando {len(pontos)} erro(s) de edição"}])
        quadros = sorted({perto(q["t"]) for q in pontos})[:12]
        f2 = a / "folha-ajuste.jpg"; folha(num, f2)
        lista = "\n".join(f"- {q['t']:.1f} s · {q['tipo']} · {q['msg']}" for q in sorted(pontos, key=lambda q: q["t"]))
        ped = (f"O editor-chefe (e a régua) acharam estes erros de edição na prévia:\n{lista}\nConserte cada um na cena, mexendo o "
               "mínimo e fiel à coluna Tela; nunca mude o que é dito. Para cada ponto, uma linha FEITO ou NAO_E.")
        r, _ = opus(num, parte_fixa(num, pastas_citadas(num, (E.pasta(num) / "ROTEIRO.md").read_text())) + parte_variavel(num, ped, f2, quadros=quadros),
                    "animador novo (conserto da revisão)")
        if not r:
            raise RuntimeError("o conserto não respondeu")
        feitas, recusadas, err = aplica(num, r, ped)
        linhas = A.respostas_do_animador(TROCA.sub("", r))
        regua = A._regua_inteira(num)
        if any(x["tipo"] == "erro" for x in regua):
            raise RuntimeError("a cena quebrou no conserto")
        conf = json.loads((a / "conferencia.json").read_text()) if (a / "conferencia.json").exists() else {}
        conf |= {"quando": E.agora(), "regua": [{k: x[k] for k in ("de", "tipo", "msg")} for x in regua], "revisao_edicao": erros}
        E._grava(a / "conferencia.json", json.dumps(conf, ensure_ascii=False, indent=1))
        copia.unlink(missing_ok=True)
        gasto = sum(g.get("usd") or 0 for g in E.gastos(num) if g.get("quando", "") >= time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime(t0 - 1)))
        E.evento(num, f"revisão de edição: {len(erros)} erro(s), {feitas} troca(s), régua {len(regua)}, {time.time() - t0:.0f} s, US$ {gasto:.2f}")
        feito = "; ".join(f"{x['t']:.0f} s: {x['msg']}" for x in linhas["FEITO"][:8])
        return True, (f"Revisei o vídeo inteiro: achei {len(erros)} erro(s) de edição e consertei {feitas}."
                      + (" " + pergunta_para_ele(num, regua) if pergunta_para_ele(num, regua) else "")
                      + E.DETALHES + f"Consertei: {feito or f'{feitas} troca(s)'}." + (" " + " ".join(err) if err else "")
                      + f" Régua: {len(regua)} problema(s). ({time.time() - t0:.0f} s, US$ {gasto:.2f})")
    except Exception as ex:
        shutil.copy2(copia, a / "cena.html"); copia.unlink(missing_ok=True)
        return False, f"a revisão de edição não deu: {str(ex)[:200]}"
