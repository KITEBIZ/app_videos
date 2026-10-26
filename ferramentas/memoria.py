#!/usr/bin/env python3
"""Memória da página para os agentes (24/10/2026, "isso pode fazer"; retoma o memoria-entre-videos aprovado em 23/10).
Ele: "o agente tem que conseguir saber o todo do insta. o que ja postamos a evolução" e "tem que saber qual foi o ultimo
video postado para nào repedir o cta". Programa, sem IA: lê o que o radar e o publicador já medem e escreve
radar/memoria.md (~200 palavras), que vai junto para o roteirista, o agente do chat, a legenda do post e a capa.

  radar/pagina.json             os posts lidos do Instagram (o radar), com visualizações, envios e o item do estúdio
  publicador/metricas.jsonl     uma linha "conta" por dia com os seguidores (a evolução)
  videos/<item>/ROTEIRO.md      o convite (a última fala nossa) de cada vídeo publicado; guardado em radar/convites.json,
                                que fica mesmo quando a pasta do vídeo é limpa

  python3 ferramentas/memoria.py           escreve radar/memoria.md e mostra
"""
import json, re, sys, unicodedata
from datetime import date, timedelta
from difflib import SequenceMatcher
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
META = 10000                                  # a meta de seguidores que ele deu (24/10/2026: "chegar aos 10k")


def _ler(arq, padrao):
    try:
        return json.loads(arq.read_text())
    except Exception:
        return padrao


def convite_do_roteiro(texto):
    """A última fala nossa do ROTEIRO.md (é o convite), sem o corte."""
    nossas = []
    for l in texto.splitlines():
        c = [x.strip() for x in l.strip().strip("|").split("|")]
        if len(c) >= 4 and c[0].isdigit() and c[2].lower() in ("nós", "nos", "nosso"):
            nossas.append(c[3])
    return nossas[-1] if nossas else ""


def _norm(t):
    t = "".join(ch for ch in unicodedata.normalize("NFD", t.lower()) if unicodedata.category(ch) != "Mn")
    return re.sub(r"[^a-z0-9 ]", "", re.sub(r"\s+", " ", t)).strip()


def parecido(a, b):
    """0 a 1: quanto dois convites se parecem (1 = iguais)."""
    return SequenceMatcher(None, _norm(a), _norm(b)).ratio() if a and b else 0.0


def convites(raiz=RAIZ, posts=()):
    """{item: convite} dos vídeos publicados, guardado em radar/convites.json (a pasta do vídeo pode ser limpa depois)."""
    arq = raiz / "radar/convites.json"
    cache = _ler(arq, {})
    novo = False
    for p in posts:
        it = str(p.get("item") or "")
        rot = raiz / "videos" / it / "ROTEIRO.md"
        if it and rot.exists():
            c = convite_do_roteiro(rot.read_text())
            if c and cache.get(it) != c:
                cache[it] = c; novo = True
    if novo:
        arq.write_text(json.dumps(cache, ensure_ascii=False, indent=1))
    # 24/10/2026 (roteiro-fluido): as falas nossas de cada roteiro publicado, para achar as expressões gastas
    arq_f = raiz / "radar/falas.json"
    falas = _ler(arq_f, {})
    mudou = False
    for p in posts:
        it = str(p.get("item") or "")
        rot = raiz / "videos" / it / "ROTEIRO.md"
        if it and rot.exists():
            fs = [c[3] for c in (l.strip().strip("|").split("|") for l in rot.read_text().splitlines())
                  if len(c) >= 4 and c[0].strip().isdigit() and c[2].strip().lower() in ("nós", "nos", "nosso")]
            fs = [f.strip() for f in fs]
            if fs and falas.get(it) != fs:
                falas[it] = fs; mudou = True
    if mudou:
        arq_f.write_text(json.dumps(falas, ensure_ascii=False, indent=1))
    return cache


def seguidores(raiz=RAIZ):
    """[(dia, seguidores)] em ordem, um por dia (o último medido do dia)."""
    por_dia = {}
    arq = raiz / "publicador/metricas.jsonl"
    if arq.exists():
        for l in arq.read_text().splitlines():
            try:
                d = json.loads(l)
            except Exception:
                continue
            if d.get("tipo") == "conta" and d.get("seguidores"):
                por_dia[d.get("dia") or d.get("medido", "")[:10]] = int(d["seguidores"])
    pag = _ler(raiz / "radar/pagina.json", {})
    if pag.get("seguidores"):
        por_dia[pag.get("medido", "")[:10]] = int(pag["seguidores"])
    return sorted(por_dia.items())


def _num(x):
    try:
        return float(x)
    except Exception:
        return 0.0


def dados(raiz=RAIZ):
    pag = _ler(raiz / "radar/pagina.json", {})
    posts = sorted([p for p in pag.get("posts", []) if p.get("postado")], key=lambda p: p.get("quando") or p["postado"], reverse=True)
    cv = convites(raiz, posts)
    for p in posts:
        p["convite"] = cv.get(str(p.get("item") or ""), "")
    return pag, posts, seguidores(raiz)


def montar(raiz=RAIZ):
    pag, posts, seg = dados(raiz)
    linhas = ["## Memória da página @newsbr360 (programa, sem IA; atualiza a cada leitura do radar)"]
    if seg:
        dia, agora = seg[-1]
        def em(dias):
            alvo = (date.fromisoformat(dia) - timedelta(days=dias)).isoformat()
            antes = [s for d, s in seg if d <= alvo]
            return antes[-1] if antes else None
        sem, mes = em(7), em(30)
        evol = []
        if sem: evol.append(f"{agora - sem:+d} em 7 dias")
        if mes: evol.append(f"{agora - mes:+d} em 30 dias")
        meta = f"; faltam {META - agora} para os {META // 1000} mil" if agora < META else ""
        linhas.append(f"- Seguidores: {agora} em {dia}" + (f" ({', '.join(evol)})" if evol else "") + meta + ".")
    if posts:
        u = posts[0]
        linhas.append(f"- Último vídeo postado ({u['postado']}, {u.get('tipo') or u.get('formato') or '-'}): \"{u.get('titulo') or '-'}\"; "
                      f"abriu com \"{(u.get('abertura') or '')[:110]}\"; convite: \"{u.get('convite') or '?'}\".")
        ult = [p for p in posts[1:9] if p.get("convite")]
        if ult:
            linhas.append("- Convites dos anteriores (não repita nem parafraseie): " + " | ".join(f"\"{p['convite']}\"" for p in ult[:5]) + ".")
        try:
            import fluidez
            gs = fluidez.gastas(raiz)
        except Exception:
            gs = []
        if gs:
            linhas.append("- Expressões gastas nos últimos roteiros (não use; diga de outro jeito): " + " | ".join(f'"{g}"' for g in gs) + ".")
        ab = [p.get("abertura") for p in posts[:8] if p.get("abertura")]
        if ab:
            linhas.append("- Aberturas recentes (varie o jeito de abrir): " + " | ".join(f"\"{a[:70]}\"" for a in ab[:5]) + ".")
        recentes = posts[:30]
        top = sorted(recentes, key=lambda p: _num(p.get("envios_100")), reverse=True)[:3]
        if top and _num(top[0].get("envios_100")):
            linhas.append("- Os mais compartilhados dos últimos 30 (envios por 100 visualizações): " + "; ".join(
                f"\"{p.get('titulo') or '-'}\" {_num(p.get('envios_100')):.1f} ({p.get('tipo') or p.get('formato') or '-'})" for p in top) + ".")
        vis = [_num(p.get("visualizacoes")) for p in recentes if p.get("visualizacoes")]
        if vis:
            vis.sort()
            linhas.append(f"- Mediana de visualizações dos últimos {len(vis)}: {int(vis[len(vis) // 2])}.")
    linhas.append("""
### O convite falado no fim do vídeo (a legenda do post segue a regra dela) (24/10/2026, ele: "tem que ser variavel conforme o tipo de video, mas em geral sempre pedir para
compartilhar, comentar e seguir o perfil" e "podemos pedir para seguir para chegar aos 10k")
- Sempre os três, numa ou duas frases curtas e naturais, no fim: comentar (uma pergunta que nasce da conclusão deste
  vídeo, nunca enquete de voto), compartilhar e seguir a página.
- O pedido de compartilhar tem SEMPRE um destinatário, dito do jeito deste vídeo: quem te mandou o vídeo dele, o amigo
  que acredita nisso, quem só viu a manchete, o grupo da família (24/10/2026: em 18 vídeos medidos, os com destinatário
  tiveram 1,79 envios a cada 100 visualizações contra 1,03 dos outros; envio é o sinal mais forte). Varie as palavras,
  nunca o destinatário.
- Varie pelo tipo: checagem pergunta se a pessoa já tinha visto aquilo; análise pergunta o que ela acha da conclusão;
  "fazer igual" puxa a experiência dela. Enquanto não chegar aos 10 mil, pode usar a meta ("faltam N para 10 mil").
- Nunca igual ao do último vídeo postado nem parecido com os anteriores acima: o estúdio trava o roteiro que repete.""")
    return "\n".join(linhas) + "\n"


def escrever(raiz=RAIZ):
    t = montar(raiz)
    (raiz / "radar").mkdir(exist_ok=True)
    (raiz / "radar/memoria.md").write_text(t)
    return t


def ler(raiz=RAIZ):
    """O texto da memória para o pedido de um agente; refaz se o radar ou as métricas mediram depois dela."""
    arq = raiz / "radar/memoria.md"
    fontes = [raiz / "radar/pagina.json", raiz / "publicador/metricas.jsonl"]
    if not arq.exists() or any(f.exists() and f.stat().st_mtime > arq.stat().st_mtime for f in fontes):
        try:
            return escrever(raiz)
        except Exception as ex:
            print("memória da página: não consegui montar:", ex, file=sys.stderr)
            return arq.read_text() if arq.exists() else ""
    return arq.read_text()


def repetido(convite, raiz=RAIZ, limite=.8):
    """Se o convite repete o do último vídeo postado ou se parece com os 5 anteriores: a frase do motivo; senão ''."""
    if not convite:
        return ""
    _, posts, _ = dados(raiz)
    com = [p for p in posts if p.get("convite")]
    for k, p in enumerate(com[:6]):
        r = parecido(convite, p["convite"])
        if (k == 0 and r >= .65) or r >= limite:
            onde = "do último vídeo postado" if k == 0 else f"de um vídeo de {p['postado']}"
            return f"o convite repete o {onde} (#{p.get('item')}: \"{p['convite']}\")"
    return ""


if __name__ == "__main__":
    print(escrever())
