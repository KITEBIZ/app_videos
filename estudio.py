"""Estúdio v2 da @newsbr360: os dados (16/10/2026, "aprovo o plano v2-parte1").

Cada vídeo é um arquivo: a pasta videos/<número>/, que nasce quando a pauta entra e guarda tudo do vídeo.
  ficha.json        etapa, tipo, link, o que está fazendo agora, o que espera dele (só o estúdio escreve)
  chat.jsonl        a conversa, uma mensagem por linha, cada uma com o id que o celular mandou (repetida não duplica)
  historico.jsonl   o que aconteceu, com a hora
  referencia/       áudio, transcrição, quadros e dados do post da pauta
  ANALISE.md · CHECAGEM.md · INTENCAO.md · ROTEIRO.md   (o roteiro em blocos: bloco N = linha N da tabela)
  versoes/          o ROTEIRO.md antes de cada mudança
"""
import json, os, re, threading, time, unicodedata
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent
VIDEOS = RAIZ / "videos"
ETAPAS = ["Pauta", "Roteiro e voz", "Animação", "Aguardando", "Publicado"]
PRIMEIRO = 201                     # a v2 começa no 201 para não confundir com os números da v1
TIPOS = {"analisar": "Analisar a fala", "igual": "Fazer igual", "ideia": "Ideia escrita"}
_trava = threading.RLock()


def agora():
    return datetime.now().astimezone().isoformat(timespec="seconds")


def pasta(num):
    return VIDEOS / str(int(num))


def _grava(arq, texto):
    # 24/10/2026 (animacao-mais-rapida-e-certa): o provisório tem nome próprio por processo e linha de execução; com um
    # nome só, duas gravações ao mesmo tempo apagavam o provisório uma da outra (a tarja do #370 falhou 3 vezes assim)
    tmp = arq.with_name(f"{arq.name}.{os.getpid()}.{threading.get_ident()}.tmp")
    tmp.write_text(texto)
    os.replace(tmp, arq)


MOLDES = {"curso": "MOLDE-CURSO.md", "conferir": "MOLDE-FOMOS-CONFERIR.md",
          "microdoc": "MOLDE-MICRO-DOC.md", "numeros": "MOLDE-NUMEROS.md"}   # numeros: 24/10/2026, "pode fazer o molde números" (o #368)   # microdoc: 24/10/2026, "pode ensiar esse formato ao agente?" (o #367)     # conferir: 18/10/2026, "aprovo o plano formato-fomos-conferir"


# 19/10/2026 (ele: "quero colocar no ar o app"): o estúdio passa a rodar DENTRO da VPS; o que antes ia por ssh/scp
# (publicar, números do Instagram) roda direto nela
NA_VPS = __import__("socket").gethostname() == "kitebiz-prod"
VPS = "usuario@SEU_SERVIDOR"


def na_vps(cmd):
    """O comando para rodar `cmd` (shell) na VPS: direto, se o estúdio já está nela; por ssh, se não."""
    return ["bash", "-c", cmd] if NA_VPS else ["ssh", "-o", "ConnectTimeout=15", VPS, cmd]


def para_vps(origem, destino):
    """Copia um arquivo local para um caminho da VPS (cp nela mesma, scp de fora)."""
    return ["cp", str(origem), destino] if NA_VPS else ["scp", "-q", str(origem), f"{VPS}:{destino}"]


def molde(num):
    """17/10/2026 ("aprovo o plano molde-curso"): com um molde ligado no vídeo, as regras dele vão junto para o
    roteirista, o agente, o animador e a legenda (regras/MOLDE-*.md); sem ele, nada."""
    arq = MOLDES.get(ler_ficha(num).get("molde") or "")
    return "\n\n" + (RAIZ / "regras" / arq).read_text() + "\n" if arq else ""


def ler_ficha(num):
    return json.loads((pasta(num) / "ficha.json").read_text())


class _entre_processos:
    """25/10/2026 (plano de melhorias): trava que vale também para os outros programas (o baixar.py rodado pelo agente,
    o radar), não só para as linhas do servidor: dois ler-mudar-gravar da ficha ao mesmo tempo perdiam uma das mudanças."""
    def __init__(self, arq):
        self.arq = arq

    def __enter__(self):
        import fcntl
        self.arq.parent.mkdir(parents=True, exist_ok=True)
        self.f = open(self.arq, "a")
        fcntl.flock(self.f, fcntl.LOCK_EX)
        return self

    def __exit__(self, *a):
        import fcntl
        fcntl.flock(self.f, fcntl.LOCK_UN); self.f.close()


def mexe_ficha(num, **campos):
    with _trava, _entre_processos(pasta(num) / ".ficha.lock"):
        f = ler_ficha(num)
        antes = (f.get("etapa"), f.get("passo"), f.get("esperando") or "")
        f.update(campos)
        f["atualizado"] = agora()
        _grava(pasta(num) / "ficha.json", json.dumps(f, ensure_ascii=False, indent=1))
        if {"etapa", "passo", "esperando"} & set(campos):
            _confere_mapa(num, antes, f)
        return f


def _confere_mapa(num, antes, f):
    """24/10/2026 ("aprovo o plano mapa-de-passos", parte 2): toda mudança de etapa, passo ou espera é conferida no mapa
    (passos.py). Por enquanto só anota em mapa-avisos.jsonl (ao lado de videos/) o estado que não existe no mapa (nunca recusa: recusar podia
    travar um vídeo); quando o registro ficar limpo, passa a recusar."""
    import passos
    erros = passos.confere(f.get("etapa"), f.get("passo"), f.get("esperando") or "")
    if erros:
        # ao lado da pasta de vídeos: na VPS e na cópia local é a raiz do estúdio; num teste, a pasta temporária dele
        with (VIDEOS.parent / "mapa-avisos.jsonl").open("a") as h:
            h.write(json.dumps({"quando": agora(), "num": int(num), "antes": antes,
                                "depois": [f.get("etapa"), f.get("passo"), f.get("esperando") or ""], "erros": erros}, ensure_ascii=False) + "\n")


def evento(num, texto):
    with _trava, (pasta(num) / "historico.jsonl").open("a") as h:
        h.write(json.dumps({"quando": agora(), "texto": texto}, ensure_ascii=False) + "\n")


def numeros():
    return sorted(int(p.name) for p in VIDEOS.glob("*") if p.name.isdigit() and (p / "ficha.json").exists())


LIXEIRA = VIDEOS / "_lixeira"


def excluir(num):
    """16/10/2026 ("aprovo o plano botao-excluir"): o vídeo vai para a lixeira do estúdio (videos/_lixeira/<número>-<hora>),
    inteiro; dá para recuperar movendo a pasta de volta."""
    LIXEIRA.mkdir(exist_ok=True)
    destino = LIXEIRA / f"{int(num)}-{agora()[:19].replace(':', '').replace('-', '')}"
    evento(num, "excluído por ele (foi para a lixeira)")
    pasta(num).rename(destino)
    return destino


def criar_item(tipo, link="", texto="", id_msg=None):
    """A pauta vira o arquivo do vídeo na hora. Devolve (número, se já existia). O mesmo id de mensagem não cria duas."""
    if tipo not in TIPOS:
        raise ValueError(f"tipo desconhecido: {tipo}")
    with _trava, _entre_processos(VIDEOS / ".criar.lock"):
        if id_msg:
            for n in numeros():
                if ler_ficha(n).get("id_pauta") == id_msg:
                    return n, True
        na_lixeira = [int(p.name.split("-")[0]) for p in LIXEIRA.glob("*-*") if p.name.split("-")[0].isdigit()] if LIXEIRA.exists() else []
        num = max(numeros() + na_lixeira, default=PRIMEIRO - 1) + 1
        p = pasta(num)
        p.mkdir(parents=True)
        ficha = {"num": num, "titulo": "", "tipo": tipo, "link": link, "texto_dele": texto, "etapa": "Pauta",
                 "passo": "recebida", "passo_desde": agora(), "erro": "", "esperando": "", "nota": None,
                 "id_pauta": id_msg, "criado": agora(), "atualizado": agora(), "mudou": []}
        _grava(p / "ficha.json", json.dumps(ficha, ensure_ascii=False, indent=1))
        (p / "chat.jsonl").write_text("")
        evento(num, f"pauta recebida ({TIPOS[tipo]})" + (f": {link}" if link else ""))
        return num, False


# --- chat ------------------------------------------------------------------------------------------------------

def mata(proc):
    """Para o processo e os filhos dele (Popen com start_new_session=True)."""
    import signal
    try:
        os.killpg(proc.pid, signal.SIGKILL)
    except (ProcessLookupError, PermissionError):
        pass
    try:
        proc.wait(timeout=10)
    except Exception:
        pass


def prazo(proc, segundos):
    """25/10/2026 (revisão de solidez): o relógio que para `proc` (e os filhos) passado o prazo, mesmo com quem chamou
    preso lendo a saída dele. Devolve o Timer (cancel() no fim; .estourou diz se parou pelo prazo)."""
    t = threading.Timer(segundos, lambda: (setattr(t, "estourou", True), mata(proc)))
    t.daemon = True; t.estourou = False
    t.start()
    return t


def chat(num):
    # 25/10/2026 (revisão de solidez): uma linha cortada (processo morto no meio de gravar) derrubava o vídeo inteiro: a
    # tela dava erro e o trabalhador quebrava a cada volta; a linha ruim é pulada
    arq = pasta(num) / "chat.jsonl"
    out = []
    for l in (arq.read_text().splitlines() if arq.exists() else []):
        try:
            if l.strip():
                out.append(json.loads(l))
        except ValueError:
            pass
    return out


DETALHES = "\n\n[[detalhes]]\n"   # 24/10/2026 (ele: "pode fazer" a parte B): o que vem depois disto vai recolhido no chat


def chat_add(num, quem, texto, id_msg=None, **extra):
    """Grava a mensagem ANTES de qualquer trabalho começar. Com id repetido, devolve a gravada (o celular reenviou).
    extra: responde=<id da mensagem dele> na resposta do agente (é o que diz que ela foi respondida).
    Texto com DETALHES: a parte de depois vira o campo "detalhes", que a tela mostra fechado (o relatório da conferência,
    os avisos do animador, tempo e custo; antes vinham colados na resposta, ACHADOS resposta.3)."""
    if DETALHES in texto:
        texto, det = texto.split(DETALHES, 1)
        texto, extra = texto.strip(), extra | ({"detalhes": det.strip()} if det.strip() else {})
    with _trava, _entre_processos(pasta(num) / ".chat.lock"):
        if id_msg:
            for m in chat(num):
                if m.get("id") == id_msg:
                    return m, True
        m = {"id": id_msg or f"{quem}-{time.time_ns()}", "quem": quem, "texto": texto, "quando": agora()} | extra
        with (pasta(num) / "chat.jsonl").open("a") as c:
            c.write(json.dumps(m, ensure_ascii=False) + "\n")
            c.flush(); os.fsync(c.fileno())
        return m, False


DECISOES = "## Decisões dele (valem para o vídeo inteiro)"


def intencao(num, limite=4000):
    """O INTENCAO.md do vídeo ("O que queremos mostrar": o Ângulo, o que ele escreveu na pauta e as decisões dele)."""
    arq = pasta(num) / "INTENCAO.md"
    return arq.read_text()[:limite] if arq.exists() else "(ainda não existe)"


def anota_decisao(num, decisao, palavras=""):
    """24/10/2026 ("aprovo"/"pode consertar?" o plano intencao-viva; ele: "no passado combinamos de ter uma pasta do video
    e tudo ficar nessa pagina inclusive essas decisoes"): a decisão dele que vale para o vídeo inteiro vira uma linha do
    INTENCAO.md, que todos os agentes leem. A mesma decisão não entra duas vezes."""
    decisao = " ".join(str(decisao).split()).strip()
    if not decisao:
        return False
    with _trava:
        arq = pasta(num) / "INTENCAO.md"
        txt = arq.read_text() if arq.exists() else "# O que queremos mostrar\n"
        if decisao.lower() in txt.lower():
            return False
        if DECISOES not in txt:
            txt = txt.rstrip() + f"\n\n{DECISOES}\n"
        ele = " ".join(str(palavras).split())[:200]
        txt = txt.rstrip() + f"\n- {agora()[8:10]}/{agora()[5:7]} {agora()[11:16]} · {decisao}" + (f' (ele: "{ele}")' if ele else "") + "\n"
        _grava(arq, txt)
    evento(num, f"decisão dele anotada no INTENCAO.md: {decisao[:160]}")
    return True


def pendentes(num):
    """Mensagens dele que ainda não têm resposta (o agente responde na ordem; servidor reiniciado retoma daqui)."""
    msgs = chat(num)
    respondidas = {m.get("responde") for m in msgs if m["quem"] == "agente"}
    # inicio: a mensagem que criou a pauta (24/10/2026), atendida pela própria pauta
    return [m for m in msgs if m["quem"] == "ele" and m["id"] not in respondidas and not m.get("inicio")]


# --- roteiro em blocos ----------------------------------------------------------------------------------------

LINHA = re.compile(r"^\|\s*(\d+)\s*\|(.*)\|\s*$")


def blocos(num, texto=None):
    """Os blocos do ROTEIRO.md (ou de `texto`, um ROTEIRO.md guardado): [{n, bloco, quem, fala, tela, nosso}] na ordem.
    Linha que não é da tabela é ignorada."""
    arq = pasta(num) / "ROTEIRO.md"
    if texto is None and not arq.exists():
        return []
    out = []
    for l in (arq.read_text() if texto is None else texto).splitlines():
        m = LINHA.match(l.strip())
        if not m:
            continue
        c = [x.strip() for x in m.group(2).split("|")]
        if len(c) < 4:
            continue
        bloco, quem, fala, tela = c[0], c[1], c[2], " | ".join(c[3:])
        nosso = re.fullmatch(r"n[oó]s", quem, re.I) is not None
        out.append({"n": int(m.group(1)), "bloco": bloco, "quem": quem, "fala": fala, "tela": tela, "nosso": nosso})
    return out


# 22/10/2026 ("aprovo o plano idioma-do-video"; ele: "vou começar a criar conteudo em espanhol tb"): o idioma do vídeo é
# a linha "Idioma: espanhol" no alto do ROTEIRO.md, que o roteirista e o agente escrevem quando o vídeo não é em
# português (é um campo do roteiro, como a tabela; sem a linha, português). Vale para a voz, a conferência da voz, a
# legenda, os textos fixos das peças, a capa e a legenda do post.
IDIOMAS = {"pt": "português do Brasil", "es": "espanhol", "en": "inglês"}
_NOMES_IDIOMA = {"portugues": "pt", "português": "pt", "pt": "pt", "espanhol": "es", "español": "es", "espanol": "es",
                 "es": "es", "ingles": "en", "inglês": "en", "english": "en", "en": "en"}
LINHA_IDIOMA = re.compile(r"^\s*\**idioma\**\s*:\s*\**\s*([^\s*.,;]+)", re.I | re.M)


def idioma(num, texto=None):
    """'pt', 'es' ou 'en': a linha "Idioma:" das 12 primeiras linhas do ROTEIRO.md (ou de `texto`); sem ela, 'pt'."""
    arq = pasta(num) / "ROTEIRO.md"
    if texto is None:
        texto = arq.read_text() if arq.exists() else ""
    m = LINHA_IDIOMA.search("\n".join(texto.splitlines()[:12]))
    return _NOMES_IDIOMA.get(m.group(1).lower(), "pt") if m else "pt"


def _ferramentas():
    import sys
    if str(RAIZ / "ferramentas") not in sys.path:
        sys.path.insert(0, str(RAIZ / "ferramentas"))


def memoria(num=None):
    """24/10/2026 ("isso pode fazer"; memoria-entre-videos): o que a página já postou, o último convite, os seguidores e a
    meta, e a regra do convite (ferramentas/memoria.py, sem IA). Vai para o roteirista, o agente, a legenda e a capa."""
    _ferramentas(); import memoria as M
    t = M.ler(RAIZ)
    # 26/10/2026 (o analista da conta, publicador/analista.py): o que o público está dizendo, para todos que escrevem
    pub = RAIZ / "radar/publico.md"
    if pub.exists():
        t = (t + "\n\n" if t else "") + pub.read_text()[:6000]
    return "\n\n" + t if t else ""


def convite_repetido(num):
    """O motivo, se a última fala nossa do roteiro repete o convite do último vídeo postado ou dos anteriores; senão ''."""
    _ferramentas(); import memoria as M
    arq = pasta(num) / "ROTEIRO.md"
    return M.repetido(M.convite_do_roteiro(arq.read_text()), RAIZ) if arq.exists() else ""


def regra_idioma(num):
    """O que vai para o roteirista, o agente, o animador, a capa e a legenda do post quando o vídeo não é em português
    (vazio em português)."""
    lg = idioma(num)
    if lg == "pt":
        return ""
    nome = IDIOMAS[lg]
    return f"""

## Idioma deste vídeo: {nome} (22/10/2026, "aprovo o plano idioma-do-video")
Tudo o que o público vê e ouve sai em {nome}: as nossas falas, os títulos e textos da tela, os selos (o veredito pode ser
escrito em {nome} ou com a chave em português do Verdadômetro, as duas valem), o texto da capa e a legenda do post. A
fala de outra pessoa continua a original, em português, nunca traduzida (só se corta); a legenda traduzida por baixo
dela o estúdio põe. Nome próprio de lugar e instituição brasileira fica em português (Metrô, Avenida Paulista,
Prefeitura). As notas da coluna Tela para o animador podem ficar em português. A linha "Idioma: {nome}" no alto do
ROTEIRO.md fica sempre (é ela que diz ao estúdio o idioma).
"""


def confere_roteiro(num):
    """Lista do que está quebrado no ROTEIRO.md (vazia = ok): blocos 1..N em ordem, cada um com quem e fala."""
    bs = blocos(num)
    if not bs:
        return ["o roteiro não tem a tabela de blocos (| # | Bloco | Quem | Fala | Tela |)"]
    erros = []
    if [b["n"] for b in bs] != list(range(1, len(bs) + 1)):
        erros.append(f"os blocos não vão de 1 a {len(bs)} em ordem: {[b['n'] for b in bs]}")
    for b in bs:
        if not b["quem"] or not b["fala"]:
            erros.append(f"bloco {b['n']} sem quem fala ou sem fala")
    return erros


# o corte do trecho de outra pessoa, no fim da fala: "(106,90-115,40)" corta o vídeo da pauta (referencia/); com a origem,
# "(106,90-115,40 material/thdYriHHEh0)" corta um vídeo que o agente ou ele baixou (17/10/2026, "aprovo o plano agente-baixa")
CORTE = re.compile(r"\s*\(\s*(\d+[.,]\d+)\s*-\s*(\d+[.,]\d+)(?:\s+(material/[\w.-]+))?\s*\)\s*$")


def corte(fala):
    """(início, fim, pasta de origem relativa ao vídeo) ou None."""
    m = CORTE.search(fala or "")
    return (float(m.group(1).replace(",", ".")), float(m.group(2).replace(",", ".")), m.group(3) or "referencia") if m else None


def _palavra(p):
    p = "".join(c for c in unicodedata.normalize("NFD", str(p).lower()) if unicodedata.category(c) != "Mn")
    return re.sub(r"[^\w]", "", p)


NUMERAIS = set("zero um uma dois duas tres quatro cinco seis sete oito nove dez onze doze treze quatorze catorze quinze "
               "dezesseis dezessete dezoito dezenove vinte trinta quarenta cinquenta sessenta setenta oitenta noventa cem "
               "cento duzentos duzentas trezentos quatrocentos quinhentos seiscentos setecentos oitocentos novecentos mil".split())


def _so_palavras(ps):
    """As palavras normalizadas, com cada número (\"100\", \"cem\", \"dois mil e vinte\") virando um "#": a transcrição
    escreve em algarismo o que o roteiro escreve por extenso (#316: "cem anos" e "100 anos")."""
    out = []
    for p in ps:
        w = _palavra(p)
        if not w:
            continue
        num = w.isdigit() or w in NUMERAIS
        if num and out and out[-1] == "#":
            continue
        if w == "e" and out and out[-1] == "#":
            out.append("#e")                      # "dois mil e vinte": o "e" só conta se não vier outro número depois
            continue
        if num and out and out[-1] == "#e":
            out.pop()                             # o "e" era do número: fica um "#" só
            continue
        out.append("#" if num else w)
    return ["e" if w == "#e" else w for w in out]


def _conferida(num, c, texto):
    """25/10/2026 (#382: o take do Metrópoles que veio do #304 pelo acervo; a transcrição automática dele diz "hoje é dia
    de descanso", e a fala certa, "Vamos lá, meu general!", foi conferida à mão no roteiro do #304): a mesma fala, do mesmo
    take e do mesmo corte, já usada num roteiro nosso, vale como conferida. Devolve (vale, o corte conferido de outro
    roteiro quando só o corte é diferente, para o erro dizer qual usar)."""
    cod, sugestao = Path(c[2]).name, ""
    for rot in VIDEOS.glob("*/ROTEIRO.md"):
        outro = rot.parent.name
        if outro == str(num) or f"material/{cod}" not in rot.read_text(errors="replace"):
            continue
        for ob in blocos(outro):
            oc = corte(ob["fala"])
            if not ob["nosso"] and oc and Path(oc[2]).name == cod and _so_palavras(CORTE.sub("", ob["fala"]).split()) == texto:
                if abs(oc[0] - c[0]) <= .3 and abs(oc[1] - c[1]) <= .5:
                    return True, ""
                sugestao = f" (no roteiro do #{outro} esta fala está conferida em ({oc[0]:g}-{oc[1]:g} material/{cod}): use esse corte)"
    return False, sugestao


def falas_alheias(num, antes_md=""):
    """22/10/2026 ("aprovo o plano roteiro-com-direcao"; ele: "quando tem uma fala de uma pessoa ele não pode mudar, ele
    pode cortar"): o texto de cada trecho de outra pessoa tem que ser as palavras que ela disse, em sequência, dentro do
    corte (palavras.json da origem). Só confere o trecho que mudou desde `antes_md`: o que já estava (como o "tortura"
    corrigido à mão no #304) não trava a mudança de outro bloco. Devolve a lista de erros (vazia = ok)."""
    antes = {(b["quem"], " ".join(b["fala"].split())) for b in blocos(num, antes_md)} if antes_md else set()
    erros, cache = [], {}
    for b in blocos(num):
        c = corte(b["fala"])
        if b["nosso"] or not c or (b["quem"], " ".join(b["fala"].split())) in antes:
            continue
        arq = pasta(num) / c[2] / "palavras.json"
        if arq not in cache:
            try:
                cache[arq] = [w for w in json.loads(arq.read_text()) if _palavra(w[2])]
            except (OSError, ValueError):
                cache[arq] = None
        ws = cache[arq]
        if ws is None:
            erros.append(f"bloco {b['n']}: não achei a transcrição de {c[2]} para conferir a fala de {b['quem']}")
            continue
        texto = _so_palavras(CORTE.sub("", b["fala"]).split())
        dentro = _so_palavras(w[2] for w in ws if w[0] >= c[0] - .3 and w[1] <= c[1] + .3)
        k = len(texto)
        if not k or not any(dentro[i:i + k] == texto for i in range(len(dentro) - k + 1)):
            vale, sugestao = _conferida(num, c, texto) if k else (False, "")
            if not vale:
                erros.append(f"bloco {b['n']}: a fala de {b['quem']} não é o que ela disse entre {c[0]:.2f} e {c[1]:.2f} s "
                             "(fala de outra pessoa só se corta: mude o corte e tire palavras do começo ou do fim, nunca troque palavra)"
                             + sugestao)
    return erros


def segundos(bs):
    """Duração estimada: nossas falas a 2,9 palavras por segundo (ritmo da voz dele) + os trechos pelo corte."""
    t = 0.0
    for b in bs:
        c = corte(b["fala"])
        if not b["nosso"] and c:
            t += c[1] - c[0]
        else:
            t += len(b["fala"].split()) / 2.9
    return round(t)


def foto_roteiro(num):
    """Guarda o ROTEIRO.md de agora em versoes/ (antes de uma mudança). Devolve o caminho ou None."""
    arq = pasta(num) / "ROTEIRO.md"
    if not arq.exists():
        return None
    d = pasta(num) / "versoes"; d.mkdir(exist_ok=True)
    destino = d / f"ROTEIRO-{datetime.now():%Y%m%d-%H%M%S-%f}.md"
    destino.write_text(arq.read_text())
    return destino


def mudados(antes_md, num):
    """Números dos blocos que mudaram entre o texto antes e o ROTEIRO.md de agora."""
    tmp = {}
    for l in antes_md.splitlines():
        m = LINHA.match(l.strip())
        if m:
            tmp[int(m.group(1))] = " ".join(m.group(2).split())
    out = []
    for l in (pasta(num) / "ROTEIRO.md").read_text().splitlines():
        m = LINHA.match(l.strip())
        if m and tmp.get(int(m.group(1))) != " ".join(m.group(2).split()):
            out.append(int(m.group(1)))
    return out


def anota_gasto(num, quem, modelo, res):
    """19/10/2026 (ele: "quanto esta gastando cada vez que gera o video?"; só a animação anotava): cada chamada ao
    claude, de qualquer parte do estúdio, vira uma linha em videos/<n>/gasto.jsonl. res: o resultado do claude
    (total_cost_usd, usage, duration_ms) ou um dict já com usd. Valor equivalente: na assinatura não é cobrado à parte,
    mas é o que gasta o limite."""
    try:
        usd = res.get("total_cost_usd", res.get("usd", res.get("equivalente_usd")))
        linha = {"quando": agora(), "quem": quem, "modelo": modelo, "usd": round(usd, 4) if usd is not None else None,
                 "tokens": res.get("usage") or res.get("tokens"), "segundos": round((res.get("duration_ms") or 0) / 1000, 1) or res.get("segundos")}
        # o uso da conta depois da chamada (19/10/2026, ele: "quero saber quanto % gasta em cada video")
        lim = ler_limite() or {}
        j = lim.get("unifiedWindows") or {}
        if j:
            linha["conta"] = {"quando": lim.get("quando"), "sessao": (j.get("five_hour") or {}).get("utilization"),
                              "semana": (j.get("seven_day") or {}).get("utilization"),
                              "sessao_volta": (j.get("five_hour") or {}).get("resetsAt")}
        with _trava, open(pasta(num) / "gasto.jsonl", "a") as g:
            g.write(json.dumps(linha, ensure_ascii=False) + "\n")
    except Exception:
        pass          # anotar nunca pode parar o trabalho


def gastos(num):
    a = pasta(num) / "gasto.jsonl"
    if not a.exists():
        return []
    out = []
    for l in a.read_text().splitlines():
        try:
            out.append(json.loads(l))
        except ValueError:
            pass
    return out


def claude_resultado(saida):
    """A saída do claude -p (--output-format json, ou stream-json, que traz também o uso da conta) → o dict do resultado
    (texto em ["result"]); se não for JSON, o texto. No stream-json, o uso da conta vai para limite.json (19/10/2026)."""
    try:
        s = json.loads(saida)
        return s if isinstance(s, dict) else {"result": saida}
    except ValueError:
        pass
    res = None
    for l in saida.splitlines():
        try:
            ev = json.loads(l)
        except ValueError:
            continue
        if ev.get("type") == "rate_limit_event":
            guarda_limite(ev.get("rate_limit_info") or {})
        elif ev.get("type") == "result":
            res = ev
    return res or {"result": saida}


LIMITE = RAIZ / "limite.json"


def guarda_limite(info):
    """19/10/2026 (ele: "não posso gastar todo meu limite com o opus"): o claude manda, em toda chamada com stream-json,
    quanto da conta já foi usado (janela de 5 h e semana). Guarda o último para a tela mostrar; não gasta nada a mais."""
    if info:
        _grava(LIMITE, json.dumps({"quando": agora(), **info}, ensure_ascii=False))


def ler_limite():
    try:
        return json.loads(LIMITE.read_text())
    except (OSError, ValueError):
        return None


def origem(n):
    """24/10/2026 (ele: "poderia dar um resumo curto do video naquela area, informar qual é o perfil"): de quem é o vídeo
    da pauta e a primeira frase da legenda dele (ou da fala, se não houver legenda), para o cartão da lista."""
    ref = pasta(n) / "referencia"
    try:
        m = json.loads((ref / "meta.json").read_text())
    except (OSError, ValueError):
        return {}
    texto = (m.get("legenda_do_post") or "").strip()
    if not texto and (ref / "transcricao.txt").exists():
        texto = (ref / "transcricao.txt").read_text()[:400].strip()
    frase = re.split(r"(?<=[.?!])\s", re.sub(r"\s+", " ", texto), maxsplit=1)[0] if texto else ""
    return {"perfil": m.get("conta") or "", "quem": m.get("quem_postou") or "",
            "resumo": frase if len(frase) <= 120 else frase[:117].rsplit(" ", 1)[0] + "…"}


def canal(itens):
    """24/10/2026 (ele: "ali no publicado deveria listar todos os vídeos publicados no canal"): os posts do Instagram que
    a memória da página leu (radar/pagina.json), sem os que já aparecem como vídeo do app (mesmo link)."""
    try:
        d = json.loads((RAIZ / "radar/pagina.json").read_text())
    except (OSError, ValueError):
        return {"posts": [], "medido": None}
    ja = {(i.get("publicado") or {}).get("instagram", "").rstrip("/") for i in itens}
    posts = []
    for p in d.get("posts") or []:
        if (p.get("link") or "").rstrip("/") in ja:
            continue
        leg = re.sub(r"\s+", " ", p.get("legenda") or "").strip()
        frase = p.get("titulo") or re.split(r"(?<=[.?!])\s", leg, maxsplit=1)[0][:110]
        posts.append({"link": p.get("link"), "postado": p.get("postado") or (p.get("quando") or "")[:10], "titulo": frase,
                      "views": p.get("visualizacoes"), "shares": p.get("compartilhamentos"), "comentarios": p.get("comentarios")})
    posts.sort(key=lambda x: x["postado"] or "", reverse=True)
    return {"posts": posts, "medido": d.get("medido"), "na_conta": d.get("posts_na_conta")}


# 25/10/2026 (ele: "uma bateria de testes para ver o que podemos limpar para ficar super rápido"; medido no ar: o
# funil levava 86 ms e pesava 70 KB, pedido pela tela a cada 2 s, refazendo o cartão de todos os ~90 vídeos): o cartão
# de cada vídeo fica guardado e só é refeito quando um dos arquivos de que ele depende muda
_cartoes = {}
_DO_CARTAO = ("ficha.json", "ROTEIRO.md", "gasto.jsonl", "narracao/completo.json", "publicacao/numeros.json",
              "animacao/capa.jpg", "referencia/capa-original.jpg", "referencia/meta.json", "referencia/transcricao.txt")


def _assinatura(n):
    p, out = pasta(n), []
    for rel in _DO_CARTAO:
        try:
            out.append((p / rel).stat().st_mtime_ns)
        except OSError:
            out.append(0)
    return tuple(out)


def cartao(n):
    sig = _assinatura(n)
    guardado = _cartoes.get(n)
    if guardado and guardado[0] == sig:
        return guardado[1]
    f = ler_ficha(n)
    bs = blocos(n)
    cj = pasta(n) / "narracao/completo.json"      # com a voz gravada, a duração é a medida, não a estimada
    d = ({k: f.get(k) for k in ("num", "titulo", "tipo", "etapa", "passo", "passo_desde", "erro", "esperando",
                                "nota", "link", "criado", "atualizado", "progresso", "formato")}
         | {"blocos": len(bs), "tem_capa": (pasta(f["num"]) / "animacao/capa.jpg").exists(), "tem_ref": int((pasta(f["num"]) / "referencia/capa-original.jpg").stat().st_mtime) if (pasta(f["num"]) / "referencia/capa-original.jpg").exists() else 0, "views": (json.loads((pasta(f["num"]) / "publicacao/numeros.json").read_text()).get("views") if (pasta(f["num"]) / "publicacao/numeros.json").exists() else None),
            "segundos": round(json.loads(cj.read_text())["duracao"]) if cj.exists() else (segundos(bs) if bs else 0),
            "gasto": round(sum(g.get("usd") or 0 for g in gastos(n)), 2), "origem": origem(n),
            "publicado": f.get("publicado")})
    _cartoes[n] = (sig, d)
    return d


def funil(etapa=None):
    """etapa=None: todos os itens (como antes); etapa="X": só os itens dessa etapa (e o canal só no Publicado); etapa="":
    nenhum item (a tela com um vídeo aberto só precisa das contagens)."""
    itens = [cartao(n) for n in numeros()]
    lista = itens if etapa is None else [i for i in itens if i["etapa"] == etapa]
    return {"versao_tela": int((RAIZ / "web/index.html").stat().st_mtime),
            "canal": canal(itens) if etapa in (None, "Publicado") else {"posts": [], "medido": None},
            "etapas": ETAPAS, "contagem": {e: sum(1 for i in itens if i["etapa"] == e) for e in ETAPAS},
            "itens": lista, "limite": ler_limite()}
