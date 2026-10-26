"""O agente de capa (21/10/2026, "aprovo o plano agente-de-capa"; ele: "o gerador de capa tem que ser um llm que usa os
olhos para ver o vídeo e escolher o melhor momento e a frase mais chamativa para conseguir o clique ... tem que ser
barato"). Era um agente com ferramentas (Opus, ~US$ 0,98 e ~4 min por par, medido em 17 capas) que relia tudo a cada
passo; agora:

  1. os Olhos de capa (Sonnet, UMA chamada) veem a prévia (1 quadro por segundo, com a fala de cada trecho), o roteiro, a
     intenção, as regras (regras/CAPA.md e a capa do molde) e o estudo do que deu clique (estudos/capas/LEIA.md), e
     devolvem as duas opções: desenho, o segundo de cada foto, a fala entre aspas, o selo, o título e o destaque;
  2. o programa tira a foto desse segundo do vídeo ORIGINAL do take e recorta o rosto (YuNet): foto sempre real;
  3. o programa monta as duas capas nos desenhos fixos da identidade (um rosto; dois rostos frente a frente);
  4. os Olhos conferem as capas prontas (Sonnet, chamada pequena); rosto ruim troca a foto pelo 2º momento, uma vez.
Pedido dele ("Flávio e Lula frente a frente") entra no passo 1. Escreve capa-1.html, capa-2.html e capas.json, como antes.

  python3 capa_agente.py <número> ["pedido"]
"""
import json, re, subprocess, sys, time
from pathlib import Path

import estudio as E

COR = {"ERRADO": "errado", "FALSO": "errado", "NÃO CUMPRIU": "errado", "SEM PROVA": "sem-prova", "EXAGERO": "exagero",
       "MEIA-VERDADE": "exagero", "VERDADE": "verdade"}
ESC = lambda s: str(s).replace("&", "&amp;").replace("<", "&lt;").replace('"', "&quot;")

PEDIDO = """Você é os Olhos de capa da @newsbr360. Assista o vídeo (a folha: 1 quadro por segundo, o segundo em amarelo) e
escolha a capa que faz a pessoa PARAR e querer ver. Siga as regras e o estudo abaixo; eles valem mais que o seu gosto.

{regras}

## O que deu clique na página (estudos/capas/LEIA.md)
{estudo}

## Este vídeo
Formato: {formato} · molde: {molde}
Intenção: {intencao}
Roteiro (bloco · de-até · quem fala · fala):
{roteiro}
Takes (de-até no vídeo · rótulo): {takes}
Fotos de rosto já recortadas: {rostos}
{pedido}

## Desenhos que o estúdio sabe montar
- "um_rosto": a foto do rosto grande no alto (até o topo), a fala entre aspas perto dele, o selo, o título e o destaque.
- "dois_rostos": duas pessoas, uma de cada lado, de frente uma para a outra, esmaecendo no meio; o título embaixo.

Responda SÓ um JSON, sem cercas, com DUAS opções que variam no que importa (o rosto, o momento ou a fala):
{{"opcoes": [{{"desenho": "um_rosto" | "dois_rostos",
  "fotos": [{{"t": <segundo do vídeo com o rosto, com emoção: boca aberta, gesto, olhar>, "quem": "<nome>"}}],
  "aspas": "<fala LITERAL do roteiro, palavra por palavra, até ~70 letras, ou vazio>", "quem_aspas": "<de quem é a fala>",
  "selo": "<VERDADE|MEIA-VERDADE|EXAGERO|SEM PROVA|ERRADO|NÃO CUMPRIU ou vazio>",
  "titulo": "<o título em CAIXA ALTA, até ~40 letras>", "destaque": "<a frase amarela, até ~22 letras>",
  "doc": "<a linha pequena do documento, ou vazio>", "prova": "<mm:ss em que o vídeo prova a capa>",
  "porque": "<por que chama atenção, uma frase>", "risco": "<o que pode falhar>",
  "foto_reserva": {{"t": <outro segundo bom do mesmo rosto>, "quem": "<nome>"}}}}]}}
Título e destaque são em Impact, onde o algarismo 0 parece a letra O ("1 PROMESSA, 0 CUMPRIDA" foi lido "O CUMPRIDA"):
escreva NENHUMA/NENHUM/ZERO por extenso no lugar do 0 sozinho.
No "dois_rostos", "fotos" tem DUAS pessoas, a primeira fica à ESQUERDA. Só escolha segundo em que a pessoa aparece de
verdade na folha. Nunca invente fala, número ou veredito que o roteiro não tenha."""

CONFERE = """Você é os Olhos que conferem a capa antes de ela ir ao ar. Para cada capa (inteira e o recorte 3:4 da grade do
Instagram), responda SÓ um JSON, sem cercas: {{"capas": [{{"op": <n>, "rosto_ok": true|false, "texto_ok": true|false,
"problema": "<o que está errado, ou vazio>", "titulo": "<o título corrigido, só se o texto não faz sentido>",
"destaque": "<a frase amarela corrigida, só se não faz sentido>", "mover_y": <inteiro>, "marca": true|false}}]}}. rosto_ok: a pessoa que a capa devia mostrar está na foto e em destaque (não a plateia), o rosto de cada pessoa aparece inteiro (olhos, nariz e boca) e
nítido, e cabe no recorte 3:4. texto_ok: o título e o destaque estão inteiros, legíveis, não cobrem o rosto e FAZEM
SENTIDO lidos em voz alta, em português correto (sem palavra trocada ou faltando: "1 PROMESSA, O CUMPRIDA" não faz).
Se não fizer sentido, devolva em "titulo"/"destaque" a frase corrigida, com o mesmo fato e o mesmo tamanho; nunca
invente fato, número ou veredito que a capa não tenha. Na fonte Impact o algarismo 0 parece a letra O: se for isso,
corrija escrevendo NENHUMA/ZERO por extenso.
ENQUADRAMENTO (25/10/2026, ele: "ele tem que olhar o enquadramento e relatar isso para consertar"): a capa é de um
Reels, vista no celular. Também é problema (escreva em "problema"): marca ou logo de outro veículo na imagem (Metrópoles,
Globo, SBT, CNN...); selo, logo ou texto encostando no rosto. Quando o rosto está cortado ou escondido por causa da
ALTURA da foto (boca atrás do degradê, queixo no título, testa cortada demais, marca de outro veículo no alto), devolva
também "mover_y": quantos pixels (na capa de 1080x1920) a foto deve andar para corrigir, negativo = a foto SOBE (aparece
mais da parte de baixo, a boca sai do degradê; a marca no alto sai da tela), positivo = DESCE (aparece mais da cabeça).
Sem problema de altura, "mover_y": 0. E "marca": true se há marca de outro veículo visível."""


def _takes(num):
    """[(ini, fim, corte, src, rótulo, crédito)] dos takes, lidos na prévia."""
    import ver
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        nav = p.chromium.launch(); pg = nav.new_page(viewport={"width": 1080, "height": 1920})
        pg.goto(ver.URL.format(n=num)); pg.wait_for_function("!!window.__previa", timeout=30000, polling=200)
        r = pg.evaluate("""[...document.querySelectorAll('video.trecho')].map(v => { const c = v.closest('.peca-take');
            const rot = c && c.querySelector('.take-rotulo'); const txt = c ? c.textContent : '';
            const cred = (txt.match(/(Vídeo|Foto):[^\\n]{2,90}/) || [''])[0];
            return [+v.dataset.ini, +v.dataset.fim, +(v.dataset.corte || 0), (v.getAttribute('src') || '').split('?')[0],
                    rot ? rot.textContent.trim() : '', cred.trim()]; })""")
        nav.close()
    return sorted(tuple(x) for x in r if x[1] > x[0] and x[3])


def _rosto(video, t, janela=1.0):
    """O quadro com o maior rosto nítido perto de t (s) no vídeo: (imagem BGR, (x, y, l, a), segundo no vídeo) ou None."""
    import visao                             # 25/10/2026: o detector de rosto é um só (visao.py)
    return visao.melhor_rosto(video, t - janela / 2, t + janela / 2)


def foto(num, pedido_foto, takes, saida, outros=()):
    """A foto real do momento escolhido: o vídeo original do take daquele segundo (ou a foto de rosto já recortada com o
    nome da pessoa). Grava em `saida` e devolve (caminho relativo, largura, altura, (x, y, l, a), crédito, origem) ou None;
    origem {"src", "seg"}: o vídeo e o segundo do quadro, para a capa viva tocar esse trecho por baixo do texto (None na
    foto de rosto guardada)."""
    import cv2
    p = E.pasta(num); t = float(pedido_foto.get("t") or 0); quem = str(pedido_foto.get("quem") or "")
    nome = _nomes
    take = next((x for x in takes if x[0] <= t < x[1]), None)
    quem_take = lambda x: nome(x[4] + " " + x[5] + " " + x[3])      # rótulo, crédito e nome do arquivo
    ref = next((f for f in sorted((p / "animacao/rostos").glob("rosto-*.jpg")) if quem and nome(quem) & nome(f.stem)), None)
    # o segundo é de outra pessoa, ou de um take sem nome quando há a foto de rosto dela: no #306 o "Flávio" saiu do take
    # do Lula e a capa ficou com dois Lulas (21/10)
    # 25/10/2026 (#373, ele: "pedi uma imagem metade Lula metade o sargento e não obedeceu"): o rótulo do take do Lula era
    # "AO VIVO NA GLOBO", sem o nome, e a foto do Lula caía; a capa saiu só com o sargento. O take só é de OUTRA pessoa
    # quando o rótulo dele tem o nome de outra pessoa da mesma capa (`outros`), quando outro take tem o nome desta, ou há
    # a foto de rosto guardada desta
    outro = set().union(*[nome(o) for o in outros]) - nome(quem) if outros else set()
    tem_take_dela = any(nome(quem) & quem_take(x) for x in takes) if quem else False
    if take and quem and nome(quem) and not (nome(quem) & quem_take(take)) and ((outro & quem_take(take)) or ref or tem_take_dela):
        take = None
    if not take and quem:
        take = next((x for x in takes if nome(quem) & quem_take(x)), None)
        if take:
            t = (take[0] + take[1]) / 2
    if take:
        r = _rosto(p / take[3], take[2] + (t - take[0]))
        if r:
            q, face, seg = r
            # 23/10/2026 ("aprovo o plano capa-sem-tarja"; a capa do #354 saiu com 520 px da tarja preta da Veja no alto): a
            # tarja gravada no vídeo, medida naquele trecho (a mesma medida da peça de take), sai da foto antes de montar
            tarja = [0, 0]
            try:
                import animacao
                tarja = animacao.tarja_do_video(p / take[3], max(0.0, seg - .5), 1.0)
            except Exception as ex:
                E.evento(num, f"capa: a tarja não foi medida ({str(ex)[:120]})")
            if any(tarja):
                alto = q.shape[0]; cima, baixo = round(tarja[0] * alto), round(tarja[1] * alto)
                q = q[cima:alto - baixo]
                face = (face[0], max(0, face[1] - cima), face[2], face[3])
            cv2.imwrite(str(saida), q, [cv2.IMWRITE_JPEG_QUALITY, 92])
            return str(saida.relative_to(p)), q.shape[1], q.shape[0], face, take[5], {"src": take[3], "seg": seg, "tarja": tarja}
    if ref:
        q = cv2.imread(str(ref)); r = _rosto_em_imagem(q)
        if r:
            return str(ref.relative_to(p)), q.shape[1], q.shape[0], r, "", None
    return None


def _nomes(s):
    """As palavras de um nome sem acento ("Flávio" e "rosto-flavio" casam; com acento o #306 ficou sem o Flávio, 21/10)."""
    import unicodedata
    s = unicodedata.normalize("NFKD", s.lower()).encode("ascii", "ignore").decode()
    return set(re.findall(r"[a-z]{3,}", s))


def _rosto_em_imagem(q):
    import visao
    return visao.maior(q, .6)


def _linhas(texto, largura):
    # 25/10/2026 (#373: "COM A POLÍCIA / E O SARGENTO" saiu com a barra na capa): a barra é quebra de linha, nunca letra
    if "/" in texto:
        return [l for parte in texto.split("/") for l in _linhas(parte.strip(), largura)]
    out, atual = [], ""
    for w in texto.split():
        if len(atual) + len(w) + 1 > largura and atual:
            out.append(atual); atual = w
        else:
            atual = (atual + " " + w).strip()
    return out + ([atual] if atual else [])


def _tam(texto, maximo, largura=900):
    return min(maximo, int(largura / max(1, len(texto)) * 1.9))


# queixo (25/10/2026, #382: o Lula do vídeo de selfie do Metrópoles ficou com a testa e os olhos à vista e a boca atrás
# do título): o queixo não passa de y 820, onde o degradê do título fica escuro (começa em 720 com aspas, 860 sem)
CAPA_ROSTO = {"topo": 200, "alto": .36, "zoom": 1.8, "queixo": 820}


def _caixa(f, x0, larg, alto, dy=0):
    """Onde o quadro do vídeo fica: cobre a caixa (x0, 0, larg, alto), centrado no rosto na horizontal. A foto é o quadro do
    vídeo, sem edição nenhuma (ele, 21/10: "não quero mude a foto. so tem que pegar trechos do video tirar uma foto e
    colocar o texto"); 22/10/2026 ("aprovo o plano enquadramento-automatico"; no #332 o rosto do Dallagnol ficou pequeno
    e embaixo, atrás do texto): o quadro aproxima até o rosto ter CAPA_ROSTO["alto"] da largura da caixa (no máximo
    1,8 vez o tamanho que só cobre a caixa: vídeo de celular de 480 px fica borrado se aproximar mais) e sobe até o alto da
    cabeça ficar em y CAPA_ROSTO["topo"], abaixo dos selos. Devolve (x, y, largura, altura)."""
    W, H, (fx, fy, fl, fa) = f[1], f[2], f[3]
    cobre = max(larg / W, alto / H)
    esc = min(cobre * CAPA_ROSTO["zoom"], max(cobre, CAPA_ROSTO["alto"] * larg / max(1, fa)))
    x = min(x0, max(x0 + larg - W * esc, x0 + larg / 2 - (fx + fl / 2) * esc))
    # o alto da cabeça em "topo"; rosto grande demais para isso (vídeo de selfie) sobe até o queixo ficar em "queixo":
    # corta o alto da cabeça, mas olhos e boca ficam à vista
    y = min(CAPA_ROSTO["topo"] - (fy - .5 * fa) * esc, CAPA_ROSTO["queixo"] - (fy + fa) * esc)
    # dy (25/10/2026, ele: "ele tem que olhar o enquadramento e relatar isso para consertar"): o ajuste que os Olhos da capa
    # pediram ("mover_y"), negativo sobe a foto
    y = min(0, max(alto - H * esc, y + dy))
    return round(x), round(y), round(W * esc), round(H * esc)


def _imagem(f, x0, larg, alto, dy=0):
    x, y, w, h = _caixa(f, x0, larg, alto, dy)
    return f'<image href="{ESC(f[0])}" x="{x}" y="{y}" width="{w}" height="{h}" preserveAspectRatio="none"/>'


def _dois(op, fotos):
    return op.get("desenho") == "dois_rostos" and len(fotos) >= 2 and all(fotos[:2])


def _no_plano(video, seg, janela=4.0, minimo=1.7):
    """(começo, duração) do trecho que toca por baixo do texto da capa, sem atravessar um corte da edição do vídeo
    (21/10/2026, #316: a reportagem cortava para uma cerimônia 1,5 s depois da foto, por baixo de "LULA PROMETEU").
    Começa no quadro da foto e vai até antes do próximo corte (no máximo `janela` s); recua só o que falta para andar
    `minimo` s, sem passar do corte de antes. Os cortes vêm do ffmpeg (mudança de cena acima de 0,3; calibrado no #316:
    achou o corte de 45,1 s)."""
    de = max(0.0, seg - janela)
    out = subprocess.run(["ffmpeg", "-nostdin", "-v", "info", "-ss", f"{de:.2f}", "-t", f"{2 * janela:.2f}", "-i", str(video), "-an",
                          "-vf", "scale=320:-2,select='gt(scene,0.3)',showinfo", "-f", "null", "-"], capture_output=True, text=True).stderr
    cortes = [de + float(x) for x in re.findall(r"pts_time:([0-9.]+)", out)]
    antes = max([c for c in cortes if c <= seg + .02], default=0.0)
    depois = min([c for c in cortes if c > seg + .02], default=seg + janela + 1)
    ini = max(antes + .05, min(seg, depois - .05 - minimo))
    return round(ini, 3), round(max(.1, min(janela, depois - .05 - ini)), 3)


def fundo(op, fotos, pasta=None):
    """A capa viva (21/10/2026, "aprovo o plano capa-viva"; ele: "se tiver um vídeo por baixo ele tem que começar em 1,7
    segundos no máximo"): os trechos que tocam por baixo do texto no começo do vídeo, no lugar e no quadro da foto.
    [{src, seg, x, y, w, h, caixa: [x0, largura], lado}] ou [] (foto sem vídeo de origem: a capa fica parada)."""
    if _dois(op, fotos):
        pares = [(fotos[0], 0, 640, "esq"), (fotos[1], 440, 640, "dir")]
    elif any(fotos):
        pares = [(next(f for f in fotos if f), 0, 1080, "")]
    else:
        return []
    if not all(f[5] for f, *_ in pares):
        return []
    return [{**f[5], **(dict(zip(("seg", "dur"), _no_plano(pasta / f[5]["src"], f[5]["seg"]))) if pasta else {}), "foto_seg": f[5]["seg"],
             **_no_lugar_da_foto(_caixa(f, x0, larg, 1120, int(op.get("ajuste_y") or 0)), f[5].get("tarja")), "caixa": [x0, larg], "lado": lado}
            for f, x0, larg, lado in pares]


def _no_lugar_da_foto(caixa, tarja):
    """Onde o vídeo da capa viva fica: a foto é o quadro SEM a tarja (capa-sem-tarja); o vídeo tem a tarja, então fica
    mais alto e sobe, para a parte sem tarja cair exatamente onde está a foto."""
    x, y, w, h = caixa
    cima, baixo = tarja or (0, 0)
    if not (cima or baixo):
        return {"x": x, "y": y, "w": w, "h": h}
    alto = h / (1 - cima - baixo)
    return {"x": x, "y": round(y - cima * alto), "w": w, "h": round(alto)}


def _rostos_na_capa(op, fotos):
    """As caixas (x0, y0, x1, y1) dos rostos na capa de 1080x1920, com folga para a testa e o cabelo."""
    caixas = [(fotos[0], 0, 640), (fotos[1], 440, 640)] if _dois(op, fotos) else [(next((f for f in fotos if f), None), 0, 1080)]
    out = []
    for f, x0, larg in caixas:          # os mesmos lugares de svg(): esquerda 0-640, direita 440-1080, um rosto 0-1080
        if not f:
            continue
        x, y, w, h = _caixa(f, x0, larg, 1120, int(op.get("ajuste_y") or 0))
        k = w / f[1]; fx, fy, fl, fa = f[3]
        out.append((x + (fx - .15 * fl) * k, y + (fy - .6 * fa) * k, x + (fx + 1.15 * fl) * k, y + (fy + 1.1 * fa) * k))
    return out


# 25/10/2026 (#373: o selo CHECAGEM no canto de cima à direita cobriu a testa e os olhos do sargento): o selo vai ao primeiro
# lugar livre de rosto; o canto de sempre continua o primeiro
LUGARES_SELO = [(800, 60), (430, 40), (830, 600), (30, 600)]


def _lugar_do_selo(op, fotos):
    rostos = _rostos_na_capa(op, fotos)
    def cobre(x, y):
        return sum(max(0, min(x + 220, r[2]) - max(x, r[0])) * max(0, min(y + 188, r[3]) - max(y, r[1])) for r in rostos)
    return min(LUGARES_SELO, key=lambda p: (cobre(*p) > 0, cobre(*p), LUGARES_SELO.index(p)))


def svg(k, op, fotos, formato, molde="", so_texto=False):
    """O desenho da capa (as medidas da capa do molde do #298, que deu certo), em um ou dois rostos. so_texto: sem a foto
    e sem o fundo azul de trás (a camada de cima da capa viva; o vídeo toca por baixo)."""
    dy = int(op.get("ajuste_y") or 0)
    defs = f"""<linearGradient id="c{k}-desce" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#0a1748" stop-opacity="0"/>
      <stop offset=".4" stop-color="#0a1748" stop-opacity=".93"/><stop offset="1" stop-color="#0a1748" stop-opacity="1"/></linearGradient>"""
    corpo = '<rect width="1080" height="1920" fill="#0a1748"/>'
    aspas = (op.get("aspas") or "").strip().strip("“”\"")
    # a fala cabe inteira em 3 linhas (letra menor se precisar) ou fica de fora; cortada no meio, nunca
    ls, tam_a = [], 56
    for larg, tam_a in ((26, 56), (32, 46)):
        ls = _linhas(f"“{aspas}”", larg) if aspas else []
        if len(ls) <= 3:
            break
    else:
        ls = []
    passo = int(tam_a * 1.2)
    texto_aspas = "".join(f'<text x="60" y="{1070 - (len(ls) - 1 - i) * passo}">{ESC(l)}</text>' for i, l in enumerate(ls))
    # 25/10/2026 (ele, #382: "baixa um pouco mais o degradê, para ficar mais para baixo"): 100 px mais baixo (era 620/760)
    faixa = 720 if ls else 860
    if so_texto:
        corpo = ""
    elif _dois(op, fotos):
        defs += f"""<linearGradient id="c{k}-esq" x1="0" y1="0" x2="1" y2="0"><stop offset=".6" stop-color="#fff"/><stop offset="1" stop-color="#fff" stop-opacity="0"/></linearGradient>
      <linearGradient id="c{k}-dir" x1="0" y1="0" x2="1" y2="0"><stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset=".4" stop-color="#fff"/></linearGradient>
      <mask id="c{k}-me"><rect x="0" width="640" height="1920" fill="url(#c{k}-esq)"/></mask>
      <mask id="c{k}-md"><rect x="440" width="640" height="1920" fill="url(#c{k}-dir)"/></mask>"""
        corpo += f'<g mask="url(#c{k}-me)">{_imagem(fotos[0], 0, 640, 1120, dy)}</g><g mask="url(#c{k}-md)">{_imagem(fotos[1], 440, 640, 1120, dy)}</g>'
    elif any(fotos):                                    # faltou uma das duas: um rosto só, nunca a capa em branco
        corpo += _imagem(next(f for f in fotos if f), 0, 1080, 1120, dy)
    # 25/10/2026 (#373: com dois vídeos o crédito numa linha só passava da borda, "imagem ilustrativa, sem"): uma linha por
    # vídeo, de baixo para cima a partir de y 842
    creditos = [c[:72] for c in dict.fromkeys(f[4] for f in fotos if f and f[4])]
    credito = "".join(f'<text x="60" y="{842 - (len(creditos) - 1 - i) * 30}">{ESC(c)}</text>' for i, c in enumerate(creditos))
    selo = (op.get("selo") or "").strip().upper()
    # o selo fora do rosto: no canto de cima à direita (dentro do recorte 3:4) com um rosto; entre os dois, no peito,
    # com dois (em 700,560 cobria o rosto, 21/10)
    sx, sy = (430, 540) if _dois(op, fotos) else (830, 250)
    selo_img = (f'<image href="/logos/verdadometro-{COR[selo]}.png" x="{sx}" y="{sy}" width="220" height="188"/>'
                if selo in COR else "")
    nao_cumpriu = (f'<text class="im" x="{sx + 110}" y="{sy + 228}" font-family="Impact" text-anchor="middle" font-size="38" fill="#ff4d5e">{ESC(selo)}</text>'
                   if selo == "NÃO CUMPRIU" else "")
    cx, cy = _lugar_do_selo(op, fotos)
    # Fomos conferir: sem tarja do Instituto (MOLDE-FOMOS-CONFERIR, regra 7); os outros: o logo à esquerda e o selo da capa
    # à direita (regras/CAPA.md, regra 5)
    marca = ("" if molde == "conferir" else
             '<rect x="40" y="70" width="300" height="88" rx="44" fill="#050a23" fill-opacity=".7"/>'
             '<image href="/logos/instituto-br360.png" x="62" y="88" width="256" height="64"/>'
             + ('' if selo_img else f'<image href="/logos/selo-capa-{"analise" if formato == "analise" else "checagem"}.png" x="{cx}" y="{cy}" width="220" height="188"/>'))
    # o título inteiro, em até 3 linhas (letra menor quando é longo); cortar deixava "ABRIR O" no fim (21/10)
    for larg in (16, 18, 20, 22, 24, 28):
        tl = _linhas((op.get("titulo") or "").upper(), larg)
        if len(tl) <= 3:
            break
    tam_t = min(_tam(l, 104) for l in tl) if tl else 96
    titulo = "".join(f'<text x="540" y="{1230 + i * (tam_t + 12)}">{ESC(l)}</text>' for i, l in enumerate(tl))
    dest = (op.get("destaque") or "").upper()
    y_dest = 1230 + len(tl) * (tam_t + 12) + 20
    return f"""<!-- capa {k} (agente de capa: {ESC(op.get('desenho', ''))}) -->
<svg width="1080" height="1920" viewBox="0 0 1080 1920">
  <defs>{defs}</defs>
  {corpo}
  <rect x="0" y="{faixa}" width="1080" height="{1120 - faixa}" fill="url(#c{k}-desce)"/>
  {'<rect x="0" y="918" width="1080" height="202" fill="#0a1748"/>' if ls else ''}
  <rect x="0" y="1118" width="1080" height="802" fill="#0a1748"/>
  {marca}
  <g font-family="Montserrat" font-weight="700" font-size="22" fill="#dfe6ff" opacity=".9">{credito}</g>
  {selo_img}{nao_cumpriu}
  <g font-family="Montserrat" font-weight="800" font-style="italic" font-size="56" fill="#F4F6FF">{texto_aspas}</g>
  <g class="im" font-family="Impact" text-anchor="middle" fill="#F4F6FF" font-size="{tam_t}">{titulo}</g>
  <text class="im" x="540" y="{y_dest + 60}" font-family="Impact" text-anchor="middle" fill="#ffc933" font-size="{_tam(dest, 110)}">{ESC(dest)}</text>
  <text x="540" y="{y_dest + 120}" font-family="Montserrat" font-weight="600" font-size="28" text-anchor="middle" fill="#dfe6ff">{ESC(op.get('doc') or '')}</text>
</svg>
"""


def _ler(p, n, lim=4000):
    return (p / n).read_text()[:lim] if (p / n).exists() else "(não existe)"


def _json(texto):
    """O JSON da resposta, com os deslizes de digitação que o Sonnet já cometeu consertados (21/10/2026, #316 duas vezes
    seguidas: '{"t": 6, ""quem": "Lula"}' derrubava as duas opções). Não deu: {} (vale como "não devolveu")."""
    for t in (texto, re.sub(r'(?<=[{,\s])""(?=[A-Za-z_])', '"', texto), re.sub(r",\s*([}\]])", r"\1", texto)):
        try:
            return json.loads(t)
        except ValueError:
            pass
    return {}


def olhos_de_capa(num, pedido, folha_arq, takes):
    import animador_novo as AN
    p = E.pasta(num); f = E.ler_ficha(num)
    cj = json.loads((p / "narracao/completo.json").read_text()) if (p / "narracao/completo.json").exists() else {}
    tempos = {b.get("n", i + 1): (b.get("ini", 0), b.get("fim", 0)) for i, b in enumerate(cj.get("blocos") or [])}
    roteiro = "\n".join(f"{b['n']} · {tempos.get(b['n'], (0, 0))[0]:.1f}-{tempos.get(b['n'], (0, 0))[1]:.1f} s · {b.get('quem', '')} · "
                        f"{re.sub(r'\s+', ' ', b.get('fala', ''))[:220]}" for b in E.blocos(num))
    regras = (E.RAIZ / "regras/CAPA.md").read_text() + E.molde(num) + E.regra_idioma(num) + E.memoria(num)
    if f.get("molde") == "conferir":
        m = (E.RAIZ / "regras/MOLDE-FOMOS-CONFERIR.md").read_text()
        regras += "\n\n" + m[m.find("## Capa"):m.find("## Legenda")]
    texto = PEDIDO.format(regras=regras, estudo=_ler(E.RAIZ, "estudos/capas/LEIA.md", 5000), formato=f.get("formato"),
                          molde=f.get("molde"), intencao=_ler(p, "INTENCAO.md", 1500), roteiro=roteiro,
                          takes="; ".join(f"{a:.1f}-{b:.1f} s · {r}" for a, b, _, _, r, _ in takes) or "(nenhum)",
                          rostos=", ".join(x.stem.replace("rosto-", "") for x in sorted((p / "animacao/rostos").glob("rosto-*.jpg"))) or "(nenhuma)",
                          pedido=f"\nPEDIDO DELE PARA A CAPA (vale mais que tudo): {pedido.strip()[:1500]}" if pedido else "")
    resp, uso = AN.opus(num, [{"type": "text", "text": texto}, AN.img(folha_arq)], "capa (olhos de capa)", limite=180, modelo="sonnet")
    m = re.search(r"\{.*\}", resp or "", re.S)
    d = _json(m.group(0)) if m else {}
    return [o for o in d.get("opcoes") or [] if isinstance(o, dict)][:2], uso


def olhos_conferem(num, ops=()):
    import animador_novo as AN
    a = E.pasta(num) / "animacao"
    blocos = [{"type": "text", "text": CONFERE}]
    for k in (1, 2):
        # quem a foto devia mostrar: no #306 saiu a plateia no lugar do Lula e os Olhos deram ok (21/10)
        quem = ", ".join(str(f.get("quem")) for f in (ops[k - 1].get("fotos") or []) if f.get("quem")) if len(ops) >= k else ""
        for nome in (f"capa-{k}.jpg", f"capa-{k}-grade.jpg"):
            if (a / nome).exists():
                blocos += [{"type": "text", "text": f"Capa {k}{' (recorte 3:4 da grade)' if 'grade' in nome else ''}"
                            + (f", devia mostrar: {quem}" if quem and "grade" not in nome else "") + ":"}, AN.img(a / nome)]
    resp, _ = AN.opus(num, blocos, "capa (olhos conferem)", limite=120, modelo="sonnet")
    m = re.search(r"\{.*\}", resp or "", re.S)
    try:
        return {c.get("op"): c for c in _json(m.group(0)).get("capas", [])} if m else {}
    except ValueError:
        return {}


def fazer(num, pedido=None):
    """As duas capas pelo agente de capa. Devolve a frase para o chat; levanta exceção se não deu (capa.fazer cai no
    caminho de antes)."""
    import animador_novo as AN, capa
    p = E.pasta(num); a = p / "animacao"; (a / "rostos").mkdir(parents=True, exist_ok=True); t0 = time.time()
    folha_arq = a / "folha-capa.jpg"; AN.folha(num, folha_arq)
    takes = _takes(num)
    if not takes and not list((a / "rostos").glob("rosto-*.jpg")):
        raise RuntimeError("o agente de capa não achou foto nos takes (a cena ainda não tem take)")   # antes de gastar
    ops, _ = olhos_de_capa(num, pedido, folha_arq, takes)
    if len(ops) < 2:
        raise RuntimeError("os Olhos de capa não devolveram as duas opções")
    formato, molde = E.ler_ficha(num).get("formato") or "", E.ler_ficha(num).get("molde") or ""
    fotos_de = {}
    for k, op in enumerate(ops, 1):
        quens = [str(f.get("quem") or "") for f in op.get("fotos") or []]
        fs = [foto(num, f, takes, a / f"rostos/capa-{k}-{i}.jpg", outros=quens[:i] + quens[i + 1:])
              for i, f in enumerate(op.get("fotos") or [])]
        if not any(fs) and op.get("foto_reserva"):
            fs = [foto(num, op["foto_reserva"], takes, a / f"rostos/capa-{k}-r.jpg")]
        fotos_de[k] = fs
    # sem foto nenhuma, a capa sairia só com o texto no fundo azul (#316, 21/10): não entrega; capa.fazer cai no de antes
    if not any(f for fs in fotos_de.values() for f in fs):
        raise RuntimeError("o agente de capa não achou foto nos takes")
    def grava(k, op):
        """capa-k.html (a capa inteira) e capa-k-texto.html (só o texto, a camada de cima da capa viva)."""
        (a / f"capa-{k}.html").write_text(svg(k, op, fotos_de[k], formato, molde))
        f = fundo(op, fotos_de[k], p)
        (a / f"capa-{k}-texto.html").write_text(svg(k, op, fotos_de[k], formato, molde, so_texto=True)) if f else \
            (a / f"capa-{k}-texto.html").unlink(missing_ok=True)
        return f

    def lista():
        return json.dumps([{"op": k, "frase": " / ".join(x for x in (op.get("titulo"), op.get("destaque")) if x),
                            "prova": op.get("prova", ""), "porque": op.get("porque", ""), "risco": op.get("risco", ""),
                            "desenho": op.get("desenho"), "fundo": fundos[k], "aviso": op.get("aviso", ""),
                            "ajuste_y": int(op.get("ajuste_y") or 0)} for k, op in enumerate(ops, 1)], ensure_ascii=False, indent=1)
    fundos = {k: grava(k, op) for k, op in enumerate(ops, 1)}
    E._grava(a / "capas.json", lista())          # atômico (25/10/2026): a tela lia pela metade e refazia as capas
    _, erros = capa.fotos(num)
    conf = olhos_conferem(num, ops)
    trocas, reenquadradas = [], []
    for k, op in enumerate(ops, 1):           # um ajuste: rosto ruim troca pela foto reserva; texto sem sentido, pelo corrigido
        c = conf.get(k) or {}
        novo = {x: str(c[x]).strip() for x in ("titulo", "destaque")
                if str(c.get(x) or "").strip() and str(c[x]).strip().upper() != str(op.get(x) or "").strip().upper()}
        if novo:
            op.update(novo); fundos[k] = grava(k, op); trocas.append(k)
        try:
            mover = max(-400, min(400, int(c.get("mover_y") or 0)))
        except (TypeError, ValueError):
            mover = 0
        if mover and (c.get("rosto_ok") is False or c.get("marca")):
            # 25/10/2026 (#382: os Olhos disseram "a boca some no degradê" e o conserto trocou pela foto reserva, do mesmo
            # vídeo e com a mesma altura: o defeito ficou): o problema era a altura, então a foto anda o que eles pediram
            op["ajuste_y"] = int(op.get("ajuste_y") or 0) + mover
            fundos[k] = grava(k, op); trocas.append(k); reenquadradas.append(k)
            continue
        if c.get("rosto_ok") is False and op.get("foto_reserva"):
            r = foto(num, op["foto_reserva"], takes, a / f"rostos/capa-{k}-r.jpg")
            if r:
                # troca a foto da MESMA pessoa: trocar sempre a primeira pôs o Lula no lugar do Flávio (#306, 21/10)
                fs, quem = list(fotos_de[k]), _nomes(str(op["foto_reserva"].get("quem") or ""))
                i = next((i for i, f in enumerate(op.get("fotos") or []) if quem & _nomes(str(f.get("quem") or ""))), 0)
                fotos_de[k] = fs[:i] + [r] + fs[i + 1:] if fs else [r]
                fundos[k] = grava(k, op); trocas.append(k)
    if trocas:
        _, erros = capa.fotos(num)
        # 25/10/2026: depois do ajuste os Olhos olham de novo (uma vez); o que ainda estiver errado fica na opção (a tela
        # mostra o aviso no cartão) e no chat; antes dizia "ajustada depois de conferir" sem conferir
        novo = olhos_conferem(num, ops)
        # 25/10/2026 (revisão de solidez): a reconferência que falhou não deixa valer o veredito de antes do ajuste
        conf = {**conf, **novo} if novo else {k: {"problema": "ajustei, mas não consegui conferir de novo: olhe a capa"}
                                              for k in set(trocas)} | {k: v for k, v in conf.items() if k not in trocas}
    for k, op in enumerate(ops, 1):
        c = conf.get(k) or {}
        # aviso: o que os Olhos reprovaram, ou a conferência que não veio (sem "rosto_ok")
        ruim = bool(c) and (c.get("rosto_ok") is False or c.get("texto_ok") is False or bool(c.get("marca")) or "rosto_ok" not in c)
        op["aviso"] = str(c.get("problema") or "").strip()[:300] if ruim else ""
    E._grava(a / "capas.json", lista())          # atômico (25/10/2026): a tela lia pela metade e refazia as capas
    gasto = sum(x.get("usd") or 0 for x in (json.loads(l) for l in (p / "gasto.jsonl").read_text().splitlines() if l.strip())
                if x.get("quem", "").startswith("capa (") and x.get("quando", "") >= time.strftime("%Y-%m-%dT%H:%M", time.localtime(t0)))
    E.evento(num, f"capas pelo agente de capa em {time.time() - t0:.0f} s, US$ {gasto:.2f}" + (f", ajustada depois de conferir: {sorted(set(trocas))}" if trocas else ""))
    # 25/10/2026 (ele: "em outros vídeos vai ser só pedir?"): faltou a imagem de uma das duas pessoas, a capa sai com um
    # rosto só; o chat avisa quem faltou e como resolver (antes, calado)
    sem_foto = []
    for k, op in enumerate(ops, 1):
        if op.get("desenho") == "dois_rostos" and not _dois(op, fotos_de[k]):
            quem = [str(f.get("quem") or "?") for f, r in zip(op.get("fotos") or [], fotos_de[k]) if not r] or ["a segunda pessoa"]
            sem_foto.append(f"opção {k} saiu com um rosto só: não achei imagem de {', '.join(quem)} no vídeo")
    linhas = [f"**Opção {k}:** {op.get('titulo', '')} / {op.get('destaque', '')}" + (f" · “{op['aspas']}”" if op.get("aspas") else "")
              + f" · prova aos {op.get('prova', '?')}" for k, op in enumerate(ops, 1)]
    faltas = [f"opção {k}: {op['aviso']}" for k, op in enumerate(ops, 1) if op.get("aviso")]
    return ("Fiz as duas capas olhando o vídeo.\n" + "\n".join(linhas)
            + (f"\nReenquadrei pelo que os Olhos viram: opção {', '.join(map(str, sorted(set(reenquadradas))))}." if reenquadradas else "")
            + (f"\nOs Olhos conferiram e ainda apontam (está marcado na opção): {'; '.join(faltas)}." if faltas
               else "\nOs Olhos não conseguiram conferir as capas (falharam): olhe as duas antes de escolher." if not conf
               else "\nOs Olhos conferiram as duas: ok.")
            + (f"\nAtenção: {'; '.join(sem_foto)}. Mande um vídeo ou uma foto dessa pessoa no chat e peça a capa de novo." if sem_foto else "")
            + (f" (Erro na página da capa: {'; '.join(erros)[:160]})" if erros else "")
            + f" ({time.time() - t0:.0f} s, US$ {gasto:.2f})")


if __name__ == "__main__":
    print(fazer(int(sys.argv[1]), sys.argv[2] if len(sys.argv) > 2 else None))
