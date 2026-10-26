# Biblioteca de cenas do estúdio v2: o que se repete nas 7 animações

Análise só lendo (nenhum arquivo do projeto foi alterado). 18/10/2026.
Etiquetas: **medido** (comando/arquivo ao lado) · **acho que** (dedução minha).

## Conclusão em 4 linhas

- **Medido:** 63% das linhas das 7 cenas (1873 de 2965) são padrões que se repetem entre vídeos e ainda são escritos à mão.
  Nos vídeos do formato "Fomos conferir" a fatia é maior: #298 79% (345/435), #300 81% (369/454).
  Comando: `python3 .../scratchpad/biblio/conta.py` (intervalos de linha por padrão; a escolha das fronteiras é minha, o script só
  confere que nenhum intervalo se sobrepõe e soma).
- Das peças prontas, só `T.selo`, `T.take`, `T.locutor`, `T.seguir` e `T.assinatura` existem. Tudo o mais (documento com grifo,
  frase no pé do take, tela ELE DISSE, placar, número grande, linha do tempo, lista ✓/✗, abertura "quem disse + N afirmações")
  é reescrito do zero a cada vídeo.
- As 10 peças da seção (b) cobrem 1395 das 1873 linhas de padrão (medido: soma das categorias que elas absorvem, saída do
  `conta.py`; take_faixa, que já é peça, ficou de fora). Linhas cobertas não são linhas economizadas: cada chamada ainda custa
  2-3 linhas.
- **Sobre a "bolinha":** nas 7 cenas não existe nenhum vídeo recortado em círculo (medido, seção c). As bolinhas publicadas são
  FOTOS paradas. O que os outros vídeos usam para o trecho da pessoa é a FAIXA do `T.take` (largura toda, y 330 a 1130). É isso
  que o #298 trocou por tela cheia.

---

## (a) Tabela dos padrões

Linhas = svg + js daquele padrão naquela cena (medido com `conta.py`). "Usos" contei lendo os arquivos.

| Padrão | O que mostra | Vídeos / blocos | Linhas (total · por uso) | Já é peça? | Varia muito? |
|---|---|---|---|---|---|
| **Documento / print desenhado com grifo** | cartão branco ou azul, cabeçalho com veículo e data, 2-4 linhas de texto, grifo amarelo que cresce na palavra dita, fonte embaixo, aproximação lenta | 202 b1 (Senado, post do Lula) · 204 b3 (BBC, CNN) · 210 b2 (DOU) · 296 b3-b5 (3 cartões) · 298 b3 (leque), b5, b6, b9 · 299 manchetes em papel (4, `<img>`) · 300 b6, b9, b10 | 288 · ~10-27 por uso (21 usos) | não | pouco: o desenho se repete (cabeçalho+linhas+grifo). Muda cor do cabeçalho, nº de linhas, posição |
| **Linha do tempo / duas datas** | trilho, marcos com data e rótulo, barra que enche, "13 DIAS DEPOIS" | 204 b6 · 210 b3 (44h→42h→40h) · 296 b7 · 298 b7 · 299 linha 2019-2024 e linha final 2005-2014-2025 | 205 · ~25-45 por uso (7 usos) | não | médio: 2 ou 3 marcos, com ou sem rosto, barra de período |
| **Frase no pé do take** | sobre o pé do vídeo (y 990-1120): a fala dele em Impact, "AFIRMAÇÃO 1", passos numerados "1 A PRESSÃO" com palavras que acendem, pergunta "NÃO SABIA?" | 204 b1 (pílulas) · 296 b1, b2, b6 · 298 b2, b4 · 300 b2, b3, b7, b8 | 176 · ~10-20 por uso (≈12 usos) | não (a regra só diz a faixa `T.TAKE.titulo`) | pouco: sempre 1-2 linhas, troca no instante da palavra |
| **Pedido / pergunta final (penúltima tela)** | COMPARTILHE / VOCÊ ACREDITA? / MANDA PRO TEU AMIGO / CONTRATAR OU CORTAR? | todos os 7 | 171 · 8 a 72 (7 usos; 210 tem 72) | não | médio: texto sempre grande e centrado; 202 e 210 têm opções/botões |
| **Número grande** | "US$ 750 MI", "15,04%", "R$ 6,2 BI", "25 de 38", 75 x 1, contagem 0→600 | 202 b2-b6 · 204 b5 (15→8) · 210 b2, b4, b7 · 296 b7 · 298 b9 · 299 b3, b5, b7 | 144 · ~6-13 por uso (≈15 usos) | não (`conta` reescrito em 202 e 299) | pouco no número; o entorno varia |
| **Lista ✓ / ✗** | linhas com ícone verde/vermelho que acende quando é dita | 204 b5 · 210 b1, b3, b8 · 296 b8 (3 avisos) · 300 b7 | 118 · ~12-35 por uso (7 usos) | não | pouco |
| **Lado a lado / antes x agora** | dois cartões (ANTES/AGORA, CLASSE MÉDIA/QUEM GANHA, CÂMARA/SENADO, dois SEM PROVA) | 202 b7 · 204 b2 · 210 b4 · 300 b9 | 106 · ~13-36 (4 usos) | não | **muito**: cada um tem miolo diferente |
| **Abertura "quem disse + N afirmações"** | foto do autor (círculo ou retângulo), NOME, faixa amarela "4 AFIRMAÇÕES", depois vira pílula pequena no alto | 298 b1 · 300 b1 | 88 · 27 e 61 | não | pouco (é o formato Fomos conferir) |
| **Take em tela cheia** | vídeo cobrindo 1080x1920, rosto enquadrado em x 480 y 640, pé escurecido, véus que escondem letreiros, 2 planos (aberto/fechado) | 202 b1 (`<video>` à mão) · 298 b2, b4, b8 | 83 · 22 (202) e 61 (298) | **meio**: 298 chama `T.take` e depois mexe por dentro do DOM da peça (`cheia()`, `veu()`) | pouco |
| **Ajudantes de animação** | `entra`, `sai`, `grifo`, `pulsa`, `aproxima`, `fonte`, `conta`, `P()` com valor de reserva, troca de tela por bloco | todos os 7 | 76 · 4 a 23 por vídeo | não | quase nada (mesmas funções copiadas) |
| **Tela do veredito "ELE DISSE"** | pílula vermelha ELE/ELA DISSE, a frase dele em 2 linhas Impact, selo no meio, fonte embaixo | 296 b6 · 298 b3, b5, b9 · 300 b6 | 74 · 8-23 (5 usos) | só o selo (`T.selo`) | pouco: a regra já fixa o layout |
| **Placar** | "4 AFIRMAÇÕES" + uma linha por veredito nas cores do Verdadômetro, entra com a palavra | 298 b10 · 300 b11 | 62 · 23 e 39 | não | quase nada |
| **Galeria de fotos (polaroide, uma a uma)** | moldura branca, data, crédito, girada, entram em sequência | 300 b5, b6, b10 | 52 · 1 vídeo | não (função `polaroide` só no 300) | pouco |
| **Foto em bolinha** | foto recortada em círculo, aro colorido, nome embaixo (ou iniciais se faltar a foto) | 204 b4, b7 · 298 b1, b6 · 299 (presidentes, réus) | 51 · 5-12 (≈10 usos) | não (299 tem `rosto` com reserva de iniciais) | pouco |
| **Take na faixa** | `T.take` padrão (y 330-1130) com zoom/foco | 204 b1 (à mão) · 296 b1, b2, b6 · 299 4 takes · 300 b2-b8 | 43 · 2-3 por uso | **sim** | pouco |
| **Foto de arquivo em tela cheia** | foto com aproximação lenta, vinheta escura, crédito no pé | 299 (5 fotos) | 33 · 1 vídeo | não | pouco |
| **Contador de itens** | AVISO 1/2/3 que acendem, círculos 1-2-3-4 | 296 b3-b5 · 298 b3 | 30 | não | pouco |
| **Pílula de contexto no alto** | "2005 · MENSALÃO", "PRESIDENTE NA ÉPOCA" | 299 · (298/300 usam igual na abertura) | 29 | não | pouco |
| **Cartela de capítulo** | presidente, CAPÍTULO N, ano, nome | 299 | 28 · 1 vídeo | não | pouco (só no formato documentário) |
| **Vinheta UMA PRODUÇÃO INSTITUTO br360** | símbolo das 24 bolinhas acendendo | 299 | 16 · copia o array `PONTOS` à mão | não | nada |

Peças já prontas, uso medido (`grep -o` em cada cena): `T.selo` 202:4 (via ajudante), 204:4, 210:1, 298:4, 300:4 · `T.take` 296:3, 298:5, 299:4 (via ajudante), 300:5 · `T.seguir` só 298 e 300 (2 cada; a regra é de 18/10) · `T.locutor` 296, 298, 299, 300 · `T.assinatura` 7/7.

---

## (b) As 10 peças que valem fazer primeiro (por linhas economizadas)

"Economia" = linhas do padrão menos ~2-3 linhas por chamada (**acho que**; não medi um vídeo refeito com as peças).

| # | Peça (chamada proposta) | O animador ainda decide | Economia estimada |
|---|---|---|---|
| 1 | **`T.fala({ini, fim, corte, src, quem:'ELE'|'ELA', rotulo, credito, rosto:[fx,fy], escala, planos:[{em:'Depois', escala:2.9}], esconde:[{t0,t1,area}], aproxima:1.1})`**: o take em TELA CHEIA (o que o #298 faz com `cheia()`+`veu()`), com 1-2 planos, véu para letreiro queimado e ELA DISSE. Pode ser `T.take({..., cheia:{rosto, escala}})` | onde está o rosto, o corte do vídeo, onde quebra em dois planos, o que esconder | #298: 61 → ~12 linhas (≈50). Em todo vídeo com fala de alguém (4 de 7) |
| 2 | **`T.pe([{t, texto, destaque, rotulo:'AFIRMAÇÃO 1'|num:1, sub, palavras:[{t,texto}]}], {sai})`**: frase no pé do take, troca no instante | o texto e quando troca | ~35 por vídeo com take (176 linhas em 4 vídeos) |
| 3 | **`T.documento({ini, sai, veiculo, data, cor, linhas:[...], grifo:[{linha, t}], fonte, x, y, larg, tema:'claro'|'escuro'|'papel', img})`**: cartão de veículo/nota/post com grifo e aproximação lenta; `img` para o print verdadeiro (299) | o texto, o que grifar e quando | ~40 por vídeo (288 linhas, 21 usos) |
| 4 | **`T.veredito({ini, sai, quem:'ELE', frase:['…','…'], destaque, selo:'VERDADE', fonte})`**: a tela própria do veredito (pílula ELE DISSE + frase + `T.selo` + fonte), o layout que a regra já fixa | a frase, o selo, a fonte | ~10 por uso, até 4 usos por vídeo (74 linhas hoje) |
| 5 | **`T.placar({ini, titulo:'4 AFIRMAÇÕES', linhas:[[1,'VERDADE'],[2,'SEM PROVA']], palavras:['verdade','meia',…], pedido:'MANDA PRA QUEM…'})`** + **`T.contador({n:4, ini, y})`** (1-2-3-4 / AVISO 1-2-3) | só os números e as palavras | ~30 por vídeo Fomos conferir (62+30 linhas) |
| 6 | **`T.abertura({nome, foto, recorte, n:4, ate:3, faixa:true, ate_palavra:[1,'quatro']})`**: "WAGNER MOURA · 4 AFIRMAÇÕES" no quadro 0, vira pílula no alto | a foto e o recorte | ~30-50 (88 linhas em 2 vídeos) |
| 7 | **`T.numero({t, texto:'R$ 6,2 BI', de:0, ate:6.2, casas:1, cor, sub, fonte, x, y, tam})`** | o valor, a cor, o subtítulo | ~15 por vídeo (144 linhas, ≈15 usos) |
| 8 | **`T.linhaTempo({ini, marcos:[{t, data, rotulo, cor, rosto}], barra:{de,ate,t}, destaque:{t, texto:'13 DIAS DEPOIS'}, y})`** | os marcos e o destaque | ~25 por uso (205 linhas, 7 usos) |
| 9 | **`T.lista({ini, y, itens:[{t, ok:true|false|'espera', texto, sub}]})`** (✓ ✗ ⏳ acendendo na palavra) | os itens | ~15 por uso (118 linhas, 7 usos) |
| 10 | **`T.anim`**: `entra/sai/grifo/pulsa/aproxima/conta` + `T.palavra(n,w,k,reserva)` + `T.telas([...])` (troca de tela por bloco sem buraco). E **`T.foto({src, recorte, cx, cy, r, nome, sub, cor})`** (bolinha com reserva de iniciais, como o `rosto` do 299) | nada novo | ~10-20 por vídeo (76 linhas) + ~5 por foto |

Fora do top 10, mas baratos se o formato repetir: `T.galeria` (polaroides do #300, 52 linhas, 1 vídeo), `T.fotoArquivo` + `T.capitulo` + `T.vinheta` (só o #299, documentário; a vinheta copia o array das 24 bolinhas, que já existe em `take.js`), `T.pedido({linhas, destaque, botao})` (171 linhas, mas varia; ver d).

**O que isso dá num vídeo Fomos conferir** (acho que): #298 e #300 têm 345 e 369 linhas de padrão; com as peças 1-10, cada cena cairia de ~440 para ~150-200 linhas, e o que sobra é o que é do vídeo (texto, tempos, a cena nova). Se o tempo do animador acompanha o tamanho do que ele escreve, os 14 min caem para algo como 6-8 min; não medi isso.

Achados no caminho (nada consertado; análise só lendo):
- **b.1** `videos/298/animacao/cena.html:268`: a função `take` é definida e nunca chamada (os 5 takes chamam `T.take` direto). Código morto (medido: `grep -o "T.take(" ` = 6 = 5 chamadas + a definição).
- **b.2** `cheia()` no #298 (linhas 248-257) reescreve o estilo de dentro da peça `take.js` (`box.style.top`, `.take-pe`). Se o `take.js` mudar o DOM, o #298 quebra em silêncio. Motivo para a peça 1 existir.
- **b.3** `videos/300/animacao/cena.html:277`: `elaDisse` troca o texto "ELE DISSE" no DOM; falta `quem:'ELA'` no `T.take`.
- **b.4** `videos/296/animacao/cena.html:317-321`: conserto local "o quadro 0 do vídeo da pauta é o rosto do autor": cada take parado no corte antes de aparecer. Isso é do `take.js`, não da cena; os outros vídeos não têm o conserto (acho que podem mostrar o quadro errado no primeiro instante; não conferi nos quadros).
- **b.5** O array das 24 bolinhas do símbolo está copiado em 3 peças (`take.js`, `verdadometro.js`, `assinatura.js`), em `web/index.html` e na cena do #299 (medido: `grep -l "141,287,'#ff4d5e'"`). Uma peça `T.simbolo(x,y,h)` resolveria.
- **b.6** #202 e #204 escrevem `<video>` à mão (feitos antes do `T.take` de 17/10). Não precisa mexer: já publicados.

---

## (c) Tela cheia (#298) x faixa e bolinha

**A premissa "bolinha" não bate com o que está nos arquivos** (medido):
- `grep -c "<video" videos/*/animacao/cena.html`: só 202 (2 vídeos, tela cheia) e 204 (1, faixa y 270-1250). Os outros usam `T.take`.
- Nenhuma cena recorta vídeo em círculo; os `clip-path` circulares (204, 298, 299) são de FOTO parada.
- No chat do #298 (`videos/298/chat.jsonl`, 18/10 10:21) o animador diz que pôs o Wagner "em tela larga" (a faixa do `T.take`). Às 10:33 ele pediu: "quando o vagner aparece ele deveria aparecer em tela cheia". Então **o que ele chama de bolinha deve ser a FAIXA do `T.take`** (acho que), ou a foto em bolinha da abertura.

Quadros (360 px de largura) em `/private/tmp/claude-501/-Users-MAC-Projetos-KITEBIZ-conteudo/1bc902f5-64b2-4ef8-9a66-63cfaf0fa9a4/scratchpad/biblio/`:

| Arquivo | O que é |
|---|---|
| `q-298-12s.jpg`, `q-298-25s.jpg`, `q-298-53s.jpg` | #298 **tela cheia**: rosto ocupa o terço de cima, imagem clara até y ~1000 e escurecendo até ~1660, passo numerado e crédito por cima do pé |
| `q-296-02s.jpg`, `q-296-10s.jpg` | #296 **faixa** do `T.take` (Lula no JN): vídeo só entre y 330 e 1130, fundo azul em cima e embaixo |
| `q-299-14s.jpg` | #299 **faixa** com vídeo de arquivo (Jefferson) |
| `q-204-04s.jpg` | #204 faixa à mão (y 270-1250) com "VOCÊ É MEI?" por cima |
| `q-202-01s.jpg` | #202 tela cheia à mão (Lula comemorando) |
| `q-204-26s.jpg`, `q-299-26s.jpg`, `q-298-04s.jpg` | **foto em bolinha** parada: Lula 2022 (r 140), réus do Mensalão (r 95), Wagner na abertura (r 220) |
| `comparacao.jpg` | lado a lado: 298 abertura, 298 tela cheia, 296 faixa, 299 faixa, 204 bolinha, 299 bolinhas |
| `folha-<n>.jpg` | um quadro a cada 2 s de cada vídeo publicado (202, 204, 210, 296, 298, 299) |

Geometria (medido no código):
- Faixa (`web/pecas/take.js`, `TAKE.video = [330, 1130]`): 1080 x 800 = 42% da altura; sombra nos últimos 300 px.
- Tela cheia (#298 `cheia()`): caixa 1080 x 1920; pé com gradiente de y 1000 (transparente) a 1414 (80%) e 1662 (opaco). Vídeo limpo em 1000 px (52%), visível até ~1400. Rosto em x 480, y 640, vídeo 1920x1080 ampliado 2,1 a 2,9 vezes.
- Bolinha: diâmetro 190 a 440 px, foto parada.

Olhando os quadros: na tela cheia o rosto fica maior e o vídeo vira o fundo da cena, sem a moldura azul em cima. Na faixa, o vídeo parece um cartão e sobra azul vazio (y 240-330 e 1130-1290). Na bolinha não há movimento nenhum.

Custo da tela cheia (medido no #298): precisou de véus para esconder letreiros queimados do Revelando (`veu()` 3 vezes), o crédito e o rótulo ficam sobre a imagem, e o vídeo fonte tem que aguentar 2-3x de ampliação. Vídeo 540x960 da pauta (296, 300) em tela cheia fica "um pouco mole" (a regra já aceita isso).

---

## (d) O que NÃO deve virar peça (varia demais)

- **Cenas-metáfora desenhadas**: impressora de dinheiro com proibido (202 b8), celular tocando/bloqueado (210 b6, 35 linhas), banco rachando (210 b7), 60 bonecos que ficam vermelhos (202 b6), hemiciclo 75 x 1 (202 b2), lojas com porta de aço (202 b5), picanha e caneco (204 b7). São o que dá cara a cada vídeo; cada uma apareceu 1 vez.
- **Ícones** (`<symbol>`: pessoa, loja, urna, pix, risada, picanha, fone, ampulheta, check). No máximo um arquivo de ícones para copiar (✓ ✗ ⏳ entram na peça `T.lista`), não uma peça animada.
- **Lado a lado / antes x agora** (4 usos, 4 formas diferentes): melhor o animador montar com `T.documento` e `T.anim`.
- **Frase grande que bate palavra a palavra** fora do take (202 b1 "QUEM PAGA?", b8, 204 b7): o tamanho, a quebra e o objeto junto mudam sempre; `T.anim` cobre o movimento.
- **Pedido final**: o texto grande e sozinho é padrão, mas 202 (contratar ou cortar + balão) e 210 (link, WhatsApp, opções; 72 linhas) mostram que muda por vídeo. Uma `T.pedido` simples serve para metade; o resto continua à mão.
- **Barra de votos que não chega** (210 b7) e **contagem regressiva** (204 b5): cada uma 1 vez.
- **A "ponte" do #300** (cópia da pergunta por cima do começo da assinatura, linhas 444-452): não é peça; acho que é uma opção que falta na `T.assinatura` (`T.assinatura({segura:'.b11-perg'})`).
