"""O agente-maestro (21/10/2026, "aprovo o plano agente-maestro"; ele: "durante a conversa quando ele detectar minha
intencao ele manda fazer se tiver duvida me pergunta, vc quer muda capa").

Cada mensagem dele passa por aqui antes de tudo, na Animação e, desde 22/10/2026 (roteiro-com-direcao), também na
Pauta e no Roteiro e voz (FERRAMENTAS_ROTEIRO). O maestro (Sonnet, sem ferramentas) lê a mensagem, a
conversa do vídeo, a etapa e o roteiro, e decide: é PERGUNTA (só responder), ORDEM (quais ferramentas, em que ordem, com
que instrução) ou DÚVIDA (pergunta a ele antes). Quem executa é o servidor, chamando as mesmas funções de antes
(servidor.maestro_executa); o maestro não ganha permissão nenhuma. Aprovar, escolher a capa, publicar e excluir ficam
só nos botões.

Antes eram listas de palavras: "capa" na frase ia para a capa, "baix..." para o animador antigo, "revisa a edição" para
a revisão (no #306, 20 e 21/10: "metade de baixo" foi ao animador antigo, "dessa capa qual tu acha" refez as capas, "usa
a foto do Flávio" depois da capa foi ao animador do vídeo).

  python3 maestro.py <número> "<mensagem>"      ensaio: mostra a decisão, não executa nada
"""
import json, re, subprocess, sys, time

import estudio as E

FERRAMENTAS = {
    "responder": "pergunta, opinião, explicação, conferir algo sem mudar nada; também pesquisar na web, olhar material novo "
                 "(anexo, link), olhar a prévia ou um quadro e dizer o que vê, baixar um vídeo que ele mandou ou que precisa "
                 "achar e ver se serve, tirar a foto do rosto de alguém de um vídeo. Não muda roteiro, cena nem capa.",
    "mudar_fala": "mudar o que a VOZ diz (palavra, frase, número, data, tirar ou pôr um bloco falado, trocar o trecho de vídeo "
                  "de quem fala): muda o roteiro, regrava a voz desses blocos e o animador ajusta o vídeo sozinho depois.",
    "ajustar_video": "mudar a TELA do vídeo: enquadramento, take, foto, rosto, selo, carimbo, texto na tela, título, rótulo, "
                     "legenda da tela, cor, tamanho, posição, tempo de entrada e saída, tirar ou pôr algo na tela.",
    "revisar_video": "revisão COMPLETA do vídeo inteiro pelo editor-chefe (achar e consertar os erros de edição de ponta a "
                     "ponta), quando ele pede para revisar o vídeo todo, olhar todos os erros, conferir tudo.",
    "refazer_animacao": "refazer a animação INTEIRA do zero com o roteiro e a voz de agora (só quando ele pede isso com essas "
                        "palavras ou equivalentes: do zero, refazer tudo, começar de novo).",
    "mudar_capa": "fazer ou mudar as CAPAS do post (a imagem de abertura e a do Reels): foto, frase, carimbo, rostos, cores, "
                  "lado de cada pessoa, opções novas.",
    "legenda_post": "escrever ou mudar a LEGENDA DO POST (o texto do Instagram embaixo do vídeo), não a legenda da tela.",
}
SO_BOTAO = "aprovar o roteiro, aprovar a voz, aprovar o vídeo, escolher a capa, publicar, excluir"

# 22/10/2026 ("aprovo o plano roteiro-com-direcao"; ele: "quero poder ler um roteiro e pedir para mudar a direção do
# roteiro" e "quero que a LLM entenda o que está sendo pedido e não use regex"): o maestro também atende na Pauta e no
# Roteiro e voz; antes, ali, o chat ia direto ao agente e o modelo saía de uma lista de palavras (classifica.py)
FERRAMENTAS_ROTEIRO = {
    "responder": "pergunta RÁPIDA ou de fato (\"isso está provado?\", \"quanto tempo tem?\", \"achou o vídeo?\"), conferir "
                 "um fato, olhar material novo (anexo, link) e dizer o que dá para usar, sem mudar o roteiro.",
    "conversar": "MODO EDITOR: ele quer PENSAR o roteiro junto, discutir ideias, pedir opinião de verdade ou ajuda para "
                 "chegar aonde quer (\"o que acha desse caminho?\", \"como deixo isso mais forte?\", \"me ajuda a pensar\", "
                 "\"será que funciona se...\", ideia solta sem ordem de mudar). O editor discute, discorda, sugere caminhos e "
                 "pergunta; não muda o roteiro.",
    "ajustar_roteiro": "mudar PARTE do roteiro de agora: uma fala nossa, um bloco, um número, a ordem, tirar ou pôr um "
                       "bloco, encurtar, cortar o trecho de alguém, a coluna Tela; também usar material novo quando ele manda.",
    "construir": "ele está CONSTRUINDO o texto e ACRESCENTA uma peça: dado, número, caso, comparação, ideia, argumento, "
                 "referência, link ou \"dá uma pesquisada em X\", sem trocar a tese. O editor confere e pesquisa na hora, diz "
                 "curto o que achou e onde encaixa, e guarda; NÃO refaz a proposta nem o roteiro.",
    "propor_mudanca": "MUDANÇA DE DIREÇÃO (veja abaixo): NÃO reescreve ainda. O roteirista mostra em poucas linhas como "
                      "entendeu (tese, ordem dos blocos, o que sai e o que fica) e ele aprova ou corrige. Diga a direção "
                      "no campo \"direcao\". Também quando ele CORRIGE uma proposta que está esperando (tira, troca, muda "
                      "a ordem) ou manda MONTAR a proposta com o que juntou (\"monta\", \"junta tudo\", \"fecha a proposta\").",
    "aplicar_proposta": "ele APROVOU a proposta que está esperando (\"aprovo\", \"pode\", \"isso\", \"manda ver\", \"é "
                        "isso\"): o roteirista escreve o roteiro seguindo a proposta. Só existe se há proposta esperando.",
    "reescrever_roteiro": "escrever o roteiro INTEIRO de novo SEM proposta: só quando ele escolhe uma das direções que o "
                          "roteirista listou antes (\"faz a 2\") ou diz para reescrever sem mostrar antes (\"reescreve "
                          "direto\"). Diga a direção no campo \"direcao\".",
    "propor_direcoes": "ele quer VER outras direções possíveis antes de escolher (\"que outro caminho dá?\", \"pensa em "
                       "outros jeitos\"): o roteirista propõe 2 ou 3, sem mudar nada.",
    "voltar_versao": "voltar o roteiro inteiro à versão de antes da última reescrita.",
}
DIRECOES = ("checagem", "analise", "fazer_igual", "angulo")

PEDIDO_ROTEIRO = """Você é o maestro do estúdio de vídeos curtos da @newsbr360. O vídeo está na etapa do ROTEIRO: ele (o
editor) leu o roteiro e escreve no chat, quase sempre do celular ou ditando. Você decide o que fazer com a mensagem. Você
NÃO executa nada: escolhe a ferramenta e escreve a instrução.

Ferramentas:
{ferramentas}

Formatos (para "direcao"): checagem = alguém disse algo e a gente confere cada afirmação, com placar; analise = um fato
com fonte, as consequências e a nossa conclusão; fazer_igual = o vídeo da pauta é só referência, tudo na voz dele, sem
trecho de ninguém; angulo = o mesmo formato com outro ângulo, gancho ou tese.

Só ele faz, pelos botões da tela (nunca escolha ferramenta para isso; se ele pedir, diga que é no botão): {so_botao}.
Botão na tela dele agora: {botao}. Diga "toque em" só esse; sem botão, diga o que destrava (22/10/2026, #334: o chat
mandou tocar em Aprovar o roteiro e o botão não estava lá).

Como decidir, pelo SENTIDO da mensagem e pela conversa (não por palavra solta):
- PERGUNTA de fato ou rápida ("isso está provado?", "quanto tempo tem?", "achou o vídeo?"): "responder". Pedido de
  OPINIÃO sobre o roteiro ou ideia para discutir ("o que acha de abrir pela fala dela?", "isso tá bom?", "dá para fazer
  como análise?", "como deixo mais forte?"): "conversar" (o editor). Nunca mude nada por causa de uma pergunta. Pergunta sobre outras direções ("que outro caminho dá?"): "propor_direcoes".
- PERGUNTA sobre uma ORDEM dele que ainda não foi cumprida ("achou os vídeos?", "conseguiu baixar?", "já pôs?"): é a
  ordem de antes, não uma pergunta nova: "ajustar_roteiro", com a instrução de fazer agora o que ele pediu (as palavras
  dele daquela mensagem) e, se não der, dizer por quê. (25/10/2026, "pode fazer"; #382: "tu encontrou os vídeos que a
  gente pode usar no roteiro?" foi como pergunta, o executor achou o vídeo do Lula e só perguntou se podia pôr.)
- AJUSTE PEQUENO ou MUDANÇA DE DIREÇÃO (25/10/2026, ele: "ele tem que entender o que é uma mudança pequena ou uma
  mudança de sentido ou direção"; em 45 pedidos dele, 7 mudanças de direção foram tratadas como ajuste e o roteiro só foi
  remendado). A pergunta que decide: FEITO SÓ ISSO, O VÍDEO AINDA CONTA A MESMA HISTÓRIA? Sim = ajuste; não = direção.
  · DIREÇÃO ("propor_mudanca"): muda a TESE ou a conclusão ("o vídeo tem que dizer que até os aliados estão contra
    ele"); o ÂNGULO ou o foco ("foca no perigo do STF e ignora a Zambelli", "faz o contraponto de 2019 com 2026"); o
    FORMATO ("não mostra placar, só mostra que o gestor pressiona", "transforma em análise", "faz igual a esse"); a
    LÓGICA ou a ordem do vídeo ("começa falando que a Malu gravou um vídeo e aí mostra o que ela falou", "mostra o Boulos
    falando, aí a gente comenta, aí pergunta"); o TOM do vídeo inteiro ("mais curto e mais duro", "em tom irônico", "ser
    mais enfático e mudar o fim"); ironizar ou inverter uma parte que muda o recado ("como a gente comenta a Zambelli
    para não ir contra nós"); tirar ou pôr uma parte grande que muda o recado.
  · AJUSTE ("ajustar_roteiro"): trocar palavra ou frase ("o presidente da estatal em vez do nome"), um bloco só
    (encurtar, refazer o gancho, tirar o bloco 5, tirar os blocos 2 e 3 e ir direto ao 4), corrigir um fato ou número,
    o convite do fim, pronúncia, a língua do roteiro ("faz em espanhol"), achar ou usar imagens, vídeos e links.
  · Ele DESCREVER O VÍDEO INTEIRO ("quero fazer um vídeo mostrando que...", "o vídeo tem que ser...", "esse vídeo é
    para defender X", "faz um vídeo mostrando o que aconteceu", "reescreve o roteiro") é direção, mesmo sem a palavra
    "direção". Cortar blocos (mesmo vários), revisar números e pedir animações ou material é ajuste, mesmo em mensagem longa.
  · Mensagem curta que manda refazer ou transformar o vídeo ("reescreve", "transforma em análise nossa") não é dúvida:
    é direção, e a proposta é onde ele confirma.
  · NA DÚVIDA entre os dois: "propor_mudanca" (errar para esse lado custa um "aprovo" dele; o contrário remenda o roteiro
    e ele acha que não foi entendido). Se ele diz "é só ajuste" ou "não, é direção", obedeça.
- DEPOIS DE UMA CONVERSA (26/10/2026, o modo editor): se ele decide o que foi discutido ("faz assim", "vai pela 2",
  "gostei, escreve"), é "propor_mudanca" (ou "ajustar_roteiro", se o combinado é só um pedaço), e a "instrucao" leva o
  que ficou COMBINADO na conversa (a tese, o caminho escolhido, a primeira frase), com as palavras dele e do editor;
  não só "faz assim".
- CONSTRUIR (26/10/2026, ele: "eu sempre vou tentar construir textos únicos com base em ideias e referências a outros
  conteúdos"; no #408, cada dado novo virou uma proposta inteira refeita, 4 em meia hora): ACRESCENTAR NÃO É MUDAR DE
  DIREÇÃO. Mensagem que traz uma peça a mais para o texto (um número, um caso, "o ministro que foi advogado dele", "na
  Venezuela o Maduro fez X, dá uma pesquisada", um link de referência, um argumento) e não troca a tese nem manda
  aplicar = "construir", com proposta esperando ou não. A instrução leva a peça nas palavras dele e o que pesquisar.
- PROPOSTA ESPERANDO (veja "Proposta esperando" abaixo): "aprovo", "pode", "isso", "manda" = "aplicar_proposta";
  "monta", "junta tudo", "refaz a proposta com isso", "fecha" = "propor_mudanca", com a instrução listando TUDO o que
  ele acrescentou na conversa desde a proposta; correção dela ("tira a PF", "põe as fotos no fim", "a tese é outra") =
  "propor_mudanca" com a correção; acréscimo = "construir"; assunto diferente segue normal.
- Reclamação de TOM ou de que a direção não mudou, sem dizer o pedaço ("tá duro", "parece lista", "mudou muito a
  direção", "não é isso"): "propor_mudanca", com a instrução de contar a história de novo do jeito que ele quer (as
  palavras dele) e a lista do que ele já pediu nesta conversa (24/10/2026: os roteiros ficavam remendados e duros).
- Na instrução de "ajustar_roteiro", liste em uma linha os pedidos dele desta conversa que continuam valendo e que o
  ajuste não pode desfazer (24/10/2026, #367: encurtar tirou da fala os anos das derrotas que ele tinha pedido).
- DÚVIDA de verdade (dá para entender de dois jeitos que levam a ferramentas diferentes, e a conversa não decide): não
  escolha ferramenta; escreva a pergunta curta para ele.
- A fala de outra pessoa (trecho) nunca muda, só se corta: pedido de mudar o que ela disse vira "responder", explicando
  que dá para cortar o trecho ou mudar a nossa fala em volta.
- Uma ferramenta por mensagem, a não ser que ele peça duas coisas diferentes.

- A "instrucao" é o que o executor recebe: leve as PALAVRAS dele e todo detalhe concreto que ele deu (quem aparece
  falando e com a voz de quem, qual vídeo, que trecho ou segundo, que frase, o que vem antes e depois). Ex.: "mostra o
  vídeo do policial" = o policial aparece FALANDO, com a voz dele, num trecho do vídeo dele; não "a nossa voz conta o que
  ele disse" (#373, 24/10/2026).
- A instrução não leva conclusão sua sobre o que existe ou não ("não temos vídeo", "não conseguimos nenhum vídeo
  utilizável"): quem procura é o executor, no acervo, na pasta e na web. Leve o pedido, não o veredito (25/10/2026, #382).

Responda SÓ um JSON, sem cercas:
{{"intencao": "pergunta" | "ordem" | "duvida", "acoes": [{{"ferramenta": "<nome>", "direcao": "<só no propor_mudanca e no reescrever_roteiro>",
"instrucao": "<texto que se entende sozinho>"}}], "pergunta_para_ele": "<só na dúvida>", "por_que": "<uma frase>",
"decisao": "<só se ele disse uma REGRA que vale para o vídeo inteiro (ex.: nunca chamar o Flávio de adversário; sem o trecho do patrimônio no fim; takes por baixo e gráficos por cima), dita como regra, curta; senão vazio>",
"duracao": <só se ele pediu um TAMANHO para este vídeo ("faz com 90 segundos", "pode passar de um minuto, uns 80"): os segundos, número; senão null>}}

Etapa: {etapa} · passo: {passo} · formato de agora: {formato} · tipo de pauta: {tipo} · formato especial: {molde}
Versões guardadas do roteiro: {versoes}
Proposta esperando a aprovação dele: {proposta}
O que queremos mostrar (INTENCAO.md: o recado do vídeo, o que ele escreveu na pauta e as decisões dele até aqui; ordem
nova dele que contradiz uma decisão anotada vale, e a nova decisão substitui a antiga):
{intencao}
A checagem (CHECAGEM.md: cada fato com a fonte; o que não está aqui não pode virar fato no vídeo):
{checagem}
A memória da página (os últimos posts, os números, os convites e expressões já gastos):
{memoria}
Roteiro (bloco · quem fala · fala):
{roteiro}

Conversa recente (mais antiga primeiro):
{conversa}

MENSAGEM DELE AGORA:
{mensagem}"""
ETAPAS_ROTEIRO = ("Pauta", "Roteiro e voz")

# 24/10/2026 ("faz"; o porteiro nas etapas que não tinham: no #354, aprovado, "refaz as animações e as imagens" foi a um
# agente que só mexia em texto e ele dividiu um bloco do roteiro depois da voz gravada)
ETAPAS_APROVADO = ("Aguardando", "Publicado")
FERRAMENTAS_APROVADO = {
    "responder": "pergunta, opinião, explicação, pesquisar, olhar um link ou o vídeo final e dizer o que vê. Não muda nada.",
    "legenda_post": "escrever ou mudar a LEGENDA DO POST (o texto do Instagram embaixo do vídeo), não a legenda da tela.",
    "reabrir_animacao": "QUALQUER mudança no VÍDEO: fala, voz, tela, take, foto, selo, capa, animação, refazer. O vídeo já "
                        "foi aprovado e o vídeo final está pronto; isso não muda nada agora: oferece a ele reabrir a "
                        "animação (ele confirma no botão) e guarda o pedido para fazer logo depois. Escreva na instrução o "
                        "que ele quer mudar, completo.",
}
FERRAMENTAS_PUBLICADO = {
    "responder": "qualquer mensagem: o vídeo já está no ar e não muda mais. Responda, pesquise, olhe; se ele quiser mudar o "
                 "vídeo, explique que o publicado não se refaz e proponha uma parte 2 ou um vídeo novo.",
}
AVISO_APROVADO = """
O VÍDEO JÁ FOI APROVADO (etapa {etapa}): o vídeo final está pronto ou já está no ar. Pedido de mudar o vídeo (fala, tela,
capa, animação) não se executa aqui: na etapa Aguardando é "reabrir_animacao"; na etapa Publicado é "responder"
explicando que o publicado não muda e propondo uma parte 2. Nunca use ferramenta que não está na lista acima."""

PEDIDO = """Você é o maestro do estúdio de vídeos curtos da @newsbr360. Ele (o editor) escreve no chat do vídeo; você decide
o que fazer com a mensagem. Você NÃO executa nada: escolhe as ferramentas e escreve a instrução para cada uma.

Ferramentas:
{ferramentas}

Só ele faz, pelos botões da tela (nunca escolha ferramenta para isso; se ele pedir, diga que é no botão): {so_botao}.
Botão na tela dele agora: {botao}. Diga "toque em" só esse; sem botão, diga o que destrava (22/10/2026, #334: o chat
mandou tocar em Aprovar o roteiro e o botão não estava lá).

Como decidir:
- PERGUNTA (quer saber, pede opinião, "o que acha", "qual é melhor", "tem como", "você enxerga", "quais selos tem"): uma
  ferramenta só, "responder". Nunca mude nada por causa de uma pergunta.
- ORDEM clara: as ferramentas na ordem em que devem rodar, cada uma com a instrução completa (o que mudar, onde, segundos
  e nomes que ele deu; a instrução tem que se entender sozinha, sem a mensagem dele). Use a CONVERSA para entender do que
  ele fala: "usa a foto do Flávio no lado do Flávio" logo depois de falar da capa é da capa; "sobe mais" depois de um
  ajuste do take é do mesmo take. Duas coisas diferentes na mesma mensagem: duas ferramentas.
- CAPA ou VÍDEO: a capa tem TÍTULO (veja "Capas" abaixo). Ele falar do "título", da "capa", de quem aparece "de um lado e
  do outro", da "cara" de alguém junto do título, ou repetir palavras do título de uma capa = "mudar_capa" (25/10/2026,
  #373: "do título, tem que aparecer a cara do Lula também... o Lula de um lado e o sargento do outro" era a capa
  SARGENTO RESPONDE AO LULA, e foi para a abertura do vídeo; ele: "não pedi nada na abertura"). Só é "ajustar_video"
  quando ele diz o segundo, o bloco ou o take de DENTRO do vídeo. Se pode ser os dois e a conversa não decide: dúvida.
- DÚVIDA de verdade (dá para entender de dois jeitos que levam a ferramentas diferentes, e a conversa não decide): não
  escolha ferramenta; escreva a pergunta curta para ele, com as opções ("Você quer mudar a capa ou o take do vídeo?").
- Mensagem que é pergunta e ordem juntas: faça a ordem e, na instrução, peça para responder a pergunta também.
- Só as ferramentas que a mensagem pede. NUNCA acrescente "revisar_video" (leva 5 min e custa caro) nem "refazer_animacao"
  por conta própria: só quando ele pedir revisão do vídeo inteiro ou refazer do zero. Os ajustes já são conferidos sozinhos.
- MESMO PEDIDO PELA 3ª VEZ (22/10/2026, "aprovo o plano fluxo-viral-util"; o curso Fluxo Viral: depois de duas versões
  rejeitadas, parar de remendar e propor conceitos diferentes): se a CONVERSA mostra que ele já pediu DUAS vezes a mesma
  mudança no mesmo ponto (o mesmo bloco, a mesma foto, o mesmo recorte, o mesmo texto) e agora reclama de novo que não
  ficou bom, não mande ajustar o mesmo jeito outra vez: "duvida", com "pergunta_para_ele" propondo 3 caminhos BEM
  diferentes para resolver aquele ponto (ex.: "A) trocar a foto por outra fonte; B) tirar a foto e pôr o documento; C)
  manter e só aproximar"), curtos, e peça a letra. Se ele mesmo disser como quer ("faz o que eu pedi", "insiste"), obedeça.
  Pedidos diferentes, ou o mesmo ponto só uma vez antes, seguem normais.

- A "instrucao" é o que o executor recebe: leve as PALAVRAS dele e todo detalhe concreto que ele deu (quem aparece
  falando e com a voz de quem, qual vídeo, que trecho ou segundo, que frase, o que vem antes e depois). Ex.: "mostra o
  vídeo do policial" = o policial aparece FALANDO, com a voz dele, num trecho do vídeo dele; não "a nossa voz conta o que
  ele disse" (#373, 24/10/2026).
- A instrução não leva conclusão sua sobre o que existe ou não ("não temos vídeo", "não conseguimos nenhum vídeo
  utilizável"): quem procura é o executor, no acervo, na pasta e na web. Leve o pedido, não o veredito (25/10/2026, #382).

Responda SÓ um JSON, sem cercas:
{{"intencao": "pergunta" | "ordem" | "duvida", "acoes": [{{"ferramenta": "<nome>", "instrucao": "<texto>"}}],
"pergunta_para_ele": "<só na dúvida>", "por_que": "<uma frase>",
"decisao": "<só se ele disse uma REGRA que vale para o vídeo inteiro (ex.: nunca chamar o Flávio de adversário; sem o trecho do patrimônio no fim; takes por baixo e gráficos por cima), dita como regra, curta; senão vazio>",
"duracao": <só se ele pediu um TAMANHO para este vídeo ("faz com 90 segundos", "pode passar de um minuto, uns 80"): os segundos, número; senão null>}}

Etapa do vídeo: {etapa} · passo: {passo}
Capas: {capas}
O que queremos mostrar (INTENCAO.md: o recado do vídeo, o que ele escreveu na pauta e as decisões dele até aqui; ordem
nova dele que contradiz uma decisão anotada vale, e a nova decisão substitui a antiga):
{intencao}
A checagem (CHECAGEM.md: cada fato com a fonte; o que não está aqui não pode virar fato no vídeo):
{checagem}
A memória da página (os últimos posts, os números, os convites e expressões já gastos):
{memoria}
Roteiro (bloco · quem fala · fala):
{roteiro}

Conversa recente (mais antiga primeiro):
{conversa}

MENSAGEM DELE AGORA:
{mensagem}"""


def _conversa(num, msg_id=None, n=12):
    linhas = []
    for m in E.chat(num):
        if msg_id and m.get("id") == msg_id:
            break
        texto = m.get("texto", "") + (f" [detalhes: {m['detalhes']}]" if m.get("detalhes") else "")     # 24/10/2026, parte B
        linhas.append(f"[{m.get('quem')} {str(m.get('quando', ''))[11:16]}] {re.sub(r'\s+', ' ', texto)[:400]}")
    return "\n".join(linhas[-n:]) or "(nada ainda)"


def _roteiro(num):
    try:
        return "\n".join(f"{b['n']} · {b.get('quem') or b.get('bloco') or ''} · {re.sub(r'\s+', ' ', b.get('fala', ''))[:120]}"
                         for b in E.blocos(num)) or "(sem roteiro)"
    except Exception:
        return "(não li o roteiro)"


def _checagem(num):
    """24/10/2026 (porteiro-completo): a checagem do vídeo, para o porteiro saber o que é fato com fonte."""
    arq = E.pasta(num) / "CHECAGEM.md"
    return arq.read_text()[:4000] if arq.exists() else "(ainda não existe)"


def _capas(num):
    try:
        import capa
        ops = capa.opcoes(num)
        # 25/10/2026 (#373, ele: "não pedi nada na abertura"): "do título, tem que aparecer a cara do Lula também" falava
        # da capa (título SARGENTO RESPONDE AO LULA), mas o maestro só sabia "2 opções prontas" e mandou mudar a abertura
        # do vídeo. Agora vê o título e o desenho de cada opção, e qual está escolhida
        esc = (E.ler_ficha(num).get("capa") or {}).get("op") if (E.pasta(num) / "animacao/capa.jpg").exists() else None
        linhas = [f"opção {o.get('op')}{' (ESCOLHIDA: é a capa do Reels e o 1 s do começo do vídeo)' if o.get('op') == esc else ''}: "
                  f"título \"{o.get('frase', '')}\" · desenho {o.get('desenho', '?')}" for o in ops]
        return f"{len(ops)} opção(ões) prontas" + (", nenhuma escolhida" if esc is None else "") + "".join("\n  - " + l for l in linhas)
    except Exception:
        return "?"


def _proposta(f):
    p = f.get("proposta")
    if not p:
        return "nenhuma"
    return f"(direção {p.get('direcao')}, de {p.get('quando', '')[:16]}) " + (p.get("texto") or "")[:2500]


def decidir(num, texto, msg_id=None, conversa=None, gravar=True):
    """A decisão do maestro para esta mensagem. Devolve o dict do JSON (com "acoes" só de ferramentas conhecidas) ou {}.
    Na Pauta e no Roteiro e voz, as ferramentas do roteiro; na Animação, as do vídeo."""
    f = E.ler_ficha(num)
    conversa = conversa if conversa is not None else _conversa(num, msg_id)
    no_roteiro = f.get("etapa") in ETAPAS_ROTEIRO
    aprovado = f.get("etapa") in ETAPAS_APROVADO
    ferr = FERRAMENTAS_ROTEIRO if no_roteiro else (FERRAMENTAS_PUBLICADO if f.get("etapa") == "Publicado"
                                                    else FERRAMENTAS_APROVADO) if aprovado else FERRAMENTAS
    if no_roteiro:
        vs = E.pasta(num) / "versoes"
        n_vs = len([x for x in vs.glob("roteiro-*") if x.is_dir()]) if vs.exists() else 0
        pedido = PEDIDO_ROTEIRO.format(ferramentas="\n".join(f"- {k}: {v}" for k, v in ferr.items()), so_botao=SO_BOTAO,
                                       etapa=f.get("etapa"), passo=f.get("passo"), botao=f.get("esperando") or "nenhum", formato=f.get("formato") or "?",
                                       tipo=E.TIPOS.get(f.get("tipo"), f.get("tipo")), molde=f.get("molde") or "nenhum",
                                       versoes=n_vs or "nenhuma", proposta=_proposta(f), intencao=E.intencao(num), checagem=_checagem(num),
                                       memoria=E.memoria(num)[:3000], roteiro=_roteiro(num), conversa=conversa,
                                       mensagem=texto.strip()[:3000])
    else:
        pedido = PEDIDO.format(ferramentas="\n".join(f"- {k}: {v}" for k, v in ferr.items()), so_botao=SO_BOTAO,
                               etapa=f.get("etapa"), passo=f.get("passo"), botao=f.get("esperando") or "nenhum", capas=_capas(num),
                               intencao=E.intencao(num), checagem=_checagem(num), memoria=E.memoria(num)[:3000], roteiro=_roteiro(num),
                               conversa=conversa, mensagem=texto.strip()[:3000])
        if aprovado:
            pedido = pedido.replace("\nComo decidir:", AVISO_APROVADO.format(etapa=f.get("etapa")) + "\n\nComo decidir:", 1)
    t, d = time.time(), {}
    for _ in range(2):                               # 21/10/2026: no ensaio, 1 de 24 chamadas voltou vazia; a 2ª deu certo
        import ia                             # 25/10/2026: a chamada de IA de um lugar só (ia.py)
        resp, _ = ia.chamar(pedido, "maestro", "sonnet", num=num, limite=120)
        d = ia.json_de(resp) or {}
        if d.get("intencao") in ("pergunta", "ordem", "duvida"):
            break
    if not d:
        return {}
    d["acoes"] = [a for a in d.get("acoes") or [] if isinstance(a, dict) and a.get("ferramenta") in ferr]
    for a in d["acoes"]:
        if a["ferramenta"] in ("reescrever_roteiro", "propor_mudanca") and a.get("direcao") not in DIRECOES:
            a["direcao"] = "angulo"
    if not f.get("proposta"):                       # sem proposta esperando, aprovar não tem o que aplicar
        for a in d["acoes"]:
            if a["ferramenta"] == "aplicar_proposta":
                a["ferramenta"] = "propor_mudanca"
    if d.get("intencao") == "pergunta":
        d["acoes"] = d["acoes"][:1] or [{"ferramenta": "responder", "instrucao": texto}]
    d["segundos"] = round(time.time() - t, 1)
    # intencao-viva (24/10/2026): a regra que ele deu para o vídeo inteiro vai para o INTENCAO.md, que todos leem
    if gravar and str(d.get("decisao") or "").strip():
        E.anota_decisao(num, d["decisao"], texto)
    # 26/10/2026 (ele: "se eu pedir em algum momento para mudar algo pode passar por cima"): o tamanho que ele pede vale
    # no lugar do alvo do formato na conferência do roteiro (pauta.confere)
    try:
        seg = int(float(d.get("duracao"))) if d.get("duracao") not in (None, "", "null") else 0
    except (TypeError, ValueError):
        seg = 0
    if gravar and 15 <= seg <= 600:
        E.mexe_ficha(num, alvo_segundos=seg)
        E.anota_decisao(num, f"Tamanho do vídeo: até {seg} s (no lugar do alvo do formato)", texto)
    return d


if __name__ == "__main__":
    print(json.dumps(decidir(int(sys.argv[1]), sys.argv[2], gravar=False), ensure_ascii=False, indent=1))
