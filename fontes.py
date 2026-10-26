"""Conferência das fontes (19/10/2026; ele: "todos os fatos que já foram checados quem checou?" e "faz a conferência das
fontes"). O roteirista e o agente acham a fonte e escrevem a checagem, e a segunda opinião confia no que está escrito:
ninguém reabria o link para ver se o número ou a frase citada está mesmo lá.

  1. o programa lê o CHECAGEM.md e, para cada linha, abre cada link e tira o texto da página (sem IA);
  2. separa só os trechos da página que falam daquele fato (os números e as palavras do que foi escrito);
  3. uma chamada do Sonnet, sem ferramentas, diz fonte por fonte: confirma, em parte, não confirma, ou não deu para ler.
Grava fontes.json no vídeo. Roda com o roteiro parado e ao aprovar, só quando a checagem mudou (servidor.conferir_fontes).

  python3 fontes.py <número>
"""
import hashlib, html, json, re, subprocess, sys, time, urllib.request
from pathlib import Path

import estudio as E

MODELO = "sonnet"
LINK = re.compile(r"\[([^\]]*)\]\((https?://[^)\s]+)\)")
# 25/10/2026 ("faz"; o #383 escreveu os links soltos, "https://...", e a conferência leu 0 fontes, como se estivesse tudo certo)
SOLTO = re.compile(r"https?://[^\s<>|()\[\]]+")


def links_de(texto):
    """Os links do texto: os de [nome](link) e os soltos."""
    return [u for _, u in LINK.findall(texto)] + [u.rstrip(".,;:'\"") for u in SOLTO.findall(LINK.sub("", texto))]
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_0) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0 Safari/537.36"
COMUNS = set("sobre entre ainda depois antes segundo também quando porque desde mesmo apenas cerca maior menor "
             "fonte veredito governo brasil presidente".split())


def linhas_da_checagem(num, sem_link=False):
    """[(afirmação, o que a fonte diz, [links])] das linhas da tabela do CHECAGEM.md (sem_link: também as que não têm
    link nenhum, com a lista vazia)."""
    arq = E.pasta(num) / "CHECAGEM.md"
    if not arq.exists():
        return []
    # 24/10/2026 ("pode consertar?"; o #367 deu 0 fontes): a tabela pode ter colunas antes da afirmação ("# | Afirmação |
    # Fonte original | Selo"); as colunas saem do cabeçalho, e sem cabeçalho valem as duas primeiras, como antes
    out, ia, ib = [], 0, 1
    for l in arq.read_text().splitlines():
        cel = [c.strip() for c in l.strip().strip("|").split("|")]
        if len(cel) < 3 or set(cel[0]) <= set("-: "):
            continue
        baixo = [c.lower() for c in cel]
        if any(c.startswith("afirma") for c in baixo):
            ia = next(i for i, c in enumerate(baixo) if c.startswith("afirma"))
            ib = next((i for i, c in enumerate(baixo) if i != ia and ("fonte" in c or "diz" in c)), ia + 1)
            continue
        if max(ia, ib) >= len(cel):
            continue
        links = links_de(cel[ia] + " " + cel[ib])
        if links or sem_link:
            out.append((LINK.sub(r"\1", cel[ia]), LINK.sub(r"\1", cel[ib]), links))
    return out


def texto_da_pagina(url):
    """O texto da página (sem IA). Devolve (texto, erro)."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "pt-BR,pt;q=0.9"})
        with urllib.request.urlopen(req, timeout=20) as r:
            tipo = r.headers.get("Content-Type", "")
            corpo = r.read(3_000_000)
        if "pdf" in tipo or url.lower().endswith(".pdf"):
            return "", "é um PDF (não li)"
        h = corpo.decode("utf-8", "replace")
    except Exception as ex:
        return pelo_navegador(url, f"não abriu ({str(ex)[:80]})")
    h = re.sub(r"(?is)<(script|style|noscript|svg)[^>]*>.*?</\1>", " ", h)
    t = html.unescape(re.sub(r"(?s)<[^>]+>", " ", h))
    t = re.sub(r"\s+", " ", t).strip()
    return (t, "") if len(t) > 200 else ("", "página sem texto (talvez precise de navegador ou de login)")


def pelo_navegador(url, erro):
    """Site que recusa o pedido simples (403): tenta com um navegador de verdade (Chrome do playwright, sem IA)."""
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            b = p.chromium.launch(); pg = b.new_page(user_agent=UA)
            pg.goto(url, timeout=30000, wait_until="domcontentloaded"); pg.wait_for_timeout(1500)
            t = re.sub(r"\s+", " ", pg.inner_text("body")).strip(); b.close()
        return (t, "") if len(t) > 200 else ("", erro)
    except Exception:
        return "", erro


def norm(t):
    import unicodedata          # acento composto ou decomposto (á pode vir de dois jeitos na página)
    t = unicodedata.normalize("NFC", t)
    return re.sub(r"\s+", " ", re.sub(r"[“”\"'‘’«»]", "", t.lower())).strip()


def aspas_batem(texto, afirmado):
    """O programa confirma sozinho (sem IA): uma frase entre aspas da checagem, de 4 palavras ou mais, está igual na
    página. Devolve a frase achada ou ""."""
    pagina = norm(texto)
    for frase in re.findall(r"[\"“'‘]([^\"”'’]{15,240})[\"”'’]", afirmado):
        if len(frase.split()) >= 4 and norm(frase) in pagina:
            return frase
    return ""


def trechos(texto, afirmado, n=6, largura=420):
    """Os pedaços da página com mais números e palavras do que foi escrito na checagem."""
    numeros = set(re.findall(r"\d+(?:[.,]\d+)?", afirmado))
    palavras = {w for w in re.findall(r"[A-Za-zÀ-ú]{5,}", afirmado.lower()) if w not in COMUNS}
    pedacos = [texto[i:i + largura] for i in range(0, len(texto), largura // 2)]
    nota = lambda p: 3 * sum(1 for x in numeros if x in p) + sum(1 for w in palavras if w in p.lower())
    melhores = sorted(pedacos, key=nota, reverse=True)[:n]
    return [p for p in melhores if nota(p) > 0]


PEDIDO = """Você confere fontes de uma checagem jornalística. Para cada item abaixo há o que a checagem diz que a fonte
afirma e trechos tirados da página da fonte pelo programa (não a página inteira). Diga, só com base nos trechos, se a
fonte confirma o que a checagem atribui a ela. Números, datas e frases entre aspas têm que bater. Se os trechos não
bastam para saber, diga "não deu para saber" (não chute).

{itens}

Responda SÓ um JSON: [{{"item": <número>, "confirma": "sim" | "em parte" | "não" | "não deu para saber",
"trecho": "<até 25 palavras da página que provam, copiadas>", "obs": "<até 20 palavras: o que não bate, se algo>"}}]"""


def conferir(num, forcar=False):
    p = E.pasta(num)
    checagem = p / "CHECAGEM.md"
    if not checagem.exists():
        return None
    marca = hashlib.md5(checagem.read_bytes()).hexdigest()
    arq = p / "fontes.json"
    antes = json.loads(arq.read_text()) if arq.exists() else {}
    if antes.get("hash") == marca and not forcar:
        return antes
    # 19/10/2026 (ele: "essa conferência vai ser uma constante. temos que baratear isso"): o resultado de cada fonte fica
    # guardado pela chave (link + o que a checagem diz dela) e só o que é novo ou mudou é conferido de novo; e o que
    # o programa confirma sozinho (a frase entre aspas está igual na página) não vai à IA
    guardados = antes.get("por_item", {})
    itens, sem, reuso, programa, por_item = [], [], [], [], {}
    for afirmacao, fonte, links in linhas_da_checagem(num):
        for url in dict.fromkeys(links):
            chave = hashlib.md5((url + "|" + fonte).encode()).hexdigest()[:16]
            if chave in guardados and not forcar:
                reuso.append(guardados[chave]); por_item[chave] = guardados[chave]; continue
            texto, erro = texto_da_pagina(url)
            frase = aspas_batem(texto, fonte) if texto else ""
            if frase:
                x = {"afirmacao": afirmacao[:160], "url": url, "confirma": "sim", "trecho": frase[:200], "obs": "conferido pelo programa (a frase está igual na página)"}
                programa.append(x); por_item[chave] = x; continue
            ts = trechos(texto, fonte) if texto else []
            if erro or not ts:
                x = {"afirmacao": afirmacao[:160], "url": url, "confirma": "não deu para ler", "obs": erro or "a página não fala do que foi escrito"}
                sem.append(x); por_item[chave] = x; continue
            itens.append({"afirmacao": afirmacao[:160], "fonte_diz": fonte[:700], "url": url, "trechos": ts, "chave": chave})
    resultado = []
    if itens:
        texto = "\n\n".join(f"ITEM {i + 1} · {x['url']}\nA checagem diz que esta fonte afirma: {x['fonte_diz']}\nTrechos da página:\n"
                            + "\n".join(f"- {t}" for t in x["trechos"]) for i, x in enumerate(itens))
        import ia                             # 25/10/2026: a chamada de IA de um lugar só (ia.py)
        resp, _ = ia.chamar(PEDIDO.format(itens=texto), "conferência das fontes", MODELO, num=num, limite=600, cwd=p)
        try:
            for x in ia.json_de(resp, "[") or []:
                i = int(x.get("item", 0)) - 1
                if 0 <= i < len(itens):
                    y = {"afirmacao": itens[i]["afirmacao"], "url": itens[i]["url"], "confirma": x.get("confirma"),
                         "trecho": x.get("trecho", ""), "obs": x.get("obs", "")}
                    resultado.append(y); por_item[itens[i]["chave"]] = y
        except (ValueError, TypeError):
            pass
    todas = reuso + programa + resultado + sem
    sem_link = sum(1 for *_, ls in linhas_da_checagem(num, sem_link=True) if not ls)
    conf = {"quando": E.agora(), "hash": marca, "fontes": todas, "por_item": por_item, "linhas_sem_link": sem_link,
            "rodada": {"reaproveitadas": len(reuso), "pelo_programa": len(programa), "pela_ia": len(itens), "sem_como_ler": len(sem)},
            "contagem": {k: sum(1 for x in todas if x["confirma"] == k) for k in ("sim", "em parte", "não", "não deu para saber", "não deu para ler")}}
    E._grava(arq, json.dumps(conf, ensure_ascii=False, indent=1))
    c = conf["contagem"]
    E.evento(num, f"conferência das fontes: {c['sim']} confirmam, {c['em parte']} em parte, {c['não']} não confirmam, "
                  f"{c['não deu para saber'] + c['não deu para ler']} sem como conferir, {sem_link} linha(s) sem link")
    return conf


def aviso(conf):
    """A frase para o chat: só as LINHAS da checagem em que nenhuma fonte confirmou e alguma disse "não" ou "em parte"
    (no #301 o Congresso em Foco confirmava só em parte, mas o JB, na mesma linha, confirmava tudo)."""
    fs = conf.get("fontes", [])
    if not fs and conf.get("linhas_sem_link"):
        # 25/10/2026 (#383): sem link nenhum a conferência não abre nada; os zeros pareciam "tudo certo"
        return (f"Não achei link nenhum na checagem ({conf['linhas_sem_link']} linha(s) da tabela): a conferência não abriu "
                "fonte nenhuma. Vale pôr o link de cada fonte antes de aprovar.")
    ok = {x["afirmacao"] for x in fs if x["confirma"] == "sim"}
    ruins = [x for x in fs if x["confirma"] in ("não", "em parte") and x["afirmacao"] not in ok]
    if not ruins:
        return ""
    return ("Conferi as fontes da checagem abrindo cada link. " + f"{len(ruins)} afirmação(ões) sem fonte que confirme tudo: "
            + "; ".join(f"\"{x['afirmacao'][:70]}\" ({re.sub(r'^https?://(www\\.)?', '', x['url'])[:40]}): {x['confirma']}, {x['obs']}" for x in ruins[:4])
            + ". Vale corrigir antes de aprovar.")


if __name__ == "__main__":
    print(json.dumps(conferir(int(sys.argv[1]), forcar=True), ensure_ascii=False, indent=1)[:5000])
