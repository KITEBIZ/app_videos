"""A capa do vídeo (estúdio v2, 16/10/2026, "aprovo o plano v2-capa").

  python3 capa.py <número>                 as duas opções de capa
  python3 capa.py <número> "pedido dele"   muda as capas pelo pedido

O animador (claude, regras/CAPA.md) escreve animacao/capa-1.html e capa-2.html (paradas) e animacao/capas.json (a frase,
o momento do vídeo que prova a capa, por que chama atenção, o risco). O estúdio tira a foto de cada uma (capa-N.jpg e o
recorte 3:4 da grade, capa-N-grade.jpg). Ele escolhe na tela: a escolhida vira animacao/capa.html (o 1 s do começo da
prévia) e animacao/capa.jpg (a capa do Reels).
"""
import json, re, shutil, sys
from pathlib import Path

import estudio as E

FERR = E.RAIZ / "ferramentas"
sys.path.insert(0, str(FERR))
GRADE = (240, 1680)            # o recorte 3:4 que a grade do Instagram mostra (RECEITA "Capa")


def pagina(num, op, texto=False):
    """A capa sozinha, 1080x1920, com o fundo e as letras da prévia (o mesmo fundo do web/tocador.html). texto: só a
    camada de texto da capa viva (capa-N-texto.html), em fundo transparente."""
    p = E.pasta(num) / "animacao"
    arq = p / ("capa.html" if op == "escolhida" else f"capa-{int(op)}{'-texto' if texto else ''}.html")
    corpo = arq.read_text() if arq.exists() else ""
    toc = (E.RAIZ / "web/tocador.html").read_text()
    i = toc.index('<svg id="fundo"'); fundo = "" if texto else toc[i:toc.index("</svg>", i) + 6]
    return f"""<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><title>Capa #{int(num)}</title>
<base href="/item/{int(num)}/">
<style>
@font-face {{ font-family: "Montserrat"; src: url("/fontes/montserrat-latin.woff2") format("woff2"); font-weight: 400 900; }}
@font-face {{ font-family: "Impact"; src: url("/fontes/impact.ttf") format("truetype"); }}
html, body {{ margin: 0; background: {"transparent" if texto else "#0a1748"}; }}
#root {{ position: relative; width: 1080px; height: 1920px; overflow: hidden; }}
#root svg text {{ font-family: "Montserrat", sans-serif; }}
#root .im, #root .im text {{ font-family: "Impact", sans-serif !important; }}
#capa {{ position: absolute; inset: 0; }}
</style></head><body><div id="root">{fundo}<div id="capa">{corpo}</div></div></body></html>"""


PORTA = 4400                     # o estúdio de teste (cópia) troca


def fotos(num):
    """Tira a foto de cada opção (e da escolhida): capa-N.jpg (1080x1920) e capa-N-grade.jpg (o recorte 3:4)."""
    from playwright.sync_api import sync_playwright
    from PIL import Image
    a = E.pasta(num) / "animacao"
    ops = [n for n in (1, 2) if (a / f"capa-{n}.html").exists()]
    feitos = []
    with sync_playwright() as pw:
        nav = pw.chromium.launch()
        pg = nav.new_page(viewport={"width": 1080, "height": 1920})
        erros = []
        pg.on("pageerror", lambda e: erros.append(str(e)))
        for n in ops:
            pg.goto(f"http://127.0.0.1:{PORTA}/item/{int(num)}/capa.html?op={n}")
            pg.evaluate("document.fonts.ready.then(() => 0)")
            pg.wait_for_load_state("networkidle")
            png = a / f"capa-{n}.png"
            pg.screenshot(path=str(png), clip={"x": 0, "y": 0, "width": 1080, "height": 1920})
            im = Image.open(png).convert("RGB")
            im.save(a / f"capa-{n}.jpg", quality=92)
            im.crop((0, GRADE[0], 1080, GRADE[1])).save(a / f"capa-{n}-grade.jpg", quality=90)
            png.unlink()
            feitos += [a / f"capa-{n}.jpg", a / f"capa-{n}-grade.jpg"]
            # capa viva (21/10/2026): a camada de texto, transparente onde a foto fica (o vídeo toca por baixo)
            texto = a / f"capa-{n}-texto.png"
            if (a / f"capa-{n}-texto.html").exists():
                pg.goto(f"http://127.0.0.1:{PORTA}/item/{int(num)}/capa.html?op={n}&texto=1")
                pg.evaluate("document.fonts.ready.then(() => 0)")
                pg.wait_for_load_state("networkidle")
                pg.screenshot(path=str(texto), clip={"x": 0, "y": 0, "width": 1080, "height": 1920}, omit_background=True)
                feitos.append(texto)
            else:
                texto.unlink(missing_ok=True)
        nav.close()
    return feitos, erros


def opcoes(num):
    a = E.pasta(num) / "animacao"
    try:
        lista = json.loads((a / "capas.json").read_text())
    except (OSError, json.JSONDecodeError):
        lista = []
    lista = [o for o in lista if isinstance(o, dict) and (a / f"capa-{o.get('op')}.jpg").exists()]
    return lista


def contexto(num, pedido):
    p = E.pasta(num)
    material = sorted(str(x.relative_to(p)) for pasta in ("material", "anexos", "referencia") if (p / pasta).exists()
                      for x in (p / pasta).rglob("*") if x.is_file() and x.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp", ".mp4"))
    ler = lambda n, lim=10000: (p / n).read_text()[:lim] if (p / n).exists() else "(não existe)"
    ja = (p / "animacao/capas.json").exists()
    # E.molde: a capa também recebe as regras do molde do vídeo (18/10/2026, "aprovo o plano capa-fomos-conferir")
    return f"""{(E.RAIZ / 'regras/CAPA.md').read_text().replace('<estúdio>', str(E.RAIZ)).replace('<número>', str(int(num)))}{E.molde(num)}

## Este vídeo (#{int(num)}), pasta {p}
Fotos e vídeos na pasta: {', '.join(material[:80]) or '(nenhum)'}
Quadros do vídeo pronto (um perto do fim de cada bloco): {', '.join(sorted(str(x.relative_to(p)) for x in (p / 'animacao/depois').glob('*.png'))) if (p / 'animacao/depois').exists() else '(não há)'}

INTENCAO.md:
{ler('INTENCAO.md', 3000)}

ROTEIRO.md:
{ler('ROTEIRO.md')}

As capas de agora: {'existem (animacao/capa-1.html, capa-2.html, capas.json); leia antes de mudar' if ja else 'ainda não existem: faça as duas opções'}

## O que fazer agora
{pedido or 'Faça as duas opções de capa deste vídeo.'}
"""


def fazer(num, pedido=None, na_ficha=True):
    """Roda o animador com as regras da capa; devolve a resposta dele (resumida). na_ficha=False: junto com a animação,
    sem mexer na porcentagem nem nos passos dela (17/10/2026, animacao-rapida)."""
    import agente
    a = E.pasta(num) / "animacao"
    a.mkdir(exist_ok=True)
    # 19/10/2026 (ele: "pode fazer"): no formato Fomos conferir a capa é sempre o mesmo desenho (o do #298); o programa
    # monta as duas opções sem IA (capa_molde.py). O agente só entra quando ele pede uma capa diferente, ou se o molde falhar
    # "refaz a capa pelo molde" no chat também vem para cá (ele, 19/10/2026: "o que faço lá?")
    # 21/10/2026 ("aprovo o plano agente-de-capa"): primeiro o agente de capa (capa_agente.py: os Olhos veem a folha do
    # vídeo, escolhem o momento e a frase, o programa monta com o quadro do take como ele é; ~US$ 0,10 e ~1 min). Se ele
    # falhar, segue o caminho de antes. "pelo molde" no pedido continua indo direto ao molde.
    aviso = ""
    if not (pedido and re.search(r"(?i)\bmolde\b", pedido)):
        try:
            import capa_agente
            return capa_agente.fazer(num, pedido)
        except Exception as ex:
            import traceback; traceback.print_exc()
            E.evento(num, f"agente de capa falhou ({str(ex)[:120]}); capas pelo caminho de antes")
            aviso = f"(O agente de capa não conseguiu: {str(ex)[:120]}. Fiz pelo caminho de antes.) "
    if (not pedido or re.search(r"(?i)\bmolde\b", pedido)) and E.ler_ficha(num).get("molde") == "conferir":
        try:
            import capa_molde
            capa_molde.fazer(num)
            _, erros = fotos(num)
            if opcoes(num) and not erros:
                E.evento(num, f"capas feitas pelo molde (sem IA): {len(opcoes(num))} opção(ões)")
                return aviso + ("Fiz as duas pelo molde da capa do Wagner (sem IA): a fala com o carimbo mais forte e outra com "
                        "um carimbo diferente. Se quiser outra, me diga como.")
        except Exception:
            import traceback; traceback.print_exc()
    if na_ficha:
        E.mexe_ficha(num, progresso=5, passos=[])
    permitidas = ["Read", "Write", "Edit", "Glob", "Grep", f"Bash(python3 {FERR / 'ver.py'}:*)"]
    resposta, codigo = agente.trabalhar(num, contexto(num, pedido), ferramentas="Read,Write,Edit,Glob,Grep,Bash", permitidas=permitidas,
                                        na_ficha=na_ficha, quem="capas")
    if na_ficha:
        E.mexe_ficha(num, progresso=90)
    _, erros = fotos(num)
    if na_ficha:
        E.mexe_ficha(num, progresso=None)
    if codigo or not resposta:
        resposta = "O animador parou antes de terminar a capa. Peça de novo, por favor."
    if not opcoes(num):
        resposta += " (As opções de capa não ficaram prontas: faltou o capas.json ou a capa.)"
    if erros:
        resposta += " (Erro na página da capa: " + "; ".join(erros)[:200] + ")"
    E.evento(num, f"capas feitas: {len(opcoes(num))} opção(ões)")
    return aviso + resposta


def escolher(num, op):
    """A escolhida vira animacao/capa.html (1 s do começo da prévia) e animacao/capa.jpg (capa do Reels)."""
    a = E.pasta(num) / "animacao"
    o = next((x for x in opcoes(num) if int(x.get("op", 0)) == int(op)), None)
    if not o:
        raise ValueError("essa opção de capa não existe")
    shutil.copy2(a / f"capa-{int(op)}.html", a / "capa.html")
    shutil.copy2(a / f"capa-{int(op)}.jpg", a / "capa.jpg")
    # capa viva (21/10/2026, "aprovo o plano capa-viva"): o texto por cima e o trecho que toca por baixo no começo do
    # vídeo; capa sem vídeo de origem (a do caminho de antes) apaga os da escolha anterior e fica parada até 1,7 s
    texto = a / f"capa-{int(op)}-texto.png"
    if o.get("fundo") and texto.exists():
        shutil.copy2(texto, a / "capa-texto.png")
        (a / "capa-fundo.json").write_text(json.dumps(o["fundo"], ensure_ascii=False))
    else:
        (a / "capa-texto.png").unlink(missing_ok=True); (a / "capa-fundo.json").unlink(missing_ok=True)
    E.mexe_ficha(num, capa={"op": int(op), "frase": o.get("frase", ""), "quando": E.agora()})
    E.evento(num, f"capa escolhida por ele: opção {int(op)} ({o.get('frase', '')[:80]})")
    return o


if __name__ == "__main__":
    print(fazer(int(sys.argv[1]), " ".join(sys.argv[2:]) or None))
