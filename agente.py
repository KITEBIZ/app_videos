"""O agente do vídeo responde às mensagens do chat (estúdio v2, 16/10/2026, "aprovo o plano v2-parte1").

  python3 agente.py <número>     responde, na ordem, as mensagens dele ainda sem resposta

A mensagem já está gravada no chat.jsonl antes de o agente começar (o "✓ recebida" vem dessa gravação). Antes de
cada pedido, o ROTEIRO.md vai para versoes/ (foto); depois, o estúdio confere a tabela de blocos: quebrada, volta a
foto e a resposta diz o que houve. Os blocos que mudaram ficam marcados na ficha (a tela acende).
"""
import json, re, sys, urllib.request

import estudio as E
import caderno
import pauta

LINK = re.compile(r"https?://\S+")
FOTO = re.compile(r"(\.(?:jpe?g|png|webp|gif))(?:\?|$)", re.I)
VIDEO = re.compile(r"instagram\.com/|youtube\.com/|youtu\.be/|tiktok\.com/|(?:x|twitter)\.com/\w+/status/|facebook\.com/|fb\.watch/", re.I)

FERRAMENTAS = "Read,Edit,Write,Glob,Grep,WebSearch,WebFetch"


def material(num, msg):
    """16/10/2026 (ele mandou um reel no chat do #203 para transcrever e o agente caiu na tela de login do Instagram):
    todo link da mensagem é baixado e transcrito em material/<código>/ ANTES de o agente ler. Devolve o texto para o
    agente (transcrição de cada um, ou por que não deu)."""
    import analisar_reel as A
    partes = []
    for link in dict.fromkeys(l.rstrip(".,;)\"'") for l in LINK.findall(msg["texto"])):
        link = link.rstrip(".,;)\"'")
        d = E.pasta(num) / "material" / A.codigo(link)
        try:
            if FOTO.search(link):
                d.mkdir(parents=True, exist_ok=True)
                arq = d / ("foto" + FOTO.search(link).group(1).lower())
                req = urllib.request.Request(link, headers={"User-Agent": "Mozilla/5.0"})
                arq.write_bytes(urllib.request.urlopen(req, timeout=60).read())
                E.evento(num, f"foto baixada: {link} -> material/{d.name}/{arq.name}")
                x = caderno.registrar(num, link, "foto", arquivos=[arq])
                partes.append(f"Link {link}: foto baixada em material/{d.name}/{arq.name} (olhe com Read). Ficha {x['id']}: {x['util']}")
            elif VIDEO.search(link):
                E.mexe_ficha(num, passo="baixando e transcrevendo o vídeo que você mandou", passo_desde=E.agora())
                txt = baixar_video(num, link)
                trans = d / "transcricao.txt"
                x = caderno.registrar(num, link, "vídeo", trans.read_text() if trans.exists() else "",
                                      [d / "video.mp4"] if (d / "video.mp4").exists() else [])
                partes.append(txt + f"\nFicha {x['id']} do caderno: {x['util']}")
            else:
                import fontes
                pag, erro = fontes.texto_da_pagina(link)
                if pag:
                    x = caderno.registrar(num, link, "página", pag)
                    partes.append(f"Link {link}: página lida pelo estúdio. Ficha {x['id']}: {x['util']} (texto inteiro em {x['texto']})")
                else:
                    partes.append(f"Link {link}: é uma página que o estúdio não leu ({erro}); leia com WebFetch.")
        except Exception as ex:
            E.evento(num, f"material não baixou: {link}: {str(ex)[:200]}")
            partes.append(f"Link {link}: o estúdio NÃO conseguiu baixar ({str(ex)[:200]}). Tente ler com WebFetch; se também não der, "
                          "diga isso a ele em uma linha.")
    return "\n\n".join(partes)


def baixar_video(num, link):
    """Áudio, dados, transcrição palavra a palavra e o vídeo inteiro em material/<código>/ (o link que ele manda e,
    desde 17/10/2026, "aprovo o plano agente-baixa", o que o agente acha: ferramentas/baixar.py). Devolve o texto
    para o agente."""
    import analisar_reel as A
    d = E.pasta(num) / "material" / A.codigo(link)
    meta = pauta.baixar(num, link, ref=d, quadros=False)
    trans = pauta.transcrever(num, ref=d)
    if not (d / "video.mp4").exists():   # o vídeo inteiro fica guardado para usar na edição
        A.yt([A.ytdlp(), "-q", "--no-warnings", "-S", "res:1080,br", "-f", "bv+ba/b", "--merge-output-format", "mp4",
              "-o", str(d / "video.%(ext)s"), link], quem="material (vídeo)", capture_output=True, timeout=600)
    tem_video = (d / "video.mp4").exists()
    E.evento(num, f"material baixado e transcrito: {link} -> material/{d.name}" + ("" if tem_video else " (sem o vídeo)"))
    return (f"Link {link}: vídeo {'baixado (material/' + d.name + '/video.mp4) e ' if tem_video else ''}transcrito pelo estúdio "
            f"em material/{d.name}/; quem postou: {meta.get('quem_postou')}; {meta.get('duracao')} s. "
            f"Transcrição com mm:ss (palavra por palavra em palavras.json):\n{trans[:12000]}")


def contexto(num, msg, extra=""):
    fixo, var = contexto_partes(num, msg, extra)
    return fixo + var


PALAVRAS_MAX = 2500      # acima disso (entrevista longa), o tempo de cada palavra fica no arquivo, para abrir se precisar


# 26/10/2026 (ele: "quero poder conversar com o agente discutir ideias de roteiro [...] conversar comigo como um debatedor
# para me ajudar a chegar onde eu quero com o texto"): o modo editor do maestro ("conversar") troca o "Como responder"
# curto por este e manda a conversa inteira do vídeo, não só as últimas 10 mensagens
COMO_EDITOR = """## Como responder (MODO EDITOR: ele quer pensar o roteiro com você)
Você é o editor dele, não um assistente que concorda. Converse como numa reunião de pauta, pelo celular:
- Comece pelo que você acha, direto (concorda, discorda ou "depende"), e por quê, com os fatos do caderno e da
  transcrição que você já tem aqui. Não pesquise de novo o que já está na CHECAGEM; só busque na web fato novo.
- O tom é dele: se ele quer mais duro ou mais crítico, ajude a fazer melhor; risco (processo, ataque ao eleitor) você
  avisa uma vez, curto, mas não barra. Só fato sem prova não vira fato (vira opinião nossa, com o selo).
- Discorde quando a ideia dele enfraquece o vídeo (fato sem prova, tese que um caso só não sustenta, gancho fraco),
  e diga o que faria no lugar.
- Dê de 2 a 3 caminhos CONCRETOS, numerados, cada um com a primeira frase que a voz diria.
- Termine com UMA pergunta que leve ele a decidir.
- Até umas 12 linhas. Sem nome de arquivo, comando ou nome interno.
- NÃO mude o roteiro nesta conversa. Quando ele decidir ("faz assim", "vai pela 2"), o estúdio monta a proposta."""


def contexto_partes(num, msg, extra="", modo=None):
    """19/10/2026 (ele: "o agente esta gastando bastante tokens da assinatura. cuide isso"): medido em 6 respostas, cada
    uma pagava de novo 15 a 25 mil tokens (o pedido inteiro, sem cache) e relia 90 a 190 mil abrindo, a cada vez, a
    checagem, a transcrição e o tempo das palavras. Agora (fixo, variável): o fixo do vídeo (regras, formato, análise,
    transcrição com o tempo de cada palavra) vai primeiro, com a marca de cache (trabalhar, fixo=); o que muda (ficha,
    intenção, roteiro, checagem, conversa, pedido) vai depois. Os arquivos já vêm no texto: ele não precisa abrir."""
    p = E.pasta(num)
    ficha = E.ler_ficha(num)
    conversa = [m for m in E.chat(num) if m["id"] != msg["id"]][-(40 if modo == "editor" else 10):]
    # os detalhes recolhidos na tela (24/10/2026, parte B) continuam aqui: o agente precisa saber o que a conferência achou
    linhas = "\n".join(f"{m['quando'][11:16]} {'ele' if m['quem'] == 'ele' else m['quem']}: {m['texto']}"
                       + (f" [detalhes: {m['detalhes']}]" if m.get("detalhes") else "") for m in conversa)
    ler = lambda n: (p / n).read_text()[:12000] if (p / n).exists() else "(ainda não existe)"
    try:
        ws = json.loads((p / "referencia/palavras.json").read_text())
    except (OSError, ValueError):
        ws = []
    tempos = (" ".join(f"{w[2]}@{w[0]:.2f}" for w in ws) if 0 < len(ws) <= PALAVRAS_MAX
              else "(longa demais para vir aqui: o tempo de cada palavra está em referencia/palavras.json)" if ws else "(não há)")
    # 24/10/2026 (ele: "tem que responder de forma curta"): a seção "Como responder" sai do começo e vai para o FIM do
    # pedido, logo depois da mensagem dele, como no teste que a mediu (0 de 20 respostas com mais de 4 linhas)
    regras = (E.RAIZ / 'regras/AGENTE.md').read_text().replace('<estúdio>', str(E.RAIZ)).replace('<número>', str(int(num)))
    sec = re.search(r"\n## Como responder\n.*?(?=\n## |\Z)", regras, re.S)
    como_responder = sec.group(0).strip() if sec else ""
    regras = regras.replace(sec.group(0), "\n") if sec else regras
    if ficha["etapa"] in ("Pauta", "Roteiro e voz"):        # Etapa C (26/10/2026): as mesmas regras do roteirista
        rot = (E.RAIZ / "regras/ROTEIRISTA.md").read_text()
        partes = re.findall(r"\n## (?:Regras que valem sempre|Formato do vídeo).*?(?=\n## |\Z)", rot, re.S)
        regras += "\n\n# Regras do roteiro (as mesmas do roteirista; valem para todo ajuste no ROTEIRO.md)" + "".join(partes)
    # 26/10/2026 (ele: "pode fazer a parte dos números e comentários pro agente"): onde estão os posts, os números e os
    # comentários da página; o agente lê quando a pergunta precisa (antes dizia que não tinha esses dados)
    try:
        E._ferramentas(); import desempenho
        dados = desempenho.para_agente()
    except Exception as ex:
        E.evento(num, f"dados da página não carregaram: {str(ex)[:150]}"); dados = ""
    fixo = f"""{regras}{E.molde(num)}{E.regra_idioma(num)}{E.memoria(num)}{dados}

## O material do vídeo #{num} (já está aqui: não abra estes arquivos de novo)
ANALISE.md:
{ler('ANALISE.md')}

referencia/transcricao.txt (a fala do vídeo da pauta, mm:ss):
{ler('referencia/transcricao.txt')}

referencia/palavras.json (cada palavra com o segundo em que começa, para os cortes):
{tempos}
"""
    var = f"""
## O vídeo (#{num})
Ficha: {json.dumps({k: ficha.get(k) for k in ('titulo', 'tipo', 'etapa', 'passo', 'esperando', 'link')}, ensure_ascii=False)}

INTENCAO.md:
{ler('INTENCAO.md')}

ROTEIRO.md:
{ler('ROTEIRO.md')}

CHECAGEM.md:
{ler('CHECAGEM.md')}
{caderno.para_pedido(num)}
## A conversa até aqui
{linhas or '(primeira mensagem)'}

## A mensagem dele agora
{msg['texto']}
{("## Material dos links desta mensagem (já baixado e transcrito; use isto, não tente abrir o link)" + chr(10) + extra) if extra else ""}

{COMO_EDITOR if modo == "editor" else como_responder}
"""
    return fixo, var


def passo_legivel(nome, ent, pasta):
    """O que o agente está fazendo, em português, para a tela (como a sessão do terminal mostra)."""
    arq = str(ent.get("file_path") or ent.get("path") or "")
    arq = arq.replace(str(pasta) + "/", "").replace(str(E.RAIZ) + "/", "") if arq else ""
    if nome == "WebSearch":
        return f"buscando na web: {ent.get('query', '')[:90]}"
    if nome == "WebFetch":
        return "lendo a página " + re.sub(r"^https?://(www\.)?", "", str(ent.get("url", "")))[:70]
    if nome == "Read":
        return ("olhando a foto " if re.search(r"\.(jpe?g|png|webp|gif)$", arq, re.I) else "lendo ") + arq[-70:]
    if nome in ("Edit", "Write"):
        return f"mudando o {arq[-60:]}"
    if nome in ("Grep", "Glob"):
        return "procurando nos arquivos do vídeo"
    if nome == "Bash":
        cmd = str(ent.get("command", ""))
        if "baixar.py" in cmd:
            achado = re.search(r"https?://\S+", cmd)
            link = achado.group(0).strip("'\"") if achado else ""
            # 22/10/2026 (agente-baixa-foto): o mesmo comando baixa foto; o site, não o link inteiro
            site = re.sub(r"^https?://(www\.)?", "", link).split("/")[0]
            foto = bool(re.search(r"\.(jpe?g|png|webp)(\?|$)", link, re.I))
            return ("baixando uma foto" if foto else "baixando um vídeo") + (f" de {site}" if site else "")
        if "acervo.py" in cmd and " trazer " in cmd:
            return "trazendo um vídeo do acervo para este vídeo"
        if "acervo.py" in cmd:
            return "procurando no acervo do que já baixamos"
        if "--rostos" in cmd:
            return "tirando quadros de um vídeo da pasta"
        if "--fotos" in cmd:
            return "olhando as fotos de um vídeo baixado"
        if "--capa" in cmd:
            return "tirando a foto das capas"
        if "--sons" in cmd:
            return "conferindo os sons"
        if "--regua" in cmd:
            return "medindo a prévia com a régua"
        if "ver.py" in cmd:
            return "olhando os quadros da prévia"
        # 22/10/2026 ("aprovo o plano chat-trabalhando"; #330: "list material folders", "download the two candidate
        # photos"): a descrição que a IA dá ao comando vem em inglês; o estúdio escreve o passo, em português
        primeiro = cmd.strip().split()[0] if cmd.strip() else ""
        if primeiro in ("ls", "find", "cat", "head", "tail", "grep", "wc", "file", "stat", "du"):
            return "olhando os arquivos do vídeo"
        if primeiro.startswith("python"):
            return "rodando uma ferramenta do estúdio"
        return "trabalhando nos arquivos do vídeo"
    return nome


def progresso_de(nome, ent):
    """16/10/2026 (ele: "colocar um percentual de 0 a 100% para a pessoa saber que está em desenvolvimento"): a etapa do
    animador vira porcentagem (estimativa pela etapa, não pelo tempo): lendo 10, escrevendo 40, olhando quadros 60,
    régua 80 (o resto vem de animacao.animar: antes e depois 88, conferência 95, pronto 100)."""
    cmd = str(ent.get("command", ""))
    # a capa (16/10/2026, "aprovo o plano v2-capa"): quadros do rosto 20, escrevendo 40, olhando a capa 70
    if nome == "Bash" and "--rostos" in cmd:
        return 20
    if nome in ("Write", "Edit") and "capa-" in str(ent.get("file_path", "")):
        return 40
    if nome == "Bash" and "--capa" in cmd:
        return 70
    if nome in ("Write", "Edit") and "cena.html" in str(ent.get("file_path", "")):
        return 40
    if nome == "Bash" and "--assistir" in cmd:          # olhos do animador (18/10/2026)
        return 70
    if nome == "Bash" and "--regua" in cmd:
        return 80
    if nome == "Bash" and "ver.py" in cmd:
        return 60
    return 10


# 25/10/2026 (revisão de solidez): o prazo de verdade de uma chamada (antes, o wait(1200) só vinha depois de a saída
# fechar: um claude -p travado prendia o vídeo para sempre). O animador do jeito de antes chegou a 36 min (#368)
PRAZO_AGENTE = {"agente do chat": 25 * 60}
PRAZO_PADRAO = 60 * 60
# as permissões de arquivo com caminho (revisão de segurança, 25/10/2026) moram no ia.py, a chamada de IA de um lugar só
from ia import LEITURA_DO_ESTUDIO, com_caminho, negadas  # noqa: F401 (os testes e quem chama usam por aqui)


def trabalhar(num, entrada, ferramentas=None, permitidas=None, na_ficha=True, gasto=None, quem="agente do chat", fixo=None,
              modelo="opus"):
    """Roda o agente lendo o que ele faz enquanto faz (16/10/2026, ele: "tinha que mostrar de alguma forma o que o
    agente está fazendo. como acontece com vc aqui. mas gosto de receber resumido o resultado"): cada busca, página,
    arquivo lido ou mudado vira uma linha em ficha["passos"], que a tela mostra embaixo da mensagem dele.
    Devolve (resposta final, código de saída)."""
    p = E.pasta(num)
    # na_ficha=False (17/10/2026, animacao-rapida): as capas rodam junto com a animação e não podem mexer nos passos
    # nem na porcentagem dela
    if na_ficha:
        E.mexe_ficha(num, passos=[], baixados_pedido=0, fotos_pedido=0)     # os limites de download do agente valem por pedido (agente-baixa, agente-baixa-foto)
    # 16/10/2026 (ele: "vamos trocar para o opus"): o chat usa o mesmo modelo do primeiro roteiro, que entende melhor
    # pedido ditado e propõe caminhos; é mais lento que o sonnet. 25/10/2026 (ele: "acho que temos que melhorar" o agente
    # do chat fora do ia.py): a chamada é a de um lugar só (ia.chamar: prazo, gasto, uso da conta, erro e permissões com
    # caminho); daqui só sai o aviso de cada passo para a tela
    import ia
    passos = []

    def ao_evento(ev):
        if ev.get("type") != "assistant":
            return
        for c in (ev.get("message") or {}).get("content") or []:
            if c.get("type") == "tool_use":
                novo = passo_legivel(c.get("name", ""), c.get("input") or {}, p)
                if not passos or passos[-1]["texto"] != novo:      # chat-trabalhando: sem o mesmo passo duas vezes seguidas
                    passos.append({"quando": E.agora(), "texto": novo})
                extra = {}
                if E.ler_ficha(num).get("progresso") is not None:      # só o animador usa a porcentagem
                    extra["progresso"] = max(E.ler_ficha(num)["progresso"], progresso_de(c.get("name", ""), c.get("input") or {}))
                if na_ficha:
                    E.mexe_ficha(num, passos=passos[-8:], **extra)
    # o fixo com a marca de cache (19/10/2026): da 2ª mensagem em diante, na mesma hora, ele sai pelo preço do cache
    pedido = ([{"type": "text", "text": fixo, "cache_control": {"type": "ephemeral", "ttl": "1h"}}, {"type": "text", "text": entrada}]
              if fixo else entrada)
    prazo = PRAZO_AGENTE.get(quem, PRAZO_PADRAO)
    resposta, uso = ia.chamar(pedido, quem, modelo, num=num, limite=prazo, ferramentas=ferramentas or FERRAMENTAS,
                              permitidas=permitidas or [FERRAMENTAS], modo="acceptEdits", cwd=p, dirs=[E.RAIZ / "regras"],
                              ao_evento=ao_evento)
    s = uso.get("s") or {}
    if gasto and s:      # gasto=arquivo (17/10/2026, "aprovo o plano olhos-na-animacao"): os tokens de cada chamada
        with open(gasto, "a") as g:
            g.write(json.dumps({"quando": E.agora(), "quem": "animador", "modelo": modelo, "tokens": s.get("usage"),
                                "equivalente_usd": s.get("total_cost_usd"), "segundos": (s.get("duration_ms") or 0) / 1000}) + "\n")
    if uso["erro"]:
        E.evento(num, f"{quem}: {str(uso['erro'])[:200]}")
    E.evento(num, "o agente fez: " + " · ".join(x["texto"] for x in passos)[:600] if passos else "o agente respondeu sem usar ferramentas")
    return resposta, (1 if uso["erro"] else 0)


def responder(num, msg, aviso="", modelo="opus", modo=None):
    """modelo: quem chama decide. 19/10/2026 (a conversa era 27% do gasto do dia, tudo no Opus): pergunta, opinião,
    pesquisa e material novo vão ao Sonnet; pedido de mudar o roteiro, ao Opus. Desde 22/10/2026 ("aprovo o plano
    roteiro-com-direcao"; ele: "quero que a LLM entenda o que está sendo pedido e não use regex") quem decide é o
    maestro, em todas as etapas; antes, no Roteiro, era o classifica.py (lista de palavras)."""
    p = E.pasta(num)
    foto = E.foto_roteiro(num)
    antes = foto.read_text() if foto else ""
    E.evento(num, f"pedido: {msg['texto'][:200]}")
    # 23/10/2026 (#354 em Aguardando ficou "roteiro pronto"): o passo de antes se guarda ANTES do material(), que troca
    # o passo para "baixando e transcrevendo..." quando a mensagem tem link de vídeo
    f0 = E.ler_ficha(num)
    passo0 = f0["passo"]          # volta a ele no fim (ex.: "voz pronta"); o vigia regrava se o roteiro mudou
    if passo0 == "trabalhando no seu pedido" and f0.get("passo_antes"):
        passo0 = f0["passo_antes"]              # 25/10/2026 (#375): o porteiro já marcou "trabalhando"; vale o de antes dele
    extra = (material(num, msg) if LINK.search(msg["texto"]) else "") + (("\n\n" + aviso) if aviso else "")
    # 26/10/2026 (caderno de material): o arquivo anexado vira ficha antes de o agente responder
    for nome in dict.fromkeys(re.findall(r"📎 anexei o arquivo anexos/([\w.-]+\w)", msg["texto"])):
        try:
            x = caderno.anexo(num, nome)
            extra += f"\n\nAnexo {nome}: ficha {x['id']} do caderno: {x['util']}"
        except Exception as ex:
            E.evento(num, f"caderno: o anexo {nome} não virou ficha: {str(ex)[:150]}")
    if passo0 in ("trabalhando no seu pedido", "baixando e transcrevendo o vídeo que você mandou"):
        # 24/10/2026 (#373: a pauta parou sem baixar e, depois do pedido, ficou "roteiro pronto" sem roteiro nenhum)
        passo0 = "roteiro pronto" if (E.pasta(num) / "ROTEIRO.md").exists() else "parou"
    E.mexe_ficha(num, passo="trabalhando no seu pedido", passo_desde=E.agora(), erro="")
    # 17/10/2026 ("aprovo o plano agente-baixa"): o Bash só abre o comando de baixar vídeo; 18/10 (ele: "da permissão
    # para o agente baixar fotos"): e o de tirar as fotos de um vídeo baixado, só deste número; 22/10: e o quadro da prévia
    fixo, var = contexto_partes(num, msg, extra, modo=modo)
    E.evento(num, f"agente do chat no {modelo}" + (" (modo editor)" if modo else ""))
    resposta, codigo = trabalhar(num, var, fixo=fixo, modelo=modelo, ferramentas=FERRAMENTAS + ",Bash",
                                 permitidas=[FERRAMENTAS, f"Bash(python3 {E.RAIZ / 'ferramentas/baixar.py'}:*)",
                                             # 25/10/2026 ("aprovo o acervo"): o que já baixamos, antes da web
                                             f"Bash(python3 {E.RAIZ / 'ferramentas/acervo.py'} buscar:*)",
                                             f"Bash(python3 {E.RAIZ / 'ferramentas/acervo.py'} trazer {num} :*)",   # o espaço: "trazer 3" não vale para o #37
                                             f"Bash(python3 {E.RAIZ / 'ferramentas/ver.py'} {num} --fotos:*)",
                                             # o quadro da prévia num segundo (enquadramento-automatico, 22/10/2026: "quem
                                             # ajusta não deveria enxergar?"); só os segundos, não o --assistir (que gasta)
                                             *(f"Bash(python3 {E.RAIZ / 'ferramentas/ver.py'} {num} {d}:*)" for d in range(10))])
    if codigo or not resposta:
        resposta = "Não consegui terminar este pedido (o agente parou). Mande de novo, por favor."
    erros = E.confere_roteiro(num) if (p / "ROTEIRO.md").exists() else []
    # 22/10/2026 ("aprovo o plano roteiro-com-direcao"): a fala de outra pessoa só se corta, nunca se troca
    alheias = E.falas_alheias(num, antes) if (p / "ROTEIRO.md").exists() and not erros else []
    if (erros or alheias) and foto:
        E._grava(p / "ROTEIRO.md", antes)          # atômico (25/10/2026): o vigia lia o roteiro pela metade
        E.evento(num, "a mudança quebrou o roteiro, voltei a versão anterior: " + "; ".join(erros + alheias))
        if alheias:
            resposta = ("Não mudei: a mudança trocava palavras da fala de outra pessoa, e isso não pode (" + "; ".join(alheias)[:400]
                        + "). Dá para cortar o trecho, ou mudar a nossa fala em volta dele. O roteiro ficou como estava.")
        else:
            resposta = "A mudança deixou o roteiro com defeito, então voltei como estava. Pode repetir o pedido com outras palavras?"
        mud = []
    else:
        mud = E.mudados(antes, num) if foto else []
        if mud and f0["etapa"] in ("Pauta", "Roteiro e voz"):
            resposta = _mesmas_regras(num, antes, resposta, fixo, modelo)
            mud = E.mudados(antes, num)
    # 17/10/2026 (#204): o vigia marca "gravando a voz" quando o roteiro muda em Roteiro e voz, mas o fim desta resposta
    # devolvia o passo de antes e apagava a marcação (a voz nunca regravava). Roteiro mudou em Roteiro e voz: grava.
    f_ = E.ler_ficha(num)
    if f_["passo"] == "gravando a voz" or (mud and f_["etapa"] == "Roteiro e voz"):
        passo0 = "gravando a voz"
    E.mexe_ficha(num, passo=passo0,
                 passo_desde=E.agora(), mudou=mud)
    E.chat_add(num, "agente", resposta, responde=msg["id"])
    E.evento(num, f"respondido ({len(mud)} bloco(s) mudaram)")


def _mesmas_regras(num, antes, resposta, fixo, modelo):
    """Etapa C da revisão do roteirista (26/10/2026, ele: "pode seguir"): o ajuste passa pela conferência do roteirista.
    Travessão e @ se consertam no texto; problema NOVO (que o roteiro de antes não tinha: duração, corte no meio da
    frase, fala nossa faltando) volta ao agente uma vez; se ficar, vai como aviso na resposta."""
    feitos = pauta.conserta_roteiro_md(num)
    if feitos:
        E.evento(num, "ajuste: consertado no texto: " + ", ".join(feitos))
    ja = {pauta.tipo_do_erro(e) for e in pauta.regras_quebradas(num, antes)}
    novos = lambda: [e for e in pauta.regras_quebradas(num) if pauta.tipo_do_erro(e) not in ja]
    # volta ao agente só o que é defeito do texto (corte no meio da frase, palavras que não estão na fala, fala nossa
    # faltando); a duração e o resto viram aviso, porque podem ser o que ele pediu ("põe a fala do Lula" alonga o vídeo)
    conserta = lambda es: [e for e in es if re.search(r"meio da frase|palavras|fala nossa vazia|falas nossas", e)]
    ns = novos()
    if not conserta(ns):
        if ns:
            E.evento(num, "ajuste: aviso: " + "; ".join(ns))
            return resposta + "\n\nAtenção: " + "; ".join(ns) + "."
        return resposta
    E.evento(num, "ajuste quebrou regra do roteiro, pedindo para corrigir: " + "; ".join(conserta(ns)))
    trabalhar(num, "O seu ajuste no ROTEIRO.md deixou estes problemas, que a conferência do roteiro recusa: " + "; ".join(conserta(ns))
              + ". Corrija SÓ isso no ROTEIRO.md, sem desfazer o que ele pediu. Responda em uma linha o que corrigiu.",
              fixo=fixo, modelo=modelo, ferramentas=FERRAMENTAS, permitidas=[FERRAMENTAS], quem="agente do chat (regras)")
    pauta.conserta_roteiro_md(num)
    ns = novos()
    if ns:
        E.evento(num, "ajuste: ficou assim (aviso): " + "; ".join(ns))
        return resposta + "\n\nAtenção: " + "; ".join(ns) + "."
    return resposta


def rodar(num):
    for msg in E.pendentes(num):
        responder(num, msg)


if __name__ == "__main__":
    rodar(int(sys.argv[1]))
