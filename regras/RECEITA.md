# Receita dos vídeos da @newsbr360 (07/10/2026)

Pedido do Alexandre: "analise tudo que vc aprendeu até agora com esses videos que fizemos. analise o desempenho dos videos
para que possamos criar uma receita para fazer os proximos videos".
Base: 5 Reels de 06 e 07/10/2026. Os números são de uma noite só; a receita vale como hipótese até ter uns 15 vídeos.

## 1. Desempenho (medido em 07/10 às 22h, API do Instagram + contador da grade)
| Vídeo | Tipo | No ar | Visualizações (grade) | Curtidas | Comentários | Curtidas/hora | Colaborador |
|---|---|---|---|---|---|---|---|
| Janja checagem | reação + documento | 11,5 h | **252 mil** | **47.175** | **3.653** | **4.111** | Jeffrey e Tonynho convidados; publicado pelo Edits |
| Split payment | explicação + promessa | 5,7 h | 4.961 | 943 | 24 | 164 | alexandremota.digital (aceito) |
| Senado 2027 | dado puro | 22,5 h | 4.542 | 275 | 7 | 12 | alexandremota.digital |
| Câmara 2027 | dado puro | 22,1 h | 1.148 | 167 | 4 | 8 | nenhum |
| 2º turno projeção | dado + cenário | 0,1 h | 77 | 4 | 0 | (cedo) | alexandremota.digital (pendente) |
Conta: de 8 seguidores (06/10) para **1.174** (07/10 22h). Veio quase tudo do vídeo da Janja.
Falta medir: visualização por vídeo pela API (token sem `instagram_manage_insights`), retenção e compartilhamentos.

## 2. O que os números dizem (acho que, com 5 vídeos)
1. **Reação a uma pessoa conhecida que acabou de falar algo** venceu de longe: 252 mil contra ~5 mil dos outros. O que
   puxou: rosto conhecido + afirmação dela + a gente desmentindo com documento + carimbo "SEM PROVA". Gera briga nos
   comentários (3.653), e briga é alcance.
2. **Dado puro (Senado, Câmara)** informa, mas não faz ninguém comentar. Com colaborador anda; sem colaborador, morre
   (Câmara 8 curtidas/h).
3. **Explicação com promessa (split)** foi bem para o assunto técnico: 943 curtidas em 6 h, e o primeiro comentário foi de
   um empreendedor dizendo que precisa disso. Assunto de bolso pega.
4. **Colaborador conta** (Senado 4,5 mil com colaborador; Câmara 1,1 mil sem). Sempre convidar alexandremota.digital e,
   quando fizer sentido, um perfil grande do assunto.
5. **Velocidade**: o da Janja saiu no dia seguinte ao vídeo dela. Assunto quente vale mais que vídeo perfeito.

### Leitura de 08/10/2026 (4 vídeos do dia, parcial; Alexandre: "grava isso na receita")
Medido às 22h08 pela API, com idades diferentes (3 a 15 h); a medição justa é a de 24 h (metricas.py, 10h do dia seguinte).
| Vídeo | No ar | Visualizações | Por hora | Compartilhamentos (por mil vis.) | Retenção |
|---|---|---|---|---|---|
| Míriam Leitão, checagem (06h47) | 15,4 h | 37.571 | 2.440 | 655 (17) | 46% (30,3 s de 65,4) |
| Lula 200 bi, checagem (15h11) | 7,0 h | 11.531 | 1.650 | 425 (37) | 31% (20,0 s de 63,7) |
| Bolsa Família, informativo (18h53) | 3,3 h | 3.036 | 920 | 42 (14) | 34% (22,2 s de 64,7) |
| Pimenta, checagem RS (12h14) | 9,9 h | 4.998 | 505 | 42 (8) | 41% (32,1 s de 78,5) |
Conta: 3.622 seguidores às 22h08 (3.000 na medição das 10h); 3.650 visitas ao perfil no dia; alcance do dia 1,06 milhão
(acho que ainda puxado pelo vídeo da Janja; a API não separa). Seguidores por reel: a API não entrega (veio vazio).
O que isso sugere (acho que, com 4 vídeos):
6. **Nome nacional puxa alcance; tema regional fica regional.** Míriam (Globo) e Lula foram muito mais longe que Pimenta (RS).
7. **Confronto direto gera compartilhamento.** "Lula diz que o Flávio vai cortar" teve 37 compartilhamentos por mil
   visualizações, mais que o dobro dos outros: é o vídeo que o seguidor manda para alguém.
8. **Retenção:** 31% no Lula, o vídeo publicado com os erros corrigidos depois (carimbo de 0,3 s, telas vazias); 46% na
   Míriam. Erro de acabamento custa retenção.
9. **Horário:** a Míriam saiu às 6h47 e teve o dia inteiro. Testar mais vídeos de manhã.
Recomendação do dia: checagem de nome nacional, de manhã, ~60 s. Informativo (Bolsa Família) como variação, não como linha
principal.

## 3. A receita
### Escolher o assunto (nessa ordem de força)
1. Alguém conhecido do outro lado disse algo nas últimas 24 h que um documento derruba (formato Janja).
2. Promessa ou mudança que mexe no bolso, explicada com a lei na tela (formato split).
3. Número oficial com uma surpresa dentro (formato Senado, Câmara, projeção; ex.: "Amapá decidido por 225 votos").
Descartar: assunto sem documento público; "pesquisa" sem registro no TSE (ex.: o vídeo do @eleitorweb).

**Filtro do viés (11/10/2026).** Alexandre: "o nosso viés aqui é de direita, então esses vídeos tem que ter algo que a
gente possa provar que se a gente fizer um vídeo a favor nesse momento, é ruim para nós." Antes de propor pauta:
- Fica: o documento derruba alguém do outro lado, ou desmonta acusação/boato contra o nosso lado.
- Sai (agora): a checagem acabaria contra o nosso lado (ex.: TSE apagando vídeo do Flávio, "mudar a Constituição",
  deepfake do Flávio, boca de urna falsa que circulou na direita) ou a única fonte é veículo do nosso lado (Pleno News).
- O viés escolhe a pauta e o ângulo, nunca o veredito: se o print desmentir o nosso lado, a pauta cai, não se torce.

**Como escrever para quem já tem lado (EM TESTE desde 11/10/2026, no #59; comparar com Janja e Split e tirar se piorar. Aprendizado do @pyonglee, `referencias/DeUwLY9jBK3/`, 5 min sobre
raciocínio motivado):** quem é do grupo não aceita "seu candidato errou" (vira ameaça à identidade), e as saídas são
sempre as mesmas: "não foi bem assim", "todo mundo faz", "a imprensa exagera", "o outro fez pior", "precisa entender o
contexto". Para nós:
- Antecipar a desculpa do outro lado e fechar com o documento ("e não foi tirado de contexto: aqui está a fala inteira"),
  só quando a desculpa é previsível (custa 3-5 s; o Janja venceu por ser direto).
- Não atacar o eleitor do outro lado, só a fala/o político (atacar o eleitor faz ele defender o grupo).
- A abertura dele é pergunta que o espectador sente que é sobre ele ("por que uma pessoa inteligente defende algo
  errado?") e repete a pergunta depois do aviso. Só testar; o nosso gancho forte continua sendo acusação + rosto + documento.

### Analisar o vídeo de referência (desde 08/10/2026: áudio primeiro)
- `python3 ferramentas/analisar_reel.py LINK` baixa SÓ o áudio e transcreve na Groq com tempo por palavra
  (`referencias/<código>/transcricao.txt`, `palavras.json`, `meta.json`). Medido: 7,5 s na VPS (reel de 3 min).
  Alexandre: "primeiro escuta o áudio [...] vai ter vídeo que não vamos precisar baixar".
- Só depois de decidir fazer o vídeo: `--video` baixa o vídeo (bolinha e quadros).
- Resposta padrão a um link (resumo, afirmações checáveis com chance de contestar, veredito do formato): ver
  ESTUDIO-NA-NUVEM.md, passo 0.
- Cortes da fala dele: `transcrever.borda()` com o fim da primeira palavra e o começo da última. A Groq (e o Whisper
  local) marcam a palavra depois de pausa até 1,6 s cedo demais; o acerto pelo silêncio deixou 4 de 4 casos a 0,1 s.

### Checar antes de escrever (ninguém grava sem isto)
- Todo número e toda citação na fonte original: TSE (resultados.tse.jus.br, DivulgaCand), Planalto (lei compilada,
  sem o texto riscado), Câmara/Senado (dados abertos), matéria lida inteira (não o resumo). Vai para `CHECAGEM.md`.
- Conta refeita do zero por outro caminho antes de publicar (no 2º turno, essa revisão achou "seis milhões e meio" que
  eram 6,39 e "quinze estados" que eram 14 + DF).
- O que não deu para ler no original sai do vídeo (ex.: "desde 1989", Nexo fechado) ou entra como "segundo [fonte]".
- **Quem fala (15/10/2026, "aprova o plano quem-fala"; Alexandre: "isso não podemos errar").** Quem fala não é quem
  postou: o #119 era da conta da Renata Simoso e a fala era do jornalista Eduardo Oinegue (BandNews FM, 06/02/2025); o
  #107, da Margareth Buzetti. A ficha `QUEM-FALA.json` da pauta diz quem fala, com prova; sem ela o roteiro não sai, e
  roteiro, rascunho e voz que dizem outro nome são recusados. Busca por imagem só por último; reconhecimento de rosto nunca.
- **Abertura de checagem de fala:** "<quem é> <nome> acusou/denunciou <o quê>. A gente foi verificar. Olha o que
  ele/ela disse." (Alexandre, 15/10: "o jornalista tal fez uma denúncia/acusação e a gente verificar. aí entra a fala
  dele e continua"). Quem só repostou não aparece nas falas.
- **Fala com mais de 30 dias diz de quando é** ("em fevereiro de dois mil e vinte e cinco"): vídeo velho repostado
  parece notícia de hoje.

### Decisões do vídeo do Pimenta (08/10/2026) que valem para toda checagem de fala
- **Contexto no gancho**: quem é e o que o vídeo dele É ("orientando a militância a virar votos para o Lula"), dito
  literalmente a partir da fala dele. Cargo só o medido (ele "disputou o Senado"; não é mais candidato, TSE RS 04/10).
- **A conta é a dele**: checa a frase como ele disse ("50 milhões" incluía os outros candidatos). Arredondou para cima
  = **EXAGERO**, nunca "não é verdade". Alexandre quis tirar uma parcela da conta; a recomendação foi não (vira erro nosso).
- **Tirar fala errada dele é honesto; tirar a certa, não.** Sempre fica a VERDADE (o "transporte"), no meio do vídeo.
- **Máximo 4 carimbos.** Com 5 o vídeo passou de 75 s; o que sai é o mais delicado de explicar ("metade": DESATUALIZADO).
- **Não citar o candidato do nosso lado** no vídeo de checagem (vira propaganda e perde a credibilidade).
- **Título literal** do que ele faz + placar no selo da capa ("1 EXAGERO · 2 ERROS · 1 ACERTO").
- Fecho devolve a pergunta dele ("É isso que você quer pro Brasil?" → "Antes de responder, confere o número").

### Roteiro (40 a 60 s; acima de 70 s perde gente)
1. **Gancho em 3 s**: a afirmação mais forte que o vídeo PROVA (ex.: "Com Zema e Caiado, o Flávio abre 5 milhões").
2. **Explica** o que é, com a lei/documento na tela e o trecho grifado.
3. **Prova**: print da fonte + carimbo (SEM PROVA vermelho / CONFIRMADO verde / PREVISÃO roxo).
4. **Fecho** com chamada: "compartilha" + pergunta que gera comentário SEM ser enquete de voto
   (ex.: "você vai votar no dia 25?").
- Antes e depois com o mesmo desenho quando for explicar mudança (a moeda do split).
- Números falados arredondados para baixo ou com "quase"; exatos na tela e na legenda.

### Biblioteca de cenas: consultar ANTES de desenhar (08/10/2026)
Alexandre: "tem que colocar na receita de criação do vídeo uma instrução para o editor decidir ou verificar se pode usar
um item da biblioteca de itens".
1. **No roteiro**, para cada frase, a coluna "Tela" diz qual item da biblioteca entra (catálogo em `newsbr360/MOLDES.md`,
   seção 2: hemiciclo, mapa do Brasil, placar em barras, bonecos, moeda/pizza/ícones, checagem de fala, documentos de
   tela, foto redonda/VS, carimbo, cartela final). Só fica "cena nova" o que nenhum item cobre, e o roteiro diz por quê.
2. **Usa se** o item mostra o que a frase diz sem forçar (ex.: conta de votos no Senado → hemiciclo; dado por estado →
   mapa; "fulano disse" → molde de checagem). **Não usa se** o item mudaria o sentido ou esconderia o dado (ex.: mapa
   para 3 estados; hemiciclo para pesquisa de opinião).
3. **Cena nova que serve para outro vídeo** entra na biblioteca e no catálogo do MOLDES.md no mesmo dia, com a prova de
   que o vídeo que a criou sai igual.
4. Ao mostrar o roteiro ao Alexandre, listar numa linha os itens da biblioteca usados e as cenas novas.

### Pedir para seguir e zona segura (08/10/2026, ANALISE-SEGUIDORES.md)
Alexandre: "pode colocar a faixa e a fala no molde" e "analise a zona segura do vídeo para não dificultar a pessoa de
clicar no local de seguir".
- **Fala no fecho**: a última frase termina com "Segue a NewsBR360 para a próxima checagem." (o molde avisa se faltar).
- **Faixa "SIGA @newsbr360"** no 1º trecho "ELE DISSE" depois do 1º carimbo (ficha: `seguir: {trecho: ...}`), por 2,6 s,
  no lugar da etiqueta (y 480). Antes da saída média (Janja: 26 s).
- **Zona segura da Meta** (especificação de anúncios em Reels, lida no original em 08/10): 14% em cima (0-269 px), 35%
  embaixo (1248-1920) e 6% dos lados livres de texto e logo. Nada do que desenhamos bloqueia o toque no Seguir (o botão
  do app fica por cima do vídeo); o risco é texto nosso disputar o olhar com o nome do perfil e o botão.
  Medido no molde: legenda (157 px dentro da base), marca d'água (289 px), carimbo (65 px) e contador 1/4 (79 px dentro
  do topo) estão fora da zona; mudar o layout espera o "aprovo" do Alexandre.
- **Medido nos prints do feed do Alexandre (08/10)**: o nome do perfil cobre o vídeo até ~205 px; a **pílula de seguir**
  ("newsbr360 · NewsBR360 Política com prova") fica em ~1437-1601 e cobria a marca d'água; repostagens ~1620-1724.
  **Layout 2** (padrão do molde desde 08/10, "aprovo as 3 mudanças, pode aplicar"): sem marca d'água embaixo, contador
  em y 290, legenda em y 1340. Vídeos fora do molde seguem o mesmo: `marca_dagua=None` e `legenda_original(y=1340)`.
- **Medido nos prints da aba Reels em tela cheia (08/10)**: o app amplia o vídeo a 94% e corta ~50 px de cada lado;
  seta e câmera em y 197-256; **coluna de ícones em x ≥ 914, de y 765 a 1645**; nome do perfil e legenda escrita em
  y 1565-1730. Layout 2, parte 2 ("pode fazer as alteracoes"): legenda com no máximo 20 letras por linha (partida à
  força, cada pedaço no mínimo 0,35 s), documentos em x 80-884, caixas da abertura e do placar até x 890, crédito em
  21 px, carimbo 100 px mais alto e o molde avisa texto que passe de x 900.
- **Capas**: texto entre y 300 e 1500 e até x ~900 (o 1 s de capa no começo aparece sob os ícones e o nome do perfil;
  ex.: "SÓ 1 É VERDADE" da Míriam ficou sob os ícones).

### Tela
- Fundo azul com faixas, legenda grande palavra a palavra com destaques em amarelo, marca d'água, cartela "FATO, FONTE E
  PONTO." com as fontes e créditos das fotos.
- Fotos de pessoas em **bolinha**; disputa com **VS**. Fotos oficiais (TSE, Senado, Planalto, Wikimedia CC) com crédito.
- Prints legíveis: largura estreita na captura (`capturar.py --largura 420`) e trecho grifado; texto longo vira citação grande.
- Nada parado mais de 1 s (medir com freezedetect).

### Capa (decisões do Alexandre em 07/10)
- **Padrão desde 11/10: capa estilo documentário** (`capa: {estilo: documentario, ...}` no molde de checagem; MOLDES.md).
  Alexandre: "criar um padrão de capa assim, estilo documentário, que apareça a cara da pessoa. Já está provado que
  aparecendo a cara da pessoa [...] ganha destaque." Rosto grande no alto (quadro com emoção), frase embaixo, sem
  placar/número na capa ("a gente já vai dizer como ela votou": a capa pergunta, o vídeo responde, ex. "DESCUBRA COMO
  ELA VOTOU"). Selo da capa todo branco, só o logo no meio, sem "ANÁLISE": a cor só aparece no veredito, dentro do vídeo.
- Estilo "manchete": letra condensada grossa (Impact), branco + amarelo, frase curta com verbo forte, fotos em bolinha, VS.
- A frase da capa tem que ser algo que o vídeo prova. Tom de impacto sim; acusação sem documento não.
- Conferir o recorte 3:4 da grade. 1 s de capa no começo do vídeo + capa embutida + `publicacao/capa.jpg`.
- **Teste em 08/10 (lula-200bi): capa SEM veredito.** Alexandre: "não precisa dizer na capa o que a gente encontrou,
  porque desperta a curiosidade". Formato Janja (foto grande, só o Lula, sem VS), a acusação literal e "VERDADE OU
  NÃO?" em texto (carimbo com "É VERDADE?" parecia veredito). Comparar em 24 h com Míriam e Pimenta (capas com placar).
- **Foto horizontal (TV, YouTube) entra inteira** numa faixa no alto, com a tarja do programa à vista (ela mostra quem
  fala), e o título embaixo (15/10/2026, "aprovo o plano capa-quadro-inteiro"; no #119 a foto 640x360 esticada e cortada
  no centro deixou o rosto na borda). Foto vertical continua em tela cheia. Feito sozinho pela capa estilo documentário.

### Voz e áudio
- Voz do Alexandre (Gemini TTS), frase a frase com conferência pelo Whisper; ritmo ~6,6 sílabas/s; final em -14 LUFS.
- Armadilha: a voz troca "deles" por "dele" (muda o sentido); reescrever ("dos dois") em vez de insistir.

### Publicar
- `publicar-instagram.py` com `--colaborador alexandremota.digital`, capa e `--facebook` (desde 08/10: mesmo reel na página do
  Facebook, até 90 s); token da Página (não expira; acesso a dados até
  05/01/2027).
- Melhor horário: não medido ainda. O da Janja saiu às 10h35.
- Sem impulsionar até 25/10 (Lei 9.504, art. 57-C).

### Depois de publicar
- Divulgar: canal NewsBR360 no WhatsApp, grupos abertos (Todeschini, MultiplicaCamozzato, empresários 4º Distrito),
  Direct para parceiros (lista em PARCERIAS.md), no máximo ~10 por dia.
- Comentários: responder poucos e bem (perguntas e críticas com argumento), como pessoa. **28 respostas em 4 h
  coincidiram com restrição na conta**: no máximo 5 por lote, espaçados, nunca de madrugada, nunca ofensa.
- Medir 24 h depois e anotar aqui na tabela.

## 4. Lei e limites que já apareceram
- Enquete na campanha é vedada (Lei 9.504, art. 33, § 5º): nada de "comenta 22 ou 13".
- Pesquisa precisa de registro no TSE: projeção nossa diz "projeção com votos oficiais, não é pesquisa".
- "Fake news é crime?": quem decide é a Justiça Eleitoral; nunca afirmar que alguém cometeu crime.

## 5. Próximos testes (para a receita deixar de ser hipótese)
1. Repetir o formato Janja com outra fala (ex.: Janones) e ver se 250 mil foi o formato ou a sorte.
2. Mesmo assunto com e sem colaborador grande.
3. Horário: um de manhã, um à noite.
4. Pedir `instagram_manage_insights` na próxima renovação do token para medir visualização e retenção pela API.
