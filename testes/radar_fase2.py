"""radar fase 2: pautas sugeridas, fazer, descartar, decisões no cérebro e a tela. Sem WhatsApp e sem IA de verdade.
   python3 teste_radar2.py <pasta do código>"""
import json, os, shutil, sys, threading, urllib.request
from pathlib import Path
COD = Path(sys.argv[1]); sys.path[:0] = [str(COD), str(COD / "ferramentas")]
os.environ.setdefault("GEMINI_API_KEY", "teste")
import estudio as E
T = Path("/tmp/ca/radar2/itens") / COD.name; shutil.rmtree(T, ignore_errors=True); T.mkdir(parents=True)
E.VIDEOS = T
E.LIXEIRA = T / "_lixeira"; E.LIXEIRA.mkdir(exist_ok=True)
assert not any(Path(m.__file__).parent != COD for m in [E]), "o teste carregou o estudio errado"
for f in (COD / "radar").glob("*.json"):
    f.unlink()
ok = []
def caso(n, c): ok.append((n, bool(c)))
avisos = []
try:
    import avisar; avisar.avisar = lambda texto, **k: avisos.append(texto) or {"code": "SUCCESS"}
except ImportError:
    pass
try:
    import radar as R
    assert Path(R.__file__).parent == COD, f"o teste carregou o radar errado: {R.__file__}"
except ImportError:
    R = None
juizo = lambda t, n: {"vira_video": True, "nota": n, "titulo": t, "porque": "fala sobre dinheiro com documento", "prova": "matéria do UOL",
                      "formato": "Fomos conferir", "parecido_com": ""}
r = {"medido": "2026-10-21 21:00", "sugestoes": [
    {"conta": "lindberghfarias", "quem": "Lindbergh", "link": "https://www.instagram.com/reel/AAA111/", "fator": 19.7, "interacoes": 900, "visualizacoes": -1, "juizo": juizo("Escritório do Flávio: R$ 13,7 mi", 8)},
    {"conta": "guilhermeboulos.oficial", "quem": "Boulos", "link": "https://www.instagram.com/reel/BBB222/", "fator": 42.5, "interacoes": 800, "visualizacoes": -1, "juizo": juizo("200 decretos", 8)},
    {"conta": "x", "quem": "X", "link": "https://www.instagram.com/reel/CCC333/", "fator": 10, "interacoes": 500, "visualizacoes": -1, "juizo": juizo("terceira", 7)},
    {"conta": "y", "quem": "Y", "link": "https://www.instagram.com/reel/DDD444/", "fator": 9, "interacoes": 500, "visualizacoes": -1, "juizo": juizo("quarta", 7)}]}
criados = R.sugerir(r) if R and hasattr(R, "sugerir") else []
caso(f"T1a · o radar cria as pautas sugeridas, no máximo 3 por dia (criou {len(criados)})", len(criados) == 3)
f = E.ler_ficha(criados[0]) if criados else {}
caso("T1b · a pauta fica parada esperando ele (nada roda antes)", f.get("passo") == "sugerida pelo radar" and f.get("esperando") == "Fazer esta pauta?")
caso(f"T1c · um aviso no WhatsApp por pauta ({len(avisos)}), com o link do estúdio", len(avisos) == 3 and all("admin.newsbr360.com/#/item/" in a for a in avisos))
de_novo = R.sugerir(r) if R and hasattr(R, "sugerir") else [1]
caso(f"T1d · link já sugerido não volta (na 2ª rodada criou {len(de_novo)})", de_novo == [])

argv, sys.argv = sys.argv, [sys.argv[0], "4494"]
import servidor as S
sys.argv = argv
assert Path(S.__file__).parent == COD, f"o teste carregou o servidor errado: {S.__file__}"
from http.server import ThreadingHTTPServer
S.H.log_message = lambda *a: None
andou = []
S.garantir = lambda num: andou.append(num)
srv = ThreadingHTTPServer(("127.0.0.1", 4494), S.H); threading.Thread(target=srv.serve_forever, daemon=True).start()
def post(num, acao, corpo):
    req = urllib.request.Request(f"http://127.0.0.1:4494/api/item/{num}/{acao}", data=json.dumps(corpo).encode(), method="POST")
    try:
        return urllib.request.urlopen(req, timeout=20).status
    except urllib.error.HTTPError as e:
        return e.code
n1, n2 = (criados + [0, 0])[:2]
st = post(n1, "fazer-pauta", {}) if n1 else 0
caso(f"T2 · 'Fazer esta pauta' faz a pauta andar (HTTP {st}, passo {E.ler_ficha(n1).get('passo') if n1 else '-'})",
     st == 200 and n1 and E.ler_ficha(n1).get("passo") == "recebida" and andou == [n1])
st = post(n2, "descartar-pauta", {"motivo": "acusação sem documento"}) if n2 else 0
dec = json.loads((COD / "radar/decisoes.json").read_text()) if (COD / "radar/decisoes.json").exists() else []
caso(f"T3 · 'Descartar' tira a pauta da lista e guarda o motivo (HTTP {st}, decisões {[d['decisao'] for d in dec]})",
     st == 200 and n2 not in E.numeros() and any(d["decisao"] == "descartou" and "documento" in d["porque"] for d in dec))
if R and hasattr(R, "cerebro"):
    pedido = {}
    R.ia = lambda blocos, quem, limite=240: (pedido.setdefault("t", blocos[0]["text"]), ("# Cérebro", 0))[1]
    (COD / "radar").mkdir(exist_ok=True)
    (COD / "radar/pagina.json").write_text(json.dumps({"seguidores": 9447, "posts": [{"postado": "2026-10-21", "forca": 1.0, "tipo": "REELS"}]}))
    try:
        R.cerebro()
    except Exception:
        pass
    caso("T4 · o cérebro recebe as decisões dele", "descartou" in pedido.get("t", "") and "acusação sem documento" in pedido.get("t", ""))
else:
    caso("T4 · o cérebro recebe as decisões dele", False)
# T5: a tela da pauta sugerida (o terceiro item continua sugerido)
n3 = criados[2] if len(criados) > 2 else None
if n3:
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        nav = p.chromium.launch()
        for nome, vp, mob in (("desktop", {"width": 1440, "height": 900}, False), ("celular", {"width": 390, "height": 844}, True)):
            pg = nav.new_page(viewport=vp, is_mobile=mob, device_scale_factor=2 if mob else 1)
            pg.goto(f"http://127.0.0.1:4494/#/item/{n3}"); pg.wait_for_timeout(4000)
            tem = pg.query_selector("#fazer-pauta") is not None and pg.query_selector("#descartar-pauta") is not None
            pg.screenshot(path=f"/tmp/ca/radar2/tela-{COD.name}-{nome}.png")
            caso(f"T5 · a tela ({nome}) mostra a sugestão com os dois botões", tem)
        nav.close()
else:
    caso("T5 · a tela mostra a sugestão com os dois botões", False)
for n, b in ok:
    print("PASSOU" if b else "FALHOU", "·", n)
print(f"{sum(b for _, b in ok)} de {len(ok)}")
