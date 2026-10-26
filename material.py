"""Material que não é vídeo (estúdio v2, 17/10/2026, "aprovo o plano material-qualquer"; ele: "temos que criar a
ferramenta que baixa carrossel ou imagem ou pdf ou página web, para pegar o conteúdo e montar um vídeo com base nisso").

  python3 material.py <número> <link>

Guarda em referencia/material/ as imagens (slideNN do carrossel, paginaNN do PDF, fotoNN da página ou da imagem solta,
telaNN quando é foto da tela) e texto.txt (a legenda do post, o texto do PDF ou da página). Três tentativas, uma depois
da outra (ele: "quando não há áudio ou não pode baixar poderia tirar foto de tudo e ler usando os olhos"):
  1. o original (as imagens do carrossel pelo navegador, sem login; o PDF; a imagem; o texto e as imagens da página);
  2. não deu: foto da tela de tudo (o navegador abre o link e fotografa a página, de cima a baixo);
  3. nem isso: para e pede as imagens pelo clipe.
Nunca entra com a conta dele em lugar nenhum.
"""
import json, re, subprocess, sys, time, urllib.parse, urllib.request
from pathlib import Path

import estudio as E

VIDEO_SOCIAL = ("youtube.com", "youtu.be", "tiktok.com", "x.com", "twitter.com", "facebook.com", "fb.watch", "kwai.com", "vimeo.com")
UA_CEL = ("Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 "
          "Mobile/15E148 Safari/604.1")
UA = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
MAX_IMAGENS, MAX_PAGINAS_PDF, MAX_TELAS = 12, 20, 8


class SemMaterial(RuntimeError):
    pass


def dominio(link):
    return urllib.parse.urlparse(link).netloc.lower().removeprefix("www.").removeprefix("m.")


def post_instagram(link):
    return dominio(link).endswith("instagram.com") and "/p/" in urllib.parse.urlparse(link).path


def e_material(link):
    """O link vai direto para cá (não é de vídeo): tudo que não é rede de vídeo, menos o reel do Instagram. O post
    /p/ do Instagram pode ser vídeo: tenta o vídeo primeiro (pauta.py) e cai aqui se não houver."""
    d = dominio(link)
    if d.endswith("instagram.com"):
        return False
    return not any(d == s or d.endswith("." + s) for s in VIDEO_SOCIAL)


def _baixa(url, ua=UA, timeout=60):
    req = urllib.request.Request(url, headers={"User-Agent": ua})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.headers.get("Content-Type", ""), r.read()


def _jpg(dados, alvo):
    """Qualquer imagem → JPG (até 1440 de largura)."""
    from PIL import Image
    import io
    im = Image.open(io.BytesIO(dados)).convert("RGB")
    if im.width > 1440:
        im = im.resize((1440, round(im.height * 1440 / im.width)))
    im.save(alvo, quality=90)
    return im.size


def _navegador(pw, celular=True):
    nav = pw.chromium.launch()
    ctx = nav.new_context(viewport={"width": 430, "height": 900} if celular else {"width": 1280, "height": 900},
                          device_scale_factor=2.5 if celular else 1, locale="pt-BR", user_agent=UA_CEL if celular else UA)
    return nav, ctx.new_page()


def _passa(pg, link):
    pg.goto(link, wait_until="domcontentloaded", timeout=60000)
    pg.wait_for_timeout(4000)
    vistos = []
    for _ in range(MAX_IMAGENS + 2):
        for s in pg.evaluate("""() => [...document.querySelectorAll('img')].filter(i => i.naturalWidth >= 600 &&
              /^(Photo by|Foto (de|por)|Photo shared by)/i.test(i.alt || '')).map(i => i.currentSrc || i.src)"""):
            if s not in vistos:
                vistos.append(s)
        seta = pg.locator('[aria-label="Avançar"], [aria-label="Next"]')
        if not seta.count():
            break
        seta.first.dispatch_event("click")
        pg.wait_for_timeout(1000)
    return vistos


def carrossel(link, dest):
    """As imagens do post do Instagram, passando uma a uma pela seta "Avançar" (sem login), e a legenda do post.
    Medido em 17/10/2026 no post do Mises (Dej0iZrCibX): 7 imagens 1080x1350, por trás do aviso "Veja no app"."""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        nav, pg = _navegador(pw)
        # 17/10/2026: o link dele vinha com "?img_index=6" e o carrossel abria na 6ª imagem (vieram 3 de 7); sem o que
        # vem depois do "?", vieram as 7 (medido)
        vistos = _passa(pg, link.split("?")[0])
        feitos = []
        for i, s in enumerate(vistos[:MAX_IMAGENS], 1):
            alvo = dest / f"slide{i:02d}.jpg"
            _jpg(pg.request.get(s).body(), alvo)
            feitos.append(alvo)
        og = pg.evaluate("""() => { const m = n => (document.querySelector(`meta[property="${n}"]`) || {}).content || '';
              return {titulo: m('og:title'), descricao: m('og:description')}; }""")
        nav.close()
    # a legenda: "11 mil curtidas, 177 comentários - mises_brasil em 16 de outubro de 2026: "Nesta eleição...""
    d = og.get("descricao") or ""
    conta = re.search(r"-\s*([\w.]+)\s+(?:on|em)\s", d.split(":")[0])     # só antes da legenda ("pós-graduação em")
    legenda = re.sub(r'^.*?:\s*"?', "", d, count=1).rstrip('"') if ":" in d else d
    return feitos, {"quem_postou": (og.get("titulo") or "").split(" on Instagram")[0].split(" no Instagram")[0] or None,
                    "conta": conta.group(1) if conta else None, "legenda_do_post": legenda[:4000]}


def pdf(link, dest):
    import fitz
    tipo, dados = _baixa(link, timeout=120)
    if b"%PDF" not in dados[:1024]:
        raise SemMaterial(f"o link não devolveu um PDF ({tipo})")
    doc = fitz.open(stream=dados, filetype="pdf")
    texto = "\n\n".join(f"[página {i + 1}]\n" + p.get_text() for i, p in enumerate(doc) if i < 80)
    feitos = []
    for i, p in enumerate(doc):
        if i >= MAX_PAGINAS_PDF:
            break
        pix = p.get_pixmap(matrix=fitz.Matrix(1080 / p.rect.width, 1080 / p.rect.width))
        alvo = dest / f"pagina{i + 1:02d}.jpg"
        pix.save(str(alvo))
        feitos.append(alvo)
    meta = doc.metadata or {}
    return feitos, {"titulo": meta.get("title") or None, "quem_postou": meta.get("author") or None, "paginas": len(doc)}, texto


def imagem(link, dest):
    tipo, dados = _baixa(link)
    if not tipo.startswith("image/"):
        raise SemMaterial(f"o link não é uma imagem ({tipo})")
    alvo = dest / "foto01.jpg"
    _jpg(dados, alvo)
    return [alvo], {}


def pagina(link, dest):
    """Título, data, texto principal e as imagens grandes da página; e as fotos da tela de cima a baixo (para os Olhos
    lerem o que está desenhado, tabela, gráfico)."""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        nav, pg = _navegador(pw)
        pg.goto(link, wait_until="domcontentloaded", timeout=60000)
        pg.wait_for_timeout(3500)
        info = pg.evaluate("""() => {
          const m = n => (document.querySelector(`meta[property="${n}"], meta[name="${n}"]`) || {}).content || '';
          const corpo = document.querySelector('article') || document.querySelector('main') || document.body;
          const ims = [...corpo.querySelectorAll('img')].filter(i => i.naturalWidth >= 500).map(i => i.currentSrc || i.src);
          return {titulo: m('og:title') || document.title, data: m('article:published_time') || m('date') ||
                  ((document.querySelector('time[datetime]') || {}).dateTime || ''), autor: m('author') || m('article:author'),
                  site: m('og:site_name'), texto: (corpo.innerText || '').slice(0, 40000), imagens: [...new Set(ims)].slice(0, 8)}; }""")
        feitos = []
        for i, s in enumerate(info["imagens"], 1):
            try:
                _jpg(pg.request.get(s).body(), dest / f"foto{i:02d}.jpg")
                feitos.append(dest / f"foto{i:02d}.jpg")
            except Exception:
                pass
        feitos += _telas(pg, dest)
        nav.close()
    return feitos, {"titulo": info["titulo"], "postado": info["data"][:10] or None, "quem_postou": info["autor"] or info["site"] or None}, info["texto"]


def _telas(pg, dest):
    """Fotos da tela de cima a baixo, uma por altura de tela (até MAX_TELAS)."""
    altura = pg.evaluate("() => document.documentElement.scrollHeight")
    feitos = []
    for i in range(min(MAX_TELAS, max(1, -(-altura // 900)))):
        pg.evaluate(f"() => window.scrollTo(0, {i * 900})")
        pg.wait_for_timeout(400)
        alvo = dest / f"tela{i + 1:02d}.jpg"
        pg.screenshot(path=str(alvo), type="jpeg", quality=85)
        feitos.append(alvo)
    return feitos


def foto_da_tela(link, dest):
    """Tentativa 2: não deu para baixar o original; o navegador abre o link e fotografa tudo."""
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        nav, pg = _navegador(pw)
        pg.goto(link, wait_until="domcontentloaded", timeout=60000)
        pg.wait_for_timeout(4000)
        texto = pg.evaluate("() => (document.body.innerText || '').slice(0, 20000)")
        feitos = _telas(pg, dest)
        nav.close()
    return feitos, texto


def baixar(num, link):
    """Baixa o material do link em referencia/material/ e grava referencia/meta.json. Devolve o meta."""
    ref = E.pasta(num) / "referencia"
    dest = ref / "material"; dest.mkdir(parents=True, exist_ok=True)
    meta = {"link": link, "duracao": 0}
    texto, feitos, tipo, erro = "", [], None, ""
    try:
        path = urllib.parse.urlparse(link).path.lower()
        if post_instagram(link) or dominio(link).endswith("instagram.com"):
            tipo = "carrossel"
            feitos, extra = carrossel(link, dest)
            texto = extra.get("legenda_do_post") or ""
        elif path.endswith(".pdf"):
            tipo = "pdf"
            feitos, extra, texto = pdf(link, dest)
        elif re.search(r"\.(jpe?g|png|webp|gif)$", path):
            tipo = "imagem"
            feitos, extra = imagem(link, dest)
        else:
            ct, _ = "", None
            try:
                req = urllib.request.Request(link, method="HEAD", headers={"User-Agent": UA})
                with urllib.request.urlopen(req, timeout=20) as r:
                    ct = r.headers.get("Content-Type", "")
            except Exception:
                pass
            if "pdf" in ct:
                tipo = "pdf"; feitos, extra, texto = pdf(link, dest)
            elif ct.startswith("image/"):
                tipo = "imagem"; feitos, extra = imagem(link, dest)
            else:
                tipo = "pagina"; feitos, extra, texto = pagina(link, dest)
        meta.update({k: v for k, v in extra.items() if v})
    except Exception as ex:
        erro = str(ex)[:200]
    if not feitos:
        E.evento(num, f"o material original não veio ({erro or 'nenhuma imagem'}); tirando foto da tela")
        try:
            feitos, texto2 = foto_da_tela(link, dest)
            texto = texto or texto2
            tipo = "tela"
        except Exception as ex:
            raise SemMaterial(f"não consegui baixar nem fotografar o link ({str(ex)[:160]}). Mande as imagens pelo clipe "
                              "e diga \"tenta de novo\"")
    if not feitos:
        raise SemMaterial("o link não tinha imagem nem texto que eu conseguisse ler. Mande as imagens pelo clipe")
    if texto:
        (dest / "texto.txt").write_text(texto)
    meta.update({"tipo_material": tipo, "imagens": [str(p.relative_to(E.pasta(num))) for p in feitos]})
    if texto and not meta.get("legenda_do_post"):
        meta["texto_inicio"] = " ".join(texto.split())[:600]
    (ref / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1))
    E.evento(num, f"material baixado: {tipo}, {len(feitos)} imagem(ns), {len(texto)} caracteres de texto")
    return meta


if __name__ == "__main__":
    print(json.dumps(baixar(int(sys.argv[1]), sys.argv[2]), ensure_ascii=False, indent=1))
