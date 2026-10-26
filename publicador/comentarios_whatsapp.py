#!/usr/bin/env python3
"""Respostas a comentários da @newsbr360 com convite para seguir, aprovadas em lote pelo WhatsApp (10/10/2026, "aprovo o
plano"; convite: "precisamos de ajuda segue o perfil e tal", "vamos convidar para seguir o perfil para chegar a 10k").

A cada 5 minutos (cron do alex na VPS 204), este programa:
  1. se há lote esperando: lê a resposta dele no chat com ele mesmo e publica só o que ele aprovou, de 1 a 2 min entre
     uma resposta e outra, e confere pela API que cada uma saiu e não ficou escondida;
  2. se não há lote e já passaram 3 h do último, das 8h às 22h: lê os comentários novos dos posts recentes, a IA escolhe
     até 5 perguntas ou argumentos e redige as respostas no tom das de 07/10; ~1 em 3 leva o convite para seguir com
     quanto falta para 10 mil; o lote vai para o WhatsApp dele.
MUDANÇA 10/10 ~09:10 ("não precisa mandar no whats para eu aprovar. pode responder e vai monitorando"): com
APROVACAO = False o lote publica sozinho e o WhatsApp dele só recebe aviso quando algo dá errado (recusa ou resposta
escondida). Com APROVACAO = True volta o fluxo abaixo.
Ele responde:  ok  (todas) · ok 1 3  (só essas) · não  (nenhuma) · 2: texto novo  (troca a 2 e aprova; pode vir junto
com "ok"). Sem resposta em 3 h, o lote expira (os comentários envelhecem) e o próximo começa do zero.

Cuidados: depois da restrição de 07/10 (28 respostas em 4 h), no máximo 5 por lote e nada fora das 8h-22h. A mensagem
do lote nunca leva link do Instagram: a fila de pautas (pauta_whatsapp.py) lê o mesmo chat e pegaria como pauta.
A IA roda como na fila de pautas: `claude -p` sem ferramentas, fora da pasta do estúdio.

MUDANÇA 20/10/2026 (ele: "eu quero responder mais. acho que agora podemos"; conta conferida na API: sem bloqueio, as
últimas 12 respostas visíveis): veio da v1 para o estúdio v2 (publicador/), lote a cada 1 h com até 15 respostas, 10 posts
olhados, a IA na conta Max (~/.estudio-v2.env no cron) e freio também para resposta escondida (desliga e avisa).

  python3 publicador/comentarios_whatsapp.py               uma rodada (o cron chama a cada 5 min)
  python3 publicador/comentarios_whatsapp.py --simular    redige um lote e só imprime (não manda nem grava)
  python3 publicador/comentarios_whatsapp.py --agora      manda um lote já, sem esperar as 3 h (dentro do horário)
  python3 publicador/comentarios_whatsapp.py --estado     mostra o lote atual e os últimos
  python3 publicador/comentarios_whatsapp.py --desligar / --ligar
"""
import base64, fcntl, json, random, re, subprocess, sys, time, urllib.error, urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

AQUI = Path(__file__).resolve().parent         # estudio-v2/publicador (20/10/2026; era newsbr360-estudio/newsbr360)
sys.path.insert(0, str(AQUI))
import comentarios as C                          # noqa: E402  (token, get/post e o registro de respostas)

ESTADO = C.DIR / "lotes.json"
DESLIGADO = C.DIR / "lotes.DESLIGADO"
TRAVA = Path("/tmp/comentarios-whatsapp.lock")
PASTA_IA = Path("/tmp/comentarios-whatsapp-ia")
GOWA = "http://127.0.0.1:8087"
CHAT = "5500000000000@s.whatsapp.net"           # o chat dele com ele mesmo; destino fixo, como no avisar.py
MARCA = "NewsBR360 · Comentários"
BR = ZoneInfo("America/Sao_Paulo")
HORARIO = (8, 22)
INTERVALO = timedelta(hours=1)               # 20/10/2026: era 3 h
VALIDADE = timedelta(hours=3)
POR_LOTE = 15                                  # 20/10/2026: era 5 (limite depois da restrição de 07/10)
APROVACAO = False                              # True: cada lote espera o ok dele no WhatsApp
POSTS = 10
META = 10000
CONVITES = [
    "A gente precisa da sua ajuda para chegar a 10 mil! Segue a @newsbr360 🙏",
    "Página nova, notícia com fonte. Se puder, ajuda a gente: segue o perfil 🙌",
    "Faltam {faltam} para 10 mil. Se curtiu, segue a gente, ajuda muito!",
    "Precisamos de você para crescer: segue a @newsbr360 e acompanha as próximas checagens.",
]
FEIO = re.compile(r"(?i)\b(lixo|vagabund|ladr[aã]o|puta|merda|caralh|porra|safad|idiota|macaco|nojent|fdp|bolsominion|"
                  r"petralha|gado)")


def agora():
    return datetime.now(timezone.utc)


def iso(d):
    return d.isoformat(timespec="seconds")


def quando(t):
    if isinstance(t, (int, float)):
        return datetime.fromtimestamp(t, timezone.utc)
    t = str(t or "").replace("Z", "+00:00")
    if re.search(r"[+-]\d{4}$", t):              # a Graph API manda +0000
        t = t[:-2] + ":" + t[-2:]
    try:
        d = datetime.fromisoformat(t)
    except ValueError:
        return datetime.min.replace(tzinfo=timezone.utc)
    return d if d.tzinfo else d.replace(tzinfo=timezone.utc)


def no_horario(d=None):
    h = (d or agora()).astimezone(BR).hour
    return HORARIO[0] <= h < HORARIO[1]


def carrega():
    return json.loads(ESTADO.read_text()) if ESTADO.exists() else {"lotes": [], "convites": 0}


def grava(e):
    tmp = ESTADO.with_suffix(".tmp")
    tmp.write_text(json.dumps(e, ensure_ascii=False, indent=1))
    tmp.replace(ESTADO)


# ---------- WhatsApp (só o número dele) ----------

def gowa(caminho, dados=None):
    auth = next(l.split("=", 1)[1].strip() for l in Path("/etc/kitebiz/newsbr360.env").read_text().splitlines()
                if l.startswith("GOWA_AUTH="))
    req = urllib.request.Request(f"{GOWA}{caminho}", data=json.dumps(dados).encode() if dados else None,
                                 method="POST" if dados else "GET",
                                 headers={"Content-Type": "application/json", "X-Device-Id": "alex",
                                          "Authorization": "Basic " + base64.b64encode(auth.encode()).decode()})
    return json.loads(urllib.request.urlopen(req, timeout=20).read())


def manda(texto):
    if "instagram.com" in texto:
        raise RuntimeError("mensagem com link do Instagram: a fila de pautas pegaria como pauta")
    r = gowa("/send/message", {"phone": CHAT, "message": texto})
    if r.get("code") != "SUCCESS":
        raise RuntimeError(f"WhatsApp recusou: {r}")


def mensagens_dele(desde):
    r = gowa(f"/chat/{CHAT}/messages?limit=40").get("results") or {}
    ms = r.get("data", []) if isinstance(r, dict) else r
    return [m for m in sorted(ms, key=lambda m: quando(m.get("timestamp")))
            if m.get("is_from_me") and quando(m.get("timestamp")) > desde
            and not (m.get("content") or "").startswith("NewsBR360")]


def decisao(texto, n):
    """O que ele aprovou: {numero: texto_novo_ou_None}, ou None se a mensagem não é resposta ao lote."""
    linhas = [l.strip() for l in texto.strip().splitlines() if l.strip()]
    if not linhas:
        return None
    if re.match(r"(?i)^(n[aã]o|nenhum[a]?|nada)\b", linhas[0]):
        return {}
    aprov, comando = {}, False
    for l in linhas:
        m = re.match(r"^(\d)\s*[:\-–]\s*(.+)$", l)
        if m and 1 <= int(m.group(1)) <= n:
            aprov[int(m.group(1))] = m.group(2).strip(); comando = True
            continue
        m = re.match(r"(?i)^ok\b(.*)$", l)
        if m:
            pedidos = [int(x) for x in re.findall(r"\d", m.group(1))]
            nums = [k for k in pedidos if 1 <= k <= n]
            if pedidos and not nums:                # "ok 9" num lote de 5: não adivinha, espera outra resposta
                continue
            comando = True
            for k in nums or range(1, n + 1):
                aprov.setdefault(k, None)
    return aprov if comando else None


# ---------- Instagram ----------

def seguidores(token, ig):
    return C.get(ig, token, fields="followers_count")["followers_count"]


def ja_respondidos():
    if not C.LOG.exists():
        return set()
    return {json.loads(l)["comentario"] for l in C.LOG.read_text().splitlines() if l.strip()}


def comentarios_novos(token, ig, desde):
    eu = "newsbr360"
    feitos = ja_respondidos()
    novos = []
    for m in C.get(f"{ig}/media", token, fields="id,permalink,caption", limit=POSTS)["data"]:
        titulo = (m.get("caption") or "").strip().split("\n")[0][:90]
        r = C.get(f"{m['id']}/comments", token, fields="id,text,username,timestamp,like_count,replies{username}", limit=50)
        for _ in range(2):                       # a API devolve do mais novo para o mais velho (medido em 10/10)
            velho = False
            for c in r.get("data", []):
                if quando(c.get("timestamp")) <= desde:
                    velho = True; break
                txt = (c.get("text") or "").strip()
                if (c.get("username") == eu or c["id"] in feitos or len(txt) < 15 or FEIO.search(txt)
                        or any(x.get("username") == eu for x in c.get("replies", {}).get("data", []))):
                    continue
                novos.append({"id": c["id"], "quem": c.get("username"), "texto": txt[:400], "post": m["permalink"],
                              "titulo": titulo, "legenda": (m.get("caption") or "")[:1500], "curtidas": c.get("like_count", 0)})
            if velho or not r.get("paging", {}).get("next"):
                break
            r = json.load(urllib.request.urlopen(r["paging"]["next"], timeout=30))
    return novos


# ---------- redação ----------

def anteriores(n=40):
    if not C.LOG.exists():
        return []
    return [json.loads(l)["resposta"] for l in C.LOG.read_text().splitlines() if l.strip()][-n:]


def abertura(txt):
    """As 3 primeiras palavras, sem acento nem pontuação: o que mais se repetia ("Na legenda: a", 9 de 60 em 20/10)."""
    s = __import__("unicodedata").normalize("NFD", txt.lower()).encode("ascii", "ignore").decode()
    return " ".join(re.findall(r"[a-z0-9]+", s)[:3])


def redige(cands, faltam):
    # 20/10/2026 (ele: "melhora as respostas para não repitir"): cada vídeo ganha um código (V1, V2...) e o comentário
    # aponta o seu; antes as legendas iam todas juntas e a IA citava a do vídeo errado (Janones num comentário do Boulos)
    videos = {}
    for c in cands:
        videos.setdefault(c["titulo"], {"cod": f"V{len(videos) + 1}", "titulo": c["titulo"], "legenda": c["legenda"]})
    legendas = "\n\n".join(f"{v['cod']} · \"{v['titulo']}\"\n{v['legenda']}" for v in videos.values())
    lista = "\n".join(f"[{i}] {videos[c['titulo']]['cod']} · @{c['quem']} ({c['curtidas']} curtidas): {c['texto']}"
                      for i, c in enumerate(cands))
    antes = anteriores()
    gastas = [a for a, n in __import__("collections").Counter(abertura(t) for t in antes).most_common(12) if n > 1]
    proibidos = "; ".join(f'"{a}"' for a in gastas) or "(nenhum)"
    ja_dadas = "\n".join("- " + t for t in antes[-25:])
    prompt = f"""Você responde comentários da página @newsbr360 no Instagram (notícia de política e economia "com prova":
o documento original na tela, a fonte na legenda; lema "Fato, fonte e ponto."). Escolha ATÉ {POR_LOTE} comentários abaixo
que valem resposta e escreva a resposta de cada um.

Escolha: perguntas de verdade e argumentos (a favor ou contra), de preferência com curtidas. Não escolha: xingamento,
briga, só emoji, só marcação de outra conta, só "22"/"13", propaganda, nem quem só concorda sem dizer nada.
Apoio que diz algo concreto também vale: agradeça e reforce onde conferir.
Se nenhum vale, devolva lista vazia.

Como responder (regras da página, obrigatórias):
- Curta: 1 ou 2 frases, até 220 caracteres. Tom de pessoa da página, educado, sem ironia, sem militância.
- Use a fonte: aponte onde conferir (a legenda do vídeo, o plano no TSE, a lei, o documento). Só cite o que está na
  legenda do MESMO vídeo do comentário (o código V1, V2... ao lado dele); não invente número, data, nome nem fato.
- NUNCA diga que alguém cometeu crime ou deve ser preso. Se perguntarem se é crime ou fake news: quem decide é a Justiça
  Eleitoral; o nosso trabalho é mostrar o documento.
- Nada de pedir voto, enquete ("22 ou 13"), nem atacar candidato, partido ou o Congresso.
- Pode chamar pelo primeiro nome se o @ deixar claro.
- Sem travessão longo (use ponto ou vírgula). Sem links.

NÃO REPETIR (respostas parecidas em quantidade o Instagram lê como spam e esconde):
- Cada resposta do lote começa de um jeito diferente, e nenhuma começa como as respostas já dadas abaixo.
  Começos gastos, proibidos: {proibidos}.
- Não use sempre a mesma fórmula ("Na legenda:", "Sobre X não temos fonte", "Quem decide é a Justiça Eleitoral"):
  diga a mesma ideia com outras palavras, ou responda direto ao que a pessoa disse.
- Emoji: no máximo em 1 de cada 3 respostas, e nunca o mesmo no fim de todas (o 📄 estava em 40 de 60).
- Varie o tamanho: umas com 1 frase curta, outras com 2.

Para cada resposta, escreva também dois convites curtos (até 90 caracteres cada), diferentes entre si e dos outros do lote,
ligados ao assunto quando der: "seguir" (convida a seguir a @newsbr360; pode dizer que faltam {faltam} para 10 mil) e
"compartilhar" (pede para mandar o vídeo a quem precisa ver). O programa usa um deles em parte das respostas.

Respostas que a página já deu (o tom certo, mas não copie começos nem frases):
{ja_dadas}

Legendas dos vídeos (as fontes que você pode citar):
{legendas}

Comentários:
{lista}

Devolva SÓ um JSON, sem texto em volta:
[{{"i": <número entre colchetes>, "resposta": "<texto>", "seguir": "<convite>", "compartilhar": "<convite>"}}]"""
    PASTA_IA.mkdir(exist_ok=True)
    # 25/10/2026: a chamada de IA de um lugar só (ia.py, na raiz do estúdio): prazo, uso da conta e erro iguais aos outros
    sys.path.insert(0, str(AQUI.parent)); import ia
    resposta, uso = ia.chamar(prompt, "respostas a comentários", "sonnet", limite=300, cwd=PASTA_IA)
    m = re.search(r"\[.*\]", resposta, re.S)
    if not m:
        raise RuntimeError(f"redação falhou: {(uso['erro'] or resposta or 'resposta vazia')[:200]}")
    saida, usadas = [], {abertura(t) for t in antes[-30:]}
    limpa = lambda t: " ".join(str(t or "").split()).replace("—", ",")
    for x in json.loads(m.group(0))[:POR_LOTE]:
        i, txt = int(x["i"]), limpa(x["resposta"])
        if not (0 <= i < len(cands) and txt) or re.search(r"(?i)https?://|cometeu crime|deve ser pres", txt):
            continue
        if abertura(txt) in usadas:             # a IA repetiu um começo mesmo assim: essa fica de fora
            print(f"  fora por repetir o começo \"{abertura(txt)}\": {txt[:80]}")
            continue
        usadas.add(abertura(txt))
        saida.append({**{k: cands[i][k] for k in ("id", "quem", "texto", "post", "titulo")}, "resposta": txt,
                      "seguir": limpa(x.get("seguir"))[:120], "compartilhar": limpa(x.get("compartilhar"))[:120]})
    return saida


def poe_convites(itens, e, faltam):
    # 20/10/2026 (ele: "convidar para seguir o perfil e compartilhar de formas diferentes ou alterna entre convidar para
    # seguir e pedir para compartilhar"): o convite é o que a IA escreveu para aquela resposta, alternando seguir e
    # compartilhar; as 4 frases fixas (CONVITES) só entram se a IA não mandou convite
    for it in itens:
        seguir, compartilhar = it.pop("seguir", ""), it.pop("compartilhar", "")
        e["convites"] = e.get("convites", 0) + 1
        if e["convites"] % 3 != 1:              # 1 em cada 3, contando entre lotes
            continue
        vez = (e["convites"] // 3) % 2
        convite = (compartilhar if vez else seguir) or seguir or compartilhar
        convite = convite.replace("{faltam}", faltam) if convite else CONVITES[(e["convites"] // 3) % len(CONVITES)].format(faltam=faltam)
        it["resposta"] += " " + convite


def texto_do_lote(lote):
    fim = (quando(lote["enviado"]) + VALIDADE).astimezone(BR).strftime("%H:%M")
    partes = [f"{MARCA}, lote {lote['num']} ({len(lote['itens'])} respostas). Nada sai sem o seu ok."]
    for n, it in enumerate(lote["itens"], 1):
        titulo = it["titulo"] if len(it["titulo"]) <= 60 else it["titulo"][:60].rsplit(" ", 1)[0] + "…"
        partes.append(f"{n}) @{it['quem']} no vídeo \"{titulo}\":\n\"{it['texto'][:200]}\"\n→ {it['resposta']}")
    partes.append(f"Responda: ok (todas) · ok 1 3 (só essas) · não (nenhuma) · 2: texto novo (troca a 2). Vale até {fim}.")
    return "\n\n".join(partes)


# ---------- rodada ----------

def novo_lote(e, forcar=False, simular=False):
    token, ig = C.acesso()
    ult = max((quando(l["enviado"]) for l in e["lotes"]), default=agora() - timedelta(hours=6))
    if not simular and not forcar and agora() - ult < INTERVALO:
        return
    lido = e.get("lido_ate")
    desde = quando(lido) if lido else agora() - timedelta(hours=6)
    inicio = agora()
    cands = comentarios_novos(token, ig, desde)
    cands.sort(key=lambda c: -c["curtidas"])
    cands = cands[:60]
    faltam = max(0, META - seguidores(token, ig))
    faltam = f"{round(faltam, -2):,}".replace(",", ".") if faltam >= 1000 else str(faltam)
    itens = redige(cands, faltam) if cands else []
    if simular:
        poe_convites(itens, dict(e), faltam)
        print(f"{len(cands)} comentários novos desde {iso(desde)}; {len(itens)} escolhidos\n")
        print(texto_do_lote({"num": len(e["lotes"]) + 1, "itens": itens, "enviado": iso(agora())}) if itens else "(nenhum)")
        return
    e["lido_ate"] = iso(inicio)
    if not itens:
        e["lotes"].append({"num": len(e["lotes"]) + 1, "enviado": iso(agora()), "estado": "vazio", "itens": []})
        print(f"{iso(agora())} {len(cands)} comentários novos, nenhum vale resposta")
        return
    poe_convites(itens, e, faltam)
    lote = {"num": len(e["lotes"]) + 1, "enviado": iso(agora()), "estado": "esperando", "itens": itens}
    if APROVACAO:
        manda(texto_do_lote(lote))
    else:
        lote.update(estado="aprovado", aprovacao={str(n): None for n in range(1, len(itens) + 1)}, aprovado_em=iso(agora()))
    e["lotes"].append(lote)
    print(f"{iso(agora())} lote {lote['num']} {'enviado' if APROVACAO else 'montado'}: {len(itens)} respostas de "
          f"{len(cands)} comentários novos")


def publica(lote, aprov, e):
    token, _ = C.acesso()
    ok = falhas = 0
    for n, it in enumerate(lote["itens"], 1):
        if n not in aprov:
            it["estado"] = "recusado"; continue
        if aprov[n]:
            it["resposta"] = " ".join(aprov[n].split())
        if ok or falhas:
            time.sleep(random.randint(60, 120))
        try:
            r = C.post(f"{it['id']}/replies", token, message=it["resposta"])
            v = C.get(r["id"], token, fields="id,hidden,username")
            it.update(estado="publicado" if not v.get("hidden") else "escondido", resposta_id=r["id"])
            with C.LOG.open("a") as f:
                f.write(json.dumps({"quando": time.strftime("%Y-%m-%dT%H:%M:%S"), "comentario": it["id"], "quem": it["quem"],
                                    "post": it["post"], "resposta": it["resposta"], "resposta_id": r["id"],
                                    "lote": lote["num"]}, ensure_ascii=False) + "\n")
            ok += 1
        except urllib.error.HTTPError as ex:
            it.update(estado="falhou", erro=ex.read()[:300].decode(errors="replace"))
            falhas += 1
            if falhas >= 2:                         # duas recusas seguidas: pode ser restrição de novo; para
                break
        grava(e)
    lote["estado"] = "publicado"
    esc = sum(1 for it in lote["itens"] if it.get("estado") == "escondido")
    aviso = f"{MARCA}, lote {lote['num']}: publicadas {ok} de {len(aprov)} aprovadas."
    if esc:
        aviso += f" {esc} saiu escondida pelo Instagram."
        if not falhas:                              # 20/10/2026: com o volume maior, escondida também freia
            DESLIGADO.write_text(iso(agora()) + " resposta escondida pelo Instagram")
            aviso += " Desliguei as respostas até você mandar religar."
    if falhas:
        aviso += f" {falhas} o Instagram recusou; parei. Pode ser restrição de novo, confira no app."
        DESLIGADO.write_text(iso(agora()) + " recusa do Instagram ao publicar")
        aviso += " Desliguei as respostas até você mandar religar."
    if APROVACAO or esc or falhas:
        manda(aviso)
    print(f"{iso(agora())} {aviso}")


def rodada(forcar=False):
    e = carrega()
    aberto = next((l for l in e["lotes"] if l["estado"] in ("esperando", "aprovado")), None)
    if aberto:
        if aberto["estado"] == "esperando":
            for m in mensagens_dele(quando(aberto["enviado"])):
                d = decisao(m.get("content") or "", len(aberto["itens"]))
                if d is not None:
                    aberto.update(estado="aprovado", aprovacao={str(k): v for k, v in d.items()},
                                  resposta_dele=(m.get("content") or "")[:300], aprovado_em=iso(agora()))
                    grava(e)
                    break
            else:
                if agora() - quando(aberto["enviado"]) > VALIDADE:
                    aberto["estado"] = "expirado"; grava(e)
                    print(f"{iso(agora())} lote {aberto['num']} expirou sem resposta")
                return
        if aberto["estado"] == "aprovado":
            if not no_horario():
                return                              # aprovou de noite: publica às 8h
            aprov = {int(k): v for k, v in aberto["aprovacao"].items()}
            if not aprov:
                aberto["estado"] = "recusado"; grava(e)
                manda(f"{MARCA}, lote {aberto['num']}: entendido, nenhuma publicada.")
                return
            publica(aberto, aprov, e)
            grava(e)
        return
    if no_horario():
        novo_lote(e, forcar=forcar)
        grava(e)


def main():
    a = sys.argv[1:]
    if "--desligar" in a:
        DESLIGADO.write_text(iso(agora())); print("respostas a comentários DESLIGADAS"); return
    if "--ligar" in a:
        DESLIGADO.unlink(missing_ok=True); print("respostas a comentários ligadas"); return
    if "--estado" in a:
        e = carrega()
        print("DESLIGADO" if DESLIGADO.exists() else "ligado", "· lido até", e.get("lido_ate"), "· convites", e.get("convites", 0))
        for l in e["lotes"][-6:]:
            est = ", ".join(f"{n}:{it.get('estado', '-')}" for n, it in enumerate(l["itens"], 1))
            print(f"  lote {l['num']} {l['enviado'][:16]} {l['estado']:10s} {est}")
        return
    if "--simular" in a:
        novo_lote(carrega(), simular=True); return
    if DESLIGADO.exists():
        analista_da_conta(); return
    with open(TRAVA, "w") as t:
        try:
            fcntl.flock(t, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return
        rodada(forcar="--agora" in a)
        analista_da_conta()


def analista_da_conta():
    """26/10/2026 (ele: "pode ser o mesmo que responde as pessoas"): depois das respostas, a leitura do público
    (publicador/analista.py, de 3 em 3 h); se ela falhar, as respostas não param."""
    try:
        import analista
        analista.rodada()
    except Exception as ex:
        print(f"{iso(agora())} analista falhou: {str(ex)[:300]}")


if __name__ == "__main__":
    main()
