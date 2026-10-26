#!/usr/bin/env python3
"""O material do micro documentário pronto ANTES do animador (24/10/2026, "pode fazer"; ele: "porque o micro doc não
pode usar a mesma logica dos outros videos? e'so um formato diferente" e "não pode piorar, so pode melhorar").

Medido no #368: a primeira animação numa chamada só (a dos vídeos normais, sem ferramentas) pensou 600 s sem escrever
nada, porque as regras do micro doc mandavam ELE buscar as fotos e montar a trilha, e a chamada não roda nada. Agora é
como os mosaicos dos vídeos normais: o estúdio prepara e o animador só monta.

  preparar(num, chamar)   uma chamada curta (Sonnet) lê a coluna Tela e diz quais fotos e qual trilha; o programa busca
                          na Commons (só licença livre), uma segunda chamada curta escolhe a foto certa de cada busca
                          (pessoa real só no contexto dela), baixa e recorta em paralelo e monta animacao/trilha.mp3
  pedido(num)             os blocos que entram no pedido do animador: as fotos prontas (com o crédito), a trilha e o
                          instante da virada, a peça da colagem e a cena do #367 como exemplo
  python3 ferramentas/preparo_microdoc.py <número>   prepara e mostra o que ficou pronto
"""
import base64, io, json, re, sys, time, unicodedata
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ)); sys.path.insert(0, str(RAIZ / "ferramentas"))
import estudio as E
import fotos_livres as F
import trilha as TR

MAX_FOTOS = 5
LIMITE = 180          # cada chamada curta; passou disso, segue sem (o animador desenha o que faltar)

ESCOLHE = """Você prepara o material de um micro documentário em colagem para o animador, que vai montar a cena sem
poder buscar nada. Leia o roteiro (a coluna Tela diz o que aparece) e responda SÓ um JSON, sem explicação:
{"fotos": [{"bloco": <n>, "busca": "<o que buscar na Wikimedia Commons: nome e ano ou lugar>", "nome": "<nome-curto-sem-acento>",
  "recorte": <true para retrato de pessoa (tira o fundo), false para lugar, cena ou objeto>, "para": "<quem ou o quê, e em que contexto>"}],
 "trilha": [{"estilo": "<do catálogo>", "bloco": <n>, "palavra": "<a palavra do bloco onde troca, ou vazio para o começo do bloco>"}]}
Fotos: no máximo %d. As pessoas e lugares reais que a Tela pede como foto, e até 2 fotos de lugar ou objeto real da
história que deixam a colagem mais rica mesmo sem a Tela pedir (ex.: a plataforma, o prédio). O que é desenho, gráfico,
cartaz de texto ou plenário NÃO é foto. Pessoa real só no contexto dela. Busca curta: o nome e, se ajudar, o ano. Trilha: de 2 a 4 partes, a primeira no bloco 1; a troca principal
é na virada (a palavra que muda o rumo, quase sempre "Mas"); a conclusão pode ter outra. Use estilos do catálogo.

## Catálogo de trilhas
%s

## Roteiro
%s"""

# molde números (24/10/2026, "pode fazer o editor do molde números com o recado"): uma foto de fundo por capítulo, sem
# recorte, sem repetir, gente antes de prédio (no #368 à mão a sede da Petrobras saiu 3 vezes e prende pouco)
ESCOLHE_NUMEROS = """Você prepara as fotos de FUNDO de um vídeo no molde números (cada capítulo tem uma foto em tela cheia,
tingida e escura, com o número grande por cima) para o animador, que vai montar a cena sem poder buscar nada. Leia o
roteiro e responda SÓ um JSON, sem explicação:
{"fotos": [{"bloco": <n>, "busca": "<o que buscar na Wikimedia Commons: nome e ano ou lugar, 2 a 4 palavras>", "nome": "<nome-curto-sem-acento>",
  "recorte": false, "para": "<quem ou o quê, e em que contexto>"}],
 "trilha": [{"estilo": "<do catálogo>", "bloco": <n>, "palavra": "<a palavra do bloco onde troca, ou vazio para o começo do bloco>"}]}
Fotos: UMA por bloco do roteiro (no máximo %d), cada uma de um assunto diferente: nunca a mesma pessoa ou o mesmo prédio em
dois blocos. Prefira GENTE e acontecimento (a pessoa da época, a operação, a votação, o protesto) a fachada de prédio. A
coluna Tela diz a foto quando pede. Pessoa real só no contexto dela. Trilha: de 2 a 4 partes, a primeira no bloco 1; a
troca principal é na virada (a palavra que muda o rumo, quase sempre "Mas"); a conclusão pode ter outra.

## Catálogo de trilhas
%s

## Roteiro
%s"""

CONFERE = """Para cada pedido de foto, escolha UMA foto da lista que mostra exatamente quem ou o quê o pedido diz, no
contexto certo (a época, o lugar; nunca outra pessoa nem outra história), ou nenhuma. Prefira retrato nítido, de frente,
para recorte. Responda SÓ um JSON: {"<nome>": "<título exato da lista>" ou null, ...}

%s"""


def _json(texto):
    m = re.search(r"\{.*\}", texto or "", re.S)
    return json.loads(m.group(0)) if m else None


def _norm(s):
    return re.sub(r"[^\w]", "", unicodedata.normalize("NFD", str(s).lower()).encode("ascii", "ignore").decode())


def _instante(dados, bloco, palavra):
    b = next((x for x in dados["blocos"] if x["n"] == bloco), None)
    if not b:
        return None
    if palavra:
        alvo = _norm(palavra)
        for w in dados["palavras"]:
            if b["ini"] - .15 <= w[0] <= b["fim"] + .15 and _norm(w[2]) == alvo:
                return round(w[0], 2)
    return round(b["ini"], 2)


def busca(texto):
    """A Commons não acha frase longa ("Getúlio Vargas retrato 1950" deu 0; "Getúlio Vargas 1950" deu 8, #368): tira
    palavras do fim até achar, e junta com a busca só do nome."""
    w = texto.split(); achou = []
    for k in range(len(w), 1, -1):
        achou = F.buscar(" ".join(w[:k]))
        if achou:
            break
    if len(w) > 2:
        vistos = {c["titulo"] for c in achou}
        achou += [c for c in F.buscar(" ".join(w[:2])) if c["titulo"] not in vistos]
    return achou[:10]


def preparar(num, chamar):
    """chamar(num, blocos, quem, limite, modelo) -> (texto, uso): a chamada única do animador (animador_novo.opus).
    Devolve o resumo do que ficou pronto (vai para material/colagem/preparo.json)."""
    import animacao as A
    p = E.pasta(num); t0 = time.time(); pasta = p / "material/colagem"; pasta.mkdir(parents=True, exist_ok=True)
    tabela = "\n".join(l for l in (p / "ROTEIRO.md").read_text().splitlines() if l.startswith("|"))
    catalogo = (RAIZ / "web/sons/trilhas/CATALOGO.md").read_text()
    numeros = E.ler_ficha(num).get("molde") == "numeros"
    maximo = 8 if numeros else MAX_FOTOS
    resp, _ = chamar(num, [{"type": "text", "text": (ESCOLHE_NUMEROS if numeros else ESCOLHE) % (maximo, catalogo, tabela)}],
                     "preparo do micro doc (fotos e trilha)", limite=LIMITE, modelo="sonnet")
    plano = _json(resp) or {}
    pedidos = [f for f in (plano.get("fotos") or [])[:maximo] if f.get("busca") and f.get("nome")]
    if numeros:
        for f in pedidos:
            f["recorte"] = False
    for f in pedidos:
        f["nome"] = re.sub(r"[^a-z0-9-]+", "-", _norm(f["nome"]) or "foto").strip("-")[:30]
    # a busca na Commons é do programa; a escolha da foto certa (o contexto) é de uma chamada curta
    with ThreadPoolExecutor(4) as ex:
        achadas = list(ex.map(lambda f: busca(f["busca"]), pedidos))
    lista = "\n\n".join(f"Pedido {f['nome']} (bloco {f.get('bloco')}): {f.get('para', f['busca'])}\n" +
                        "\n".join(f"- {c['titulo']} | {c['data'] or 'sem data'} | {c['autor'][:40]}" for c in cs)
                        for f, cs in zip(pedidos, achadas) if cs)
    escolha = {}
    if lista:
        r2, _ = chamar(num, [{"type": "text", "text": CONFERE % lista}], "preparo do micro doc (confere as fotos)", limite=LIMITE, modelo="sonnet")
        escolha = _json(r2) or {}
    validos = {c["titulo"] for cs in achadas for c in cs}

    def baixa(f):
        titulo = escolha.get(f["nome"])
        if titulo not in validos:
            return None
        try:
            r = F.baixar(num, titulo, f["nome"], bool(f.get("recorte")))
            return {**r, "bloco": f.get("bloco"), "para": f.get("para", "")}
        except (Exception, SystemExit) as ex:
            return {"nome": f["nome"], "erro": str(ex)[:120]}
    # a mesma foto não vale para dois pedidos (o programa confere; a chamada às vezes escolhe a mesma)
    usados = set()
    for f in pedidos:
        if escolha.get(f["nome"]) in usados:
            escolha[f["nome"]] = None
        usados.add(escolha.get(f["nome"]))
    with ThreadPoolExecutor(4) as ex:
        fotos = [x for x in ex.map(baixa, pedidos) if x]
    # a trilha: os estilos vêm da chamada, os instantes do tempo das palavras (programa)
    dados = A.dados(num)
    partes = []
    for t in plano.get("trilha") or []:
        quando = 0.0 if not partes else _instante(dados, t.get("bloco"), t.get("palavra"))
        if quando is not None and (TR.BIB / f"{t.get('estilo')}.mp3").exists() and (not partes or quando > partes[-1][1] + 3):
            partes.append((t["estilo"], quando))
    virada = partes[1][1] if len(partes) > 1 else None
    trilha_erro = ""
    if partes:
        try:
            TR.montar(num, partes)
        except (Exception, SystemExit) as ex:
            trilha_erro, partes = str(ex)[:160], []
    feito = {"fotos": fotos, "trilha": partes, "virada": virada, "trilha_erro": trilha_erro, "segundos": round(time.time() - t0, 1),
             "quando": E.agora()}
    (pasta / "preparo.json").write_text(json.dumps(feito, ensure_ascii=False, indent=1))
    return feito


def _miniatura(arq):
    """A foto para o animador ver (jpeg pequeno; o recorte sem fundo vai sobre cinza, para ele ver o contorno)."""
    from PIL import Image
    im = Image.open(arq)
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA"); fundo = Image.new("RGB", im.size, (128, 128, 128)); fundo.paste(im, mask=im.split()[-1]); im = fundo
    im = im.convert("RGB"); im.thumbnail((480, 480))
    b = io.BytesIO(); im.save(b, "JPEG", quality=80)
    return {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": base64.b64encode(b.getvalue()).decode()}}


def pedido(num):
    p = E.pasta(num)
    try:
        feito = json.loads((p / "material/colagem/preparo.json").read_text())
    except (OSError, ValueError):
        feito = {"fotos": [], "trilha": []}
    cred = {}
    try:
        cred = json.loads((p / "material/colagem/creditos.json").read_text())
    except (OSError, ValueError):
        pass
    fotos = [f for f in feito.get("fotos") or [] if not f.get("erro")]
    numeros = E.ler_ficha(num).get("molde") == "numeros"
    txt = ["## O material já está pronto (você não busca nem roda nada)",
           "As regras do molde acima falam de buscar fotos e montar a trilha: isso o estúdio JÁ FEZ. Use o que está aqui; "
           + ("o capítulo sem foto usa outra foto que não esteja na tela antes, com tom 'cinza'." if numeros else
              "o que não tiver foto vira desenho, cartaz de texto, manchete ou mapa (as peças da colagem).")]
    if fotos:
        txt.append("\n### Fotos (com direito de uso), em const F = 'material/colagem/'")
        for f in fotos:
            nome = Path(f["arquivo"]).name; c = cred.get(nome, {})
            usar = Path(f["sem_fundo"]).name if f.get("sem_fundo") else nome
            txt.append(f"- {usar} ({f['tamanho'][0]}x{f['tamanho'][1]}; bloco {f.get('bloco')}: {f.get('para', '')}); "
                       + ("fundo: N.fundo; " if numeros else f"{'recorte sem fundo: T.colagem.recorte' if f.get('sem_fundo') else 'foto inteira: T.colagem.cartaz'}; ")
                       + f"crédito na tela: \"{c.get('autor') or 'Wikimedia Commons'} ({c.get('licenca', '')})\"")
    else:
        txt.append("\nNenhuma foto livre serviu: monte com desenho, texto e as outras peças.")
    if feito.get("trilha"):
        partes = " → ".join(f"{e} desde {t:.2f} s" for e, t in feito["trilha"])
        txt.append(f"\n### Trilha já montada (animacao/trilha.mp3): {partes}." +
                   (f" A virada é aos {feito['virada']:.2f} s: ponha T.som('impacto-doc', {feito['virada']:.2f}) e a troca do fundo ali."
                    if feito.get("virada") else ""))
    blocos = [{"type": "text", "text": "\n".join(txt)}]
    for f in fotos:
        arq = p / (f.get("sem_fundo") or f["arquivo"])
        if arq.exists():
            blocos += [{"type": "text", "text": Path(arq).name}, _miniatura(arq)]
    if numeros:
        blocos.append({"type": "text", "text": "## A peça do molde (web/pecas/numeros.js), inteira: T.numeros.<função>(o) "
                       "chama a função de mesmo nome com (cena, tl, T, o)\n" + (RAIZ / "web/pecas/numeros.js").read_text()})
        blocos.append({"type": "text", "text": "## Exemplo: a cena inteira do #368 neste molde (o vocabulário e o ritmo; a história é a do SEU roteiro)\n" +
                       (RAIZ / "regras/exemplos/numeros-368.html").read_text()})
        return blocos
    blocos.append({"type": "text", "text": "## A peça da colagem (web/pecas/colagem.js), inteira: T.colagem.<função>(o) "
                   "chama a função de mesmo nome com (cena, tl, T, o)\n" + (RAIZ / "web/pecas/colagem.js").read_text()})
    blocos.append({"type": "text", "text": "## Exemplo: a cena inteira do #367, que ele aprovou (o vocabulário, não o molde)\n" +
                   (RAIZ / "regras/exemplos/micro-doc-367.html").read_text()})
    return blocos


if __name__ == "__main__":
    import animador_novo as N
    print(json.dumps(preparar(int(sys.argv[1]), N.opus), ensure_ascii=False, indent=1))
