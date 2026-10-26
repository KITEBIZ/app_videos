#!/usr/bin/env python3
"""Fotos com direito de uso para a colagem (24/10/2026, micro documentário; ele: "pegar fotos do lula criação e tudo
mais e fazer a colagem na parte que nào temos imagens"). Busca na Wikimedia Commons (onde estão as fotos da Agência
Brasil, da Agência Senado e do Arquivo Nacional), aceita só domínio público, CC0, CC BY e CC BY-SA, baixa, recorta o
fundo pela fal se pedido, e anota título, autor, licença e página em material/colagem/creditos.json (o crédito vai na
tela). Foto de pessoa real só no contexto dela: nunca use gente de uma foto como se fosse outra história.

  python3 ferramentas/fotos_livres.py <número> buscar "Fernando Collor 1990"       lista até 8 com licença e tamanho
  python3 ferramentas/fotos_livres.py <número> baixar "<título exato>" <nome> [--recorte]
      grava material/colagem/<nome>.jpg (e <nome>-sem-fundo.png com --recorte, ~US$ 0,01 na fal)
"""
import base64, json, os, re, sys, urllib.parse, urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
import estudio as E

UA = {"User-Agent": "kitebiz-conteudo/1 (seu-email@exemplo.com)"}
API = "https://commons.wikimedia.org/w/api.php"
LIVRE = ("public domain", "cc0", "cc by", "cc-by", "attribution")


def _api(params):
    return json.load(urllib.request.urlopen(urllib.request.Request(API + "?" + urllib.parse.urlencode(params), headers=UA), timeout=60))


def _info(ii):
    m = ii.get("extmetadata", {})
    g = lambda k: re.sub("<[^>]+>", "", m.get(k, {}).get("value") or "").strip()
    return {"licenca": g("LicenseShortName"), "autor": g("Artist")[:80], "data": g("DateTimeOriginal")[:20],
            "pagina": ii.get("descriptionurl"), "url": ii.get("thumburl") or ii.get("url"), "largura": ii.get("width"), "altura": ii.get("height")}


def buscar(texto, n=8):
    r = _api({"action": "query", "format": "json", "generator": "search", "gsrnamespace": 6, "gsrlimit": 20,
              "gsrsearch": "filetype:bitmap " + texto, "prop": "imageinfo", "iiprop": "url|size|extmetadata", "iiurlwidth": 1400})
    out = []
    for p in sorted(r.get("query", {}).get("pages", {}).values(), key=lambda p: p.get("index", 99)):
        i = _info(p["imageinfo"][0])
        if i["licenca"].lower().startswith(LIVRE) and (i["largura"] or 0) >= 500:
            out.append({"titulo": p["title"][5:], **i})
    return out[:n]


def baixar(num, titulo, nome, recorte=False):
    pasta = E.pasta(num) / "material/colagem"; pasta.mkdir(parents=True, exist_ok=True)
    r = _api({"action": "query", "format": "json", "prop": "imageinfo", "iiprop": "url|size|extmetadata", "iiurlwidth": 1400,
              "titles": "File:" + titulo})
    i = _info(list(r["query"]["pages"].values())[0]["imageinfo"][0])
    if not i["licenca"].lower().startswith(LIVRE):
        raise SystemExit(f"licença não livre ({i['licenca']}): não use")
    (pasta / f"{nome}.jpg").write_bytes(urllib.request.urlopen(urllib.request.Request(i["url"], headers=UA), timeout=120).read())
    if recorte:
        img = "data:image/jpeg;base64," + base64.b64encode((pasta / f"{nome}.jpg").read_bytes()).decode()
        req = urllib.request.Request("https://fal.run/fal-ai/birefnet", data=json.dumps({"image_url": img, "model": "General Use (Heavy)",
                                     "output_format": "png"}).encode(), headers={"Authorization": "Key " + os.environ["FAL_KEY"],
                                                                                "Content-Type": "application/json"})
        u = json.load(urllib.request.urlopen(req, timeout=180))["image"]["url"]
        (pasta / f"{nome}-sem-fundo.png").write_bytes(urllib.request.urlopen(u, timeout=120).read())
    arq = pasta / "creditos.json"
    cred = json.loads(arq.read_text()) if arq.exists() else {}
    cred[f"{nome}.jpg"] = {"titulo": titulo, **{k: i[k] for k in ("pagina", "licenca", "autor", "data")}}
    arq.write_text(json.dumps(cred, ensure_ascii=False, indent=1))
    from PIL import Image
    w, h = Image.open(pasta / f"{nome}.jpg").size
    return {"arquivo": f"material/colagem/{nome}.jpg", "sem_fundo": f"material/colagem/{nome}-sem-fundo.png" if recorte else None,
            "tamanho": [w, h], "credito": f"{i['autor']} ({i['licenca']})"}


if __name__ == "__main__":
    num, acao = int(sys.argv[1]), sys.argv[2]
    if acao == "buscar":
        for f in buscar(sys.argv[3]):
            print(f"{f['titulo']} | {f['largura']}x{f['altura']} | {f['licenca']} | {f['autor'][:40]} | {f['data']}")
    elif acao == "baixar":
        print(json.dumps(baixar(num, sys.argv[3], sys.argv[4], "--recorte" in sys.argv), ensure_ascii=False))
