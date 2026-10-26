"""Molde de capa (19/10/2026; ele: "vc consegue ver como ele fez a capa do wagner moura?" e o print da capa do #298 na
grade). A capa do formato Fomos conferir já era sempre o mesmo desenho (capa-1.html do #298), mas o agente a redesenhava
do zero a cada vídeo (~0,85 de peso o par). Aqui o programa monta as duas opções sem IA:
  - a fala: a afirmação com o carimbo mais forte (ERRADO/FALSO, depois SEM PROVA, EXAGERO...), literal do roteiro;
  - o carimbo: o da nossa resposta a essa fala (coluna Tela), como carimbo de borracha na cor do veredito;
  - "<NOME> FEZ <N> AFIRMAÇÕES." e o resultado ("SÓ 1 É VERDADE") contados nos carimbos: nunca contradiz o placar;
  - o rosto: o maior rosto nítido (YuNet) nos quadros do trecho daquela fala;
  - o crédito (quem postou o vídeo) e a linha do documento (as fontes das nossas respostas).
Escreve animacao/capa-1.html, capa-2.html e capas.json, como o agente escrevia; o estúdio tira as fotos (capa.fotos).

  python3 capa_molde.py <número>
"""
import json, re, sys
from pathlib import Path

import estudio as E

PEQUENAS = set("a o as os e de da do das dos em na no nas nos um uma que com para por ao à".split())
FORCA = ["ERRADO", "FALSO", "SEM PROVA", "EXAGERO", "MEIA-VERDADE", "VERDADE"]
COR = {"ERRADO": "#ff4d5e", "FALSO": "#ff4d5e", "SEM PROVA": "#b8c2e6", "EXAGERO": "#ff9f43", "MEIA-VERDADE": "#ff9f43",
       "VERDADE": "#3ddc84"}
ESC = lambda s: str(s).replace("&", "&amp;").replace("<", "&lt;")


VEREDITO = r"(MEIA-VERDADE|SEM PROVA|VERDADE|ERRADO|FALSO|EXAGERO)"


def principal(bs):
    """Quem tem mais falas no roteiro (no empate, quem fala primeiro). 19/10/2026 (#302): com Boulos e Pacifico no mesmo
    vídeo, a capa dizia "JOÃO PAULO PACIFICO FEZ 2 AFIRMAÇÕES"; o vídeo é do Boulos."""
    quem = [b["quem"] for b in bs if not b["nosso"] and b["quem"]]
    return max(dict.fromkeys(quem), key=quem.count) if quem else ""


def veredito_de(b):
    """O carimbo de um bloco nosso: "selo X" na Tela, ou a fala que começa com o veredito ("Errado. ...")."""
    m = re.search(r"selo\s+" + VEREDITO, b["tela"], re.I) or re.match(r"\s*" + VEREDITO + r"\b", E.CORTE.sub("", b["fala"]), re.I)
    return m.group(1).upper() if m else ""


def afirmacoes(num):
    """[(bloco da fala dele, carimbo da nossa resposta, telas das nossas respostas)] da pessoa principal, na ordem."""
    bs = E.blocos(num); dono = principal(bs); out = []
    for i, b in enumerate(bs):
        if b["nosso"] or b["quem"] != dono:
            continue
        telas, carimbo = [], ""
        for r in bs[i + 1:]:
            if not r["nosso"] and r["quem"] == dono:
                break
            if r["nosso"]:
                telas.append(r["tela"])
                carimbo = carimbo or veredito_de(r)
        if carimbo:
            out.append((b, carimbo, telas))
    return out


def placar(num):
    """Os carimbos do vídeo inteiro: a linha "placar 1 VERDADE · 1 SEM PROVA · 2 ERRADO" da Tela, se houver; senão os
    vereditos dos nossos blocos. A capa conta por aqui (nunca contradiz o placar)."""
    for b in reversed(E.blocos(num)):
        m = re.search(r"placar\s+((?:\d+\s+[A-ZÀ-Ú -]+?(?:\s*·\s*|$))+)", b["tela"], re.I)
        if m:
            itens = re.findall(r"(\d+)\s+" + VEREDITO, m.group(1), re.I)
            if itens:
                return [v.upper() for n, v in itens for _ in range(int(n))]
    return [v for v in (veredito_de(b) for b in E.blocos(num) if b["nosso"]) if v]


def tamanho(texto, maximo, largura=880):
    """A letra Impact que cabe na largura (uns 0,5 da altura por letra maiúscula)."""
    return int(min(maximo, largura / (0.5 * max(len(texto), 1))))


def resultado(carimbos):
    n, v = len(carimbos), sum(1 for c in carimbos if c == "VERDADE")
    if v == 0:
        return "NENHUMA É VERDADE"
    if v == n:
        return "TODAS SÃO VERDADE"
    return f"SÓ {v} É VERDADE" if v == 1 else f"SÓ {v} SÃO VERDADE"


def fala_pontuada(num, fala):
    """As palavras do trecho como a transcrição escreveu (com vírgula e ponto); o roteiro as copia sem pontuação."""
    c = E.corte(fala)
    arq = E.pasta(num) / ((c[2] if c else None) or "referencia") / "palavras.json"
    try:
        ws = [w[2] for w in json.loads(arq.read_text()) if c[0] - .05 <= w[0] < c[1] - .05]
    except (OSError, ValueError, TypeError):
        ws = []
    seco = lambda t: re.sub(r"[^\w]", "", t.lower())
    ws = ws if ws and seco(" ".join(ws)) == seco(E.CORTE.sub("", fala)) else E.CORTE.sub("", fala).split()
    # sem pontuação (a Groq às vezes não põe): ponto antes de palavra com maiúscula que não é nome. Nome = palavra que
    # aparece com maiúscula no meio de frase no NOSSO texto (nossas falas e telas e a checagem; as falas dele no roteiro
    # vêm sem pontuação, não servem): "o Brasil", "do Lula";
    # "quebrado Totalmente quebrado" → "quebrado. Totalmente quebrado"
    nosso = " ".join([b["fala"] + " " + b["tela"] for b in E.blocos(num) if b["nosso"]]
                     + [(E.pasta(num) / "CHECAGEM.md").read_text() if (E.pasta(num) / "CHECAGEM.md").exists() else ""])
    nomes = {m.lower() for m in re.findall(r"(?<=[a-zà-ú,] )([A-ZÀ-Ú][a-zà-ú][\w-]*)", nosso)}     # "SEM PROVA" não é nome
    out = []
    for i, w in enumerate(ws):
        if (i and w[:1].isupper() and w.strip(".,;!?").lower() not in nomes and out[-1][-1:] not in ".,;!?:"
                and out[-1].lower() not in PEQUENAS):
            out[-1] += "."
        out.append(w)
    return " ".join(out)


def fala_curta(fala, limite=78):
    """A fala literal, cortada numa pontuação ou palavra até ~78 letras (pode cortar o começo ou o fim, nunca mudar)."""
    f = E.CORTE.sub("", fala).strip().rstrip(".,")
    f = f[0].upper() + f[1:] if f else f
    if len(f) <= limite:
        return f
    # o maior pedaço seguido (entre vírgulas e pontos) que cabe; no empate, o mais perto do fim, onde costuma estar a
    # afirmação ("Confesso a vocês, eu me senti muito incomodado de participar de um debate com um miliciano")
    # primeiro frases inteiras (do ponto ao ponto): "Depois de dois anos é cortado, acabou." em vez de "Abertamente, que..."
    frases = re.split(r"(?<=[.!?])\s+", f)
    inteiras = [(len(x), i, x) for i, x in enumerate(" ".join(frases[i:j]) for i in range(len(frases)) for j in range(i + 1, len(frases) + 1)) if len(x) <= limite]
    if inteiras:
        acc = max(inteiras)[2].rstrip(".,;")
        return acc[0].upper() + acc[1:]
    partes = re.split(r"(?<=[,.;!?])\s+", f)
    juntos = [" ".join(partes[i:j]) for i in range(len(partes)) for j in range(i + 1, len(partes) + 1)]
    cabem = [(len(x), i, x) for i, x in enumerate(juntos) if len(x) <= limite]
    acc = max(cabem)[2].rstrip(",;.") if cabem else " ".join(f[:limite].split()[:-1])
    return acc[0].upper() + acc[1:]


def linhas(texto, largura=24):
    out, atual = [], ""
    for w in texto.split():
        if len(atual) + len(w) + 1 > largura and atual:
            out.append(atual); atual = w
        else:
            atual = (atual + " " + w).strip()
    return out + ([atual] if atual else [])


def rosto(num, b, k):
    """O quadro com o maior rosto nítido (YuNet) no trecho da fala; grava animacao/rostos/capa-<k>.jpg.
    Devolve (caminho relativo, largura, altura, (x, y, l, a) do rosto) ou None."""
    import cv2
    p = E.pasta(num); c = E.corte(b["fala"])
    if not c:
        return None
    video = p / (c[2] or "referencia") / "video.mp4"
    if not video.exists():
        return None
    import visao                             # 25/10/2026: o detector de rosto é um só (visao.py)
    achado = visao.melhor_rosto(video, c[0], c[1])
    if not achado:
        return None
    melhor = (None, achado[0], achado[1])
    (p / "animacao/rostos").mkdir(parents=True, exist_ok=True)
    rel = f"animacao/rostos/capa-{k}.jpg"
    cv2.imwrite(str(p / rel), melhor[1], [cv2.IMWRITE_JPEG_QUALITY, 92])
    return rel, melhor[1].shape[1], melhor[1].shape[0], melhor[2]


def svg(k, foto, frase, carimbo, nome, n, res, credito, doc):
    """O desenho da capa 1 do #298 (Wagner), com as mesmas medidas."""
    corpo = '<rect width="1080" height="1920" fill="#0a1748"/>'
    if foto:
        rel, W, H, (fx, fy, fl, fa) = foto
        # o quadro na largura da capa (amplia só se o rosto ficar menor que ~300 px), a testa em y ~300: o alto do
        # quadro, onde o canal põe o logo, cai no escuro de cima (o agente fazia assim no #301: logo do Metrópoles)
        # 19/10/2026 (ele: "a capa está com o topo cortado, não pode, tem que ser full"): a foto começa no topo, sem
        # escuro nem máscara em cima
        esc = max(1080 / W, 300 / max(fa, 1))
        x = min(0, max(1080 - W * esc, 540 - (fx + fl / 2) * esc)); y = min(0, 300 - fy * esc)
        nitido = ' filter="url(#nitido)"' if W < 720 else ""
        corpo += (f'<image href="{rel}" x="{x:.0f}" y="{y:.0f}" width="{W * esc:.0f}" height="{H * esc:.0f}" '
                  f'preserveAspectRatio="none"{nitido}/>')
    cor = COR.get(carimbo, "#ff4d5e")
    # até 3 linhas no tamanho do #298 (58); fala maior vai em 4 linhas menores (50), sem subir para baixo do carimbo
    ls, tam, passo = linhas(f"“{frase}.”", 24), 58, 72
    if len(ls) > 3:
        ls, tam, passo = linhas(f"“{frase}.”", 28)[:4], 50, 60
    y0 = 935 + (3 - len(ls)) * 36 if len(ls) <= 3 else 920
    texto_fala = "".join(f'<text x="40" y="{y0 + i * passo}">{ESC(l)}</text>' for i, l in enumerate(ls))
    larg_carimbo = max(260, 46 * len(carimbo) + 40)
    return f"""<!-- capa {k} (molde Fomos conferir, programa): {ESC(nome)}, carimbo {carimbo} -->
<svg width="1080" height="1920" viewBox="0 0 1080 1920">
  <defs>
    <filter id="nitido"><feConvolveMatrix order="3" kernelMatrix="0 -0.5 0 -0.5 3 -0.5 0 -0.5 0" preserveAlpha="true"/></filter>
    <linearGradient id="some-g" gradientUnits="userSpaceOnUse" x1="0" y1="190" x2="0" y2="360">
      <stop offset="0" stop-color="#fff" stop-opacity="0"/><stop offset="1" stop-color="#fff" stop-opacity="1"/></linearGradient>
    <mask id="some"><rect width="1080" height="1920" fill="url(#some-g)"/></mask>
    <linearGradient id="c{k}-desce" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#0a1748" stop-opacity="0"/>
      <stop offset=".55" stop-color="#0a1748" stop-opacity=".88"/><stop offset="1" stop-color="#0a1748" stop-opacity="1"/></linearGradient>
    <linearGradient id="c{k}-topo" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="#050a23" stop-opacity=".8"/>
      <stop offset="1" stop-color="#050a23" stop-opacity="0"/></linearGradient>
  </defs>
  {corpo}
  <rect x="0" y="760" width="1080" height="360" fill="url(#c{k}-desce)"/>
  <rect x="0" y="1118" width="1080" height="802" fill="#0a1748"/>
  <text x="40" y="842" font-family="Montserrat" font-weight="700" font-size="22" fill="#dfe6ff" opacity=".9">{ESC(credito)}</text>
  <g font-family="Montserrat" font-weight="800" font-style="italic" font-size="{tam}" fill="#F4F6FF">{texto_fala}</g>
  <g transform="translate(765 812) rotate(-9)">
    <rect x="{-larg_carimbo / 2:.0f}" y="-50" width="{larg_carimbo}" height="100" rx="14" fill="#0a1748" fill-opacity=".55" stroke="{cor}" stroke-width="9"/>
    <text class="im" x="0" y="28" font-family="Impact" text-anchor="middle" font-size="80" fill="{cor}">{ESC(carimbo)}</text>
  </g>
  <g class="im" font-family="Impact" text-anchor="middle" fill="#F4F6FF" font-size="{min(tamanho(nome + ' FEZ', 96), tamanho(f'{n} AFIRMAÇÕES.', 96))}">
    <text x="480" y="1222">{ESC(nome)} FEZ</text>
    <text x="480" y="1322">{n} AFIRMAÇÕES.</text>
  </g>
  <text class="im" x="480" y="1446" font-family="Impact" text-anchor="middle" fill="#ffc933" font-size="{tamanho(res, 124)}">{ESC(res)}</text>
  <text x="480" y="1496" font-family="Montserrat" font-weight="600" font-size="28" text-anchor="middle" fill="#dfe6ff">{ESC(doc)}</text>
</svg>
"""


def fazer(num):
    p = E.pasta(num); a = p / "animacao"; a.mkdir(exist_ok=True)
    afs = afirmacoes(num)
    if not afs:
        raise RuntimeError("o roteiro não tem afirmação com carimbo")
    cands = sorted(afs, key=lambda x: (FORCA.index(x[1]) if x[1] in FORCA else 9, E.blocos(num).index(x[0])))
    # a 2ª opção com outro carimbo, quando há (ele, 19/10/2026: "pode fazer"; no #301 as duas saíam ERRADO)
    outro = next((x for x in cands[1:] if x[1] != cands[0][1]), None)
    if outro:
        cands = [cands[0], outro]
    nome = (principal(E.blocos(num)) or "ELE").split(",")[0].strip().upper()
    todos = placar(num) or [c for _, c, _ in afs]
    res = resultado(todos)
    fontes = []
    for _, _, telas in afs:
        for t in telas:
            for f in re.findall(r"(?:[Ff]onte:\s*|manchete d[oa]\s+|\()([A-ZÁÉÍÓÚ][\wÁÉÍÓÚÂÊÔÃÕÇáéíóúâêôãõç]+(?: [A-ZÁÉÍÓÚ][\wÁÉÍÓÚÂÊÔÃÕÇáéíóúâêôãõç]+)*)", t):
                if f not in fontes and not re.match(r"(?i)selo|texto|vídeo|promessa|ele|ela", f):
                    fontes.append(f)
    doc = ("conferimos no " + ", ".join(fontes[:3])) if fontes else "conferimos nas fontes oficiais"
    opcoes = []
    for k, (b, carimbo, _) in enumerate(cands[:2], 1):
        frase = fala_curta(fala_pontuada(num, b["fala"]))
        foto = rosto(num, b, k)
        c = E.corte(b["fala"])
        try:      # o crédito do vídeo de onde saiu ESTA fala (referencia/ ou material/...)
            meta = json.loads((p / ((c[2] if c else None) or "referencia") / "meta.json").read_text())
            credito = f"Vídeo: {meta.get('quem_postou')} (@{meta.get('conta')})" if meta.get("conta") else ""
        except (OSError, ValueError):
            credito = ""
        (a / f"capa-{k}.html").write_text(svg(k, foto, frase, carimbo, nome, len(todos), res, credito, doc))
        c = E.corte(b["fala"])
        opcoes.append({"op": k, "frase": f"“{frase}.” [{carimbo}] / {nome} FEZ {len(todos)} AFIRMAÇÕES. / {res}",
                       "prova": f"{int(c[0] // 60)}:{int(c[0] % 60):02d}" if c else "",
                       "porque": f"o rosto dele no trecho da fala (bloco {b['n']}) e o carimbo {carimbo} da nossa resposta",
                       "risco": "" if foto else "não achei rosto no trecho: a capa saiu sem foto", "molde": True})
    E._grava(a / "capas.json", json.dumps(opcoes, ensure_ascii=False, indent=1))     # atômico (25/10/2026)
    return opcoes


if __name__ == "__main__":
    print(json.dumps(fazer(int(sys.argv[1])), ensure_ascii=False, indent=1))
