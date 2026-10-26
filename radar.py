#!/usr/bin/env python3
"""Radar de pautas do estúdio v2 (21/10/2026, "aprovo plano radar-no-v2"; ele: "quero que o radar leia ou saiba o que é
nosso instagram, saiba quais videos publicamos e quais bombaram e consiga procurar assuntos que possam bombar tb [...]
quero que ele tenha cérebro"). Veio do radar do v1 (ferramentas/radar.py, 12/10/2026, desligado em 20/10 com o v1).

Três partes:
  1. a página (pagina): os posts da @newsbr360 pela API, com visualizações, compartilhamentos, salvamentos, curtidas,
     comentários e tempo médio assistido (insights), e, dos vídeos do estúdio, o título, o formato, a abertura e a capa;
  2. o cérebro (cerebro): uma IA barata (haiku) lê a página e o cérebro de ontem e escreve radar/cerebro.md: o que deu
     certo e o que não deu (sempre com os vídeos e os números), o que procurar hoje e que contas faltam vigiar. "Bombar"
     = compartilhamentos + salvamentos por mil seguidores, com as visualizações junto (a recomendação que ele aceitou);
  3. o radar (rodada): lê os posts das contas vigiadas pela API (business_discovery: curtidas, comentários e, nos reels,
     visualizações), acha o que sobe mais rápido que o normal de cada conta (a nota do v1), ouve os candidatos
     (áudio + transcrição, ferramentas/analisar_reel.py) e a mesma IA julga, com o cérebro, o que vira vídeo nosso.

  python3 radar.py pagina      lê a página e grava radar/pagina.json (sem IA)
  python3 radar.py cerebro     atualiza radar/cerebro.md (uma chamada à IA)
  python3 radar.py ensaio      página + cérebro + uma rodada do radar; imprime as sugestões e NÃO cria pauta
  python3 radar.py dia         página + cérebro (o servidor roda às 6h)
  python3 radar.py rodar       um lote de contas; no fim do ciclo, julga e sugere (o servidor roda a cada 40 min, 8h às 23h)
Radar leve (21/10/2026, "aprovo o plano radar-leve"; a 1ª rodada automática foi pulada com a API em 64% do limite da hora):
as contas são lidas em LOTES lotes, um a cada 40 min (cada conta continua lida a cada 2 h, sem o pico das 35 de uma vez),
com POSTS_CONTA posts cada; no fim do ciclo, os posts de todos os lotes são pontuados, ouvidos e julgados.
Pauta sugerida (21/10/2026, fase 2): nasce na etapa Pauta parada em "sugerida pelo radar", esperando ele tocar em "Fazer
esta pauta" (aí o estúdio analisa e escreve o roteiro, como um link colado) ou "Descartar" (vai à lixeira). As decisões
vão para radar/decisoes.json e o cérebro do dia seguinte as lê. Travas: no máximo SUGESTOES_DIA pautas por dia, nenhum
link repetido (radar/sugeridos.json) e o gasto do radar parado em TETO_DIA US$ por dia. Aviso no WhatsApp dele
(ferramentas/avisar.py: o destino é fixo, só o número dele).
Contas vigiadas: radar/contas.json (a lista do v1; lado esquerda | imprensa | direita, a direita só para comparação).
"""
import fcntl, json, math, re, statistics, subprocess, sys, time, urllib.error
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
sys.path[:0] = [str(RAIZ), str(RAIZ / "ferramentas"), str(RAIZ / "publicador")]
import estudio as E
import os
if os.environ.get("RADAR_VIDEOS"):          # o ensaio roda numa cópia do código e só lê os vídeos de verdade
    E.VIDEOS = Path(os.environ["RADAR_VIDEOS"])

D = RAIZ / "radar"
CONTAS, HIST, SAIDA = D / "contas.json", D / "historico.json", D / "radar.json"
PAGINA, CEREBRO, GASTO = D / "pagina.json", D / "cerebro.md", D / "gasto.jsonl"
TRAVA = Path("/tmp/radar-v2.lock")
BRT = timezone(timedelta(hours=-3))
JANELA_H = 48              # só posts das últimas 48 h
POSTS_CONTA = 8            # posts lidos por conta (20 gastava ~80% do limite da hora do app, 12/10; 15 até 21/10)
LOTES = 3                  # as contas em 3 lotes, um a cada 40 min (radar-leve, 21/10/2026)
LOTE, POSTS = D / "lote.json", D / "posts.json"
CANDIDATOS = 18            # os mais rápidos, ouvidos e julgados
USO_MAXIMO = 50            # % do limite da hora do app: acima disso a rodada espera a próxima (era 15, do desenho de 35
                           # contas de uma vez; um lote de 12 deixa ~20% e o lote 2 era sempre pulado: radar-leve.1, 22/10)
MODELO = "haiku"           # a IA barata do cérebro e do julgamento (na assinatura)
SUGESTOES_DIA = 3          # pautas sugeridas por dia, no máximo
TETO_DIA = 2.0             # US$ por dia do radar (cérebro + julgamentos); passou, não julga mais naquele dia
SUGERIDA = "sugerida pelo radar"
CONTA_NOSSA = "newsbr360"
SUGERIDOS, DECISOES = D / "sugeridos.json", D / "decisoes.json"
ESTUDIO = "https://admin.newsbr360.com/#/item/"
CAMPOS = "id,caption,like_count,comments_count,view_count,timestamp,permalink,media_type,media_product_type"


def ler(p, padrao):
    try:
        return json.loads(p.read_text())
    except Exception:
        return padrao


def gravar(p, d, indent=None):
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".tmp")
    tmp.write_text(json.dumps(d, ensure_ascii=False, indent=indent) if not isinstance(d, str) else d)
    tmp.replace(p)


def ts(t):
    return datetime.strptime(t, "%Y-%m-%dT%H:%M:%S%z").timestamp()


def codigo(link):
    m = re.search(r"/(?:reels?|p)/([\w-]+)", link)
    return m.group(1) if m else ""


def ia(blocos, quem, limite=240):
    """Uma chamada à IA barata, sem ferramentas. Guarda a resposta em radar/chamadas/ e o gasto em radar/gasto.jsonl."""
    reg = D / "chamadas" / f"{time.strftime('%Y%m%d-%H%M%S')}-{quem}.jsonl"
    reg.parent.mkdir(parents=True, exist_ok=True)
    import ia                                 # 25/10/2026: a chamada de IA de um lugar só (ia.py)
    texto, uso = ia.chamar(blocos, quem, MODELO, limite=limite, cwd=D, registro=reg)
    with GASTO.open("a") as f:
        f.write(json.dumps({"quando": E.agora(), "quem": quem, "modelo": MODELO, "usd": uso["usd"]}) + "\n")
    return texto, uso["usd"] or 0


def _json(texto):
    m = re.search(r"\{.*\}|\[.*\]", texto or "", re.S)
    if not m:
        return None
    for t in (m.group(0), re.sub(r",\s*([}\]])", r"\1", m.group(0))):
        try:
            return json.loads(t)
        except ValueError:
            pass
    return None


# ---------- 1. a página ----------

def pagina(limite=80):
    """Os posts da @newsbr360 com os números (insights) e, quando o vídeo é do estúdio, título, formato, abertura e capa."""
    import comentarios as C
    t, ig = C.acesso()
    eu = C.get(ig, t, fields="username,followers_count,media_count")
    posts, depois = [], None
    while len(posts) < limite:
        q = dict(fields="id,permalink,timestamp,caption,media_type,media_product_type,like_count,comments_count", limit=50)
        if depois:
            q["after"] = depois
        r = C.get(f"{ig}/media", t, **q)
        posts += r.get("data", [])
        depois = (r.get("paging") or {}).get("cursors", {}).get("after")
        if not depois or not r.get("data"):
            break
    estudio = {}
    for n in E.numeros():
        f = E.ler_ficha(n)
        link = ((f.get("publicado") or {}).get("instagram") or "").rstrip("/") + "/"
        if codigo(link):
            estudio[codigo(link)] = n

    def numeros(m):
        try:
            v = {x["name"]: x["values"][0]["value"] for x in C.get(f"{m['id']}/insights", t,
                 metric="views,reach,shares,saved,ig_reels_avg_watch_time")["data"]}
        except Exception:
            v = {}
        # 22/10/2026 (fluxo-viral-util): % de quem pula nos 3 primeiros segundos (reels_skip_rate, só Reels, desde
        # 03/12/2025; a Meta diz "estimada e em desenvolvimento"). Chamada à parte: se falhar, o resto não se perde
        try:
            v.update({x["name"]: x["values"][0]["value"] for x in C.get(f"{m['id']}/insights", t, metric="reels_skip_rate")["data"]})
        except Exception:
            pass
        return m, v

    with ThreadPoolExecutor(4) as pool:
        lidos = list(pool.map(numeros, posts[:limite]))
    saida = []
    for m, v in lidos:
        n = estudio.get(codigo(m.get("permalink", "")))
        item = {}
        if n:
            f = E.ler_ficha(n); bs = E.blocos(n)
            item = {"item": n, "titulo": f.get("titulo"), "tipo": E.TIPOS.get(f.get("tipo"), f.get("tipo")), "formato": f.get("formato"),
                    "molde": f.get("molde"), "abertura": (bs[0].get("fala") if bs else "")[:200],
                    "capa": (f.get("capa") or {}).get("frase", ""), "capa_jpg": str(E.pasta(n) / "publicacao/capa.jpg"),
                    "nicho": f.get("nicho"), "gancho_familia": f.get("gancho_familia")}
        saida.append({"link": m.get("permalink"), "postado": datetime.fromtimestamp(ts(m["timestamp"]), BRT).strftime("%Y-%m-%d"),
                      "quando": datetime.fromtimestamp(ts(m["timestamp"]), BRT).isoformat(timespec="minutes"),
                      "tipo": m.get("media_product_type") or m.get("media_type"), "legenda": (m.get("caption") or "")[:300],
                      "curtidas": m.get("like_count"), "comentarios": m.get("comments_count"),
                      "visualizacoes": v.get("views"), "alcance": v.get("reach"), "compartilhamentos": v.get("shares"),
                      "salvamentos": v.get("saved"), "tempo_medio_s": round((v.get("ig_reels_avg_watch_time") or 0) / 1000, 1),
                      "pula_3s": v.get("reels_skip_rate"), **item})
    seg = eu.get("followers_count") or 1
    for p in saida:      # "bombar": compartilhamentos + salvamentos por mil seguidores
        p["forca"] = round(1000 * ((p["compartilhamentos"] or 0) + (p["salvamentos"] or 0)) / seg, 2)
        # 22/10/2026 ("aprovo o plano fluxo-viral-util"): envios a cada 100 visualizações, o que mais diz se o vídeo se
        # espalha (mede o vídeo, não o tamanho da página)
        p["envios_100"] = round(100 * (p["compartilhamentos"] or 0) / p["visualizacoes"], 2) if p.get("visualizacoes") else None
    r = {"medido": E.agora(), "conta": eu.get("username"), "seguidores": seg, "posts_na_conta": eu.get("media_count"),
         "lidos": len(saida), "posts": saida, "mediana": medianas(saida)}
    gravar(PAGINA, r, 1)
    return r


def medianas(posts, n=30):
    """A mediana da página nos últimos n posts: visualizações e envios a cada 100 (a régua do "acima do normal")."""
    import statistics
    ps = [p for p in posts if p.get("visualizacoes")][:n]
    if not ps:
        return {}
    pulos = [p["pula_3s"] for p in ps if p.get("pula_3s") is not None]
    return {"visualizacoes": statistics.median(p["visualizacoes"] for p in ps),
            "envios_100": statistics.median(p["envios_100"] or 0 for p in ps),
            "pula_3s": statistics.median(pulos) if pulos else None, "posts": len(ps)}


# ---------- 1b. a parte 2 dos nossos vídeos que estouram (22/10/2026, "aprovo o plano fluxo-viral-util") ----------
# o curso Fluxo Viral (RT17): reel acima de 2x a mediana do perfil pede parte 2 ou variação em até 48 h

PARTE2_FATOR = 2.0
PARTE2_HORAS = 48
PARTE2_DIA = 1

PEDIDO_PARTE2 = """Você é o radar de pautas da @newsbr360 (checagem de fatos sobre política, com documento). O vídeo abaixo, NOSSO,
foi muito acima do normal da página. Proponha a PARTE 2: um vídeo novo que continua o assunto enquanto ele está quente.
Caminhos bons: uma fala nova da mesma pessoa sobre o mesmo tema; o desdobramento (o que aconteceu depois, a resposta de
alguém, um documento novo); a afirmação que ficou de fora do primeiro. Nada de repetir o mesmo vídeo. Use só o que está
abaixo e diga o que precisa ser achado e provado.
Responda SÓ um JSON: {{"titulo": "até 8 palavras", "angulo": "a ideia da parte 2 em uma frase", "porque": "por que pode
render, comparando com o primeiro", "buscar": "o que achar (fala, documento, notícia) e onde", "formato": "Fomos conferir ou Análise"}}

O vídeo #{num}: {titulo} · publicado em {postado} · {visualizacoes} visualizações ({fator}x a mediana) · {envios} envios a cada 100
Roteiro:
{roteiro}
Checagem:
{checagem}
"""


def parte2(agora=None):
    """Os vídeos nossos das últimas PARTE2_HORAS acima de PARTE2_FATOR vezes a mediana (em visualizações ou em envios a
    cada 100) viram pauta sugerida "Parte 2", que espera ele decidir como as outras. Uma por dia, uma por vídeo."""
    pag = ler(PAGINA, {})
    agora = agora or datetime.now(BRT)
    med = pag.get("mediana") or medianas(pag.get("posts") or [])
    if not med:
        return []
    sug = ler(SUGERIDOS, {})
    hoje = agora.strftime("%Y-%m-%d")
    if sum(1 for k, v in sug.items() if k.startswith("parte2-") and v.get("quando", "")[:10] == hoje) >= PARTE2_DIA:
        return []
    criados, fila = [], []
    for p in pag.get("posts") or []:
        n = p.get("item")
        quando = p.get("quando") or (p.get("postado", "") + "T12:00-03:00")
        if not n or not p.get("visualizacoes") or f"parte2-{n}" in sug:
            continue
        idade_h = (agora - datetime.fromisoformat(quando)).total_seconds() / 3600
        if not 0 <= idade_h <= PARTE2_HORAS:
            continue
        fv = p["visualizacoes"] / max(1, med["visualizacoes"])
        fe = (p.get("envios_100") or 0) / max(.01, med["envios_100"] or .01)
        if max(fv, fe) >= PARTE2_FATOR and p["visualizacoes"] >= med["visualizacoes"]:
            fila.append((max(fv, fe), fv, fe, n, p))
    # o mais forte primeiro (calibração de 22/10: em 20/10 o #305, raspando 2,0x, passava na frente do #301, 86x)
    for _, fv, fe, n, p in sorted(fila, key=lambda x: -x[0]):
        pasta = E.pasta(n)
        ler_ = lambda a: (pasta / a).read_text()[:6000] if (pasta / a).exists() else "(não há)"
        texto, usd = ia([{"type": "text", "text": PEDIDO_PARTE2.format(num=n, titulo=p.get("titulo") or "", postado=p.get("postado"),
                          visualizacoes=p["visualizacoes"], fator=round(fv, 1), envios=p.get("envios_100"),
                          roteiro=ler_("ROTEIRO.md"), checagem=ler_("CHECAGEM.md"))}], f"parte2-{n}")
        j = _json(texto) or {}
        if not j.get("titulo"):
            continue
        ideia = (f"Parte 2 do #{n} ({p.get('titulo')}), sugerida pelo radar: o #{n} teve {p['visualizacoes']} visualizações, "
                 f"{fv:.1f}x a mediana da página, e {p.get('envios_100')} envios a cada 100 (mediana {med['envios_100']}). "
                 f"Ângulo: {j.get('angulo', '')} Buscar: {j.get('buscar', '')} Formato sugerido: {j.get('formato', '')}.")
        num, _ = E.criar_item("ideia", link="", texto=ideia, id_msg=f"radar-parte2-{n}")
        E.mexe_ficha(num, titulo=j["titulo"][:90], passo=SUGERIDA, passo_desde=E.agora(), esperando="Fazer esta pauta?", parte2_de=n,
                     radar={"conta": CONTA_NOSSA, "quem": f"parte 2 do #{n}", "fator": round(max(fv, fe), 1), "nota": None,
                            "porque": j.get("porque"), "prova": j.get("buscar"), "formato": j.get("formato"), "parecido_com": f"#{n}",
                            "medido": pag.get("medido")})
        E.evento(num, f"sugerida pelo radar: parte 2 do #{n} ({fv:.1f}x a mediana em visualizações, {fe:.1f}x em envios)")
        sug[f"parte2-{n}"] = {"quando": agora.isoformat(timespec="seconds"), "num": num, "titulo": j["titulo"]}
        criados.append(num)
        try:
            import avisar
            avisar.avisar(f"NewsBR360 · o #{n} está {fv:.0f}x acima do normal: o radar sugeriu a parte 2, {j['titulo']}. "
                          f"Faça ou descarte no estúdio: {ESTUDIO}{num}")
        except Exception as e:
            E.evento(num, f"aviso da parte 2 no WhatsApp não saiu: {str(e)[:120]}")
        break                                            # uma por dia
    gravar(SUGERIDOS, sug, 1)
    return criados


# ---------- 2. o cérebro ----------

PEDIDO_CEREBRO = """Você é o cérebro do radar de pautas da página @newsbr360 (Instagram, checagem de fatos sobre política, com vídeos
curtos). Seu trabalho: olhar os números da própria página e escrever o que dá certo e o que não dá, para o radar saber o
que procurar nas outras contas e nas notícias.

## Quem é a página (regras do estúdio)
{identidade}

## Os posts da página, do mais recente ao mais antigo
"força" = compartilhamentos + salvamentos por mil seguidores (o que mais faz o Instagram mostrar a quem não segue);
visualizações junto. Média da página: força {media_forca}, visualizações {media_vis}. Seguidores: {seguidores}.
"envios/100" = compartilhamentos a cada 100 visualizações: mede o VÍDEO (se ele se espalha), não o tamanho da página; é o
número principal para comparar um vídeo com outro. "% pula nos 3 s" = quem saiu antes de 3 s (a Meta diz que é estimado).
"gancho <família>" = o molde da primeira frase (regras/GANCHOS.md). Quando houver vídeos com família anotada, diga qual
família rende mais em envios/100, com quantos vídeos de cada (pouca amostra é pouca amostra).
{tabela}

## O cérebro de ontem (atualize; não comece do zero)
{anterior}

## As decisões dele sobre pautas sugeridas pelo radar
{decisoes}

Escreva o cérebro novo em português, em Markdown, com estas seções e nada mais:
# Cérebro do radar · {hoje}
## O que deu certo
## O que não deu
## O que procurar hoje
## Contas que faltam vigiar
## O que mudou desde ontem
Regras: todo "deu certo" ou "não deu" cita os vídeos (data e título ou legenda curta) e os números; sem isso, não entra.
Diga quantos vídeos sustentam cada ponto ("3 vídeos"); com 1 ou 2, escreva "pouca amostra". Não invente número. Em "O que
procurar hoje": assuntos, pessoas e tipos de fala concretos (ex.: "promessa antiga de político que dá para comparar com
o que fez"), no máximo 8 linhas. Em "Contas que faltam vigiar": só @ que apareceram nos posts ou nas notícias, com o
porquê. Até 600 palavras."""


def cerebro():
    """O cérebro do dia: a IA lê a página, as capas dos 5 mais fortes e dos 3 mais fracos e o cérebro de ontem."""
    pg = ler(PAGINA, None) or pagina()
    ps = pg["posts"]
    forcas = [p["forca"] for p in ps if p.get("forca") is not None]
    vis = [p["visualizacoes"] for p in ps if p.get("visualizacoes")]
    linha = lambda p: (f"- {p['postado']} · {p.get('tipo')} · força {p['forca']} · {p.get('visualizacoes') or '?'} vis · "
                       f"{p.get('compartilhamentos') or 0} comp · {p.get('salvamentos') or 0} salv · {p.get('curtidas') or 0} curt · "
                       f"{p.get('tempo_medio_s') or '?'} s assistidos"
                       # fluxo-viral-util (22/10/2026): envios a cada 100 visualizações, % que pula nos 3 s e a família do gancho
                       + (f" · {p['envios_100']} envios/100" if p.get("envios_100") is not None else "")
                       + (f" · {p['pula_3s']}% pula nos 3 s" if p.get("pula_3s") is not None else "")
                       + (f" · gancho {p['gancho_familia']}" if p.get("gancho_familia") else "")
                       + (f" · estúdio #{p['item']}: \"{p.get('titulo')}\" ({p.get('tipo') or ''}{', molde ' + p['molde'] if p.get('molde') else ''}); "
                          f"abre com \"{p.get('abertura')}\"; capa \"{p.get('capa')}\"" if p.get("item") else
                          f" · legenda: \"{re.sub(r'\s+', ' ', p.get('legenda') or '')[:160]}\""))
    identidade = "\n".join((E.RAIZ / "regras" / n).read_text()[:2500] for n in ("IDENTIDADE.md", "PUBLICO.md") if (E.RAIZ / "regras" / n).exists())
    decisoes = ler(D / "decisoes.json", [])
    texto = PEDIDO_CEREBRO.format(identidade=identidade, media_forca=round(statistics.median(forcas), 2) if forcas else "?",
                                  media_vis=int(statistics.median(vis)) if vis else "?", seguidores=pg["seguidores"],
                                  tabela="\n".join(linha(p) for p in ps), hoje=datetime.now(BRT).strftime("%d/%m/%Y"),
                                  anterior=CEREBRO.read_text() if CEREBRO.exists() else "(primeiro dia: não há)",
                                  decisoes="\n".join(f"- {d['quando'][:10]} · {d['decisao']} · {d['titulo']} · {d.get('porque', '')}"
                                                     for d in decisoes[-30:]) or "(nenhuma ainda)")
    blocos = [{"type": "text", "text": texto}]
    com_capa = [p for p in ps if p.get("capa_jpg") and Path(p["capa_jpg"]).exists()]
    for p in sorted(com_capa, key=lambda p: -p["forca"])[:5] + sorted(com_capa, key=lambda p: p["forca"])[:3]:
        import base64
        blocos += [{"type": "text", "text": f"Capa do vídeo de {p['postado']} (\"{p.get('titulo')}\", força {p['forca']}):"},
                   {"type": "image", "source": {"type": "base64", "media_type": "image/jpeg",
                                                "data": base64.b64encode(Path(p["capa_jpg"]).read_bytes()).decode()}}]
    novo, usd = ia(blocos, "cerebro")
    if not novo.startswith("#"):
        raise RuntimeError("o cérebro não veio: " + novo[:200])
    if CEREBRO.exists():
        (D / "cerebros").mkdir(exist_ok=True)
        CEREBRO.replace(D / "cerebros" / f"cerebro-{time.strftime('%Y%m%d-%H%M')}.md")
    gravar(CEREBRO, novo + "\n")
    return novo, usd


# ---------- 3. o radar ----------

def uso_api(c, t, ig):
    """Quanto (em %) do limite da hora do app já foi gasto (cabeçalho x-app-usage; 12/10: o que pega é o total_time)."""
    import urllib.request
    url = c.API + ig + "?fields=business_discovery.username(newsbr360){followers_count}&access_token=" + t
    try:
        with urllib.request.urlopen(url, timeout=30) as r:
            u = json.loads(r.headers.get("x-app-usage") or "{}")
    except urllib.error.HTTPError as e:
        u = json.loads(e.headers.get("x-app-usage") or "{}") or {"erro": 100}
    except Exception:
        u = {}
    return max(u.values(), default=0)


def coletar(contas=None):
    import comentarios as c
    t, ig = c.acesso()
    uso = uso_api(c, t, ig)
    if uso >= USO_MAXIMO:
        return [], {}, [f"API já em {uso}% do limite da hora do app: radar pulado (volta na próxima rodada)"]
    posts, contas_ok, falhas, limite = [], {}, [], []

    def uma(x):
        if limite:
            return x, None, "pulada: limite de chamadas da API"
        erro = {}
        for n in (POSTS_CONTA, 5):       # 21/10: três contas pediram "reduce the amount of data"; com 5 posts, lê
            try:
                q = f"business_discovery.username({x['username']}){{username,name,followers_count,media.limit({n}){{{CAMPOS}}}}}"
                return x, c.get(ig, t, fields=q)["business_discovery"], None
            except urllib.error.HTTPError as e:
                erro = json.loads(e.read() or b"{}").get("error", {})
                if erro.get("code") in (4, 17, 32, 613):      # 12/10: três rodadas seguidas estouraram o limite do app
                    limite.append(1)
                    break
                if "reduce the amount of data" not in str(erro.get("message", "")):
                    break
            except Exception as e:
                return x, None, str(e)[:90]
        return x, None, str(erro.get("message", "erro da API"))[:90]

    with ThreadPoolExecutor(6) as pool:
        for x, bd, erro in pool.map(uma, ler(CONTAS, {}).get("contas", []) if contas is None else contas):
            if erro:
                falhas.append(f"@{x['username']}: {erro}")
                continue
            contas_ok[x["username"]] = bd.get("followers_count")
            for m in bd.get("media", {}).get("data", []):
                posts.append(dict(m, origem=x["username"], quem=x["nome"], lado=x["lado"], seguidores=bd.get("followers_count")))
    return posts, contas_ok, falhas


def pontuar(posts):
    """A nota do v1: velocidade (curtidas + comentários por hora, entre rodadas quando há a anterior) sobre o ritmo típico
    da própria conta; nota = fator x log10(10 + velocidade). Um post 5x acima do normal de conta média passa à frente."""
    agora = time.time()
    hist = ler(HIST, {})
    por_origem = {}
    for m in posts:
        m["inter"] = int(m.get("like_count") or 0) + int(m.get("comments_count") or 0)
        m["idade_h"] = max(0.5, (agora - ts(m["timestamp"])) / 3600)
        por_origem.setdefault(m["origem"], []).append(m)
    tipico = {}
    for o, ms in por_origem.items():
        velhos = [m["inter"] for m in ms if m["idade_h"] >= 24]
        tipico[o] = max(1.0, statistics.median(velhos) / 24 if len(velhos) >= 3 else statistics.median(m["inter"] / m["idade_h"] for m in ms))
    vistos, saida = set(), []
    for m in posts:
        link = m.get("permalink", "").rstrip("/") + "/"
        if not link.startswith("https://") or link in vistos or m["idade_h"] > JANELA_H:
            continue
        vistos.add(link)
        h = hist.setdefault(link, {"pub": ts(m["timestamp"]), "s": []})
        anterior = next((s for s in reversed(h["s"]) if 0.5 <= (agora - s[0]) / 3600 <= 8), None)
        vel = max(0.0, (m["inter"] - anterior[1] - anterior[2]) / ((agora - anterior[0]) / 3600)) if anterior else m["inter"] / m["idade_h"]
        h["s"] = (h["s"] + [[round(agora), int(m.get("like_count") or 0), int(m.get("comments_count") or 0), int(m.get("view_count") or -1)]])[-30:]
        fator = vel / tipico[m["origem"]]
        saida.append({"quem": m["quem"], "conta": m["origem"], "lado": m["lado"], "seguidores": m.get("seguidores"), "link": link,
                      "codigo": codigo(link), "video": m.get("media_type") == "VIDEO",
                      "postado": datetime.fromtimestamp(ts(m["timestamp"]), BRT).strftime("%Y-%m-%d %H:%M"),
                      "idade_h": round(m["idade_h"], 1), "interacoes": m["inter"],
                      "visualizacoes": int(m["view_count"]) if m.get("view_count") is not None else -1,
                      "vel_h": round(vel), "fator": round(fator, 1), "nota": round(fator * math.log10(10 + vel), 2),
                      "legenda": (m.get("caption") or "")[:600]})
    for k in [k for k, v in hist.items() if agora - v["pub"] > 72 * 3600]:
        del hist[k]
    gravar(HIST, hist)
    return saida


def candidatos(lista):
    """Os mais rápidos (sem a direita, sem barulho pequeno, até 3 por conta)."""
    out, por_conta = [], {}
    for p in sorted(lista, key=lambda p: -p["nota"]):
        if p["lado"] == "direita" or p["interacoes"] < 200 or p["vel_h"] < 20 or por_conta.get(p["conta"], 0) >= 3:
            continue
        por_conta[p["conta"]] = por_conta.get(p["conta"], 0) + 1
        out.append(p)
        if len(out) == CANDIDATOS:
            break
    return out


def ouvir(posts):
    """Vídeo ainda não ouvido: ferramentas/analisar_reel.py (só áudio + transcrição, em referencias/<código>/, não repete)."""
    for p in posts:
        trans = RAIZ / "referencias" / p["codigo"] / "transcricao.txt"
        if p["video"] and p["codigo"] and not trans.exists():
            try:
                subprocess.run([sys.executable, str(RAIZ / "ferramentas/analisar_reel.py"), p["link"]], capture_output=True,
                               text=True, cwd=RAIZ, timeout=300)
            except Exception as e:
                print(f"{p['codigo']}: não consegui ouvir ({str(e)[:100]})")
        p["fala"] = " ".join(re.sub(r"^\d+:\d+\s+", "", l) for l in trans.read_text().splitlines())[:1200] if trans.exists() else ""


PEDIDO_JULGAR = """Você é o radar de pautas da @newsbr360. Abaixo, o cérebro (o que dá certo e o que não dá na nossa página) e os
posts que estão subindo agora em outras contas. Para cada post, decida se ele pode virar um vídeo NOSSO, no nosso estilo.

## O cérebro
{cerebro}

## Nossos formatos
- Fomos conferir: alguém público disse algo; mostramos a fala dele e conferimos nas fontes (selo do resultado).
- Analisar a fala: explicamos com provas o que está por trás de uma fala ou de um fato.
- Fazer igual: refazemos no nosso estilo um vídeo que bombou (mesma ideia, nossas provas).
Só vale se der para PROVAR com documento, vídeo antigo, dado oficial ou matéria de veículo grande.

## Vídeos que já fizemos (não repetir o mesmo assunto da mesma pessoa)
{feitos}

## Posts subindo agora
{posts}

Responda SÓ um JSON, sem cercas: {{"posts": [{{"n": <número do post>, "vira_video": true|false, "nota": <0 a 10>,
"formato": "Fomos conferir|Analisar a fala|Fazer igual", "titulo": "<título da pauta, até 70 letras>",
"porque": "<por que pode bombar, citando o cérebro, uma frase>", "prova": "<onde provar, uma frase>",
"parecido_com": "<nosso vídeo mais parecido, ou vazio>"}}]}}. nota 7 ou mais só quando tem afirmação checável, prova
provável e combina com o que o cérebro diz que dá certo. Nunca invente fato que o post não tenha."""


def julgar(cands):
    cer = CEREBRO.read_text() if CEREBRO.exists() else "(ainda não há cérebro)"
    feitos = "\n".join(f"- #{n} {E.ler_ficha(n).get('titulo')}" for n in E.numeros()[-40:] if E.ler_ficha(n).get("titulo"))
    posts = "\n".join(f"{i}. @{p['conta']} ({p['quem']}, {p['lado']}) · {p['postado']} · {p['fator']}x o normal · "
                      f"{p['interacoes']} interações{(' · ' + str(p['visualizacoes']) + ' vis') if p['visualizacoes'] >= 0 else ''}\n"
                      f"   legenda: {re.sub(r'\s+', ' ', p['legenda'])[:300]}\n   fala: {p.get('fala', '')[:600] or '(sem fala)'}"
                      for i, p in enumerate(cands, 1))
    texto, usd = ia([{"type": "text", "text": PEDIDO_JULGAR.format(cerebro=cer, feitos=feitos or "(nenhum)", posts=posts)}], "julgar")
    d = _json(texto) or {}
    for j in d.get("posts", []) if isinstance(d, dict) else []:
        try:
            cands[int(j["n"]) - 1]["juizo"] = j
        except (KeyError, ValueError, IndexError, TypeError):
            pass
    return usd


def _falhou(msg):
    """A rodada não saiu: grava a hora mesmo assim (o servidor só tenta de novo dali a 2 h) e devolve o erro."""
    r = {"medido": datetime.now(BRT).strftime("%Y-%m-%d %H:%M"), "erro": msg, "candidatos": [], "sugestoes": []}
    gravar(SAIDA, r, 1)
    return r


def gasto_hoje():
    hoje = datetime.now(BRT).strftime("%Y-%m-%d")
    return sum(x.get("usd") or 0 for x in (json.loads(l) for l in GASTO.read_text().splitlines() if l.strip())
               if x.get("quando", "")[:10] == hoje) if GASTO.exists() else 0.0


def rodada():
    t0 = time.time()
    if gasto_hoje() >= TETO_DIA:
        return _falhou(f"o radar já gastou US$ {gasto_hoje():.2f} hoje (teto US$ {TETO_DIA:.2f}): rodada pulada")
    posts, contas_ok, falhas = coletar()
    total = len(ler(CONTAS, {}).get("contas", []))
    if len(contas_ok) < total / 2:
        return _falhou(f"só {len(contas_ok)} de {total} contas lidas ({'; '.join(falhas)[:200]})")
    lista = pontuar(posts)
    cands = candidatos(lista)
    ouvir(cands)
    usd = julgar(cands)
    sugestoes = sorted((p for p in cands if (p.get("juizo") or {}).get("vira_video") and (p["juizo"].get("nota") or 0) >= 7),
                       key=lambda p: -p["juizo"]["nota"])[:3]
    r = {"medido": datetime.now(BRT).strftime("%Y-%m-%d %H:%M"), "segundos": round(time.time() - t0), "contas_lidas": len(contas_ok),
         "posts_48h": len(lista), "falhas": falhas, "usd_julgar": usd,
         "candidatos": [{k: p.get(k) for k in ("conta", "quem", "link", "fator", "vel_h", "interacoes", "visualizacoes", "juizo")} for p in cands],
         "sugestoes": [{k: p.get(k) for k in ("conta", "quem", "link", "fator", "interacoes", "visualizacoes", "juizo")} for p in sugestoes]}
    gravar(SAIDA, r, 1)
    return r


def rodar_lote():
    """Um lote de contas (radar-leve). Guarda os posts lidos em radar/posts.json; quando o ciclo fecha (todos os lotes
    lidos), pontua, ouve, julga e devolve o resultado como a rodada; antes disso, {"lote": i}."""
    est = ler(LOTE, {"i": 0})
    contas = ler(CONTAS, {}).get("contas", [])
    n = math.ceil(len(contas) / LOTES)
    i = est.get("i", 0) % LOTES
    lote = contas[i * n:(i + 1) * n]
    posts, contas_ok, falhas = coletar(lote)
    if lote and len(contas_ok) < len(lote) / 2:
        gravar(LOTE, {"i": i, "quando": time.time(), "erro": "; ".join(falhas)[:200]}, 1)
        return {"erro": f"lote {i + 1}: só {len(contas_ok)} de {len(lote)} contas lidas ({'; '.join(falhas)[:200]})"}
    cache = ler(POSTS, {})
    for x in lote:
        if x["username"] in contas_ok:
            cache[x["username"]] = {"quando": time.time(), "posts": [p for p in posts if p["origem"] == x["username"]]}
    gravar(POSTS, cache)
    gravar(LOTE, {"i": (i + 1) % LOTES, "quando": time.time(), "falhas": falhas}, 1)
    if (i + 1) % LOTES:
        return {"lote": i + 1, "contas_lidas": len(contas_ok), "falhas": falhas}
    t0 = time.time()
    if gasto_hoje() >= TETO_DIA:
        return _falhou(f"o radar já gastou US$ {gasto_hoje():.2f} hoje (teto US$ {TETO_DIA:.2f}): julgamento pulado")
    todos = [p for v in cache.values() if time.time() - v["quando"] < 3 * 3600 for p in v["posts"]]
    lista = pontuar(todos)
    cands = candidatos(lista)
    ouvir(cands)
    usd = julgar(cands)
    sugestoes = sorted((p for p in cands if (p.get("juizo") or {}).get("vira_video") and (p["juizo"].get("nota") or 0) >= 7),
                       key=lambda p: -p["juizo"]["nota"])[:3]
    r = {"medido": datetime.now(BRT).strftime("%Y-%m-%d %H:%M"), "segundos": round(time.time() - t0),
         "contas_lidas": sum(1 for v in cache.values() if time.time() - v["quando"] < 3 * 3600), "posts_48h": len(lista),
         "falhas": falhas, "usd_julgar": usd,
         "candidatos": [{k: p.get(k) for k in ("conta", "quem", "link", "fator", "vel_h", "interacoes", "visualizacoes", "juizo")} for p in cands],
         "sugestoes": [{k: p.get(k) for k in ("conta", "quem", "link", "fator", "interacoes", "visualizacoes", "juizo")} for p in sugestoes]}
    gravar(SAIDA, r, 1)
    return r


def sugerir(r):
    """As pautas sugeridas da rodada: até SUGESTOES_DIA por dia, sem link que já é item ou já foi sugerido. Devolve os
    números criados."""
    sug = ler(SUGERIDOS, {})
    hoje = datetime.now(BRT).strftime("%Y-%m-%d")
    feitos_hoje = sum(1 for v in sug.values() if v.get("quando", "")[:10] == hoje)
    ja = set(sug) | {codigo(E.ler_ficha(n).get("link") or "") for n in E.numeros()}
    criados = []
    for p in r.get("sugestoes", []):
        if feitos_hoje + len(criados) >= SUGESTOES_DIA:
            break
        c = codigo(p["link"])
        if not c or c in ja:
            continue
        j = p["juizo"]
        texto = (f"Sugerida pelo radar ({r['medido']}): @{p['conta']} ({p['quem']}), {p['fator']}x o normal da conta. "
                 f"{j.get('titulo', '')}. Por que pode bombar: {j.get('porque', '')} Onde provar: {j.get('prova', '')} "
                 f"Formato sugerido: {j.get('formato', '')}.")
        num, _ = E.criar_item("analisar", link=p["link"], texto=texto, id_msg=f"radar-{c}")
        E.mexe_ficha(num, titulo=j.get("titulo", "")[:90], passo=SUGERIDA, passo_desde=E.agora(), esperando="Fazer esta pauta?",
                     radar={"conta": p["conta"], "quem": p["quem"], "fator": p["fator"], "nota": j.get("nota"), "porque": j.get("porque"),
                            "prova": j.get("prova"), "formato": j.get("formato"), "parecido_com": j.get("parecido_com"), "medido": r["medido"]})
        E.evento(num, f"sugerida pelo radar (nota {j.get('nota')}): {j.get('titulo', '')}")
        sug[c] = {"quando": E.agora(), "num": num, "titulo": j.get("titulo", "")}
        criados.append(num)
        try:
            import avisar
            avisar.avisar(f"NewsBR360 · o radar sugeriu uma pauta: {j.get('titulo', '')} (@{p['conta']}, nota {j.get('nota')}). "
                          f"{j.get('porque', '')[:160]} Faça ou descarte no estúdio: {ESTUDIO}{num}")
        except Exception as e:
            E.evento(num, f"aviso do radar no WhatsApp não saiu: {str(e)[:120]}")
    gravar(SUGERIDOS, sug, 1)
    return criados


def decidir(num, decisao, motivo=""):
    """Ele fez ou descartou uma pauta sugerida: vai para radar/decisoes.json (o cérebro do dia seguinte lê)."""
    f = E.ler_ficha(num)
    d = ler(DECISOES, [])
    d.append({"quando": E.agora(), "num": num, "decisao": decisao, "titulo": f.get("titulo") or "", "link": f.get("link"),
              "conta": (f.get("radar") or {}).get("conta"), "porque": motivo.strip()[:300]})
    gravar(DECISOES, d[-200:], 1)


def main():
    a = sys.argv[1:] or ["ensaio"]
    with open(TRAVA, "w") as t:
        fcntl.flock(t, fcntl.LOCK_EX)
        if a[0] == "pagina":
            pg = pagina(); print(f"{pg['lidos']} posts lidos, {sum(1 for p in pg['posts'] if p.get('item'))} do estúdio")
        elif a[0] == "cerebro":
            novo, usd = cerebro(); print(novo); print(f"\n(US$ {usd:.3f})")
        elif a[0] == "dia":
            pagina(); _, usd = cerebro(); print(f"cérebro do dia atualizado (US$ {usd:.3f})")
            p2 = parte2()
            print(f"parte 2 sugerida: {p2}" if p2 else "parte 2: nenhum vídeo nosso acima de 2x a mediana nas últimas 48 h")
        elif a[0] == "rodar":
            r = rodar_lote()
            if r.get("erro"):
                print("radar:", r["erro"]); return
            if "lote" in r:
                print(f"radar: lote {r['lote']} de {LOTES} lido ({r['contas_lidas']} contas)"
                      + (f" · falhas: {'; '.join(r['falhas'])[:160]}" if r["falhas"] else "")); return
            criados = sugerir(r)
            print(f"radar {r['medido']}: {r['contas_lidas']} contas, {len(r['candidatos'])} candidatos, "
                  f"{len(r['sugestoes'])} com nota 7+, pautas criadas: {criados or 'nenhuma'}")
        elif a[0] == "ensaio":
            pg = pagina(); print(f"página: {pg['lidos']} posts lidos ({sum(1 for p in pg['posts'] if p.get('item'))} do estúdio), {pg['seguidores']} seguidores")
            novo, u1 = cerebro(); print("\n" + novo + f"\n(cérebro: US$ {u1:.3f})\n")
            r = rodada()
            if r.get("erro"):
                print("RADAR:", r["erro"]); return
            print(f"radar: {r['contas_lidas']} contas, {r['posts_48h']} posts de 48 h, {len(r['candidatos'])} candidatos julgados "
                  f"(US$ {r['usd_julgar']:.3f}) em {r['segundos']} s" + (f" · falhas: {'; '.join(r['falhas'])[:200]}" if r["falhas"] else ""))
            for c in sorted(r["candidatos"], key=lambda c: -((c.get("juizo") or {}).get("nota") or 0)):
                j = c.get("juizo") or {}
                print(f"  {j.get('nota', '?'):>2} · {'VIRA' if j.get('vira_video') else 'não '} · @{c['conta']} {c['fator']}x · "
                      f"{j.get('titulo', '')} · {j.get('formato', '')}\n       porque: {j.get('porque', '')}\n       prova: {j.get('prova', '')}\n       {c['link']}")
            print(f"\nSUGERIDAS (nota 7+, no máximo 3): {len(r['sugestoes'])} · nada foi criado (ensaio)")


if __name__ == "__main__":
    main()
