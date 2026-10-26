#!/usr/bin/env python3
"""Régua de layout dos vídeos (12/10/2026, Alexandre: "algumas animaçoes ficam erradas, elementos sobrepostos etc...
conseguimos pensar em algum tipo de guardrail [...] para ja fazer isso certo no origem?" e "começa pela regua").

Mede, não opina. Abre o index.html do vídeo num navegador sem tela, leva a linha do tempo a cada 0,25 s e mede a caixa
de cada texto, imagem e vídeo visível. Reprova:
  sobreposto     texto em cima de texto
  encostado      legenda quase tocando outro texto (o crédito de um print, por exemplo), sem cruzar (13/10)
  escondido      texto embaixo de uma imagem desenhada depois dele (o rótulo que "nasce atrás da foto")
  estourado      texto saindo da caixa (o retângulo do mesmo grupo) em que ele mora
  pequeno        texto com menos de 26 px de altura (letra ~21): não se lê no celular (19/10/2026, #302: a montagem
                 "mesmo dia, mesma história" tinha cartões com letra de 20 px)
  empilhado      dois rótulos/faixas no alto ao mesmo tempo (19/10, #302: o rótulo do take por cima da faixa do vídeo)
  encavalado     na troca de cena, um texto ainda sumindo por cima de outro entrando (19/10, #302, 59 s e 68 s)
  falta-selo     a coluna Tela do roteiro pede "selo X" e o texto X não aparece no tempo do bloco (20/10/2026)
  fora           texto onde o app cobre ou corta: acima de y 240, fora de x 64-1016, passando de x 900 na faixa dos
                 ícones (y 765-1880) ou abaixo de y 1615 (nome de quem publicou) (medido no print do iPhone dele em
                 18/10/2026, ferramentas/celular.py; antes: prints da aba Reels, RECEITA.md)
Só conta o que dura 0,3 s ou mais (cruzamento de transição não é erro). Para cada problema salva um quadro com as
caixas marcadas em <video>/revisao/regua/ e escreve <video>/revisao/REGUA.md.

  python3 ferramentas/regua.py democracia-novo            mede o vídeo inteiro
  python3 ferramentas/regua.py democracia-novo --de 40 --ate 60
Sai com código 1 se achou problema (para o montador poder barrar a prévia)."""
import json, sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PASSO = 0.25
MINIMO = 0.3
# Medido nos prints da aba Reels (RECEITA.md, 08/10): o app amplia a 94% e corta ~50 px de cada lado; seta e câmera
# em y 197-256; coluna de ícones em x >= 914 de y 765 a 1645. 12/10: a regra de x 900 vale só na faixa dos ícones (o
# título a x 953 na altura y 290 aparece inteiro).
# 18/10/2026 ("aprovo o plano celular-e-zona-segura"): medido pixel a pixel no print dele (iPhone, reel em colaboração,
# ferramentas/celular.py): escala 0,9375, corte ~47 px de cada lado (+17 de margem); a barra de cima termina em y 225;
# a borda dos ícones fica em x 919-927 (a régua de 08/10 já dizia ~914), até o fim da tela; o avatar de quem publicou
# começa em y ~1628 e o nome em 1658. (A 1ª versão desta medida, no olho, pôs os ícones em 873 e acusou todas as
# legendas à toa.)
TOPO, CORTE_ESQ, CORTE_DIR = 240, 64, 1016
ICONES_X, ICONES_Y = 900, (765, 1880)
BAIXO = 1615                    # daqui para baixo o app põe o avatar e o nome, a legenda do post e "curtido por"

MEDIR = r"""
(t) => {
  const tl = window.__timelines && window.__timelines["main"];
  if (tl) tl.seek(t, false);
  const raiz = document.querySelector('#root');
  const vivo = (el) => {
    for (let e = el; e && e !== document.body; e = e.parentElement) {
      const ds = e.getAttribute && e.getAttribute('data-start');
      if (ds !== null && e.classList && e.classList.contains('clip')) {
        const s = parseFloat(ds), d = parseFloat(e.getAttribute('data-duration') || '1e9');
        if (t < s || t >= s + d) return 0;
      }
    }
    let op = 1;
    for (let e = el; e && e !== document.documentElement; e = e.parentElement) {
      const cs = getComputedStyle(e);
      if (cs.display === 'none' || cs.visibility === 'hidden') return 0;
      // 12/10: só o estilo calculado; o atributo opacity="0" da marcação é sobrescrito pelo GSAP (estilo em linha)
      op *= parseFloat(cs.opacity || '1');
    }
    return op;
  };
  const caixa = (el) => { const r = el.getBoundingClientRect(); return [r.left, r.top, r.right, r.bottom]; };
  const nome = (el) => {
    const g = el.closest('g[class], g[id], [id]');
    return (g && (g.id || g.getAttribute('class')) || el.tagName).toString().slice(0, 40);
  };
  const todos = Array.from(raiz.querySelectorAll('svg text, svg image, img, video, svg rect'));
  const ordem = new Map(todos.map((e, i) => [e, i]));
  const out = [];
  for (const el of todos) {
    const tag = el.tagName.toLowerCase();
    if (tag === 'rect') continue;
    const op = vivo(el);
    if (op < 0.25) continue;            // 19/10/2026: de 0,25 a 0,5 só para o "encavalado" (as outras regras pedem 0,5)
    const b = caixa(el);
    if (b[2] - b[0] < 2 || b[3] - b[1] < 2) continue;
    const item = {op, i: ordem.get(el), tipo: tag === 'text' ? 'texto' : 'imagem', nome: nome(el),
                  txt: tag === 'text' ? (el.textContent || '').trim().slice(0, 40) : '', b,
                  leg: tag === 'text' && /^lb\d+$/.test(el.getAttribute('class') || '')};   // 13/10: a legenda (cenas.legenda)
    if (tag === 'text') {
      // a caixa do texto: o retângulo irmão no mesmo grupo (pílula, placar, carimbo), se houver um só
      const g = el.parentElement;
      const rs = g ? Array.from(g.children).filter(c => c.tagName.toLowerCase() === 'rect') : [];
      // 12/10 (calibração no item 54): só é a caixa dele se o centro do texto cai dentro do retângulo; o crédito
      // embaixo do cartão e o sublinhado do título não são caixa
      if (rs.length === 1 && vivo(rs[0]) >= 0.5) {
        const r = caixa(rs[0]), cx = (b[0] + b[2]) / 2, cy = (b[1] + b[3]) / 2;
        // e, na horizontal, o centro ou uma das pontas do texto dentro dele (texto muito comprido tem o centro fora)
        const xin = (x) => x > r[0] && x < r[2];
        if (cy > r[1] && cy < r[3] && (xin(cx) || xin(b[0] + 1) || xin(b[2] - 1))) {
          item.dentro = r;
          // 22/10/2026 (editor-327; #327: "...O VÍDEO DA <b>JANDIRA</b>" em amarelo dentro da caixa amarela): as cores do
          // texto e de cada pedaço dele, e a cor da caixa, para achar letra da cor do fundo
          item.fundo = getComputedStyle(rs[0]).fill;
          item.cores = [el, ...el.querySelectorAll('tspan')].filter(e => (e.textContent || '').trim())
            .map(e => [getComputedStyle(e).fill, (e.textContent || '').trim().slice(0, 30)]);
        }
      }
    } else {
      if (tag === 'video') item.video = true;
      // imagem de fundo de tela inteira não conta; o take em tela cheia entra só como marca de "vídeo tocando"
      // (22/10/2026, editor-327: para o take longo e a tela parada), fora das regras de caixa
      if ((b[2] - b[0]) * (b[3] - b[1]) > 0.6 * 1080 * 1920) {
        if (tag === 'video') out.push({...item, tipo: 'video'});
        continue;
      }
    }
    out.push(item);
  }
  // 12/10 (calibração): quem está por cima de cada texto se pergunta ao próprio navegador, que respeita o recorte da
  // imagem (a caixa de uma foto recortada em círculo ou de um print com zoom é maior que o que aparece).
  // 14/10/2026 ("aprovo o plano agente-sem-esses-erros"): no #111 o disco do carimbo SEM PROVA cobriu "VÍDEO DELE" e a
  // foto "A ACUSAÇÃO" ficou com um pedaço aparecendo atrás do cartão do Pimenta, e a régua passou. Eram 3 pontos na
  // linha do meio, só imagem contava, e o que tem pointer-events: none (o cartão) não responde ao elementFromPoint.
  // Agora: 15 pontos no miolo de cada texto e de cada imagem, qualquer coisa desenhada DEPOIS conta (disco, forma, foto).
  if (!document.getElementById('__regua_pe')) {
    const st = document.createElement('style'); st.id = '__regua_pe'; st.textContent = '* { pointer-events: auto !important }';
    document.head.appendChild(st);
  }
  const depois = (a, b) => !!(a.compareDocumentPosition(b) & Node.DOCUMENT_POSITION_FOLLOWING) && !b.contains(a) && !a.contains(b);
  const desenho = (e) => e && ['circle', 'ellipse', 'path', 'polygon', 'rect', 'image', 'img', 'video', 'text', 'tspan', 'textpath', 'line', 'use']
    .includes(e.tagName.toLowerCase());
  const grupo = (e) => { const g = e.closest('g[class], g[id], [id]'); return (g && (g.id || g.getAttribute('class')) || e.tagName).toString().slice(0, 40); };
  for (const x of out) {
    const el = todos[x.i], h = x.b[3] - x.b[1], cobre = new Map();
    let n = 0, cobertos = 0;
    const meu = grupo(el);
    for (const fx of [0.1, 0.3, 0.5, 0.7, 0.9]) for (const fy of [0.3, 0.5, 0.7, 0.85]) {
      const px = x.b[0] + fx * (x.b[2] - x.b[0]), py = x.b[1] + fy * h;
      if (px < 0 || py < 0 || px >= 1080 || py >= 1920) continue;
      n++;
      // a pilha inteira no ponto: o de cima que está visível de verdade (no #111 um retângulo transparente de outra
      // cena ficava por cima de tudo e escondia o disco do carimbo)
      const e = document.elementsFromPoint(px, py).find((c) => c === el || el.contains(c) || (desenho(c) && vivo(c) >= 0.5));
      if (!e || e === el || el.contains(e) || e.contains(el) || !depois(el, e)) continue;
      const g = grupo(e);
      if (g === meu) continue;   // peças do mesmo desenho (o logo dentro do próprio carimbo)
      // 22/10/2026 ("aprovo o plano regua-sem-alarme-falso"; ele: "a regua reclama em alguns videos mas quando eu olho
      // não consigo detectar nada"; medido no #340):
      // - outro texto não cobre: a célula de cada letra inclui o espaço do acento, e duas linhas juntas ("R$ 16 BI EM
      //   2028" / "R$ 15 BI EM 2029") se tocavam sem a letra encostar; texto sobre texto é do "sobreposto", que mede o miolo
      // - camada de tela inteira (o fundo do fecho) não cobre: o texto da cena anterior embaixo dela já saiu da tela
      //   ("FONTE: MENSAGEM PRESIDENCIAL" aos 46,7 s, 20 de 20 pontos, e o quadro não mostra nada)
      if (['text', 'tspan', 'textpath'].includes(e.tagName.toLowerCase())) continue;
      const eb = e.getBoundingClientRect();
      if (eb.width * eb.height > 0.6 * 1080 * 1920) continue;
      cobertos++; cobre.set(g, (cobre.get(g) || 0) + 1);
    }
    x.pontos = n; x.cobertos = cobertos;
    x.coberto = Array.from(cobre).filter(([g, c]) => c >= 2).map(([g]) => g);
    x.coberto_1 = Array.from(cobre).map(([g]) => g);
  }
  // 22/10/2026 (editor-327): uma forma desenhada no miolo (as bolinhas do logo na assinatura são círculos) também ocupa
  // o centro; o fundo listrado da página (#fundo) não
  for (const e of raiz.querySelectorAll('svg circle, svg ellipse, svg path, svg polygon')) {
    if (e.closest('#fundo') || vivo(e) < 0.5) continue;
    const b = caixa(e), a = (b[2] - b[0]) * (b[3] - b[1]);
    if (a < 4 || a > 0.6 * 1080 * 1920 || b[0] > 980 || b[2] < 100 || b[1] > 1050 || b[3] < 400) continue;
    out.push({op: vivo(e), tipo: 'forma', nome: nome(e), txt: '', b});
    break;
  }
  return out;
}
"""


def cruza(a, b, folga=4):
    x0, y0 = max(a[0], b[0]) + folga, max(a[1], b[1]) + folga
    x1, y1 = min(a[2], b[2]) - folga, min(a[3], b[3]) - folga
    return max(0, x1 - x0) * max(0, y1 - y0)


def miolo(b, corte=0.2):
    h = b[3] - b[1]
    return [b[0], b[1] + corte * h, b[2], b[3] - corte * h]


FOLGA_LEGENDA = 20  # px entre o miolo da legenda e o de outro texto (13/10, A-62-regua.2: legenda colada no crédito do
# print). Calibrado em casos desenhados: miolo a 1, 11 e 16 px parece colado no olho; a 21 px já se lê separado.


def encosta(a, b):
    """Legenda e outro texto que não se cruzam mas quase se tocam: dividem a mesma faixa na horizontal e a distância
    na vertical, entre os miolos das linhas, é menor que FOLGA_LEGENDA."""
    ma, mb = miolo(a), miolo(b)
    junto_x = min(ma[2], mb[2]) - max(ma[0], mb[0]) > 0
    gap_y = max(mb[1] - ma[3], ma[1] - mb[3])
    return junto_x and gap_y < FOLGA_LEGENDA


def area(a):
    return max(0, a[2] - a[0]) * max(0, a[3] - a[1])


def _rgb(s):
    """'rgb(255, 201, 51)' ou '#ffc933' -> (255, 201, 51); outra coisa (none, url(...)) -> None."""
    import re
    s = (s or "").strip().lower()
    m = re.match(r"rgba?\((\d+),\s*(\d+),\s*(\d+)", s)
    if m:
        return tuple(int(x) for x in m.groups())
    m = re.match(r"#([0-9a-f]{6})$", s)
    return tuple(int(m.group(1)[i:i + 2], 16) for i in (0, 2, 4)) if m else None


# 22/10/2026 (editor-327; ele: "analise o vídeo da jandira e vê o que daria para melhorar na edição e melhora o editor"):
# o que a régua não via e os Olhos e o vídeo final viram no #327
CENTRO = (100, 400, 980, 1050)     # o miolo da tela, acima dos rodapés (y ~1090) e da legenda (y 1340): sem nada nele por
                                   # VAZIO_S, a tela está vazia (calibrado no #327: aos 33 s só os rodapés, e o olho vê vazio)
VAZIO_S = 1.0
TAKE_LONGO_S = 6.0                 # a mesma imagem de uma pessoa falando, sem nada entrar por cima (4 a 16 s no #327)


def _no_centro(x):
    b, c = x["b"], CENTRO
    return not x.get("leg") and b[0] < c[2] and b[2] > c[0] and b[1] < c[3] and b[3] > c[1]


def tempo(quadros):
    """[(t, itens)] -> problemas que só aparecem olhando o tempo: centro vazio, take longo sem variação e tela parada."""
    out = []
    def corridas(cond):
        ini = None
        for t, itens in quadros + [(None, None)]:
            ok = t is not None and cond(itens)
            if ok and ini is None:
                ini = t
            if not ok and ini is not None:
                yield ini, ant
                ini = None
            ant = t
    for a, z in corridas(lambda its: not any(_no_centro(x) for x in its if x.get("op", 1) >= .5)):
        if z - a + PASSO >= VAZIO_S:
            out.append({"tipo": "centro-vazio", "msg": "o centro da tela fica vazio (só legenda, fundo ou rodapé): ponha a prova no meio", "ini": a, "fim": z, "caixas": []})
    # take longo: um vídeo na tela o tempo todo e o resto igual (nenhum texto nem imagem entra ou sai por cima)
    sinal = lambda its: tuple(sorted(x["nome"] for x in its if x.get("op", 1) >= .5 and not x.get("leg")))
    tem_video = lambda its: any(x.get("video") for x in its)
    ini, s0 = None, None
    for t, itens in quadros + [(None, None)]:
        s = sinal(itens) if t is not None and tem_video(itens) else None
        if s is not None and s == s0:
            fim = t
        else:
            if ini is not None and s0 is not None and fim - ini + PASSO >= TAKE_LONGO_S:
                out.append({"tipo": "take-longo", "msg": "a mesma imagem de quem fala, sem nada mudar (varie a cada 3 a 4 s: "
                            "aproximar o rosto, a palavra-chave na tela)", "ini": ini, "fim": fim, "caixas": []})
            ini, fim, s0 = t, t, s
    return out


PEQUENO = 26          # px de altura da caixa do texto; o crédito dos takes (letra 24) mede 29
TOPO_FAIXA = (220, 360)


def problemas(itens):
    achados = []
    # 19/10/2026: o texto ainda sumindo (ou aparecendo) por cima de outro, na troca de cena
    meio = [x for x in itens if x["tipo"] == "texto" and x["txt"] and 0.25 <= x.get("op", 1) < 0.9]
    todos_t = [x for x in itens if x["tipo"] == "texto" and x["txt"] and x.get("op", 1) >= 0.25]
    for a in meio:
        for b in todos_t:
            if b is a or b["nome"] == a["nome"] or b.get("leg") or a.get("leg"):
                continue
            if cruza(miolo(a["b"]), miolo(b["b"])) > 0.15 * min(area(miolo(a["b"])), area(miolo(b["b"]))):
                achados.append(("encavalado", f"na troca de cena, '{a['txt']}' ({a['nome']}) por cima de '{b['txt']}' ({b['nome']})", (a, b)))
                break
    itens = [x for x in itens if x.get("op", 1) >= 0.5]
    for a in itens:
        if a["tipo"] == "texto" and len(a["txt"]) >= 3 and not a.get("leg") and a["b"][3] - a["b"][1] < PEQUENO:
            achados.append(("pequeno", f"'{a['txt']}' com letra pequena demais para o celular ({a['b'][3] - a['b'][1]:.0f} px; mínimo {PEQUENO})", (a,)))
    alto = {}
    for a in itens:
        if a["tipo"] == "texto" and a["txt"] and TOPO_FAIXA[0] <= a["b"][1] <= TOPO_FAIXA[1] and a.get("dentro"):
            alto.setdefault(a["nome"], a)
    if len(alto) >= 2:
        a, b = list(alto.values())[:2]
        achados.append(("empilhado", f"dois rótulos no alto ao mesmo tempo: '{a['txt']}' e '{b['txt']}'", (a, b)))
    txts = [x for x in itens if x["tipo"] == "texto" and x["txt"]]
    imgs = [x for x in itens if x["tipo"] == "imagem"]
    for k, a in enumerate(txts):
        if a["b"][1] < TOPO:
            achados.append(("fora", f"'{a['txt']}' acima de y {TOPO} (y {a['b'][1]:.0f})", (a,)))
        if a["b"][0] < CORTE_ESQ or a["b"][2] > CORTE_DIR:
            achados.append(("fora", f"'{a['txt']}' cortado na borda (x {a['b'][0]:.0f}-{a['b'][2]:.0f})", (a,)))
        elif a["b"][2] > ICONES_X and a["b"][3] > ICONES_Y[0] and a["b"][1] < ICONES_Y[1]:
            achados.append(("fora", f"'{a['txt']}' embaixo dos ícones do app (x {a['b'][2]:.0f}, y {a['b'][1]:.0f})", (a,)))
        if a["b"][3] > BAIXO:
            achados.append(("fora", f"'{a['txt']}' embaixo do nome de quem publicou (y {a['b'][3]:.0f}; o app começa em {BAIXO})", (a,)))
        if a.get("dentro"):
            r = a["dentro"]
            if a["b"][0] < r[0] - 2 or a["b"][2] > r[2] + 2 or a["b"][1] < r[1] - 2 or a["b"][3] > r[3] + 2:
                achados.append(("estourado", f"'{a['txt']}' sai da caixa", (a,)))
            fundo = _rgb(a.get("fundo"))
            for cor, pedaco in a.get("cores") or []:
                c = _rgb(cor)
                if fundo and c and sum((x - y) ** 2 for x, y in zip(c, fundo)) ** .5 < 60:
                    achados.append(("invisivel", f"'{pedaco}' da mesma cor da caixa em que está (não se lê)", (a,)))
                    break
        for b in txts[k + 1:]:
            # 12/10 (calibração): a caixa do texto inclui o espaço de acento e de perna da letra; duas linhas bem
            # juntas ("MAS DÁ PARA / ACABAR?") cruzavam as caixas sem a letra encostar. Mede só o miolo da linha.
            if cruza(miolo(a["b"]), miolo(b["b"])) > 0.15 * min(area(miolo(a["b"])), area(miolo(b["b"]))):
                achados.append(("sobreposto", f"'{a['txt']}' x '{b['txt']}'", (a, b)))
            elif a.get("leg") != b.get("leg") and encosta(a["b"], b["b"]):
                leg, outro = (a, b) if a.get("leg") else (b, a)
                achados.append(("encostado", f"legenda '{leg['txt']}' encosta em '{outro['txt']}'", (a, b)))
        # 14/10 (agente-sem-esses-erros): 2 ou mais dos 15 pontos do texto cobertos por algo desenhado depois
        if a.get("cobertos", 0) >= 2:
            quem = ", ".join(a.get("coberto") or ["outro elemento"])
            im = next((x for x in imgs if x["nome"] in (a.get("coberto") or [])), None)
            achados.append(("escondido", f"'{a['txt']}' com parte coberta por {quem}", (a, im) if im else (a,)))
        elif a.get("cobertos", 0) == 1:
            # um ponto só: a borda de outra peça tocando a letra (o disco do SEM PROVA na base de "VÍDEO" no #111)
            achados.append(("encostado", f"'{a['txt']}' com a borda de {', '.join(a.get('coberto_1') or ['outra peça'])} encostando", (a,)))
    # 14/10 (agente-sem-esses-erros): imagem com só um pedaço aparecendo atrás de outra (a foto "A ACUSAÇÃO" atrás do
    # cartão do Pimenta no #111): coberta em mais da metade dos pontos, mas não inteira
    for im in imgs:
        n, c = im.get("pontos", 0), im.get("cobertos", 0)
        if n >= 6 and 0.5 <= c / n < 1:
            achados.append(("pedaço", f"imagem {im['nome']} com só um pedaço aparecendo atrás de {', '.join(im.get('coberto') or ['outro elemento'])}", (im,)))
    return achados


SELO = __import__("re").compile(r"selo\s+((?:[A-ZÁÉÍÓÚÂÊÔÃÕÇ][A-ZÁÉÍÓÚÂÊÔÃÕÇ-]*\s?)+)")


def _sem_acento(s):
    return __import__("unicodedata").normalize("NFD", s.upper()).encode("ascii", "ignore").decode()


NUM = __import__("re").compile(r"(?<![A-Za-z0-9])\d+(?:[.,]\d+)*")     # número grudado em letra não conta (br360, Poder360)


def _nums(texto):
    """Os números de um texto, do jeito que a tela escreve ("33,5 MI" -> 33,5; "21%" -> 21; "56.104.503" fica inteiro);
    só os de 2 algarismos ou mais, ou com vírgula (1, 2 e 3 aparecem em todo lugar)."""
    return {n.rstrip(".,") for n in NUM.findall(texto or "") if len(n.replace(".", "").replace(",", "")) >= 2 or "," in n}


def _mesmo(a, b):
    """O mesmo número, também arredondado na tela ("21%" na tela e "21,08%" no roteiro)."""
    return a == b or b.startswith(a + ",") or a.startswith(b + ",")


def numeros_por_bloco(d):
    """24/10/2026 (consertos-do-369; ele: "pode fazer [...] as medidas da régua"): os números que cada bloco diz ou pede
    na Tela, com o tempo do bloco. [(bloco, ini, fim, {números})]"""
    import json, re
    rot, comp = d / "ROTEIRO.md", d / "narracao/completo.json"
    if not rot.exists() or not comp.exists():
        return []
    tempos = {b["n"]: (b["ini"], b["fim"]) for b in json.loads(comp.read_text())["blocos"]}
    out = []
    for l in rot.read_text().splitlines():
        m = re.match(r"^\|\s*(\d+)\s*\|(.*)\|\s*$", l.strip())
        if m and int(m.group(1)) in tempos:
            out.append((int(m.group(1)), *tempos[int(m.group(1))], _nums(m.group(2))))
    return sorted(out)


def antes_da_hora(quadros, blocos):
    """O número de um bloco que aparece na tela antes de o bloco começar (#369, 2 s: 21%, 33,5 MI e 51×49 em volta do
    título, números dos blocos 4 e 7). Só conta número que nenhum bloco até o de agora diz ou pede; a legenda não conta."""
    achados = {}
    for t, itens in quadros:
        b = next((x for x in blocos if x[1] - .05 <= t < x[2] + .3), None)
        if not b:
            continue
        ja = set().union(*(x[3] for x in blocos if x[0] <= b[0]))
        for it in itens:
            if it["tipo"] != "texto" or it.get("leg") or it["op"] < .5:
                continue
            for n in _nums(it["txt"]):
                if any(_mesmo(n, j) for j in ja):
                    continue
                dono = next((x[0] for x in blocos if x[0] > b[0] and any(_mesmo(n, j) for j in x[3])), None)
                if dono is None:
                    continue
                k = (it["txt"], dono)
                a = achados.setdefault(k, {"tipo": "antes-da-hora", "ini": t, "fim": t, "caixas": [it["b"]],
                                           "msg": f"'{it['txt']}' aparece no bloco {b[0]}, mas o número é do bloco {dono}: entre só quando ele for dito"})
                a["fim"] = t
    return [a for a in achados.values() if a["fim"] - a["ini"] + PASSO >= MINIMO]


def selos_pedidos(d):
    """20/10/2026 (ele: "porque não acerta a animação de primeira?"; 7 de 60 problemas do editor nos #300-#305 eram a
    coluna Tela não seguida, como o selo DOCUMENTO que faltou no #304): os selos que a coluna Tela de cada bloco pede,
    com o tempo do bloco na voz. [(bloco, selo, ini, fim)]"""
    import json, re
    rot, comp = d / "ROTEIRO.md", d / "narracao/completo.json"
    if not rot.exists() or not comp.exists():
        return []
    tempos = {b["n"]: (b["ini"], b["fim"]) for b in json.loads(comp.read_text())["blocos"]}
    out = []
    for l in rot.read_text().splitlines():
        m = re.match(r"^\|\s*(\d+)\s*\|(.*)\|\s*$", l.strip())
        if not m or int(m.group(1)) not in tempos:
            continue
        c = [x.strip() for x in m.group(2).split("|")]
        for sel in SELO.findall(c[3] if len(c) > 3 else ""):
            out.append((int(m.group(1)), sel.strip(), *tempos[int(m.group(1))]))
    return out


def medir(pasta, de=0.0, ate=None, url=None, prefixo="", limpar=True):
    """v2 (16/10/2026): com `url`, mede a prévia servida pelo estúdio (o tocador em modo cru, sem escala) e grava os
    quadros em <pasta>/revisao/regua/; sem `url`, como na v1 (o index.html da pasta). prefixo e limpar (20/10/2026):
    para medir trechos ao mesmo tempo (animacao._regua_inteira), cada trecho grava os quadros com o seu prefixo e só
    quem chama apaga os antigos."""
    from playwright.sync_api import sync_playwright
    d = RAIZ / pasta
    html = d / "index.html"
    with sync_playwright() as p:
        nav = p.chromium.launch()
        pg = nav.new_page(viewport={"width": 1080, "height": 1920})
        pg.goto(url or html.as_uri())
        # 12/10: com polling por quadro (raf) a espera não termina neste servidor sem tela; por tempo funciona
        pg.wait_for_function("!!(window.__timelines && window.__timelines['main'])", timeout=30000, polling=200)
        pg.evaluate("document.fonts.ready")
        dur = pg.evaluate("window.__timelines['main'].duration()")
        # 23/10/2026 ("aprovo o plano travas-da-verificacao"): a cena com erro de código não se mede (a régua lia o texto do
        # erro como layout, #354); vira um problema "erro", que trava a aprovação e manda o animador consertar
        erro = pg.evaluate("window.__erroCena || ''")
        if erro:
            nav.close()
            return dur, [{"tipo": "erro", "msg": f"a animação tem erro de código: {erro}", "ini": 0.0, "fim": 0.0, "caixas": []}]
        capa_ate = float(pg.evaluate("window.__capaAte || 0"))
        ate = min(ate or dur, dur)
        abertos, fechados = {}, []
        t = de
        textos = []                     # (t, textos na tela): para os selos que a coluna Tela pede
        quadros = []                    # (t, itens): para o centro vazio, o take longo e a tela parada (editor-327)
        while t <= ate + 1e-9:
            vistos = set()
            itens = pg.evaluate(MEDIR, t)
            quadros.append((t, itens))
            textos.append((t, " ".join(_sem_acento(x["txt"]) for x in itens if x["tipo"] == "texto" and x["op"] >= .5)))
            for tipo, msg, els in problemas(itens):
                chave = (tipo, msg)
                vistos.add(chave)
                if chave in abertos:
                    abertos[chave]["fim"] = t
                else:
                    abertos[chave] = {"tipo": tipo, "msg": msg, "ini": t, "fim": t, "caixas": [e["b"] for e in els]}
            for chave in [c for c in abertos if c not in vistos]:
                fechados.append(abertos.pop(chave))
            t = round(t + PASSO, 3)
        fechados += abertos.values()
        valem = [p for p in fechados if p["fim"] - p["ini"] + PASSO >= MINIMO] + tempo(quadros)
        # o que fica todo embaixo da capa não vale (o mesmo filtro do servidor, mas com o tempo de verdade: no #334 a cena
        # passava T.capa(tCapa) e o filtro, que lia o número escrito, não pegava); o que passa da capa continua
        if capa_ate:
            valem = [p for p in valem if not (p["ini"] < capa_ate - .05 and p["fim"] <= capa_ate + .3)]
        # 24/10/2026 (consertos-do-369): número de um bloco na tela antes da hora
        valem += [p for p in antes_da_hora(quadros, numeros_por_bloco(d)) if not (capa_ate and p["fim"] <= capa_ate + .3)]
        # selo pedido na coluna Tela que não aparece no tempo do bloco (até 1,5 s depois, o selo entra na palavra)
        # (por bloco: o trecho medido tem que cobrir o bloco inteiro e 1,5 s depois; medindo em trechos, cada bloco cai
        # num trecho só)
        for n, sel, ini, fim in selos_pedidos(d):
            if ini >= de - 1e-6 and (fim + 1.5 <= ate + 1e-6 or ate >= dur - 1e-6):
                alvo = _sem_acento(sel)
                if not any(ini - .25 <= tt <= fim + 1.5 and alvo in tx for tt, tx in textos):
                    valem.append({"tipo": "falta-selo", "msg": f"bloco {n}: a coluna Tela pede o selo {sel} e ele não aparece",
                                  "ini": ini, "fim": fim, "caixas": []})
        saida = d / "revisao/regua"
        saida.mkdir(parents=True, exist_ok=True)
        if limpar:
            for f in saida.glob("*.png"):
                f.unlink()
        for n, prob in enumerate(sorted(valem, key=lambda p: p["ini"]), 1):
            meio = (prob["ini"] + prob["fim"]) / 2
            pg.evaluate(MEDIR, meio)
            pg.evaluate("""(cx) => { document.querySelectorAll('.regua-x').forEach(e => e.remove());
                for (const b of cx) { const d = document.createElement('div'); d.className = 'regua-x';
                  d.style.cssText = `position:fixed;left:${b[0]}px;top:${b[1]}px;width:${b[2]-b[0]}px;height:${b[3]-b[1]}px;
                  border:4px solid #ff2d2d;box-sizing:border-box;z-index:99999;pointer-events:none`;
                  document.body.appendChild(d); } }""", prob["caixas"])
            prob["quadro"] = f"revisao/regua/{prefixo}{n:02d}-{prob['tipo']}-{meio:05.1f}s.png"
            pg.screenshot(path=str(d / prob["quadro"]))
        nav.close()
    return dur, sorted(valem, key=lambda p: p["ini"])


def main():
    a = sys.argv[1:]
    if not a:
        sys.exit(__doc__)
    de = float(a[a.index("--de") + 1]) if "--de" in a else 0.0
    ate = float(a[a.index("--ate") + 1]) if "--ate" in a else None
    dur, probs = medir(a[0], de, ate)
    linhas = [f"# Régua de layout · {a[0]} ({dur:.1f} s, um quadro a cada {PASSO} s)", ""]
    if not probs:
        linhas.append("Nenhum problema de layout.")
    for p in probs:
        linhas.append(f"- {p['ini']:6.2f}-{p['fim'] + PASSO:6.2f} s · **{p['tipo']}** · {p['msg']} · {p['quadro']}")
    (RAIZ / a[0] / "revisao/REGUA.md").write_text("\n".join(linhas) + "\n")
    print("\n".join(linhas))
    sys.exit(1 if probs else 0)


if __name__ == "__main__":
    main()
