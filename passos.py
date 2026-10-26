"""O mapa de passos do estúdio (24/10/2026, "aprovo o plano mapa-de-passos"; R3 do ESTUDIO-V2-REFATORAR-2310.md).

Uma tabela só com cada passo de um vídeo: em que etapa ele pode estar, que tipo de passo é, o que ele espera de você,
os botões (as ações do servidor, /api/item/<n>/<acao>) e a saída. Antes, o estado eram três textos soltos (etapa, passo,
esperando) comparados em ~140 lugares, e a lista "está trabalhando" existia em 5 cópias diferentes: daí os becos sem
saída (#334 sem botão; #354 na VPS em "Aguardando · roteiro pronto · Publicar" depois de o agente mudar o roteiro de um
vídeo já aprovado).

Parte 1 (esta): só a tabela e o teste (testes/mapa_passos.py), que mostra os becos de hoje sem mudar nada.
Parte 2: o servidor passa a mudar de passo por aqui e as ações aceitam pela tabela.
Parte 3: a tela desenha os botões que o servidor manda.

Tipos:
  trabalhando  o estúdio está fazendo algo; o trabalhador continua sozinho e, ao religar, `religar` diz o que fazer
  espera       parado esperando você: tem de ter botão ou o chat como saída
  parou        deu errado: tem de ter botão de tentar de novo (e o chat)
  fim          publicado; o chat só conversa
"""

ETAPAS = ["Pauta", "Roteiro e voz", "Animação", "Aguardando", "Publicado"]

# as esperas (o campo "esperando" da ficha): o texto é o que a tela mostra em "ESPERANDO VOCÊ · ..."
APROVAR_ROTEIRO, APROVAR_VOZ, VOZ_PROBLEMA, GRAVAR_VOZ = "Aprovar o roteiro", "Aprovar a voz", "Voz com problema", "Gravar a voz"
ESCOLHER_CAPA, APROVAR_VIDEO, PUBLICAR, FAZER_PAUTA = "Escolher a capa", "Aprovar o vídeo", "Publicar", "Fazer esta pauta?"

T, E_, P, F = "trabalhando", "espera", "parou", "fim"

# passo: {etapas, tipo, espera (as esperas possíveis; "" = nenhuma), botoes, chat (mensagem dele é saída), religar, tela}
# religar: o que o servidor faz com o passo ao reiniciar ("continua" = o trabalhador recomeça; senão, o passo de destino)
PASSOS = {
    # ---- Pauta ----
    "sugerida pelo radar": {"etapas": ["Pauta"], "tipo": E_, "espera": [FAZER_PAUTA], "botoes": ["fazer-pauta", "descartar-pauta"],
                            "chat": False, "tela": "o radar sugeriu; você decide se faz"},
    "recebida": {"etapas": ["Pauta"], "tipo": T, "religar": "continua", "tela": "na fila da pauta"},
    "baixando o áudio": {"etapas": ["Pauta"], "tipo": T, "religar": "continua", "tela": "baixando o áudio"},
    "baixando o vídeo": {"etapas": ["Pauta"], "tipo": T, "religar": "continua", "tela": "baixando o vídeo"},
    "transcrevendo": {"etapas": ["Pauta"], "tipo": T, "religar": "continua", "tela": "transcrevendo"},
    "transcrevendo e assistindo": {"etapas": ["Pauta"], "tipo": T, "religar": "continua", "tela": "transcrevendo e assistindo"},
    "baixando o material": {"etapas": ["Pauta"], "tipo": T, "religar": "continua", "tela": "baixando o material"},
    "lendo o material": {"etapas": ["Pauta"], "tipo": T, "religar": "continua", "tela": "lendo o material"},
    "escrevendo o roteiro": {"etapas": ["Pauta"], "tipo": T, "religar": "continua", "tela": "escrevendo o roteiro"},
    "parou": {"etapas": ["Pauta"], "tipo": P, "espera": [""], "botoes": ["tentar-pauta"], "chat": True,
              "tela": "a pauta parou; o motivo está no chat"},
    # o roteiro existe: na Pauta espera a aprovação; em Roteiro e voz, sem voz gravada, o botão grava (botoes-sempre, #334)
    "roteiro pronto": {"etapas": ["Pauta", "Roteiro e voz"], "tipo": E_, "espera": [APROVAR_ROTEIRO, ""],
                       "botoes": {"Pauta": ["aprovar-roteiro"], "Roteiro e voz": ["gravar-voz-de-novo"]}, "chat": True,
                       "tela": "o roteiro está pronto"},
    # o agente do chat trabalhando, em qualquer etapa antes de publicar (com link no pedido, também na Animação e na
    # Publicação: testes/passo_depois_do_pedido.py); ao religar sem mensagem pendente, volta ao passo de espera da etapa
    "trabalhando no seu pedido": {"etapas": ["Pauta", "Roteiro e voz", "Animação", "Aguardando"], "tipo": T,
                                  "religar": {"Pauta": "roteiro pronto", "Roteiro e voz": "roteiro pronto",
                                              "Animação": "prévia pronta", "Aguardando": "vídeo final pronto"},
                                  "tela": "o agente está trabalhando no seu pedido"},
    "baixando e transcrevendo o vídeo que você mandou": {"etapas": ["Pauta", "Roteiro e voz", "Animação", "Aguardando"], "tipo": T,
                                                         "religar": {"Pauta": "roteiro pronto", "Roteiro e voz": "roteiro pronto",
                                                                     "Animação": "prévia pronta", "Aguardando": "vídeo final pronto"},
                                                         "botoes": {"Animação": ["escolher-capa"]}, "tela": "baixando o vídeo que você mandou"},
    # ---- Roteiro e voz (e a voz de um bloco regravada na Animação) ----
    "gravando a voz": {"etapas": ["Roteiro e voz", "Animação"], "tipo": T, "religar": "continua", "botoes": {"Animação": ["escolher-capa"]},
                       "tela": "gravando a voz"},
    "voz pronta": {"etapas": ["Roteiro e voz"], "tipo": E_, "espera": [APROVAR_VOZ], "botoes": ["aprovar-voz"], "chat": True,
                   "tela": "a voz está pronta para ouvir"},
    "voz com problema": {"etapas": ["Roteiro e voz", "Animação"], "tipo": E_, "espera": [VOZ_PROBLEMA],
                         "botoes": {"Roteiro e voz": ["aprovar-voz"], "Animação": ["aprovar-voz", "escolher-capa", "voltar-animacao", "voltar-roteiro"]},
                         "chat": True, "tela": "a conferência achou problema na voz"},
    "voz parou": {"etapas": ["Roteiro e voz", "Animação"], "tipo": P, "espera": [GRAVAR_VOZ],
                  "botoes": {"Roteiro e voz": ["gravar-voz-de-novo"], "Animação": ["gravar-voz-de-novo", "escolher-capa", "voltar-animacao", "voltar-roteiro"]},
                  "chat": True, "tela": "a voz não saiu"},
    # ---- Animação ----
    # escolher a capa vale com o animador trabalhando (só não enquanto as capas são feitas): era assim antes do mapa
    "animando": {"etapas": ["Animação"], "tipo": T, "religar": "continua", "botoes": ["escolher-capa"], "tela": "o animador está trabalhando"},
    "fazendo as capas": {"etapas": ["Animação"], "tipo": T, "religar": "continua", "tela": "fazendo as capas"},
    "escrevendo a legenda": {"etapas": ["Animação"], "tipo": T, "religar": "continua", "botoes": ["escolher-capa"], "tela": "escrevendo a legenda do post"},
    "prévia pronta": {"etapas": ["Animação"], "tipo": E_, "espera": [ESCOLHER_CAPA, APROVAR_VIDEO, ""],
                      "botoes": ["escolher-capa", "aprovar-video", "voltar-animacao", "voltar-roteiro"], "chat": True,
                      "tela": "a prévia está pronta"},
    # ---- Aguardando (Publicação) ----
    "gerando o vídeo final": {"etapas": ["Aguardando"], "tipo": T, "religar": "continua", "tela": "gerando o vídeo final"},
    "vídeo final pronto": {"etapas": ["Aguardando"], "tipo": E_, "espera": [PUBLICAR],
                           "botoes": ["publicar", "reabrir-animacao", "voltar-roteiro"], "chat": True, "tela": "pronto para publicar"},
    "o vídeo final parou": {"etapas": ["Aguardando"], "tipo": P, "espera": [""], "botoes": ["gerar-final-de-novo", "reabrir-animacao", "voltar-roteiro"],
                            "chat": True, "tela": "o vídeo final parou"},
    "vídeo final com problema": {"etapas": ["Aguardando"], "tipo": P, "espera": [""],
                                 "botoes": ["gerar-final-de-novo", "reabrir-animacao", "voltar-roteiro"], "chat": True, "tela": "o vídeo final saiu com problema"},
    # publicar nunca recomeça sozinho: pode já ter saído (retomar, 16/10/2026)
    "publicando": {"etapas": ["Aguardando"], "tipo": T, "religar": "publicação interrompida", "tela": "publicando"},
    "publicação interrompida": {"etapas": ["Aguardando"], "tipo": P, "espera": [PUBLICAR], "botoes": ["publicar", "reabrir-animacao", "voltar-roteiro"], "chat": True,
                                "tela": "o servidor reiniciou no meio; confira no Instagram antes de publicar de novo"},
    "publicação falhou": {"etapas": ["Aguardando"], "tipo": P, "espera": [PUBLICAR], "botoes": ["publicar", "reabrir-animacao", "voltar-roteiro"],
                          "chat": True, "tela": "a publicação falhou"},
    # ---- Publicado ----
    "publicado": {"etapas": ["Publicado"], "tipo": F, "espera": [""], "chat": True, "tela": "no ar"},
}

# as ações que existem no servidor (/api/item/<n>/<acao>); "mensagem" e "anexo" são o chat, valem em todo passo
ACOES = {"aprovar-roteiro", "gravar-voz-de-novo", "gerar-final-de-novo", "tentar-pauta", "aprovar-voz", "reabrir-animacao",
         "voltar-roteiro", "voltar-animacao", "escolher-capa", "aprovar-video", "fazer-pauta", "descartar-pauta", "excluir",
         "publicar"}

TRABALHANDO = tuple(p for p, d in PASSOS.items() if d["tipo"] == T)


def info(passo):
    return PASSOS.get(passo)


def botoes(passo, etapa):
    """As ações que valem neste passo e etapa. Excluir vale em toda espera e parada (o servidor ainda confere se não há
    agente trabalhando nem mensagem pendente, em pode_excluir)."""
    d = PASSOS.get(passo) or {}
    b = d.get("botoes") or []
    b = list(b.get(etapa, []) if isinstance(b, dict) else b)
    return b + (["excluir"] if d.get("tipo") in (E_, P) and etapa in d.get("etapas", []) else [])


def religar(passo, etapa):
    """O que fazer com o passo quando o servidor reinicia: "continua" (o trabalhador recomeça), o passo de destino, ou
    None (não é trabalho)."""
    r = (PASSOS.get(passo) or {}).get("religar")
    return r.get(etapa) if isinstance(r, dict) else r


def confere(etapa, passo, esperando=""):
    """O estado (etapa, passo, esperando) existe no mapa? Devolve a lista de defeitos (vazia = ok)."""
    d = PASSOS.get(passo)
    if d is None:
        return [f"passo desconhecido: {passo!r}"]
    erros = []
    if etapa not in d["etapas"]:
        erros.append(f"o passo {passo!r} não existe na etapa {etapa!r} (só em {', '.join(d['etapas'])})")
    if d["tipo"] != T and (esperando or "") not in (d.get("espera") or [""]):
        erros.append(f"no passo {passo!r} a espera {esperando!r} não existe (pode: {', '.join(repr(x) for x in d.get('espera') or [''])})")
    if d["tipo"] in (E_, P) and not botoes(passo, etapa) and not d.get("chat"):
        erros.append(f"o passo {passo!r} na etapa {etapa!r} não tem saída (nem botão nem chat)")
    return erros
