"""Servidor do estúdio v2, só no Mac (16/10/2026, "faz local primeiro. so aqui no mac").

  python3 servidor.py            http://127.0.0.1:4400

Uma tela (web/index.html) e uma API pequena. Cada vídeo tem um trabalhador próprio que faz a pauta (pauta.py) e
responde o chat (agente.py), um pedido de cada vez. Ao subir, o servidor retoma o que ficou pela metade: pauta que
não terminou e mensagem sem resposta.
"""
import hashlib, json, os, re, shutil, subprocess, sys, threading, time, traceback
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse, parse_qs

import estudio as E
import entrada
import pauta, agente, voz, animacao, capa, legenda_post, render, publicar, numeros, olhos_ponte
import maestro
import regras_tela
import passos as MAPA
import canal, stories
import olho_unico

WEB = E.RAIZ / "web"
PORTA = int(sys.argv[1]) if len(sys.argv) > 1 else 4400
LINK = re.compile(r"https?://\S+")
TIPOS_ARQ = {".html": "text/html; charset=utf-8", ".png": "image/png", ".js": "text/javascript", ".css": "text/css",
             ".jpg": "image/jpeg", ".svg": "image/svg+xml", ".json": "application/json"}
_trabalhando = {}                 # número -> thread viva
_relendo = set()                  # vídeos em que as fontes estão sendo conferidas
_guarda = threading.Lock()
# os nomes por onde ele entra além de 127.0.0.1/localhost (o Caddy repassa o Host); V2_HOSTS acrescenta outros
PARECIDO = re.compile(r"\b(parecid[oa]|igual a (este|esse|isso)|um igual|nesse estilo|no mesmo estilo|na mesma linha|"
                      r"inspirad[oa] nes[st]e|usa(r)? (como|de) refer[eê]ncia|como refer[eê]ncia)\b", re.I)
HOSTS_NOSSOS = {"admin.newsbr360.com", *filter(None, os.environ.get("V2_HOSTS", "").lower().split(","))}
EM_ANDAMENTO = ("recebida", "baixando o áudio", "baixando o vídeo", "transcrevendo", "transcrevendo e assistindo",
               "baixando o material", "lendo o material", "escrevendo o roteiro")       # material: material-qualquer (17/10)
GRAVANDO = "gravando a voz"
ANIMANDO = "animando"
VOZ_PROBLEMA = "Voz com problema"
# 22/10/2026 ("aprovo o plano voz-parou-com-botao"; #334 e #344: depois de "voz parou" não havia botão nenhum e o #344 só
# destravou mudando o roteiro): a voz que parou espera o botão de gravar de novo
GRAVAR_DE_NOVO = "Gravar a voz"
CAPANDO = "fazendo as capas"
LEGENDANDO = "escrevendo a legenda"
RENDERIZANDO = "gerando o vídeo final"
PRONTO = "vídeo final pronto"
PUBLICANDO = "publicando"
# 25/10/2026 (plano de melhorias, 2.5): os nomes de passo daqui têm de existir no mapa (passos.py); um nome mudado só
# de um lado deixava o vídeo num passo que a tela e o religar não conheciam. Falha ao subir, não no meio do trabalho.
assert {*EM_ANDAMENTO, GRAVANDO, ANIMANDO, CAPANDO, LEGENDANDO, RENDERIZANDO, PRONTO, PUBLICANDO} <= set(MAPA.PASSOS), \
    "passo do servidor fora do mapa"
# V2_PUBLICAR_SIMULA=1 (só em servidor de teste, 16/10/2026): o botão Publicar roda o publicador em simulação
SIMULA = os.environ.get("V2_PUBLICAR_SIMULA") == "1"
# 24/10/2026 ("pode fazer tudo isso"; a prova numa cópia da VPS): no modo prova o estúdio sobe, religa as fichas pelo mapa
# e mostra as telas, mas não trabalha sozinho (nada de IA, voz, animação ou vídeo final) e nunca publica
PROVA = os.environ.get("V2_PROVA") == "1"
ESPERA_OPINIAO = 45      # s sem mudar no roteiro antes de conferir as fontes (19/10/2026, vigia_roteiros)
# 26/10/2026 (ele: "limpa a segunda opinião. não vamos reconstruir ela depois. limpa tudo dela"): a segunda opinião
# (monitor.py, desligada desde 23/10) saiu inteira; nos mesmos momentos fica só a conferência das fontes


def ja_lido(n):
    """As fontes deste roteiro já foram conferidas."""
    return (E.pasta(n) / "fontes.json").exists()


# 25/10/2026 (revisão de solidez): o pedido que quebra o trabalhador voltava sem fim (o finally via a mensagem sem resposta
# e subia outro trabalhador, que pegava a mesma), pagando o maestro a cada volta e sem nada no chat. Na 2ª falha do mesmo
# pedido (ou do mesmo passo), o estúdio desiste: responde com o erro e devolve o vídeo a um passo de espera
_falhas = {}


def desiste(num, erro):
    """Conta a falha; na 2ª do mesmo pedido/passo, responde no chat e tira o vídeo do trabalho. True = desistiu."""
    f = E.ler_ficha(num)
    pend = E.pendentes(num)
    chave = (num, pend[0]["id"] if pend else "passo:" + str(f.get("passo")))
    _falhas[chave] = _falhas.get(chave, 0) + 1
    if _falhas[chave] < 2:
        return False
    curto = (erro.strip().splitlines() or ["?"])[-1][:200]
    if pend:
        E.chat_add(num, "agente", f"Não consegui fazer este pedido: o estúdio deu erro duas vezes nele ({curto}). Mande de novo, "
                                  "de outro jeito, ou peça para eu olhar o erro.", responde=pend[0]["id"])
    if f["passo"] in MAPA.TRABALHANDO + EM_ANDAMENTO:
        etapa = f["etapa"]
        if etapa == "Aguardando" and f["passo"] == RENDERIZANDO:
            destino = "o vídeo final parou"
        elif etapa == "Pauta" and not (E.pasta(num) / "ROTEIRO.md").exists():
            destino = "parou"
        else:                                    # o passo de espera da etapa (o mesmo do religar sem mensagem)
            destino = MAPA.religar("trabalhando no seu pedido", etapa) or "parou"
        espera = {"prévia pronta": esperando_animacao(num) if destino == "prévia pronta" else "", "vídeo final pronto": "Publicar",
                  "roteiro pronto": "Aprovar o roteiro" if etapa == "Pauta" else ""}.get(destino, "")
        E.mexe_ficha(num, passo=destino, passo_desde=E.agora(), esperando=espera, erro=f"parou com erro duas vezes: {curto}")
    E.evento(num, f"desisti depois de 2 falhas ({chave[1]}): {curto}")
    return True


def trabalhador(num):
    desistiu = False
    try:
        f = E.ler_ficha(num)
        if f["etapa"] == "Pauta" and f["passo"] in EM_ANDAMENTO:
            try:
                pauta.rodar(num)
            except Exception:
                traceback.print_exc()
        while E.pendentes(num) or E.ler_ficha(num)["passo"] in (GRAVANDO, ANIMANDO, CAPANDO, LEGENDANDO, RENDERIZANDO, PUBLICANDO) \
                or (E.ler_ficha(num).get("pedido_guardado") and E.ler_ficha(num)["etapa"] == "Animação"):
            if E.ler_ficha(num)["passo"] == RENDERIZANDO:
                gerar_final(num)
                continue
            if E.ler_ficha(num)["passo"] == PUBLICANDO:
                publicar_agora(num)
                continue
            if E.ler_ficha(num)["etapa"] == "Animação":
                pend = E.pendentes(num)
                passo = E.ler_ficha(num)["passo"]
                # 21/10/2026 ("aprovo o plano agente-maestro"): capas e legenda que o estúdio faz sozinho saem primeiro; cada
                # mensagem dele vai ao maestro, que decide pelo contexto (antes: listas de palavras). Maestro sem resposta:
                # o caminho de antes, abaixo
                # 23/10/2026 ("aprovo o plano travas-da-verificacao"; o revisor: "Gravar a voz" na Animação reanimava o vídeo
                # inteiro): a voz que parou ou a que ele ouviu e aprovou voltam ao bloco que mudou, não à animação toda
                if passo == GRAVANDO and not pend:
                    refazer_bloco(num, E.ler_ficha(num).get("blocos_regravar") or [])
                    continue
                if passo == ANIMANDO and E.ler_ficha(num).get("ajustar_blocos") and not pend:
                    ajustar_bloco(num, E.ler_ficha(num)["ajustar_blocos"])
                    continue
                guardado = E.ler_ficha(num).get("pedido_guardado")
                if guardado and not pend and passo not in (GRAVANDO, ANIMANDO, CAPANDO, LEGENDANDO):
                    if not maestro_atende(num, guardado):
                        E.chat_add(num, "agente", "Não consegui atender o pedido guardado agora (o estúdio não respondeu). "
                                                  "Pode mandar de novo?", responde=guardado["id"])
                    E.mexe_ficha(num, pedido_guardado=None)
                    continue
                if passo == LEGENDANDO and not pend:
                    fazer_legenda(num, msg=None)
                elif passo == CAPANDO and not pend:
                    fazer_capas(num, msg=None)
                elif pend and maestro_atende(num, pend[0]):
                    pass
                elif pend:
                    # 21/10/2026 ("aprovo o plano pedido-limpo"): o maestro já tenta 2 vezes; sem resposta dele, o chat
                    # pergunta. A rede de antes (listas de palavras de capa, legenda e fala) era o que errava no #306
                    E.chat_add(num, "agente", "Não consegui entender este pedido agora (o estúdio não respondeu). Pode "
                                              "mandar de novo?", responde=pend[0]["id"])
                    E.mexe_ficha(num, passo="prévia pronta", passo_desde=E.agora(), esperando=esperando_animacao(num))
                else:
                    animar(num)
                continue
            pend = E.pendentes(num)
            if pend and E.ler_ficha(num)["etapa"] in maestro.ETAPAS_ROTEIRO:
                # 22/10/2026 ("aprovo o plano roteiro-com-direcao"): no roteiro também é o maestro quem entende o pedido
                if not roteiro_atende(num, pend[0]):
                    E.chat_add(num, "agente", "Não consegui entender este pedido agora (o estúdio não respondeu). Pode "
                                              "mandar de novo?", responde=pend[0]["id"])
            elif pend and E.ler_ficha(num)["etapa"] in maestro.ETAPAS_APROVADO and aprovado_atende(num, pend[0]):
                pass
            elif pend:
                # Publicação e Publicado: conversa (no Sonnet; antes o classifica.py escolhia por lista de palavras); só
                # quando o maestro não respondeu (24/10/2026: agora o maestro atende também aqui, em aprovado_atende)
                responder_sem_mexer(num, pend[0])
            if E.ler_ficha(num)["passo"] == GRAVANDO:
                gravar_voz(num)
    except Exception:
        traceback.print_exc()
        E.evento(num, "trabalhador parou: " + traceback.format_exc()[-300:])
        try:
            desistiu = desiste(num, traceback.format_exc())
        except Exception:
            traceback.print_exc()
    finally:
        with _guarda:
            _trabalhando.pop(num, None)
        if not desistiu and (E.pendentes(num) or E.ler_ficha(num)["passo"] in EM_ANDAMENTO):
            garantir(num)          # chegou mensagem enquanto saía


def voltar_roteiro(num):
    """17/10/2026 ("aprovo o plano voltar-ao-roteiro"; anim.1, #298: o agente prometeu "volta para a etapa do roteiro" e
    não havia esse caminho): da Animação (ou da Publicação, antes de publicar) de volta à Pauta, esperando "Aprovar o
    roteiro". Capa e legenda ficam. Depois: aprova o roteiro, a voz regrava o que mudou, aprova a voz e a animação é
    refeita inteira (refazer_animacao)."""
    f = E.ler_ficha(num)
    if f["etapa"] not in ("Animação", "Aguardando"):
        return False, "só dá para voltar ao roteiro da Animação ou da Publicação"
    if f["passo"] in MAPA.TRABALHANDO:                # mapa-de-passos: antes, uma 7ª cópia da lista
        return False, "o estúdio está trabalhando neste vídeo; espere terminar"
    E.mexe_ficha(num, etapa="Pauta", passo="roteiro pronto", passo_desde=E.agora(), esperando="Aprovar o roteiro", erro="",
                 refazer_animacao=True, mudou=[], blocos_regravar=None, ajustar_blocos=None)
    E.evento(num, "voltou ao roteiro (pedido dele)")
    E.chat_add(num, "sistema", "Voltei ao roteiro. Peça as mudanças aqui; quando estiver bom, toque em Aprovar o roteiro. "
                               "A voz regrava o que mudou e a animação é refeita inteira. A capa continua; a legenda do post "
                               "é da versão anterior: se o roteiro mudar muito, peça \"refaz a legenda\".")
    return True, ""


_PEND = object()          # "pegue a mensagem pendente", como era antes do maestro


def maestro_atende(num, msg):
    """21/10/2026 ("aprovo o plano agente-maestro"): o maestro decide (maestro.decidir) e aqui se executa, com as mesmas
    funções de antes. Pergunta: responder. Dúvida: a pergunta dele vai ao chat e nada roda. Ordem: as ferramentas na
    ordem, cada uma com a instrução do maestro (e a mensagem dele junto). Devolve False se o maestro não respondeu (o
    trabalhador segue pelo caminho de antes)."""
    E.mexe_ficha(num, passo="trabalhando no seu pedido", passo_desde=E.agora(), erro="", pedido_desde=E.agora())
    d = maestro.decidir(num, msg["texto"], msg_id=msg["id"])
    if not d:
        E.evento(num, "maestro não respondeu; caminho de antes")
        return False
    seq = " → ".join(a["ferramenta"] for a in d.get("acoes") or []) or "-"
    E.evento(num, f"maestro ({d.get('segundos')} s): {d.get('intencao')} · {seq} · {str(d.get('por_que', ''))[:160]}")
    if d.get("intencao") == "duvida" or not d.get("acoes"):
        E.chat_add(num, "agente", d.get("pergunta_para_ele") or "Não entendi: você quer que eu mude o vídeo, a capa ou só responda?",
                   responde=msg["id"])
        E.mexe_ficha(num, passo="prévia pronta", passo_desde=E.agora(), esperando=esperando_animacao(num))
        return True
    acoes = list(d["acoes"])
    # 21/10/2026 ("aprovo o plano pedido-limpo"; #316 15:52: mudar_fala → ajustar_video animou duas vezes, US$ 0,50 a mais):
    # mudar_fala já ajusta a animação depois da voz nova; o ajustar_video da mesma ordem vai junto nessa passada
    tela_junto = ""
    if any(a["ferramenta"] == "mudar_fala" for a in acoes):
        tela_junto = " ".join((a.get("instrucao") or "").strip() for a in acoes if a["ferramenta"] == "ajustar_video").strip()
        acoes = [a for a in acoes if a["ferramenta"] != "ajustar_video"]
    for a in acoes:
        f, instrucao = a["ferramenta"], (a.get("instrucao") or "").strip()
        texto = msg["texto"] if not instrucao or instrucao == msg["texto"].strip() else \
            f"{instrucao}\n\n(A mensagem dele, para contexto: \"{msg['texto'].strip()[:1500]}\")"
        m = dict(msg, texto=texto)
        if f == "responder":
            conversar(num, m)
        elif f == "mudar_fala":
            mudar_fala(num, m, tela=tela_junto)
        elif f == "ajustar_video":
            animar(num, m)
        elif f == "revisar_video":
            animar(num, m, modo="revisar")
        elif f == "refazer_animacao":
            refazer_do_zero(num, m)
        elif f == "mudar_capa":
            fazer_capas(num, msg=m)
        elif f == "legenda_post":
            fazer_legenda(num, msg=m)
    return True


AVISO_CONVERSA_ROTEIRO = ("ELE QUER CONVERSAR (o maestro decidiu que é pergunta, opinião ou material para olhar): responda, "
                          "pesquise e confira o que ele pediu. NÃO mude ROTEIRO.md nem CHECAGEM.md: recomende e diga que "
                          "aplica quando ele mandar.")
# 26/10/2026 (ele: "eu sempre vou tentar construir textos únicos com base em ideias e referências a outros conteúdos")
AVISO_CONSTRUIR = ("ELE ESTÁ CONSTRUINDO O TEXTO e trouxe uma peça a mais (dado, caso, comparação, ideia ou referência). "
                   "Confira e pesquise na web o que ele pediu ou o que for fato novo. Responda em até 6 linhas: o que achou "
                   "(bate, não bate, não deu para confirmar, com a fonte), onde encaixa no texto (qual parte da proposta ou "
                   "do roteiro) e, se for fraco ou arriscado, diga uma vez, curto. NÃO mude ROTEIRO.md nem CHECAGEM.md e não "
                   "monte proposta. Termine com: \"Anotado. Quando quiser juntar tudo, diga monta.\"")


def roteiro_atende(num, msg):
    """22/10/2026 ("aprovo o plano roteiro-com-direcao"): na Pauta e no Roteiro e voz o maestro decide (maestro.decidir,
    FERRAMENTAS_ROTEIRO) e aqui se executa: responder e ajustar pelo agente do chat; reescrever, propor direções e voltar
    a versão pelo roteirista (pauta.py). Devolve False se o maestro não respondeu."""
    passo0 = E.ler_ficha(num)["passo"]
    if passo0 in ("trabalhando no seu pedido", "escrevendo o roteiro"):
        passo0 = "roteiro pronto"
    # 25/10/2026 (#375: com a voz pronta, a pesquisa pedida no chat voltou a "roteiro pronto" esperando "Aprovar a voz"):
    # o passo de antes fica na ficha, para o agente do chat (que vê "trabalhando no seu pedido") voltar a ele
    E.mexe_ficha(num, passo="trabalhando no seu pedido", passo_desde=E.agora(), erro="", passo_antes=passo0)
    if msg.get("acao") == "aprovar-direcao" and E.ler_ficha(num).get("proposta"):     # o botão vermelho: sem maestro
        d = {"intencao": "ordem", "acoes": [{"ferramenta": "aplicar_proposta", "instrucao": ""}], "segundos": 0,
             "por_que": "botão Aprovar a direção"}
    else:
        d = maestro.decidir(num, msg["texto"], msg_id=msg["id"])
    if not d:
        E.evento(num, "maestro não respondeu (roteiro)")
        E.mexe_ficha(num, passo=passo0, passo_desde=E.agora())
        return False
    seq = " → ".join(a["ferramenta"] + (f"({a['direcao']})" if a.get("direcao") else "") for a in d.get("acoes") or []) or "-"
    E.evento(num, f"maestro ({d.get('segundos')} s): {d.get('intencao')} · {seq} · {str(d.get('por_que', ''))[:160]}")
    if d.get("intencao") == "duvida" or not d.get("acoes"):
        E.chat_add(num, "agente", d.get("pergunta_para_ele") or "Não entendi: você quer que eu mude o roteiro ou só responda?",
                   responde=msg["id"])
        E.mexe_ficha(num, passo=passo0, passo_desde=E.agora())
        return True
    # 26/10/2026 (#408: o reel mandado junto com a mudança de direção não foi baixado e a proposta disse "ainda não vi"):
    # o roteirista não passa pelo agente.material; os links da mensagem viram material do caderno antes dele ler
    if agente.LINK.search(msg["texto"]) and any(a["ferramenta"] in ("propor_mudanca", "reescrever_roteiro", "aplicar_proposta",
                                                                    "propor_direcoes") for a in d["acoes"]):
        E.chat_add(num, "sistema", "Baixando o link que você mandou para o roteirista usar.")
        agente.material(num, msg)
        E.mexe_ficha(num, passo="trabalhando no seu pedido", passo_desde=E.agora())
    for a in d["acoes"]:
        f, instrucao = a["ferramenta"], (a.get("instrucao") or "").strip()
        texto = msg["texto"] if not instrucao or instrucao == msg["texto"].strip() else \
            f"{instrucao}\n\n(A mensagem dele, para contexto: \"{msg['texto'].strip()[:1500]}\")"
        m = dict(msg, texto=texto)
        if f == "responder":
            agente.responder(num, m, aviso=AVISO_CONVERSA_ROTEIRO, modelo="sonnet")
            continue
        if f == "construir":                 # 26/10/2026 (#408): a peça nova é conferida e guardada, sem refazer a proposta
            agente.responder(num, m, aviso=AVISO_CONSTRUIR, modelo="opus")
            continue
        if f == "conversar":                 # 26/10/2026: o editor (Opus, a conversa inteira, sem mudar o roteiro)
            agente.responder(num, m, aviso=AVISO_CONVERSA_ROTEIRO, modelo="opus", modo="editor")
            continue
        if f == "ajustar_roteiro":
            # 25/10/2026: diz como entendeu, para ele corrigir se era mudança de direção
            E.chat_add(num, "sistema", "Entendi como ajuste pequeno (a história do vídeo continua a mesma). Se era mudança "
                                       "de direção, diga \"é mudança de direção\".")
            agente.responder(num, m, modelo="opus")
            continue
        if f == "propor_mudanca":
            E.chat_add(num, "sistema", "Entendi como mudança de direção: montando a proposta (uns 2 minutos).")
        if f == "aplicar_proposta":
            E.chat_add(num, "sistema", "Proposta aprovada. Reescrevendo o roteiro por ela (uns 2 a 4 minutos).")
        if f == "reescrever_roteiro":
            nome = {"checagem": "Checagem", "analise": "Análise", "fazer_igual": "Fazer igual"}.get(a.get("direcao"), "outro ângulo")
            E.chat_add(num, "sistema", f"Reescrevendo o roteiro como {nome} (uns 2 a 4 minutos, o roteirista confere o que for novo).")
        try:
            if f == "reescrever_roteiro":
                resposta = pauta.reescrever(num, a.get("direcao"), texto)
            elif f == "propor_mudanca":
                resposta = pauta.propor_mudanca(num, a.get("direcao"), texto)
                E.mexe_ficha(num, passo=passo0, passo_desde=E.agora())
            elif f == "aplicar_proposta":
                resposta = pauta.aplicar_proposta(num, texto)
            elif f == "propor_direcoes":
                resposta = pauta.propor(num, texto)
                E.mexe_ficha(num, passo=passo0, passo_desde=E.agora())
            else:
                resposta = pauta.voltar_versao(num)
        except Exception as ex:
            traceback.print_exc()
            resposta = f"Não consegui: {str(ex)[:300]}"
            E.mexe_ficha(num, passo=passo0, passo_desde=E.agora())
        E.chat_add(num, "agente", resposta, responde=msg["id"])
    if E.ler_ficha(num)["passo"] == "trabalhando no seu pedido":     # nenhuma ação deixa o vídeo preso neste passo
        E.mexe_ficha(num, passo=passo0, passo_desde=E.agora())
    return True


def refazer_do_zero(num, msg):
    """A animação inteira de novo, com o roteiro e a voz de agora (o que fiz à mão no #306 em 20/10); a cena de agora
    vai para animacao/versoes/ antes."""
    a = E.pasta(num) / "animacao"; cena = a / "cena.html"
    if cena.exists():
        (a / "versoes").mkdir(exist_ok=True)
        shutil.copy2(cena, a / "versoes" / f"cena-antes-do-zero-{time.strftime('%Y%m%d-%H%M%S')}.html"); cena.unlink()
    E.chat_add(num, "agente", "Refazendo a animação do zero, com o roteiro e a voz de agora (uns 12 minutos). A cena de antes "
                              "ficou guardada.", responde=msg["id"])
    animar(num, msg=None)


def animar(num, msg=_PEND, modo=None):
    """16/10/2026 ("aprovo o plano v2-parte3-animacao"): a primeira animação sai sozinha; cada mensagem dele na
    Animação vai ao animador, que responde no chat. msg: a mensagem (com a instrução do maestro), None = sem mensagem."""
    if msg is _PEND:
        pend = E.pendentes(num)
        msg = pend[0] if pend else None
    E.mexe_ficha(num, passo=ANIMANDO, passo_desde=E.agora(), erro="", esperando="")
    # 17/10/2026 ("aprovo o plano animacao-rapida"): na primeira animação, a legenda do post sai AO MESMO TEMPO; ela não
    # mexe na porcentagem da animação. A capa sai logo DEPOIS (21/10/2026, "aprovo o plano capa-depois-da-animacao"):
    # o agente de capa tira a foto dos takes da cena, e em paralelo eles ainda não existiam (#316 ficou sem foto). Sem
    # capas, o fim desta função passa a "fazendo as capas" e o vigia do item as faz (fazer_capas)
    junto = capas_cedo = None
    parar = threading.Event()       # 25/10/2026: a animação não saiu, as capas que esperavam a cena desistem
    if not msg and not capa.opcoes(num):
        junto = threading.Thread(target=capas_e_legenda, args=(num, False), daemon=True); junto.start()
        # 24/10/2026 (animacao-mais-rapida-e-certa): as capas começam assim que a cena existe (os takes que o agente de
        # capa fotografa já estão nela), junto com a régua, os Olhos e o conserto; antes, só depois de tudo (+44 a 65 s)
        inicio = time.time()

        def capas_quando_houver_cena():
            cena = E.pasta(num) / "animacao/cena.html"
            for _ in range(1500):
                if parar.is_set():
                    return
                if cena.exists() and cena.stat().st_mtime >= inicio:
                    capas_e_legenda(num, capas=True, legenda=False)
                    return
                time.sleep(1)
        capas_cedo = threading.Thread(target=capas_quando_houver_cena, daemon=True); capas_cedo.start()
    pedido = msg["texto"] if msg else None
    retomada = (E.ler_ficha(num).get("animacao_pendente") or {}) if not msg else {}
    if retomada.get("pedido"):
        # 25/10/2026 (revisão de solidez): o estúdio religou no meio de uma animação; ela recomeça com o pedido que tinha
        pedido, modo = retomada["pedido"], retomada.get("modo") or modo
        E.evento(num, f"animação retomada depois de religar: {pedido[:160]}")
    if not msg and E.ler_ficha(num).get("refazer_animacao"):
        # 17/10/2026 ("aprovo o plano voltar-ao-roteiro"): o roteiro foi refeito; a cena antiga é ponto de partida
        pedido = ("O ROTEIRO FOI REFEITO (ele voltou ao roteiro, aprovou o novo e a voz foi regravada). Refaça a animação "
                  "INTEIRA para o roteiro e a voz de agora: cada bloco no tempo novo e com o que a coluna Tela pede. Reaproveite "
                  "da cena atual o que ainda servir (peças, fotos, takes), mas não deixe nada do roteiro antigo.")
        E.mexe_ficha(num, refazer_animacao=False)
    falhou = False
    try:
        resposta = animacao.animar(num, pedido, modo=modo)
    except Exception as ex:
        resposta = f"A animação não saiu: {str(ex)[:300]}. A cena ficou como estava; peça de novo."
        traceback.print_exc(); falhou = True; parar.set()
    if msg:
        E.chat_add(num, "agente", resposta, responde=msg["id"])
    elif retomada.get("pedido"):
        E.chat_add(num, "sistema", "O estúdio religou no meio da animação; retomei o que estava fazendo. " + resposta)
    else:
        E.chat_add(num, "sistema", ("" if falhou else "Primeira animação pronta. ") + resposta)
    if falhou and not (E.pasta(num) / "animacao/cena.html").exists():
        # a primeira animação não saiu: sem cena não há capa nem prévia; o vídeo espera ele pedir de novo
        E.mexe_ficha(num, passo="prévia pronta", passo_desde=E.agora(), esperando="", erro="a animação não saiu; peça de novo no chat")
        return
    # 23/10/2026 ("aprovo o plano olho-unico-observacao"): o olho único olha a prévia nova e só mostra no chat
    threading.Thread(target=olho_unico.na_previa, args=(num,), daemon=True).start()
    if junto:
        junto.join(timeout=1200)
    if capas_cedo:
        capas_cedo.join(timeout=1800)         # as capas que começaram cedo terminam antes de decidir o passo seguinte
    # 16/10/2026 ("aprovo o plano v2-capa"): sem capas, elas saem depois (desde 21/10/2026, sempre na primeira animação)
    if capas_cedo and capas_cedo.is_alive():
        # 25/10/2026 (plano de melhorias): elas ainda estão sendo feitas; uma segunda leva ao mesmo tempo gravava por cima
        # e pagava duas vezes. Quando terminarem, ele escolhe na tela
        E.evento(num, "as capas ainda estão sendo feitas depois de 30 min; não começo outra leva")
        E.mexe_ficha(num, passo="prévia pronta", passo_desde=E.agora(), esperando=esperando_animacao(num))
    elif not capa.opcoes(num):
        E.mexe_ficha(num, passo=CAPANDO, passo_desde=E.agora())
    elif not legenda_post.ler(num):
        E.mexe_ficha(num, passo=LEGENDANDO, passo_desde=E.agora())
    else:
        E.mexe_ficha(num, passo="prévia pronta", passo_desde=E.agora(), esperando=esperando_animacao(num))


def capas_e_legenda(num, capas=True, legenda=True):
    """Na primeira animação (17/10/2026, animacao-rapida): a legenda do post junto com ela, as duas capas logo depois."""
    try:
        if capas:
            r = capa.fazer(num, na_ficha=False)
            E.chat_add(num, "sistema", "Duas opções de capa prontas: escolha uma na tela. " + r)
    except Exception:
        traceback.print_exc()
    try:
        if legenda and not legenda_post.ler(num):
            E.chat_add(num, "sistema", legenda_post.fazer(num) + " Ela está na tela, embaixo da capa.")
    except Exception:
        traceback.print_exc()


AVISO_FALA = ("ESTAMOS NA ANIMAÇÃO (17/10/2026, \"aprovo o plano mudar-fala-na-animacao\"): a voz já foi gravada e o vídeo já "
              "está animado. Mude SÓ a fala que ele pediu no ROTEIRO.md (a coluna Fala), sem fato novo e sem mexer nos outros "
              "blocos nem na coluna Tela. O estúdio regrava a voz só desse bloco e o animador ajusta só esse bloco ao tempo novo; "
              "diga em uma linha o que mudou.")


AVISO_CONVERSA = ("ESTAMOS NA ANIMAÇÃO e ele quer CONVERSAR (19/10/2026: \"o agente tem que conseguir conversar comigo, analisar o "
                  "material extra que envio e ver se dá para usar ou não\"). Responda, pesquise e confira o que ele pediu. "
                  "Material novo (anexos/, link baixado em material/): abra e olhe (foto com Read; vídeo com o ver.py --fotos) e diga "
                  "em poucas linhas o que é, se dá para usar, em que bloco, e de onde veio (crédito, data); se for um fato novo, se "
                  "tem fonte confiável. NÃO mude ROTEIRO.md nem CHECAGEM.md enquanto for só conversa: recomende e pergunte. "
                  "Quando ele mandar usar: material na tela → escreva na coluna Tela do bloco o que entra, com o caminho do "
                  "arquivo; fato novo → linha na CHECAGEM.md com a fonte e, se a voz tiver de dizer, a coluna Fala do bloco "
                  "(sem mexer nos outros blocos). O estúdio regrava a voz e o animador aplica sozinhos.")


AVISO_APROVADO = ("O VÍDEO JÁ FOI APROVADO (24/10/2026): o vídeo final está pronto ou no ar. Responda, pesquise e olhe o "
                  "que ele pediu. NÃO mude ROTEIRO.md, CHECAGEM.md, a cena nem a capa: mudança no vídeo só reabrindo a "
                  "animação, pelo botão Reabrir a animação (antes de publicar) ou num vídeo novo (depois).")


def aprovado_atende(num, msg):
    """24/10/2026 ("faz"; o porteiro em Aguardando e Publicado): o maestro decide com as saídas dessas etapas
    (maestro.FERRAMENTAS_APROVADO / _PUBLICADO) e aqui se executa, sem mexer no passo do vídeo (o final pronto continua
    pronto). Pedido de mudar o vídeo vira a oferta de reabrir a animação, e o pedido fica guardado para depois.
    Devolve False se o maestro não respondeu."""
    f0 = E.ler_ficha(num)
    d = maestro.decidir(num, msg["texto"], msg_id=msg["id"])
    if not d:
        E.evento(num, "maestro não respondeu (aprovado)")
        return False
    seq = " → ".join(a["ferramenta"] for a in d.get("acoes") or []) or "-"
    E.evento(num, f"maestro ({d.get('segundos')} s): {d.get('intencao')} · {seq} · {str(d.get('por_que', ''))[:160]}")
    if d.get("intencao") == "duvida" or not d.get("acoes"):
        E.chat_add(num, "agente", d.get("pergunta_para_ele") or "Não entendi: você quer mudar a legenda do post ou o vídeo?",
                   responde=msg["id"])
        return True
    for a in d["acoes"]:
        f, instrucao = a["ferramenta"], (a.get("instrucao") or "").strip()
        texto = msg["texto"] if not instrucao or instrucao == msg["texto"].strip() else \
            f"{instrucao}\n\n(A mensagem dele, para contexto: \"{msg['texto'].strip()[:1500]}\")"
        if f == "responder":
            responder_sem_mexer(num, dict(msg, texto=texto))
        elif f == "legenda_post" and f0["etapa"] == "Aguardando":
            try:
                resposta = legenda_post.fazer(num, texto)
            except Exception as ex:
                traceback.print_exc(); resposta = f"A legenda não mudou: {str(ex)[:300]}"
            E.chat_add(num, "agente", resposta, responde=msg["id"])
        elif f == "reabrir_animacao" and f0["etapa"] == "Aguardando":
            E.mexe_ficha(num, pedido_reabrir={"id": msg["id"], "texto": msg["texto"], "instrucao": instrucao})
            E.chat_add(num, "agente", "Para isso o vídeo precisa voltar para a Animação: o vídeo final pronto deixa de valer e "
                                      "é gerado de novo quando você aprovar outra vez. Toque em Reabrir a animação e eu já "
                                      "começo pelo seu pedido.", responde=msg["id"])
    # o passo do vídeo não muda (o final pronto continua pronto; quem reabre é ele, no botão). 25/10/2026 (revisão de
    # solidez): só volta o passo que o atendimento mexeu; se ele tocou num botão enquanto o maestro decidia (Publicar,
    # Reabrir a animação), o toque vale (antes, o passo de antes era regravado e a publicação sumia calada)
    f1 = E.ler_ficha(num)
    if f1["etapa"] == f0["etapa"] and f1["passo"] in (f0["passo"], "trabalhando no seu pedido",
                                                      "baixando e transcrevendo o vídeo que você mandou"):
        E.mexe_ficha(num, passo=f0["passo"], esperando=f0.get("esperando") or "")
    return True


def responder_sem_mexer(num, msg):
    """A conversa depois de aprovado: se o agente mexer no roteiro, na checagem ou na cena mesmo com o aviso, volta como
    estava (o #354 de 23/10: dividiu um bloco depois da voz gravada e do vídeo final pronto)."""
    p = E.pasta(num)
    arqs = [p / "ROTEIRO.md", p / "CHECAGEM.md", p / "animacao/cena.html"]
    antes = {a: a.read_bytes() for a in arqs if a.exists()}
    agente.responder(num, msg, aviso=AVISO_APROVADO, modelo="sonnet")
    mexeu = [a.name for a, b in antes.items() if not a.exists() or a.read_bytes() != b]
    for a in arqs:
        if a in antes and (not a.exists() or a.read_bytes() != antes[a]):
            a.write_bytes(antes[a])
    if mexeu:
        E.mexe_ficha(num, mudou=[])
        E.evento(num, "o agente mexeu em " + ", ".join(mexeu) + " depois de aprovado; voltei como estava")


def reabrir_animacao(num):
    """24/10/2026: Aguardando → Animação, pelo botão dele. O vídeo final de antes deixa de valer (sai de novo depois de
    aprovar); o pedido guardado pelo porteiro vai ao maestro da Animação."""
    f = E.ler_ficha(num)
    if f["etapa"] != "Aguardando" or f["passo"] in (RENDERIZANDO, PUBLICANDO):
        return False, "este vídeo não está esperando publicação (ou o vídeo final está sendo gerado)"
    pedido = f.get("pedido_reabrir")
    E.mexe_ficha(num, etapa="Animação", passo="prévia pronta", passo_desde=E.agora(), esperando="", pedido_reabrir=None, erro="")
    E.mexe_ficha(num, esperando=esperando_animacao(num))
    E.evento(num, "animação reaberta por ele (o vídeo final de antes deixou de valer)")
    E.chat_add(num, "sistema", "Animação reaberta. O vídeo final de antes deixou de valer; ele sai de novo quando você aprovar o vídeo.")
    if pedido:
        # 25/10/2026 (revisão de solidez): o pedido guardado fica na ficha e o trabalhador do vídeo o atende (antes, um
        # thread solto: podia rodar junto com outro pedido no mesmo cena.html, e o religar o perdia)
        E.mexe_ficha(num, pedido_guardado={"id": pedido["id"], "texto": pedido["texto"]})
        garantir(num)
    return True, ""


def conversar(num, msg=None):
    """19/10/2026 (ele: "quero poder pedir para revisar coisas, enviar outros materiais para inserir no vídeo"): na
    Animação, pergunta, revisão e material novo vão ao agente do chat (pesquisa e olha o material), não ao animador.
    Se ele mandou usar e o roteiro mudou: fala mudou → regrava e ajusta (como mudar_fala); só a Tela → o animador aplica.
    msg: a mensagem com a instrução do maestro (sem ela, a pendente)."""
    msg = msg or E.pendentes(num)[0]
    antes = {b["n"]: b for b in E.blocos(num)}
    agente.responder(num, msg, aviso=AVISO_CONVERSA, modelo="sonnet")
    mud = E.ler_ficha(num).get("mudou") or []
    if not mud:
        E.mexe_ficha(num, passo="prévia pronta", passo_desde=E.agora(), esperando=esperando_animacao(num))
        return
    agora = {b["n"]: b for b in E.blocos(num)}
    falas = [n for n in mud if n not in antes or n not in agora or antes[n]["fala"] != agora[n]["fala"]]
    if falas:
        return refazer_bloco(num, falas)
    telas = "; ".join(f"bloco {n}: {agora[n]['tela']}" for n in mud if n in agora)
    E.chat_add(num, "sistema", f"Pondo na tela o que ficou combinado (bloco {', '.join(map(str, mud))}).")
    E.mexe_ficha(num, passo=ANIMANDO, passo_desde=E.agora(), esperando="")
    try:
        resposta = animacao.animar(num, f"Ele aprovou na conversa e a coluna Tela mudou ({telas}). Ponha isso na cena, SÓ "
                                        "nesses blocos, sem mexer no resto.")
    except Exception as ex:
        resposta = f"A animação parou: {str(ex)[:300]}"
        traceback.print_exc()
    E.chat_add(num, "sistema", resposta)
    threading.Thread(target=olho_unico.na_previa, args=(num,), daemon=True).start()     # consertos-da-revisao
    E.mexe_ficha(num, passo="prévia pronta", passo_desde=E.agora(), esperando=esperando_animacao(num))


def mudar_fala(num, msg=None, tela=""):
    """17/10/2026 ("aprovo o plano mudar-fala-na-animacao"; o "a doze dias" do #204 ficava na voz depois de a tela
    mudar): na Animação, pedido sobre o que é FALADO muda o roteiro, regrava só o bloco e o animador ajusta só ele."""
    msg = msg or E.pendentes(num)[0]
    agente.responder(num, msg, aviso=AVISO_FALA, modelo="opus")    # o maestro já decidiu que é fala (antes: classifica)
    mud = E.ler_ficha(num).get("mudou") or []
    if not mud:
        if tela:                       # a fala não mudou, mas ele também pediu tela: o ajuste ainda vale
            return animar(num, dict(msg, texto=tela))
        E.mexe_ficha(num, passo="prévia pronta", passo_desde=E.agora(), esperando=esperando_animacao(num))
        return
    refazer_bloco(num, mud, tela=tela)


def refazer_bloco(num, mud, tela=""):
    """A fala dos blocos mud mudou: regrava a voz e o animador ajusta só eles."""
    blocos = ", ".join(map(str, mud)) or "que mudou"
    E.chat_add(num, "sistema", f"Regravando a voz do bloco {blocos} e depois ajustando a animação desse bloco (uns 5 minutos).")
    E.mexe_ficha(num, passo=GRAVANDO, passo_desde=E.agora(), erro="", esperando="", blocos_regravar=list(mud))
    try:
        r = voz.gravar(num)
    except Exception as ex:
        traceback.print_exc()
        E.mexe_ficha(num, passo="voz parou", erro=str(ex)[:300], esperando=GRAVAR_DE_NOVO)
        E.chat_add(num, "sistema", f"A voz não saiu: {str(ex)[:300]}. Para tentar de novo, toque em Gravar a voz.")
        return
    # consertos-da-revisao: sem o número do bloco (o "Gravar a voz" de uma voz que parou), vale o que a voz regravou agora
    mud = list(mud) or list(r.get("novas") or [])
    E.mexe_ficha(num, blocos_regravar=mud)
    if r["problemas"]:
        # travas-da-verificacao: com o aviso na tela (Consertar ou Ouvi, está ok), como na etapa Roteiro e voz
        E.mexe_ficha(num, passo="voz com problema", erro=" · ".join(r["problemas"])[:400], esperando=VOZ_PROBLEMA)
        E.chat_add(num, "sistema", "A voz foi regravada, mas a conferência achou problema: " + " · ".join(r["problemas"])
                   + ". Ouça no player: toque em Consertar, ou, se estiver ok, em Ouvi, está ok.")
        return
    ajustar_bloco(num, mud, tela, r)


def ajustar_bloco(num, mud, tela="", r=None):
    """A voz dos blocos mud está regravada: o animador ajusta só eles (a 2ª metade do refazer_bloco; também depois do
    "Ouvi, está ok" na Animação)."""
    blocos = ", ".join(map(str, mud)) or "que mudou"
    E.mexe_ficha(num, passo=ANIMANDO, passo_desde=E.agora(), esperando="", ajustar_blocos=None, blocos_regravar=None)
    try:
        resposta = animacao.animar(num, f"A fala do bloco {blocos} mudou e a voz foi regravada (o tempo desse bloco e dos "
                                        f"seguintes mudou). Ajuste SÓ o bloco {blocos} à voz nova (confira os instantes e o que "
                                        "estiver em tempo fixo) e confira que os blocos seguintes continuam no lugar; não mude "
                                        "o desenho dos outros blocos." + (f" Ele também pediu, na tela: {tela}" if tela else ""))
    except Exception as ex:
        resposta = f"A animação parou: {str(ex)[:300]}"
        traceback.print_exc()
    dur = r["duracao"] if r else json.loads((E.pasta(num) / "narracao/completo.json").read_text())["duracao"]
    E.chat_add(num, "sistema", f"Voz do bloco {blocos} regravada ({dur:.0f} s no total) e animação ajustada. " + resposta)
    threading.Thread(target=olho_unico.na_previa, args=(num,), daemon=True).start()     # consertos-da-revisao
    E.mexe_ficha(num, passo="prévia pronta", passo_desde=E.agora(), esperando=esperando_animacao(num))


def esperando_animacao(num):
    """O que a Animação espera dele (16/10/2026, "aprovo o plano v2-aprovar-video"): escolher a capa, e com capa,
    legenda e régua em ordem, aprovar o vídeo."""
    if capa.opcoes(num) and capas_json(num)["escolhida"] is None:
        return "Escolher a capa"
    return "Aprovar o vídeo" if not faltas_aprovar(num) else ""


def graves_regua(num):
    """Os problemas graves que a última conferência deixou ("3,5 s · escondido · …"); [] sem conferência ou sem grave."""
    import animador_novo
    cf = E.pasta(num) / "animacao/conferencia.json"
    regua = json.loads(cf.read_text()).get("regua", []) if cf.exists() else []
    # 22/10/2026 ("aprovo o plano chat-trabalhando"; #330: "0,2 s · escondido · 'FOTO DA VEJA' coberta por cena", medido
    # antes de existir capa): com a capa escolhida, ela cobre a tela inteira de 0 até T.capa(ate); o que a régua viu
    # embaixo dela não vale (a conferência fica guardada de antes da capa, então o filtro é aqui, na leitura).
    # 22/10 ("aprovo o plano enquadramento-automatico"; #332: "centro-vazio aos 0 s" antes de escolher a capa): vale
    # também sem a capa escolhida, porque todo vídeo sai com uma capa nesse tempo
    cena = E.pasta(num) / "animacao/cena.html"
    m = re.search(r"T\.capa\(\s*([\d.]+)", cena.read_text()) if cena.exists() else None
    if m:
        ate = float(m.group(1))
        # 23/10/2026 ("aprovo o plano consertos-da-revisao"): o erro de código vem marcado em 0 s e caía neste filtro
        regua = [x for x in regua if x.get("tipo") == "erro" or not (x.get("de", 0) < ate - .05 and (x.get("ate") or x.get("de", 0)) <= ate + .3)]
    return [f"{x.get('de', 0):.1f} s · {x['tipo']} · {x.get('msg', '')}" for x in regua if animador_novo.grave(x)]


def faltas_aprovar(num, mesmo_assim=False):
    """O que falta para aprovar o vídeo; lista vazia = pode aprovar. mesmo_assim: ele viu o grave que a régua deixou
    e aprova assim (o botão "Aprovar mesmo assim", 21/10/2026, "aprovo o plano pedido-limpo")."""
    f = E.ler_ficha(num); falta = []
    if f["etapa"] != "Animação":
        return ["o vídeo não está na Animação"]
    if f["passo"] in (ANIMANDO, CAPANDO, LEGENDANDO) or E.pendentes(num):
        falta.append("o agente está trabalhando")
    if not (E.pasta(num) / "animacao/cena.html").exists():
        falta.append("falta a animação")
    # travas-da-verificacao: a voz regravada tem que estar conferida (antes, a voz nova com problema e a animação velha
    # passavam)
    if f["passo"] == "voz parou":
        falta.append("a voz parou: toque em Gravar a voz")
    elif f["passo"] == "voz com problema":
        falta.append("a voz tem aviso: ouça e toque em Consertar ou em Ouvi, está ok")
    elif f.get("blocos_regravar") is not None:
        # consertos-da-revisao: a voz foi regravada e a animação do bloco ainda não foi ajustada (antes, um "mudar a
        # capa" no meio levava o passo a "prévia pronta" e a trava sumia)
        falta.append(f"a voz do bloco {', '.join(map(str, f['blocos_regravar'])) or 'que mudou'} foi regravada: falta ajustar a animação dele")
    # (comparar a marca do ROTEIRO.md inteiro não serve aqui: na Animação a coluna Tela muda sem mudar a voz)
    if capas_json(num)["escolhida"] is None:
        falta.append("escolher a capa")
    lg = legenda_post.ler(num)
    if not lg:
        falta.append("falta a legenda do post")
    elif lg["erros"]:
        falta.append("a legenda não passa no portão: " + "; ".join(lg["erros"]))
    cf = E.pasta(num) / "animacao/conferencia.json"
    regua = json.loads(cf.read_text()).get("regua", []) if cf.exists() else None
    if regua is None:
        falta.append("a animação ainda não foi conferida")
    elif regua:
        # 19/10/2026 (ele: "pra mim está bom", "quero aprovar"; só letra pequena na montagem): só o grave trava;
        # letra pequena, rótulos empilhados e meio segundo vazio ficam como aviso (animador_novo.GRAVES)
        # consertos-da-revisao: erro de código na cena trava mesmo com "Aprovar mesmo assim" (o vídeo final recusa depois)
        if any(x.get("tipo") == "erro" for x in regua):
            falta.append("a animação tem erro de código: peça o conserto no chat")
        graves = [g for g in graves_regua(num) if " · erro · " not in g]
        if graves and not mesmo_assim:
            falta.append("a régua achou: " + "; ".join(graves[:3]))
    return falta


def fazer_legenda(num, msg=None):
    """16/10/2026 ("aprovo o plano v2-aprovar-video"): o agente escreve a legenda do post (regras/LEGENDA.md), ou muda
    pelo pedido dele quando a mensagem fala da legenda do post. msg: a do maestro; None = sem mensagem."""
    E.mexe_ficha(num, passo=LEGENDANDO, passo_desde=E.agora(), erro="", esperando="")
    try:
        resposta = legenda_post.fazer(num, msg["texto"] if msg else None)
    except Exception as ex:
        resposta = f"A legenda parou: {str(ex)[:300]}"
        traceback.print_exc()
    if msg:
        E.chat_add(num, "agente", resposta, responde=msg["id"])
    else:
        E.chat_add(num, "sistema", resposta + " Ela está na tela, embaixo da capa.")
    E.mexe_ficha(num, passo="prévia pronta", passo_desde=E.agora(), esperando=esperando_animacao(num))


def gerar_final(num):
    """16/10/2026 ("aprovo o plano v2-parte4-publicar"): depois de aprovado, o vídeo final sai sozinho e é conferido."""
    E.mexe_ficha(num, passo=RENDERIZANDO, passo_desde=E.agora(), erro="", esperando="", progresso=5, passos=[])
    try:
        conf = render.fazer(num)
    except Exception as ex:
        traceback.print_exc()
        E.mexe_ficha(num, passo="o vídeo final parou", erro=str(ex)[:300], progresso=None)
        E.chat_add(num, "sistema", f"O vídeo final não saiu: {str(ex)[:300]}")
        return
    if conf["erros"]:
        E.mexe_ficha(num, passo="vídeo final com problema", erro="; ".join(conf["erros"]), progresso=None)
        E.chat_add(num, "sistema", "O vídeo final saiu, mas a conferência achou problema: " + "; ".join(conf["erros"]))
    else:
        avisos = [i["msg"] for i in conf["itens"] if i["nivel"] == "AVISO"]
        E.mexe_ficha(num, passo=PRONTO, passo_desde=E.agora(), progresso=None, esperando="Publicar")
        threading.Thread(target=olhos_no_final, args=(num,), daemon=True).start()
        # 25/10/2026 (ele: "ele tem que olhar o enquadramento e relatar isso para consertar"): o que os Olhos ainda viam
        # na animação aprovada assim mesmo é lembrado antes de publicar, com o caminho do conserto
        try:
            cf = json.loads((E.pasta(num) / "animacao/conferencia.json").read_text())
            sobrou = [f"{x['t']:.1f} s: {str(x['msg'])[:140]}" for x in cf.get("sobrou") or [] if isinstance(x, dict) and "t" in x]
        except (OSError, ValueError, TypeError):
            sobrou = []
        E.chat_add(num, "sistema", f"Vídeo final pronto: {conf['duracao']:.0f} s, volume {conf['lufs']} LUFS, {conf['mb']} MB."
                   + (" Avisos: " + "; ".join(avisos) + "." if avisos else "")
                   + (f" Os Olhos ainda viam na animação: {'; '.join(sobrou[:3])}. Para consertar, toque em Reabrir a animação."
                      if sobrou else "") + " Assista na tela e toque em Publicar.")


def olhos_no_final(num):
    """17/10/2026 ("aprovo o plano olhos"): um espectador independente assiste o vídeo final; só mostra."""
    try:
        op = olhos_ponte.assistir(E.pasta(num) / "publicacao/final.mp4", E.pasta(num) / "publicacao/olhos")
        perde = "; ".join(f"{p['t']:.1f} s: {p['porque']}" for p in (op.get("perderia_atencao") or [])[:4])
        E.chat_add(num, "sistema", f"Olhos (um espectador que não sabe nada do roteiro) assistiu o vídeo final: \"{op.get('entendi', '')}\" "
                   f"Nota para segurar: {op.get('nota_para_segurar')}/10." + (f" Perderia a atenção em {perde}." if perde else ""))
    except Exception:
        traceback.print_exc()


def publicar_agora(num):
    """16/10/2026 (ele: "depois que clicar no botão tem que publicar"): o botão (dois toques) chama isto. Cada linha
    do publicador da VPS vira um passo na tela."""
    passos = []
    def passo(texto):
        if not passos or passos[-1]["texto"] != texto:
            passos.append({"quando": E.agora(), "texto": texto}); E.mexe_ficha(num, passos=passos[-8:])
    E.mexe_ficha(num, passo=PUBLICANDO, passo_desde=E.agora(), erro="", esperando="", passos=[])
    try:
        r = publicar.fazer(num, simular=SIMULA, ao_passo=passo)
    except Exception as ex:
        traceback.print_exc()
        r = {"ok": False, "links": {}, "saida": [str(ex)[:300]]}
    if r["ok"] and SIMULA:
        E.mexe_ficha(num, passo=PRONTO, passo_desde=E.agora(), esperando="Publicar", erro="")
        E.chat_add(num, "sistema", "Ensaio de publicação aprovado (servidor de teste): nada foi enviado à Meta.")
        return
    # 22/10/2026 ("aprovo o plano enquadramento-automatico"; #335: o Instagram saiu às 18:02, o Facebook respondeu 400 e o
    # vídeo ficou em "publicação falhou", com o botão Publicar, que a trava de duplicata recusa): com o Instagram no ar,
    # o vídeo está publicado; o Facebook fica pendente, com o motivo. Não tenta o Facebook de novo sozinho: no #335 a
    # falha veio depois do envio, e o reel pode ter saído (tentar de novo poderia postar duas vezes)
    parcial = not r["ok"] and not SIMULA and bool(r["links"].get("instagram"))
    if r["ok"] or parcial:
        motivo = next((l for l in reversed(r["saida"]) if l.strip()), "") if parcial else ""
        E.mexe_ficha(num, etapa="Publicado", passo="publicado", passo_desde=E.agora(), esperando="", erro="",
                     publicado={"quando": E.agora(), **r["links"], **({"facebook_pendente": motivo[:300]} if parcial else {})})
        # 25/10/2026 ("aprovo o acervo"): o que este vídeo usou entra no acervo (ferramentas/acervo.py, ~1 s, à parte)
        try:
            subprocess.Popen([sys.executable, str(E.RAIZ / "ferramentas/acervo.py"), "juntar"], cwd=E.RAIZ,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            traceback.print_exc()
        E.chat_add(num, "sistema", "Publicado. " + " · ".join(f"{k}: {v}" for k, v in r["links"].items())
                   + (f" O Facebook não saiu ({motivo[:200]}); confira na página do Facebook antes de postar lá à mão." if parcial else ""))
        # 22/10/2026 ("aprovo o plano do canal-whatsapp"): o mesmo vídeo vai ao Canal NewsBR360 do WhatsApp, com o
        # pedido de curtir e compartilhar (canal.py; falhou, o chat recebe o texto pronto para postar à mão)
        if r["links"].get("instagram"):
            # 25/10/2026 (revisão de solidez): canal e Story ficam marcados até terminar; religar no meio avisa no chat
            # (retomar), sem repostar sozinho (podem ter saído)
            E.mexe_ficha(num, pos_publicar=["canal do WhatsApp", "Story"])
            def feito(qual):
                E.mexe_ficha(num, pos_publicar=[x for x in (E.ler_ficha(num).get("pos_publicar") or []) if x != qual])
            def ao_canal():
                try:
                    canal.postar(num)
                except Exception:
                    traceback.print_exc()
                feito("canal do WhatsApp")
                # 22/10/2026 ("aprovo o plano publicar-nos-stories"): depois do canal, o Story dos primeiros 15 s
                try:
                    stories.publicar(num)
                except Exception:
                    traceback.print_exc()
                feito("Story")
            threading.Thread(target=ao_canal, daemon=True).start()
    else:
        motivo = next((l for l in reversed(r["saida"]) if l.strip()), "sem resposta do publicador")
        E.mexe_ficha(num, passo="publicação falhou", erro=motivo[:300], esperando="Publicar",
                     publicado={"parcial": r["links"]} if r["links"] else None)
        E.chat_add(num, "sistema", f"A publicação não terminou: {motivo[:300]}"
                   + (f" Já saiu em: {r['links']}. Confira antes de tocar em Publicar de novo." if r["links"] else ""))


def fazer_capas(num, msg=None):
    """16/10/2026 ("aprovo o plano v2-capa"): o animador faz as duas opções de capa (ou muda pelo pedido dele, quando a
    mensagem fala de capa); ele escolhe na tela. msg: a do maestro; None = sem mensagem."""
    E.mexe_ficha(num, passo=CAPANDO, passo_desde=E.agora(), erro="", esperando="")
    try:
        resposta = capa.fazer(num, msg["texto"] if msg else None)
    except Exception as ex:
        resposta = f"A capa parou: {str(ex)[:300]}"
        traceback.print_exc()
    if msg:
        E.chat_add(num, "agente", resposta, responde=msg["id"])
    else:
        E.chat_add(num, "sistema", "Duas opções de capa prontas: escolha uma na tela. " + resposta)
    if not legenda_post.ler(num):        # depois das capas, a legenda do post sai sozinha
        E.mexe_ficha(num, passo=LEGENDANDO, passo_desde=E.agora(), esperando="")
    else:
        E.mexe_ficha(num, passo="prévia pronta", passo_desde=E.agora(), esperando=esperando_animacao(num))


def gravar_voz(num):
    """16/10/2026 ("aprovo o plano v2-parte2-voz"): grava ou regrava só o que mudou; com o áudio pronto e conferido, o
    vídeo espera "Aprovar a voz"; com problema, fica em Roteiro e voz com o motivo."""
    E.mexe_ficha(num, passo=GRAVANDO, passo_desde=E.agora(), erro="", esperando="")
    try:
        r = voz.gravar(num)
    except Exception as ex:
        msg = str(ex)[:400]
        E.mexe_ficha(num, passo="voz parou", erro=msg, esperando=GRAVAR_DE_NOVO)
        E.chat_add(num, "sistema", f"A voz não saiu: {msg}. Para tentar de novo, toque em Gravar a voz.")
        return
    if E.ler_ficha(num)["passo"] != GRAVANDO:
        return
    if r["problemas"]:
        # 17/10/2026 ("aprovo o plano voz-com-problema"; ele: "se eu quiser aprovar eu gostaria de poder ver o botão"):
        # a voz com problema também espera por ele: consertar ou aprovar mesmo assim
        E.mexe_ficha(num, passo="voz com problema", passo_desde=E.agora(), erro=" · ".join(r["problemas"])[:400],
                     esperando=VOZ_PROBLEMA)
        E.chat_add(num, "sistema", "A voz foi gravada, mas a conferência achou problema: " + " · ".join(r["problemas"])
                   + ". Ouça no player: toque em Consertar, ou, se estiver ok, em Ouvi, está ok.")
    else:
        E.mexe_ficha(num, passo="voz pronta", passo_desde=E.agora(), esperando="Aprovar a voz")
        E.chat_add(num, "sistema", f"Voz pronta: {r['duracao']:.0f} s" + (f", regravei os blocos {', '.join(map(str, r['novas']))}" if r["novas"] else "")
                   + ". Ouça no player. Para mudar um bloco, peça aqui; para seguir, toque em Aprovar a voz.")


def molde_pedido(texto):
    """A mensagem dele liga ou desliga um molde? "conferir" (18/10/2026, "aprovo o plano formato-fomos-conferir": "usa o
    fomos conferir"), "curso" (17/10, "usa o molde curso"), "" (desliga: "volta ao molde normal") ou None (não fala de
    molde). Casos em testes/fomos_conferir.py."""
    s = __import__("unicodedata").normalize("NFD", texto.lower()).encode("ascii", "ignore").decode()
    # só verbo de ligar ("refaz as capas no formato Fomos conferir" religava o formato à toa, 18/10 10:22)
    if re.search(r"\bfomos\s+conferir\b", s) and re.search(r"\b(usa|use|usar|liga|ligar|coloca|ativa)\b", s) \
            and not re.search(r"\b(volta|tira|desliga|sem)\b", s):
        return "conferir"
    if re.search(r"\bmolde\s+(do\s+)?curso\b", s) and not re.search(r"\b(volta|tira|desliga|sem)\b.*molde", s):
        return "curso"
    # 24/10/2026 ("pode fazer o molde números"; o #368): "usa o molde números", "faz no formato números", "micro doc em
    # números". Só com molde/formato/estilo junto ("o lucro em números" é fala comum) e antes do micro doc
    if re.search(r"\b(molde|formato|estilo)\s+(de\s+|dos\s+)?numeros\b|\bmicro\s*-?\s*doc\w*\s+(em|com|no)\s+(o\s+)?(molde\s+)?numeros\b", s) \
            and not re.search(r"\b(volta|tira|desliga|sem)\b", s):
        return "numeros"
    # 24/10/2026 (o #367): "faz como micro doc", "usa o micro documentário", "faz em colagem"
    if re.search(r"\bmicro\s*-?\s*doc(umentario)?s?\b|\bem\s+colagem\b", s) and re.search(r"\b(usa|use|usar|liga|ligar|coloca|ativa|faz|faze|fazer|faca|vira|como)\b", s) \
            and not re.search(r"\b(volta|tira|desliga|sem)\b", s):
        return "microdoc"
    if re.search(r"\b(volta|tira|desliga)\b.*(molde|fomos\s+conferir|micro\s*-?\s*doc|numeros)|molde\s+normal", s):
        return ""
    return None


def conferir_fontes(num):
    """Com o roteiro parado (e ao aprovar), abre cada link da checagem, sem atrasar o chat (fontes.py). Até 26/10/2026 a
    segunda opinião (monitor.py) lia o roteiro aqui também; saiu."""
    if PROVA:                                    # modo prova: nenhuma chamada de IA sozinha
        return
    def ler():
        with _guarda:
            if num in _relendo:
                return
            _relendo.add(num)
        # 19/10/2026 (ele: "faz a conferência das fontes"): com o roteiro parado, abre cada link da checagem (só quando
        # ela mudou) e avisa no chat a afirmação que nenhuma fonte confirma
        try:
            import fontes
            if E.ler_ficha(num).get("etapa") == "Publicado":     # vídeo já no ar: não confere (19/10, rodou no #300 ao religar)
                return
            conf = fontes.conferir(num)
            frase = fontes.aviso(conf) if conf else ""
            if frase and conf.get("avisado") != conf.get("hash"):
                E.chat_add(num, "sistema", frase)
                conf["avisado"] = conf["hash"]; E._grava(E.pasta(num) / "fontes.json", json.dumps(conf, ensure_ascii=False, indent=1))
        except Exception:
            traceback.print_exc()
        finally:
            with _guarda:
                _relendo.discard(num)
    threading.Thread(target=ler, daemon=True).start()


def vigia_roteiros():
    """16/10/2026 (ele: "essa leitura tem que disparar logo depois de alterar qualquer bloco"): olha o ROTEIRO.md de
    todos os vídeos a cada 2 s; mudou (por quem for: agente, pauta, à mão), a voz regrava e, parado, as fontes são conferidas."""
    # 19/10/2026 (ele: "a segunda opinião não podemos usar uma outra ia mais barata?"; no #300 ela releu 55 vezes, 3
    # leituras do Opus cada, porque o agente grava o roteiro várias vezes seguidas): ela espera o roteiro ficar
    # ESPERA_OPINIAO s sem mudar e lê uma vez a versão final. A voz continua regravando na hora, como antes.
    import hashlib, time
    visto, mudou_em = {}, {}
    while True:
        for n in E.numeros():
          # 25/10/2026 (plano de melhorias): um vídeo com problema (pasta excluída no meio, ficha ruim) não mata mais o vigia
          # de todos (antes, sem try, o thread morria calado e a voz parava de regravar sozinha até religar)
          try:
            arq = E.pasta(n) / "ROTEIRO.md"
            if not arq.exists():
                continue
            marca = hashlib.md5(arq.read_bytes()).hexdigest()
            if visto.get(n) not in (None, marca):
                mudou_em[n] = time.time()
                if E.ler_ficha(n)["etapa"] == "Roteiro e voz":       # mudou depois da voz: regrava o que mudou
                    E.mexe_ficha(n, passo=GRAVANDO, passo_desde=E.agora(), esperando="")
                    garantir(n)
            elif n in mudou_em and time.time() - mudou_em[n] >= ESPERA_OPINIAO:
                del mudou_em[n]
                # 19/10/2026 (ele: "pode fazer"; no #302 ela releu ~15 vezes, ~1,5 de peso): só a PRIMEIRA versão é lida
                # sozinha; depois, ela lê quando ele aprova o roteiro (aprovar-roteiro) ou quando ele pede
                if not ja_lido(n):
                    E.evento(n, f"roteiro parou de mudar ({ESPERA_OPINIAO} s): "
                                + "conferindo as fontes")
                    conferir_fontes(n)
            visto[n] = marca
          except Exception:
            traceback.print_exc()
        time.sleep(2)


def garantir(num):
    if PROVA:                                    # modo prova: nenhum trabalho começa (nem pelos botões)
        return
    with _guarda:
        t = _trabalhando.get(num)
        if t and t.is_alive():
            return
        t = threading.Thread(target=trabalhador, args=(num,), daemon=True)
        _trabalhando[num] = t
        t.start()


def conserta_fora_do_mapa(n, f):
    """mapa-de-passos (24/10/2026): a ficha num estado que não existe no mapa volta, ao religar, a um passo que existe.
    O caso medido (VPS, #354, 23/10): em Aguardando, o agente mudou o roteiro de um vídeo já aprovado e devolveu o passo
    "roteiro pronto"; o vídeo ficou esperando "Publicar" com um vídeo final que não corresponde ao roteiro."""
    erro = "; ".join(MAPA.confere(f["etapa"], f["passo"], f.get("esperando") or ""))
    if f["etapa"] == "Aguardando":
        fj = E.pasta(n) / "publicacao/final.json"
        conf = json.loads(fj.read_text()) if fj.exists() else None
        if conf and not conf.get("erros"):
            E.mexe_ficha(n, passo=PRONTO, esperando="Publicar")
            rot = E.pasta(n) / "ROTEIRO.md"
            if rot.exists() and rot.stat().st_mtime > fj.stat().st_mtime:
                E.chat_add(n, "sistema", "O roteiro mudou depois do vídeo final. Confira antes de publicar, ou toque em Reabrir "
                                         "a animação para o vídeo final sair de novo com o roteiro de agora.")
        else:
            E.mexe_ficha(n, passo="o vídeo final parou", esperando="", erro="o estado deste vídeo estava fora do mapa; gere o vídeo final de novo")
    else:
        print(f"#{n} fora do mapa e sem conserto conhecido: {erro}")
        return f
    E.evento(n, f"estado fora do mapa consertado ao religar ({erro[:160]})")
    return E.ler_ficha(n)


def retomar():
    for n in E.numeros():
        f = E.ler_ficha(n)
        # ao religar, a 1ª versão sem as fontes conferidas é conferida
        if not ja_lido(n) and (E.pasta(n) / "ROTEIRO.md").exists() and f["etapa"] == "Pauta":
            conferir_fontes(n)
        if f.get("pos_publicar"):
            E.chat_add(n, "sistema", f"O estúdio religou enquanto postava no {' e no '.join(f['pos_publicar'])}: confira se "
                                     "saiu e, se não, poste à mão (não repito sozinho para não sair duas vezes).")
            E.mexe_ficha(n, pos_publicar=None)
        if f["passo"] == PUBLICANDO:     # nunca publica de novo sozinho: pode já ter saído
            E.mexe_ficha(n, passo="publicação interrompida", erro="o servidor reiniciou no meio; confira no Instagram antes de publicar de novo",
                         esperando="Publicar")
            continue
        if MAPA.confere(f["etapa"], f["passo"], f.get("esperando") or ""):
            f = conserta_fora_do_mapa(n, f)
        # mapa-de-passos (24/10/2026): o que fazer ao religar vem da tabela (antes, uma lista à parte; "baixando e
        # transcrevendo o vídeo que você mandou" ficava parado para sempre se o servidor caísse no meio)
        religa = MAPA.religar(f["passo"], f["etapa"])
        if f.get("pedido_guardado") and f["etapa"] == "Animação":
            garantir(n)
        if religa or E.pendentes(n):
            print(f"retomando #{n} ({f['passo']}, {len(E.pendentes(n))} mensagem(ns) sem resposta)")
            if religa not in (None, "continua") and not E.pendentes(n):
                if religa == "roteiro pronto" and not (E.pasta(n) / "ROTEIRO.md").exists():
                    E.mexe_ficha(n, passo="parou", erro="o servidor reiniciou no meio; mande a pauta de novo")
                    continue
                espera = {"prévia pronta": esperando_animacao(n) if religa == "prévia pronta" else "", "vídeo final pronto": "Publicar"}
                E.mexe_ficha(n, passo=religa, esperando=espera.get(religa, f.get("esperando") or ""))
            garantir(n)


def pode_excluir(num):
    f = E.ler_ficha(num)
    with _guarda:
        vivo = bool(_trabalhando.get(num) and _trabalhando[num].is_alive())
    ocupado = f["passo"] in MAPA.TRABALHANDO          # mapa-de-passos: antes, uma 6ª cópia da lista
    return f["etapa"] != "Publicado" and not vivo and not ocupado and not E.pendentes(num)


_previas = {}             # número -> {"atual": versão da cena agora, "pronta": arquivo da prévia em vídeo dessa versão, "proc": Popen}


def vigia_radar():
    """21/10/2026 ("pode fazer a fase 2 do radar"): o radar de pautas (radar.py) em outro processo, com prioridade baixa:
    o cérebro do dia a partir das 6h (se o de ontem tem mais de 20 h) e um lote de contas a cada 40 min das 8h às 23h
    (radar-leve, 21/10/2026; o ciclo de 3 lotes julga e pode criar até 3 pautas sugeridas por dia). A hora do último lote
    vem de radar/lote.json: reiniciar não roda de novo."""
    d = E.RAIZ / "radar"
    tentou_dia = ""                   # o cérebro tenta uma vez por dia (se a IA falhar, não repete a cada minuto)
    while True:
        try:
            agora = datetime.now()
            cer = d / "cerebro.md"
            try:
                ultima = float(json.loads((d / "lote.json").read_text()).get("quando") or 0)
            except Exception:
                ultima = 0
            cmd = None
            if agora.hour >= 6 and tentou_dia != f"{agora:%Y-%m-%d}" and (not cer.exists() or cer.stat().st_mtime < time.time() - 20 * 3600):
                cmd, tentou_dia = "dia", f"{agora:%Y-%m-%d}"
            elif 8 <= agora.hour <= 23 and time.time() - ultima >= 38 * 60:
                cmd = "rodar"
            if cmd:
                with open(d / "radar.log", "a") as log:
                    log.write(f"--- {agora:%Y-%m-%d %H:%M} {cmd}\n"); log.flush()
                    subprocess.run(["nice", "-n", "10", sys.executable, str(E.RAIZ / "radar.py"), cmd], cwd=E.RAIZ, stdout=log,
                                   stderr=subprocess.STDOUT, timeout=3600)
        except Exception:
            traceback.print_exc()
        time.sleep(60)


def vigia_previas():
    """21/10/2026 ("aprovo o plano previa-em-video"): a cada 10 s, para cada vídeo na Animação com a prévia pronta, se a
    prévia em vídeo não é da versão de agora, gera (render.py --previa, outro processo, nice 10); se a cena muda no meio
    ou o estúdio volta a mexer, mata a geração e recomeça na próxima volta."""
    # 25/10/2026: as prévias que o servidor anterior deixou rodando (start_new_session: sobrevivem ao religar) param aqui
    subprocess.run(["pkill", "-f", "[r]ender.py --previa"], capture_output=True)
    while True:
        try:
            # 25/10/2026 (ele, #382: "clicando no preview [...] pula a tela e não dá play"; a peça de fotos mudou, todas as
            # prévias ficaram velhas e a dele esperava atrás das dos vídeos antigos, #334 primeiro): o mais novo primeiro
            pastas = [p for p in E.VIDEOS.iterdir() if p.name.isdigit()] if E.VIDEOS.exists() else []
            for p in sorted(pastas, key=lambda p: -int(p.name)):
                if not (p / "animacao/cena.html").exists():
                    continue
                num = int(p.name); f = E.ler_ficha(num); st = _previas.setdefault(num, {"atual": None, "pronta": None, "proc": None})
                if f.get("etapa") != "Animação" or not ativo(num, f):
                    continue
                parado = f.get("passo") == "prévia pronta" and not E.pendentes(num)
                try:
                    st["atual"] = render.versao_previa(num)
                except Exception:
                    continue
                info = json.loads((p / "animacao/previa-video.json").read_text()) if (p / "animacao/previa-video.json").exists() else {}
                st["pronta"] = info.get("arquivo") if info.get("versao") == st["atual"] and (p / "animacao" / str(info.get("arquivo"))).exists() else None
                proc = st["proc"]
                # 25/10/2026 (plano de melhorias): prazo de 15 min por prévia (um Chromium travado prendia todas as outras) e
                # wait depois do kill (ficavam processos zumbis)
                travou = proc and proc.poll() is None and time.time() - st.get("desde", time.time()) > 15 * 60
                if proc and proc.poll() is None and (travou or not parado or st.get("gerando") != st["atual"]):
                    os.killpg(proc.pid, 9); st["proc"] = None                    # a cena mudou no meio: começa de novo depois
                    try:
                        proc.wait(timeout=10)
                    except Exception:
                        pass
                    if travou:
                        E.evento(num, "prévia em vídeo passou de 15 min e foi parada")
                elif proc and proc.poll() is not None:
                    st["proc"] = None
                    if proc.returncode:
                        E.evento(num, f"prévia em vídeo não saiu (código {proc.returncode})")
                ocupado = any(o is not st and o.get("proc") and o["proc"].poll() is None for o in _previas.values())
                if parado and not st["pronta"] and not st["proc"] and not ocupado:       # uma de cada vez na VPS
                    st["gerando"] = st["atual"]; st["desde"] = time.time()
                    st["proc"] = subprocess.Popen(["nice", "-n", "10", sys.executable, str(E.RAIZ / "render.py"), "--previa", str(num)],
                                                  cwd=E.RAIZ, stdout=subprocess.DEVNULL, stderr=open(p / "animacao/previa-video.log", "w"),
                                                  start_new_session=True)
        except Exception:
            traceback.print_exc()
        time.sleep(10)


# 25/10/2026 (medido às 13:00: ~3 núcleos da VPS gravando de novo a prévia do #334, parado na Animação desde 22/10,
# porque uma peça da tela mudou): a prévia em vídeo só sai para os vídeos ativos, mexidos nas últimas 48 h ou abertos na
# tela nos últimos 30 min (os outros mostram a prévia montada ao vivo, e o vídeo sai quando ele abrir)
_vistos = {}
ATIVO_H, VISTO_MIN = 24, 30          # 25/10/2026 (plano de melhorias): 48 h ainda gravava vídeos parados


def ativo(num, f=None):
    f = f or E.ler_ficha(num)
    recente = time.time() - ATIVO_H * 3600
    try:
        mexido = datetime.fromisoformat(str(f.get("atualizado"))).timestamp() >= recente
    except ValueError:
        mexido = False
    return mexido or time.time() - _vistos.get(int(num), 0) < VISTO_MIN * 60


def item_json(num):
    _vistos[int(num)] = time.time()
    f = E.ler_ficha(num)
    bs = E.blocos(num)
    with _guarda:
        vivo = bool(_trabalhando.get(num) and _trabalhando[num].is_alive())
    cj = E.pasta(num) / "narracao/completo.json"
    cf = E.pasta(num) / "animacao/conferencia.json"
    antes = sorted(p.name for p in (E.pasta(num) / "animacao/antes").glob("bloco*.png")) if (E.pasta(num) / "animacao/antes").exists() else []
    an = E.pasta(num) / "animacao"
    mudou = [int(n[5:7]) for n in antes if (an / "depois" / n).exists() and (an / "antes" / n).read_bytes() != (an / "depois" / n).read_bytes()]
    tempos = {b["n"]: round(b["ini"] + .85 * (b["fim"] - b["ini"]), 1) for b in json.loads(cj.read_text())["blocos"]} if cj.exists() else {}
    return {"animacao": {"conferencia": json.loads(cf.read_text()) if cf.exists() else None, "antes": antes, "mudou": mudou,
                         "tempos": tempos, "pode_voltar": bool(list((an / "versoes").glob("cena-*.html"))) if (an / "versoes").exists() else False,
                         "tem_cena": (an / "cena.html").exists(), "capas": capas_json(num),
                         "legenda": legenda_post.ler(num), "faltas": faltas_aprovar(num) if f["etapa"] == "Animação" else [],
                         "graves_regua": graves_regua(num) if f["etapa"] == "Animação" else [],
                         "olhos": olhos_ponte.ler(E.pasta(num) / "publicacao/olhos"),
                         # a prévia em vídeo da versão de agora (vigia_previas), ou se está sendo gerada
                         "previa_video": (f"/item/{num}/animacao/{_previas[num]['pronta']}" if _previas.get(num, {}).get("pronta") else None),
                         "previa_gerando": bool(_previas.get(num, {}).get("proc")),
                         # editor-327 (22/10/2026): os trechos parados mais de 1 s da prévia em vídeo de agora
                         "previa_parados": _parados_previa(num),
                         "final": json.loads((E.pasta(num) / "publicacao/final.json").read_text()) if (E.pasta(num) / "publicacao/final.json").exists() else None},
            "voz": json.loads(cj.read_text()) if cj.exists() else None,
            "ficha": f, "blocos": bs, "segundos": E.segundos(bs) if bs else 0, "chat": E.chat(num),
            "trabalhando": vivo, "pendentes": len(E.pendentes(num)), "pode_excluir": pode_excluir(num), "resumo": resumo_json(num),
            # mapa-de-passos (24/10/2026): o que a tabela diz deste passo (a tela vai desenhar os botões por aqui, parte 3)
            "mapa": {"trabalhando": list(MAPA.TRABALHANDO), "tipo": (MAPA.info(f["passo"]) or {}).get("tipo"),
                     "botoes": MAPA.botoes(f["passo"], f["etapa"])}}


def _parados_previa(num):
    """Os parados (render.parados_mp4) da prévia em vídeo que está na tela; da versão anterior, nada."""
    try:
        info = json.loads((E.pasta(num) / "animacao/previa-video.json").read_text())
    except (OSError, ValueError):
        return []
    return info.get("parados") or [] if info.get("arquivo") == _previas.get(num, {}).get("pronta") else []


def resumo_json(num):
    """22/10/2026 ("aprovo o plano tela-do-roteiro"; ele: "preciso visualizar o resumo e roteiro"): a análise, a
    checagem e o ângulo do roteirista, para a árvore da tela (antes ficavam só nos arquivos)."""
    p = E.pasta(num)
    ler = lambda n: (p / n).read_text()[:8000].strip() if (p / n).exists() else ""
    rot = ler("ROTEIRO.md")
    angulo = next((l.split(":", 1)[1].strip() for l in rot.splitlines() if l.startswith("Ângulo:")), "")
    return {"angulo": angulo, "analise": ler("ANALISE.md"), "checagem": ler("CHECAGEM.md")}


def capas_json(num):
    """As opções de capa para a tela; `escolhida` só vale se a capa.html é igual à opção (refeita depois, escolhe de novo)."""
    an = E.pasta(num) / "animacao"
    ops = capa.opcoes(num)
    esc = None
    if (an / "capa.html").exists():
        atual = (an / "capa.html").read_bytes()
        esc = next((int(o["op"]) for o in ops if (an / f"capa-{int(o['op'])}.html").read_bytes() == atual), None)
    marca = max([(an / f"capa-{int(o['op'])}.jpg").stat().st_mtime for o in ops], default=0)
    return {"opcoes": ops, "escolhida": esc, "tem_escolha_velha": (an / "capa.html").exists() and esc is None, "v": int(marca)}


_leves = threading.Lock()


def video_leve(arq):
    """19/10/2026 (no ar, ele: "quando clico no iPhone para dar play fica uma tela branca"): com os vídeos agora em
    1080, a prévia preparava vários trechos em alta ao mesmo tempo e o iPhone derrubava a página. A prévia pede a cópia
    leve (540 de largura, sem som: os trechos tocam mudos, a voz vem da narração), feita uma vez e guardada ao lado
    (<nome>.leve.mp4). O vídeo final (render=1) continua usando o original."""
    leve = arq.with_name(arq.stem + ".leve.mp4")
    with _leves:
        if not leve.exists() or leve.stat().st_mtime < arq.stat().st_mtime:
            tmp = leve.with_name(leve.stem + ".tmp.mp4")
            r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(arq), "-vf", "scale=540:-2", "-an", "-c:v", "libx264",
                                "-preset", "veryfast", "-crf", "28", "-g", "15", "-movflags", "+faststart", str(tmp)], capture_output=True, timeout=600)
            # -g 15 (20/10/2026, #306: "no segundo 13,8 em vez de aparecer o boulos aparece o lula"): sem ele, um quadro
            # inteiro a cada 5 a 8 s, e o pulo da prévia caía até 8 s antes do corte (o reel do Boulos mostrava o Lula)
            if r.returncode or not tmp.exists():
                return arq
            os.replace(tmp, leve)
    return leve


class H(BaseHTTPRequestHandler):
    def log_message(self, fmt, *a):
        # 23/10/2026 ("aprovo o plano travas-da-verificacao"; o erro a cada 5 min, 428 de 442 no registro): no erro o 1º
        # argumento é o código (HTTPStatus), não o texto da linha; com str() o registro não quebra mais
        primeiro = str(a[0]) if a else ""
        if "/api/" in primeiro and "GET" in primeiro:
            return                 # a tela pergunta a cada 2 s; não enche o log
        sys.stderr.write("%s\n" % (fmt % a))

    def _json(self, cod, obj, cookie=None, etag=False):
        b = json.dumps(obj, ensure_ascii=False).encode()
        if etag:
            # 25/10/2026 (medido no ar: ~3 MB por minuto por aba, a tela perguntando a cada 2 s): a impressão do conteúdo;
            # se o navegador já tem igual, "304, nada mudou", sem corpo. O Caddy, ao comprimir, pode marcar a impressão
            # (W/ na frente, "-gzip" no fim): a conferência ignora isso
            tag = '"' + hashlib.md5(b).hexdigest()[:20] + '"'
            limpa = lambda x: re.sub(r'^W/|-(gzip|zstd|br)"$', lambda m: '"' if m.group(0).startswith("-") else "", x.strip())
            if any(limpa(x) == tag for x in (self.headers.get("If-None-Match") or "").split(",") if x.strip()):
                self.send_response(304); self.send_header("ETag", tag); self.send_header("Cache-Control", "no-cache")
                self.end_headers()
                return
        self.send_response(cod)
        if cookie:
            self.send_header("Set-Cookie", cookie)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        if etag:
            self.send_header("ETag", tag); self.send_header("Cache-Control", "no-cache")
        else:
            self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def _eventos(self, q):
        """25/10/2026 (plano de melhorias: "avisos na hora, sem perguntar a cada 2 s"): a tela abre esta conexão (SSE) e o
        servidor avisa "mudou" quando a ficha, o chat ou o funil mudam (pela data dos arquivos, ~1 vez por segundo); a tela
        só então busca. A conexão fecha em 5 min e o navegador reabre sozinho."""
        num = (q.get("item") or [""])[0]
        p = E.pasta(int(num)) if num.isdigit() else None
        arqs = [p / x for x in ("ficha.json", "chat.jsonl", "ROTEIRO.md", "CHECAGEM.md", "animacao/cena.html", "animacao/capas.json",
                                "animacao/conferencia.json", "narracao/completo.json", "publicacao/final.json")] if p else []

        def assinatura():
            def m(a):
                try:
                    return a.stat().st_mtime_ns
                except OSError:
                    return 0
            fichas = max((m(E.pasta(n) / "ficha.json") for n in E.numeros()), default=0)
            return (fichas,) + tuple(m(a) for a in arqs)
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream"); self.send_header("Cache-Control", "no-cache")
        self.send_header("X-Accel-Buffering", "no"); self.end_headers()
        antes, fim, batida = assinatura(), time.time() + 300, time.time()
        try:
            self.wfile.write(b"retry: 3000\n\n"); self.wfile.flush()
            while time.time() < fim:
                time.sleep(1)
                agora_ = assinatura()
                if agora_ != antes:
                    antes = agora_
                    self.wfile.write(b"data: mudou\n\n"); self.wfile.flush()
                elif time.time() - batida > 20:            # mantém a conexão viva no Caddy e no celular
                    self.wfile.write(b": batida\n\n"); self.wfile.flush(); batida = time.time()
        except (BrokenPipeError, ConnectionResetError, OSError):
            pass

    def _corpo(self, teto=300 * 1024 * 1024):
        # 25/10/2026 (revisão de segurança): sem teto, um pedido de vários GB (até sem login) enchia a memória; negativo
        # prendia a leitura. O teto padrão é o do anexo; o JSON das rotas de entrada usa 64 KB
        try:
            n = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            n = -1
        if n < 0 or n > teto:
            raise ValueError(f"pedido grande demais ou inválido ({n} bytes)")
        return self.rfile.read(n) if n else b""

    def _bytes(self, b, tipo, faixa=None):
        """Com Range (o navegador pede pedaços de áudio e vídeo para poder pular), responde 206 com o pedaço."""
        if faixa and faixa.startswith("bytes="):
            a, _, z = faixa[6:].partition("-")
            a = int(a or 0); z = min(int(z) if z else len(b) - 1, len(b) - 1)
            self.send_response(206); self.send_header("Content-Range", f"bytes {a}-{z}/{len(b)}")
            b = b[a:z + 1]
        else:
            self.send_response(200)
        self.send_header("Content-Type", tipo); self.send_header("Accept-Ranges", "bytes"); self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(b))); self.end_headers(); self.wfile.write(b)

    def _arquivo(self, arq, tipo, faixa=None):
        """19/10/2026 (no ar, iPhone: "quando clico no preview vai para uma tela branca"): lia o arquivo inteiro a cada
        pedido e, no pedido aberto ("bytes=0-"), mandava o vídeo todo (com os vídeos em 1080, dezenas de MB por pedido, e
        o app ficava "sem conexão"). Agora lê do disco só o pedaço, e o pedido aberto recebe no máximo 2 MB por vez."""
        tam = arq.stat().st_size
        if faixa and faixa.startswith("bytes=") and tam:
            a, _, z = faixa[6:].split(",")[0].partition("-")
            if a == "":                                   # "bytes=-500": os últimos 500
                a, z = max(0, tam - int(z or 0)), tam - 1
            else:
                a = int(a); z = min(int(z) if z else a + 2 * 1024 * 1024 - 1, tam - 1)
            if a >= tam:
                self.send_response(416); self.send_header("Content-Range", f"bytes */{tam}"); self.end_headers(); return
            self.send_response(206); self.send_header("Content-Range", f"bytes {a}-{z}/{tam}")
        else:
            a, z = 0, tam - 1
            self.send_response(200)
        self.send_header("Content-Type", tipo); self.send_header("Accept-Ranges", "bytes"); self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(max(0, z - a + 1))); self.end_headers()
        with open(arq, "rb") as f:
            f.seek(a); falta = z - a + 1
            while falta > 0:
                bloco = f.read(min(256 * 1024, falta))
                if not bloco:
                    break
                self.wfile.write(bloco); falta -= len(bloco)

    def _mesmo_site(self):
        """25/10/2026 (revisão de segurança): só o próprio estúdio fala com ele. Host de outro nome é o truque de um site
        que se passa pelo endereço local (DNS rebinding); Origin de outro site num POST é uma página qualquer aberta no
        navegador mandando ordens (a cópia do Mac não tem login e publica de verdade)."""
        from urllib.parse import urlsplit
        def nosso(nome):
            return nome in ("127.0.0.1", "localhost", "::1") or nome in HOSTS_NOSSOS
        host = (self.headers.get("Host") or "").rsplit(":", 1)[0].strip("[]").lower()
        if host and not nosso(host):
            return False
        origem = self.headers.get("Origin")
        if self.command != "GET" and origem:      # "null": página isolada ou aberta de arquivo; nunca é o painel
            return origem != "null" and nosso((urlsplit(origem).hostname or "").lower())
        return True

    def _porta(self, u):
        """Entrada com Face ID (20/10/2026, entrada.py; só na VPS, V2_ENTRADA=1). Devolve True se já respondeu."""
        if not self._mesmo_site():
            self._json(403, {"erro": "pedido de outro site"})
            return True
        if not entrada.LIGADA:
            return False
        # as ferramentas do próprio estúdio (régua, quadros do animador, capas, vídeo final) abrem a prévia direto em
        # 127.0.0.1:4400, sem passar pelo Caddy (20/10/2026: com a entrada ligada às 06:47, a 1ª animação do #305 caiu
        # às 08:20 com "Timeout 30000ms"). Tudo o que vem da internet chega pelo Caddy, que sempre põe X-Forwarded-For.
        if self.client_address[0] == "127.0.0.1" and not self.headers.get("X-Forwarded-For"):
            return False
        cookie = self.headers.get("Cookie")
        dentro = entrada.vale(cookie)
        if u.path == "/entrar" and self.command == "GET":
            self._bytes((WEB / "entrar.html").read_bytes(), "text/html; charset=utf-8"); return True
        if u.path.startswith("/api/entrada/"):
            acao = u.path[len("/api/entrada/"):]
            try:
                d = json.loads(self._corpo(64 * 1024) or b"{}") if self.command == "POST" else {}
                if acao == "estado":
                    return self._json(200, {"dentro": dentro, "tem_chaves": entrada.tem_chaves()}) or True
                if acao == "senha":
                    if not entrada.senha_ok(d.get("senha")):
                        return self._json(403, {"erro": "senha errada"}) or True
                    return self._json(200, {"ok": True}, entrada.nova_sessao()) or True
                if acao == "opcoes-entrar":
                    return self._json(200, entrada.opcoes_entrar()) or True
                if acao == "entrar":
                    entrada.entrar(d)
                    return self._json(200, {"ok": True}, entrada.nova_sessao()) or True
                if acao == "sair":
                    return self._json(200, {"ok": True}, entrada.sair(cookie)) or True
                if not dentro:
                    return self._json(401, {"erro": "entre primeiro"}) or True
                if acao == "opcoes-cadastro":
                    return self._json(200, entrada.opcoes_cadastro()) or True
                if acao == "cadastrar":
                    entrada.cadastrar(d.get("credencial") or {}, d.get("nome"))
                    return self._json(200, {"ok": True}) or True
                return self._json(404, {"erro": "não existe"}) or True
            except Exception as ex:
                return self._json(400, {"erro": str(ex)[:200]}) or True
        if dentro or entrada.livre(u.path):
            return False
        if u.path.startswith("/api/"):
            return self._json(401, {"erro": "entre primeiro"}) or True
        self.send_response(303); self.send_header("Location", "/entrar"); self.send_header("Content-Length", "0")
        self.end_headers(); return True

    def do_HEAD(self):
        # quem confere se o estúdio está no ar pergunta com HEAD a cada ~5 min (pelo Caddy); antes, sem resposta (501)
        self.send_response(200); self.send_header("Content-Type", "text/plain"); self.send_header("Content-Length", "0"); self.end_headers()

    def do_GET(self):
        u = urlparse(self.path)
        if self._porta(u):
            return
        if u.path == "/api/eventos":
            return self._eventos(parse_qs(u.query))
        # 26/10/2026 (ele: "talvez eu tenha que poder ver esse caderno de regras caso queira mudar algo"): a tela Regras
        if u.path == "/api/regras":
            q = parse_qs(u.query)
            num = (q.get("item") or [""])[0]
            dec = regras_tela.decisoes(int(num)) if num.isdigit() and (E.pasta(num) / "ficha.json").exists() else None
            return self._json(200, {"cadernos": regras_tela.listar(), "decisoes": dec})
        m = re.fullmatch(r"/api/regras/([A-Z][A-Z0-9-]{1,40})", u.path)
        if m:
            try:
                return self._json(200, regras_tela.ler(m.group(1)))
            except ValueError as ex:
                return self._json(404, {"erro": str(ex)})
        if u.path == "/api/funil":
            # 25/10/2026: a tela pede só a etapa que mostra (?etapa=X; vazia = um vídeo aberto, só as contagens)
            q = parse_qs(u.query, keep_blank_values=True)
            return self._json(200, E.funil(q["etapa"][0]) if "etapa" in q else E.funil(), etag=True)
        if u.path == "/api/teste-sonnet":                    # teste sombra Sonnet x Opus, às cegas (20/10/2026, web/teste.html)
            sys.path.insert(0, str(E.RAIZ / "testes")); import sombra_sonnet
            return self._json(200, {"casos": sombra_sonnet.para_tela()})
        m = re.fullmatch(r"/item/(\d+)/(.+)", u.path)
        if m and (E.pasta(m.group(1)) / "ficha.json").exists():
            num, rel = int(m.group(1)), m.group(2)
            if rel == "capa.html":
                q = parse_qs(u.query); op = q.get("op", ["escolhida"])[0]
                return self._bytes(capa.pagina(num, op if op == "escolhida" else int(op), texto=bool(q.get("texto"))).encode(),
                                   "text/html; charset=utf-8")
            if rel == "previa.html":
                if not (E.pasta(num) / "narracao/completo.json").exists():
                    return self._json(404, {"erro": "sem voz ainda"})
                return self._bytes(animacao.pagina(num).encode(), "text/html; charset=utf-8")
            arq = (E.pasta(num) / rel).resolve()
            if not str(arq).startswith(str(E.pasta(num).resolve()) + "/") or not arq.is_file() or arq.name in ("ficha.json", "chat.jsonl"):
                return self._json(404, {"erro": "não existe"})
            tipos = {".mp3": "audio/mpeg", ".mp4": "video/mp4", ".m4a": "audio/mp4", ".png": "image/png", ".jpg": "image/jpeg",
                     ".jpeg": "image/jpeg", ".webp": "image/webp", ".svg": "image/svg+xml", ".json": "application/json"}
            if arq.suffix.lower() == ".mp4" and parse_qs(u.query).get("leve"):
                arq = video_leve(arq)
            elif arq.suffix.lower() == ".mp4" and parse_qs(u.query).get("quadro"):     # o vídeo final (render.video_quadro)
                arq = render.video_quadro(arq)
            return self._arquivo(arq, tipos.get(arq.suffix.lower(), "application/octet-stream"), self.headers.get("Range"))
        if u.path.startswith(("/fontes/", "/logos/", "/sons/", "/pecas/")):   # /sons/: v2-som; /pecas/: peças prontas (v2-verdadometro)
            arq = (WEB / u.path.lstrip("/")).resolve()
            if str(arq).startswith(str(WEB.resolve())) and arq.is_file():
                return self._arquivo(arq, {".ttf": "font/ttf", ".woff2": "font/woff2", ".png": "image/png", ".jpg": "image/jpeg", ".mp3": "audio/mpeg", ".js": "text/javascript; charset=utf-8"}.get(arq.suffix, "application/octet-stream"), self.headers.get("Range"))
        m = re.fullmatch(r"/api/item/(\d+)/audio", u.path)
        if m:
            arq = E.pasta(m.group(1)) / "narracao/completo.mp3"
            if not arq.exists():
                return self._json(404, {"erro": "sem áudio"})
            # com Range (19/10/2026, ele: "não dá para ver o local de dar play"): sem ele o navegador não deixava pular para
            # um ponto da voz (a barra não andava e o "▶ ouvir bloco" tocava do começo)
            return self._arquivo(arq, "audio/mpeg", self.headers.get("Range"))
        m = re.fullmatch(r"/api/item/(\d+)/numeros", u.path)
        if m:
            # 16/10/2026 ("aprovo o plano v2-publicado"): os números do reel na API do Instagram (só leitura); a última
            # leitura vale 10 minutos, a não ser que ele toque em atualizar
            num = int(m.group(1))
            atual = numeros.ler(num)
            velho = not atual or (time.time() - time.mktime(time.strptime(atual["quando"][:19], "%Y-%m-%dT%H:%M:%S"))) > 600
            if "atualizar" in parse_qs(u.query) or velho:
                try:
                    atual = numeros.medir(num)
                except Exception as ex:
                    return self._json(502, {"erro": str(ex)[:300], "ultimo": atual})
            return self._json(200, atual)
        m = re.fullmatch(r"/api/item/(\d+)", u.path)
        if m:
            if not (E.pasta(m.group(1)) / "ficha.json").exists():
                return self._json(404, {"erro": "não existe"})
            return self._json(200, item_json(int(m.group(1))), etag=True)
        arq = WEB / ("index.html" if u.path in ("/", "") else u.path.lstrip("/"))
        if arq.resolve().parent != WEB.resolve() or not arq.exists():
            return self._json(404, {"erro": "não existe"})
        b = arq.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", TIPOS_ARQ.get(arq.suffix, "application/octet-stream"))
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_POST(self):
        u = urlparse(self.path)
        if self._porta(u):
            return
        try:
            if u.path == "/api/ditado-registro":
                # 17/10/2026 (ele: "se clico em enviar ele não para o ditado", no Chrome; não reproduzi): instrumento, só
                # anota os passos do ditado da tela em registro-ditado.jsonl para ver onde trava na próxima vez
                with open(E.RAIZ / "registro-ditado.jsonl", "a") as arq:
                    arq.write(json.dumps({"quando": E.agora(), **json.loads(self._corpo() or b"{}")}, ensure_ascii=False) + "\n")
                return self._json(200, {"ok": True})
            if u.path == "/api/teste-sonnet/voto":
                sys.path.insert(0, str(E.RAIZ / "testes")); import sombra_sonnet
                d = json.loads(self._corpo() or b"{}")
                sombra_sonnet.votar(d.get("chave", ""), d.get("escolha", ""))
                return self._json(200, {"ok": True})
            m = re.fullmatch(r"/api/regras/([A-Z][A-Z0-9-]{1,40})/(propor|aplicar|cancelar|desfazer)", u.path)
            if m:
                nome, pedido_rg = m.groups()          # (não "acao": o teste do mapa lê as ações de vídeo por esse nome)
                try:
                    if pedido_rg == "propor":
                        return self._json(200, regras_tela.propor(nome, json.loads(self._corpo() or b"{}").get("pedido", "")))
                    return self._json(200, getattr(regras_tela, pedido_rg)(nome))
                except (ValueError, RuntimeError) as ex:
                    return self._json(400, {"erro": str(ex)})
            if u.path == "/api/pauta":
                d = json.loads(self._corpo() or b"{}")
                texto = (d.get("texto") or "").strip()
                if not texto:
                    return self._json(400, {"erro": "pauta vazia"})
                achado = LINK.search(texto)
                link = achado.group(0) if achado else ""
                tipo = d.get("tipo")
                if link and tipo not in ("analisar", "igual"):
                    return self._json(400, {"erro": "escolha Analisar a fala ou Fazer igual"})
                if not link and tipo != "ideia":       # 16/10: texto sem link só vira pauta com "Nova pauta com esta ideia"
                    return self._json(400, {"erro": "para criar pauta sem link, toque em Nova pauta com esta ideia"})
                resto = LINK.sub("", texto).strip()
                # 26/10/2026 (ele: "quero mandar um video de referencia. e quero dizer quero fazer um video parecido"): a
                # frase manda no tipo, mesmo com o botão no padrão (Analisar a fala)
                if link and PARECIDO.search(resto):
                    tipo, d["molde"] = "igual", ""
                num, ja = E.criar_item(tipo, link=link or "", texto=resto if link else texto, id_msg=d.get("id"))
                # 24/10/2026 (ele: "tudo que foi falado com o agente deveria aparecer no chat"): a mensagem que criou a pauta
                # entra na conversa do vídeo como dele, já atendida (inicio: o agente não responde de novo; quem a atende é a pauta)
                if not ja:
                    E.chat_add(num, "ele", texto, id_msg=f"inicio-{d.get('id') or num}", inicio=True)
                # 19/10/2026 (ele: "no app não tem a opção para a nova versão, só tem o item analisar"): o formato liga na
                # criação, antes do roteirista: pelo botão "Formato Fomos conferir" ou pela frase "usa o fomos conferir"
                # 24/10/2026: a ideia escrita também liga o formato pela frase ("faz como micro doc"); antes, só com link
                molde = d.get("molde") or molde_pedido(texto)
                if not ja and molde in E.MOLDES:
                    E.mexe_ficha(num, molde=molde)
                    E.evento(num, f"formato ligado na criação da pauta: {molde}")
                if not ja and d.get("formato") == "analise":           # 19/10/2026: o botão Análise
                    E.mexe_ficha(num, molde="", formato="analise", formato_pedido="analise")
                    E.evento(num, "formato Análise escolhido na criação da pauta")
                garantir(num)
                return self._json(200, {"recebida": True, "num": num, "repetida": ja, "quando": E.agora(), "molde": E.ler_ficha(num).get("molde") or ""})
            m = re.fullmatch(r"/api/item/(\d+)/(mensagem|aprovar-roteiro|gravar-voz-de-novo|gerar-final-de-novo|tentar-pauta|aprovar-voz|anexo|voltar-animacao|reabrir-animacao|voltar-roteiro|escolher-capa|aprovar-video|publicar|excluir|fazer-pauta|descartar-pauta)", u.path)
            if not m or not (E.pasta(m.group(1)) / "ficha.json").exists():
                if u.path == "/api/ditar":
                    return self._ditar()
                return self._json(404, {"erro": "não existe"})
            num, acao = int(m.group(1)), m.group(2)
            if acao == "mensagem":
                d = json.loads(self._corpo() or b"{}")
                texto = (d.get("texto") or "").strip()
                if not texto or not d.get("id"):
                    return self._json(400, {"erro": "mensagem vazia ou sem id"})
                # 25/10/2026 (ele: "quando ele detectar uma mudança de direção [...] tem que mostrar um botão. vermelho
                # aprovar direção"): o botão manda a mensagem marcada; ela aplica a proposta sem passar pelo maestro
                marca = {"acao": "aprovar-direcao"} if d.get("acao") == "aprovar-direcao" else {}
                msg, ja = E.chat_add(num, "ele", texto, id_msg=d["id"], **marca)
                # 17/10/2026 ("aprovo o plano molde-curso"): "usa o molde curso" liga a opção neste vídeo; "volta ao molde
                # normal" desliga. O pedido segue para o agente como qualquer outro (ele já recebe as regras do molde)
                # (18/10/2026, 10:2x: a linha do semac tinha saído junto com o molde_pedido e o "volta pro roteiro"
                # abaixo dava NameError em toda mensagem da Animação: o pedido de capa do #298 ficou parado)
                semac = __import__("unicodedata").normalize("NFD", texto.lower()).encode("ascii", "ignore").decode()
                pede = None if ja else molde_pedido(texto)
                if pede == "conferir":
                    E.mexe_ficha(num, molde="conferir", formato="checagem"); E.evento(num, "formato fomos conferir ligado por ele")
                    E.chat_add(num, "sistema", "Formato Fomos conferir ligado neste vídeo: quem disse e quantas afirmações, a fala dele e a nossa "
                                               "prova com carimbo para cada uma, placar no fim e um pedido só.")
                elif pede == "curso":
                    E.mexe_ficha(num, molde="curso"); E.evento(num, "molde curso ligado por ele")
                    E.chat_add(num, "sistema", "Molde curso ligado neste vídeo: fato nas 5 primeiras palavras, conversa, um pedido só, título de 0 a 3 s sem tela vazia.")
                elif pede == "microdoc":
                    # 24/10/2026 ("pode ensiar esse formato ao agente?"; o #367)
                    E.mexe_ficha(num, molde="microdoc"); E.evento(num, "formato micro documentário ligado por ele")
                    E.chat_add(num, "sistema", "Formato micro documentário ligado neste vídeo: a história em capítulos com uma virada, "
                                               "animação em colagem com fotos livres e crédito, trilha que troca na virada.")
                elif pede == "numeros":
                    # 24/10/2026 ("pode fazer o molde números"; o #368)
                    E.mexe_ficha(num, molde="numeros"); E.evento(num, "molde números ligado por ele")
                    E.chat_add(num, "sistema", "Molde números ligado neste vídeo: uma foto ou vídeo por capítulo no fundo, tingido, "
                                               "o número grande no centro com a fonte, régua de capítulos e o recado na conclusão.")
                elif pede == "":
                    nome_molde = {"conferir": "Formato Fomos conferir", "microdoc": "Formato micro documentário", "numeros": "Molde números"}.get(E.ler_ficha(num).get("molde"), "Molde curso")
                    E.mexe_ficha(num, molde=""); E.evento(num, f"{nome_molde} desligado por ele")
                    E.chat_add(num, "sistema", f"{nome_molde} desligado: este vídeo volta ao jeito de sempre.")
                f = E.ler_ficha(num)
                # voltar-ao-roteiro (17/10/2026): "volta pro roteiro" na Animação faz o mesmo que o botão; o pedido segue
                # para o agente, que já está na etapa do roteiro
                if not ja and f["etapa"] in ("Animação", "Aguardando") and re.search(r"\bvolt\w*\s+(pro|para o|ao|o)\s+roteiro\b", semac):
                    ok, motivo = voltar_roteiro(num)
                    if not ok:
                        E.chat_add(num, "sistema", f"Não voltei ao roteiro: {motivo}.")
                    f = E.ler_ficha(num)
                if not ja and f["passo"] == "parou" and f["etapa"] == "Pauta" and not E.blocos(num):
                    E.mexe_ficha(num, passo="recebida")          # a pauta que parou recomeça com a mensagem dele
                    E.chat_add(num, "agente", "Vou tentar a pauta de novo desde o começo.", responde=msg["id"])
                garantir(num)
                return self._json(200, {"recebida": True, "id": msg["id"], "quando": msg["quando"], "repetida": ja})
            # mapa-de-passos (24/10/2026, parte 2): o botão só vale no passo em que a tabela diz que ele existe; passo
            # fora do mapa (ficha antiga) segue as conferências de antes
            if acao in MAPA.ACOES:
                f = E.ler_ficha(num)
                if MAPA.info(f["passo"]) and acao not in MAPA.botoes(f["passo"], f["etapa"]):
                    return self._json(409, {"erro": f"este botão não vale agora ({f['passo']})"})
            if acao == "aprovar-roteiro":
                f = E.ler_ficha(num)
                if f["etapa"] != "Pauta" or f.get("esperando") != "Aprovar o roteiro":
                    return self._json(409, {"erro": "este vídeo não está esperando a aprovação do roteiro"})
                erros = E.confere_roteiro(num)
                if erros:
                    return self._json(409, {"erro": "o roteiro tem defeito: " + "; ".join(erros)})
                # 24/10/2026 ("isso pode fazer"; ele: "tem que saber qual foi o ultimo video postado para nào repedir o cta")
                rep = E.convite_repetido(num)
                if rep:
                    return self._json(409, {"erro": rep + ": peça no chat para variar o convite"})
                E.mexe_ficha(num, etapa="Roteiro e voz", esperando="", passo=GRAVANDO, passo_desde=E.agora(), mudou=[])
                E.evento(num, "roteiro aprovado por ele")
                E.chat_add(num, "sistema", "Roteiro aprovado. Estou gravando a voz (uns 2 minutos).")
                garantir(num)
                conferir_fontes(num)      # as fontes da versão aprovada (junto com a voz; não atrasa)
                return self._json(200, {"ok": True})
            if acao == "gravar-voz-de-novo":
                f = E.ler_ficha(num)
                # voz parada, ou o roteiro na etapa Roteiro e voz sem voz gravada (o #334 ficou assim, sem botão; botoes-sempre)
                if not (f.get("passo") == "voz parou" or (f["etapa"] == "Roteiro e voz" and f.get("passo") == "roteiro pronto")):
                    return self._json(409, {"erro": "a voz deste vídeo não está parada"})
                E.mexe_ficha(num, esperando="", passo=GRAVANDO, passo_desde=E.agora(), erro="")
                E.evento(num, "ele pediu para gravar a voz de novo")
                E.chat_add(num, "sistema", "Gravando a voz de novo (uns 2 minutos).")
                garantir(num)
                return self._json(200, {"ok": True})
            if acao == "gerar-final-de-novo":
                # travas-da-verificacao (23/10/2026): o vídeo final que parou ou saiu com problema, sem refazer a animação
                f = E.ler_ficha(num)
                if f["etapa"] != "Aguardando" or f.get("passo") not in ("o vídeo final parou", "vídeo final com problema"):
                    return self._json(409, {"erro": "o vídeo final deste vídeo não está parado"})
                E.mexe_ficha(num, passo=RENDERIZANDO, passo_desde=E.agora(), esperando="", erro="", progresso=5)
                E.evento(num, "ele pediu o vídeo final de novo")
                E.chat_add(num, "sistema", "Gerando o vídeo final de novo (uns 4 minutos).")
                garantir(num)
                return self._json(200, {"ok": True})
            if acao == "tentar-pauta":
                # travas-da-verificacao: a pauta que parou recomeça (o mesmo que a mensagem dele fazia)
                f = E.ler_ficha(num)
                if f["etapa"] != "Pauta" or f.get("passo") != "parou":
                    return self._json(409, {"erro": "esta pauta não está parada"})
                if E.blocos(num):              # consertos-da-revisao: a mesma conferência do caminho pela mensagem
                    return self._json(409, {"erro": "esta pauta já tem roteiro: peça a mudança no chat"})
                E.mexe_ficha(num, passo="recebida", passo_desde=E.agora(), erro="")
                E.evento(num, "ele pediu a pauta de novo")
                E.chat_add(num, "sistema", "Tentando a pauta de novo desde o começo.")
                garantir(num)
                return self._json(200, {"ok": True})
            if acao == "aprovar-voz" and E.ler_ficha(num)["etapa"] == "Animação":
                f = E.ler_ficha(num)
                if f.get("esperando") != VOZ_PROBLEMA or not json.loads(self._corpo() or b"{}").get("mesmo_assim"):
                    return self._json(409, {"erro": "a voz deste vídeo não está esperando o seu ok"})
                if not f.get("blocos_regravar"):
                    # consertos-da-revisao: sem saber o bloco, o trabalhador reanimava o vídeo inteiro (caminho caro)
                    E.chat_add(num, "sistema", "A voz está ok, mas não sei qual bloco mudou. Diga aqui qual bloco ajustar na animação.")
                    return self._json(409, {"erro": "diga no chat qual bloco ajustar"})
                E.mexe_ficha(num, passo=ANIMANDO, passo_desde=E.agora(), esperando="", erro="",
                             ajustar_blocos=f.get("blocos_regravar") or [])
                E.evento(num, "voz regravada aprovada por ele com o aviso (Animação)")
                E.chat_add(num, "sistema", "Voz aprovada. Ajustando a animação do bloco que mudou.")
                garantir(num)
                return self._json(200, {"ok": True})
            if acao == "aprovar-voz":
                f = E.ler_ficha(num)
                cj = E.pasta(num) / "narracao/completo.json"
                if f["etapa"] != "Roteiro e voz" or f.get("esperando") not in ("Aprovar a voz", VOZ_PROBLEMA) or not cj.exists():
                    return self._json(409, {"erro": "a voz ainda não está pronta para aprovar"})
                import hashlib
                c = json.loads(cj.read_text())
                if c.get("roteiro") != hashlib.md5((E.pasta(num) / "ROTEIRO.md").read_bytes()).hexdigest():
                    return self._json(409, {"erro": "o áudio não é do roteiro de agora; espere regravar"})
                # voz-com-problema: com aviso da conferência, só passa com o "Ouvi, está ok" dele (mesmo_assim)
                mesmo_assim = bool(json.loads(self._corpo() or b"{}").get("mesmo_assim"))
                if c.get("problemas") and not mesmo_assim:
                    return self._json(409, {"erro": "a conferência achou problema na voz; toque em Consertar ou em Ouvi, está ok"})
                E.mexe_ficha(num, etapa="Animação", esperando="", passo=ANIMANDO, passo_desde=E.agora(), mudou=[], erro="")
                E.evento(num, "voz aprovada por ele" + (" com o aviso da conferência: " + " · ".join(c["problemas"]) if c.get("problemas") else ""))
                E.chat_add(num, "sistema", "Voz aprovada. O animador está fazendo a primeira animação (uns 5 a 10 minutos).")
                garantir(num)
                return self._json(200, {"ok": True})
            if acao == "reabrir-animacao":
                ok, motivo = reabrir_animacao(num)
                return self._json(200 if ok else 409, {"ok": True} if ok else {"erro": motivo})
            if acao == "voltar-roteiro":
                ok, motivo = voltar_roteiro(num)
                return self._json(200 if ok else 409, {"ok": True} if ok else {"erro": motivo})
            if acao == "voltar-animacao":
                # 16/10/2026 ("Voltar como estava" da prancha): a cena volta à versão de antes da última mudança, e o antes e o
                # depois e a conferência são refeitos
                an = E.pasta(num) / "animacao"
                vers = sorted((an / "versoes").glob("cena-*.html")) if (an / "versoes").exists() else []
                if not vers or E.ler_ficha(num)["passo"] in (ANIMANDO, CAPANDO):
                    return self._json(409, {"erro": "não há versão anterior, ou o animador está trabalhando"})
                import shutil
                atual = an / "cena.html"
                shutil.copy2(atual, an / f"cena-desfeita-{int(time.time())}.html")
                shutil.copy2(vers[-1], atual); vers[-1].unlink()
                animacao.fotos_dos_blocos(num, "depois")
                E.evento(num, "animação voltou para a versão anterior (pedido dele)")
                E.chat_add(num, "sistema", "Voltei a animação para como estava antes da última mudança.")
                threading.Thread(target=animacao.conferir, args=(num,), daemon=True).start()
                return self._json(200, {"ok": True})
            if acao == "escolher-capa":
                # 16/10/2026 ("aprovo o plano v2-capa"): a escolhida vira o 1 s do começo da prévia e a capa do Reels
                d = json.loads(self._corpo() or b"{}")
                if E.ler_ficha(num)["passo"] == CAPANDO:
                    return self._json(409, {"erro": "o animador está refazendo as capas; espere terminar"})
                try:
                    o = capa.escolher(num, int(d.get("op", 0)))
                except ValueError as ex:
                    return self._json(409, {"erro": str(ex)})
                E.mexe_ficha(num, esperando=esperando_animacao(num))
                E.chat_add(num, "sistema", f"Capa escolhida: opção {int(d['op'])} ({o.get('frase', '')}). Ela abre a prévia (1 s) e vai ser a capa do Reels.")
                return self._json(200, {"ok": True})
            if acao == "aprovar-video":
                # 16/10/2026 ("aprovo o plano v2-aprovar-video"): com capa, legenda e régua em ordem, vai para a etapa de
                # publicação (no funil, "Aguardando"), onde fica até ser publicado (a publicação é a parte 4)
                mesmo = bool(json.loads(self._corpo() or b"{}").get("mesmo_assim"))
                falta = faltas_aprovar(num, mesmo_assim=mesmo)
                if falta:
                    return self._json(409, {"erro": "ainda não dá para aprovar: " + "; ".join(falta)})
                E.mexe_ficha(num, etapa="Aguardando", passo=RENDERIZANDO, passo_desde=E.agora(), esperando="", progresso=5)
                gr = graves_regua(num) if mesmo else []
                E.evento(num, "vídeo aprovado por ele" + (f" mesmo com a régua: {'; '.join(gr)[:200]}" if gr else ""))
                E.chat_add(num, "sistema", "Vídeo aprovado. Estou gerando o vídeo final (uns 4 minutos); depois é só tocar em Publicar.")
                garantir(num)
                return self._json(200, {"ok": True})
            if acao in ("fazer-pauta", "descartar-pauta"):
                # 21/10/2026 (fase 2 do radar): a pauta que o radar sugeriu só anda quando ele decide
                f = E.ler_ficha(num)
                if f.get("passo") != "sugerida pelo radar":
                    return self._json(409, {"erro": "esta pauta não está esperando decisão"})
                import radar
                motivo = (json.loads(self._corpo() or b"{}").get("motivo") or "")
                if acao == "fazer-pauta":
                    radar.decidir(num, "fez", motivo)
                    E.mexe_ficha(num, passo="recebida", passo_desde=E.agora(), esperando="")
                    E.evento(num, "pauta do radar: ele mandou fazer")
                    garantir(num)
                else:
                    radar.decidir(num, "descartou", motivo)
                    E.evento(num, "pauta do radar: ele descartou" + (f" ({motivo.strip()[:120]})" if motivo.strip() else ""))
                    E.excluir(num)
                return self._json(200, {"ok": True})
            if acao == "excluir":
                # 16/10/2026 ("aprovo o plano botao-excluir"): vai para a lixeira; nunca com agente trabalhando nem publicado
                if not pode_excluir(num):
                    return self._json(409, {"erro": "não dá para excluir agora: vídeo publicado ou agente trabalhando"})
                E.excluir(num)
                return self._json(200, {"ok": True})
            if acao == "publicar" and PROVA:
                return self._json(409, {"erro": "modo prova: esta cópia não publica"})
            if acao == "publicar":
                # 16/10/2026 ("aprovo o plano v2-parte4-publicar"): o segundo toque no botão publica de verdade
                f = E.ler_ficha(num)
                fj = E.pasta(num) / "publicacao/final.json"
                conf = json.loads(fj.read_text()) if fj.exists() else None
                if f["etapa"] != "Aguardando" or f["passo"] in (RENDERIZANDO, PUBLICANDO) or not conf or conf.get("erros"):
                    return self._json(409, {"erro": "o vídeo final não está pronto para publicar"})
                if f.get("publicado") and f["publicado"].get("instagram"):
                    return self._json(409, {"erro": "este vídeo já foi publicado"})
                E.mexe_ficha(num, passo=PUBLICANDO, passo_desde=E.agora(), esperando="", passos=[])
                E.evento(num, "publicar: tocado por ele (dois toques)")
                garantir(num)
                return self._json(200, {"ok": True})
            if acao == "anexo":
                nome = re.sub(r"[^\w.-]+", "-", parse_qs(u.query).get("nome", ["anexo"])[0])[:80] or "anexo"
                d = E.pasta(num) / "anexos"; d.mkdir(exist_ok=True)
                (d / nome).write_bytes(self._corpo())
                msg, ja = E.chat_add(num, "ele", f"📎 anexei o arquivo anexos/{nome}", id_msg=self.headers.get("X-Id"))
                garantir(num)
                return self._json(200, {"recebida": True, "id": msg["id"], "quando": msg["quando"]})
        except Exception as ex:
            traceback.print_exc()
            return self._json(500, {"erro": str(ex)[:300]})

    def _ditar(self):
        """24/10/2026 ("pode ir consertar a parte do chat que envia o audio"): a tela manda o áudio do começo até agora a
        cada ~1 s (X-Parcial: 1) e o inteiro ao parar. Erro da Groq volta explicado (antes derrubava a conexão calado), e
        cada volta deixa uma linha no registro, sem o texto (como no kiteprocess)."""
        sys.path.insert(0, str(E.RAIZ / "ferramentas"))
        from transcrever import ditado
        audio, parcial, t0 = self._corpo(), self.headers.get("X-Parcial") == "1", time.time()
        tipo = (self.headers.get("Content-Type") or "?").split(";")[0]
        try:
            texto = ditado(audio)
        except Exception as e:
            print(f"ditado: {len(audio)} bytes de {tipo}{' (parcial)' if parcial else ''} · {time.time() - t0:.1f} s · ERRO {str(e)[:200]}", flush=True)
            return self._json(502, {"erro": f"não transcreveu: {str(e)[:200]}"})
        print(f"ditado: {len(audio)} bytes de {tipo}{' (parcial)' if parcial else ''} · {time.time() - t0:.1f} s · {len(texto)} caracteres", flush=True)
        return self._json(200, {"texto": texto})


if __name__ == "__main__":
    E.VIDEOS.mkdir(exist_ok=True)
    retomar()
    if not PROVA:                                # modo prova: sem os vigias (eles chamam IA e geram vídeo sozinhos)
        threading.Thread(target=vigia_roteiros, daemon=True).start()
        threading.Thread(target=vigia_previas, daemon=True).start()
    if os.environ.get("V2_RADAR", "1") == "1" and not PROVA:       # o servidor de teste (V2_RADAR=0) não roda o radar
        threading.Thread(target=vigia_radar, daemon=True).start()
    print(f"estúdio v2 em http://127.0.0.1:{PORTA}")
    class Servidor(ThreadingHTTPServer):
        def handle_error(self, request, client_address):
            # 19/10/2026 (no ar, iPhone): o celular corta a conexão do vídeo ao pular na barra; não é erro do estúdio
            import sys as _s
            if isinstance(_s.exc_info()[1], (ConnectionResetError, BrokenPipeError)):
                return
            super().handle_error(request, client_address)
    Servidor(("127.0.0.1", PORTA), H).serve_forever()
