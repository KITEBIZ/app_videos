# Estudo: como o vídeo é montado hoje e como montar mais rápido sem perder qualidade

17/10/2026. Só leitura e medição; nada foi mudado no estúdio. Etiquetas: **medido** (rodei ou li o registro agora),
**anotado** (registro de antes, não reconferido), **acho que** (dedução minha).
Fonte das medições: `videos/<n>/historico.jsonl` e `chat.jsonl` dos vídeos #202, #204, #210 e #211, mais dois testes
de tempo que rodei agora em cópia (fotos da prévia).

---

## 1. Como é hoje

**Do link ao vídeo publicado, em 7 passos:**

1. **Pauta** (`pauta.py`): baixa o vídeo uma vez, transcreve palavra a palavra; ao mesmo tempo os Olhos assistem a
   referência; o roteirista (Opus) escreve ROTEIRO.md, INTENCAO.md e CHECAGEM.md.
2. **Roteiro** (você + agente do chat, Opus): cada mudança passa pela segunda opinião do roteiro, que relê ao lado.
3. **Voz** (`voz.py`): grava só as falas que mudaram, corta os trechos de vídeo dos outros, confere cada corte ouvindo.
4. **Animação** (`animacao.py`, regras em `regras/ANIMADOR.md`), o passo mais longo. Detalhe abaixo.
5. **Capas e legenda do post** (`capa.py`, `legenda_post.py`): correm **ao mesmo tempo** que a primeira animação.
6. **Vídeo final** (`render.py`): tira a animação quadro a quadro (30 por segundo) num navegador e junta o som.
7. **Publicação** (`publicar.py`): manda o arquivo para o servidor e o publicador de lá posta no Instagram e Facebook.

**A animação, passo a passo:**

1. O estúdio prepara os dados: tempos de cada bloco na voz, palavra por palavra, legenda já cortada em pedaços.
2. O **animador** (Opus, com permissão de ler, escrever e tirar fotos da prévia) recebe: as regras do animador
   (10,7 KB), o formato (checagem ou análise), a lista de blocos com o tempo e o que a coluna Tela pede, a lista de
   fotos e vídeos da pasta, INTENCAO, ROTEIRO e as últimas 30 mensagens suas. **medido**
3. Ele escreve **um arquivo só, `animacao/cena.html`**: todo o desenho do vídeo (textos, imagens, takes, carimbos) e
   a linha do tempo de cada entrada. Tamanho medido: #211 25 KB, #204 28 KB, #202 34 KB, #210 37 KB. Na primeira
   animação ele lê como modelo o exemplo da v1 (`regras/exemplo-animacao-v1.html`, **64 KB**) e, no #210, também a cena
   inteira do #204 (28 KB). **medido** nos passos registrados.
4. Peças prontas que ele chama em vez de desenhar: só duas hoje, **Verdadômetro** e **assinatura** (`web/pecas/`).
   Todo o resto (take com crédito, citação, número grande, linha do tempo, placar, manchete com fonte) é desenhado do
   zero em cada vídeo. **medido**
5. O **tocador** (`web/tocador.html`) junta a cena, o fundo, a legenda palavra a palavra, a voz, a trilha e os sons; é
   a prévia que você vê e a mesma página que o vídeo final fotografa.
6. Ele confere o próprio trabalho tirando fotos da prévia e ouvindo a lista de sons (`ver.py`). A régua ele não passa
   mais (decisão animacao-rapida).
7. Depois, o **estúdio confere sozinho**: fotos de cada bloco (3 por bloco), régua do vídeo, lista de sons, e a
   segunda opinião (Opus) assistindo a prévia como os Olhos (2 quadros por segundo nos 15 s iniciais, depois 1 a cada
   3,5 s). Em mudança pequena (até 3 blocos), a segunda opinião olha só o trecho mudado.

---

## 2. Onde vai o tempo (só tempo de máquina; o tempo seu de ler e decidir fica de fora)

| Passo | Medido | Fonte |
|---|---|---|
| Pauta com link até roteiro v1 | 4 min 11 s (#211), 3 min 26 s (#204), 4 min 13 s (#202); 2 de 3 foram antes do download único | histórico |
| dentro dela: baixar | 30 s (#211, vídeo inteiro) contra 1 min 26 s (#204, só o áudio, antes) | histórico |
| dentro dela: transcrever + Olhos | 49 s (#211) | histórico |
| dentro dela: roteirista (Opus) | 2 min 52 s (#211), 1 min 58 s (#204, 1 min 58 s #202) | histórico |
| Pauta de ideia escrita até roteiro | 2 min 53 s (#210) | histórico |
| Mudança no roteiro pelo chat | 7 a 70 s por pedido (16 pedidos no #204) | histórico |
| Voz | 37 s com 7 falas novas (#211); 28 s com 1 (#210); 10 a 15 s sem fala nova | histórico |
| **Primeira animação: animador** | **7 min 10 s (#211), 7 min 02 s (#210)**; 12 min 40 s (#204, antes de animacao-rapida) | voz aprovada até "o agente fez" |
| **Primeira animação: conferência** | **2 min 50 s (#211), 2 min 51 s (#210)** | "o agente fez" até "animação conferida" |
| dentro dela: fotos de 1 instante por bloco | 11,9 s para 8 quadros (o estúdio faz 3 rodadas: ~36 s) | **medido agora** no #211 |
| dentro dela: quadros para a segunda opinião | 42,4 s para 44 quadros | **medido agora** no #211 |
| dentro dela: régua do vídeo inteiro | 24 s (#211) | medido hoje às 08:58 |
| dentro dela: segunda opinião (Opus) | o resto, acho que ~70 s | acho que (2:50 menos o medido) |
| Capas + legenda do post | 2 min 40 s + 32 s (#211), **em paralelo** com o animador: não atrasam | histórico |
| Mudança na animação, inteira (pedido até conferida) | 7 min 29 s, 5 min 09 s, 4 min 19 s (#210); 9 min 14 s (#211) | chat + histórico |
| Mudança pequena com conferência parcial | 3 min 09 s (#211: animador 1 min 36 s + conferência 1 min 33 s) | chat + histórico |
| Vídeo final | 3 min 43 s (#210, 61 s de vídeo), 4 min 23 s (#204); 9 min 32 s (#202, primeiro do dia) | histórico |
| Publicação | 3 min 06 s (#210), 2 min 06 s (#204), 2 min 20 s (#202) | histórico |

**O caminho de máquina de um vídeo sem retrabalho (#210):** pauta 2:53 + voz 0:28 + animação 9:53 + final 3:43 +
publicação 3:06 = **cerca de 20 min**, e a **animação é metade disso**. **medido** (soma dos tempos acima)

**O que pesa de verdade é o retrabalho na animação:** no #210 foram 3 mudanças (17 min de máquina) e duas delas foram
você copiando para o chat o que a régua já tinha medido ("a régua ainda acusa..."). No #211, 13 dos 16 problemas da
régua eram o mesmo: legenda encostando no crédito do take. **medido** no chat e na régua.

---

## 3. Como acelerar sem perder qualidade (ranqueado por ganho contra risco)

Nenhuma proposta tira conferência. Todas se provam com a mesma régua, a mesma segunda opinião e o mesmo vídeo lado a lado.

| # | O que muda | Ganho esperado | Risco para a qualidade | Como provar que não perdeu |
|---|---|---|---|---|
| 1 | **Régua conserta sozinha** (já aprovado, em construção) | tira as idas e vindas de "a régua acusa X": no #210, 2 de 3 mudanças (12 min de máquina + o seu tempo) | nenhum novo: o animador só mexe no que a régua mediu | régua zera ou cai; segunda opinião igual ou melhor |
| 2 | **Biblioteca de peças** para o que se repete: take com crédito, citação grande, número grande, manchete com fonte, linha do tempo, placar (como já são o Verdadômetro e a assinatura) | acho que 2 a 4 min na primeira animação (ele escreve chamadas curtas em vez de 25 a 37 KB de desenho) e **menos problemas de régua**: a peça "take com crédito" posiciona o crédito longe da legenda uma vez para sempre (13 de 16 no #211) | vídeos ficarem parecidos demais; peça mal feita erra em todos | refazer #210 e #211 com as peças: régua igual ou menor, notas da segunda opinião iguais ou melhores, você compara lado a lado |
| 3 | **Modelo pronto em vez de exemplo de 64 KB**: o animador recebe um catálogo curto das peças e um esqueleto de cena, em vez de ler o exemplo da v1 e a cena de outro vídeo | acho que 30 s a 1 min (menos leitura, menos exploração) | perder detalhe de estilo que o exemplo ensina | mesmo teste da linha 2 |
| 4 | **Dar os dados prontos** (tempo de cada palavra, quadros do take): hoje ele gasta passos listando pasta, "inspect narration JSON", "count lines", montando grade de quadros do take | acho que 30 s a 1 min | nenhum | contar passos e tempo do animador antes e depois em 2 vídeos |
| 5 | **Vídeo final em 4 navegadores em paralelo** (cada um fotografa um quarto do vídeo; o Mac tem 16 núcleos) | acho que de 3:43 para 1:30 | um trecho sair fora de sincronia na emenda | comparar quadro a quadro com o render de hoje (mesmos quadros) e a conferência do final (duração, volume, parados) |
| 6 | **Conferência em paralelo**: régua e quadros da segunda opinião ao mesmo tempo; as 3 rodadas de fotos dos blocos num navegador só | acho que 30 a 40 s por animação (régua 24 s corre junto com os quadros de 42 s; 2 aberturas de navegador a menos) | nenhum: mesmas medidas | conferencia.json igual (mesma régua, mesmos quadros) |
| 7 | **Segunda opinião da animação no Sonnet** em vez do Opus | acho que 30 s e metade do uso da assinatura | ver menos; no roteiro e nos Olhos o Sonnet empatou (anotado: #204, 4 de 4 problemas iguais), mas na animação **não testei** | rodar as duas no mesmo vídeo em 3 vídeos; só trocar se acharem os mesmos problemas |
| 8 | **Animador no Sonnet só para mudanças pequenas** (até 3 blocos) | acho que metade do tempo da mudança pequena | errar mais o desenho | só depois da linha 2; testar em 5 pedidos reais com a régua e a segunda opinião |

**O que eu NÃO recomendo:** tirar a segunda opinião, a régua ou as fotos; animador no Sonnet para a primeira
animação; diminuir os quadros que a segunda opinião vê (foi assim que ela passou a achar a tela vazia do começo).

---

## 4. O que eu faria primeiro

1. **Terminar a régua que conserta sozinha** (já aprovada) e medir as rodadas.
2. **A peça "take com crédito"**, a primeira da biblioteca: é a que mais gera problema de régua hoje (13 de 16 no #211)
   e aparece em todo vídeo com fala de político. Provar em #211 e #210 lado a lado.
3. **Vídeo final em paralelo**: ganho grande, fácil de provar (quadro a quadro igual), sem mexer no que o animador faz.

Com 1 a 3, acho que um vídeo sem retrabalho cai de ~20 min de máquina para ~15, e o retrabalho por régua some.

---

## 5. O que eu não sei

- **Quanto do tempo do animador é escrever e quanto é pensar e explorar.** O registro só tem o início e o fim; para
  saber, seria preciso medir os passos dele com hora.
- **Se o Sonnet anima com a mesma qualidade.** Nunca foi testado na animação.
- **Se a biblioteca deixa os vídeos repetitivos.** Só se vê comparando vídeos reais; e pelos números do Instagram.
- **Onde vão os 2 a 3 min da publicação** (envio do arquivo, publicador da VPS, Instagram processando): não medi por dentro.
- **Por que o final do #202 levou 9:32** (o dobro dos outros): não investiguei; pode ter sido a primeira execução do dia.

**Visto de passagem, fora deste estudo:** no #211 o pedido "Conserta o problema que a conferência achou na voz" chegou
**duas vezes** (08:12:28 e 08:12:30) e o agente trabalhou duas vezes (08:13:06 e 08:13:55). **medido** no chat.jsonl.
Pode ser toque duplo no botão "Consertar" novo.
