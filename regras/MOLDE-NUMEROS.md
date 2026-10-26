# Molde "números" (24/10/2026)

Ele liga dizendo "usa o molde números" (ou "formato números", "micro doc em números") e desliga com "volta ao molde
normal". Nasceu no #368 (Petrobras), montado à mão. Pedido: "pode fazer o molde números -- podemos usar nossas animacoes e
tudo mais sobre as fotos de fundo. e quando tiver video usamos videos. acho que é um bom formato mesmo para os mini doc".
Referências que ele mandou: reels DePqpN0gX9G e DeRgAHbAJ9e (Brasil Paralelo): usamos o jeito, não a identidade (as
cores, as fontes e o logo são os nossos). Vale POR CIMA das outras regras, só neste vídeo. O que NÃO muda: a voz, a
checagem (todo número na CHECAGEM.md com fonte), a legenda palavra a palavra.

## O recado manda
Todo vídeo tem um recado: o **Ângulo** do roteiro (INTENCAO.md), uma frase. O molde é o vocabulário; a história é do
roteiro. Cada capítulo tem de servir ao recado, e a conclusão mostra o recado NA TELA (no #368: "Tirar dos políticos a
escolha de quem manda"). Quem só assistir sem som tem de sair com o recado.

## Roteiro (roteirista e agente do chat)
1. A história em **capítulos** (4 a 7), quase sempre em linha do tempo, com **uma virada** ("Mas..."). De 45 a 65 s.
2. **Cada capítulo tem um número** que a tela mostra grande (valor, ano, placar, porcentagem), com a fonte na CHECAGEM.
   A fala não precisa dizer o número inteiro: a tela mostra.
3. Opinião só na conclusão, marcada ANÁLISE. Estimativa diz que é estimativa (selo PREVISÃO).
4. Na coluna Tela, diga a foto de cada capítulo (quem ou o quê, em que época): é o que o estúdio vai buscar.

## Animação (animador): a peça `T.numeros` (web/pecas/numeros.js) é de ENCAIXE
O pedido traz a cena inteira do #368 (`regras/exemplos/numeros-368.html`) e a peça. As casas são fixas; não calcule
posição à mão:
- **Fundo:** `N.fundo` uma foto ou trecho de vídeo por capítulo, tingido e escurecido embaixo, aproximando devagar, com
  `credito`. **Vídeo quando houver** (`take: {src, corte}`, o trecho que fala daquilo), foto quando não. **Uma foto
  diferente a cada capítulo; gente antes de prédio.** Fundo `tom: 'vermelho'` só da virada até o fim do escândalo;
  `'cinza'` na conclusão e no convite.
- **Topo (y 360):** `N.titulo` com `sobre` (o lugar/data em caixa alta pequena) e a palavra-chave em `<b>` (tarja amarela).
- **Centro (y 820-900):** `N.numero` (conta do zero; `conta: false` em ano) com `rotulo` e `fonte`; ou `N.barra` (placar,
  comparação), `N.barras` (antes e depois), ou uma peça nossa (selo, plenário, documento, caminho desenhado).
- **Embaixo (y 1190):** `N.regua` com os capítulos, do bloco 2 até o convite.
- **Troca de capítulo:** `N.troca(t)` (a faixa de luz, com whoosh). Na virada: `N.troca` + `T.som('impacto-doc', t)` e o
  fundo vermelho.
- **Convite:** `N.comenta` com a pergunta curta do vídeo (no #368, "SIM OU NÃO") e, no "segue", o número que falta para
  a meta da página (está na memória).

**Ritmo (medido pelo estúdio):**
- **Número grande já no 0 s.** O primeiro quadro é o que faz parar: título e número do bloco 1 entram juntos no 0 s.
- **Algo muda na tela pelo menos a cada 2 s** (um número entra, a tarja, a barra cresce, o selo). A aproximação lenta do
  fundo não conta. O estúdio mede a diferença entre os quadros e aponta o segundo parado.
- **Nunca centro vazio:** o título e o número do capítulo entram no começo do bloco (não espere a palavra).
- Selos ficam ao menos 2,2 s (o selo leva 1,2 s para assentar).

## Fotos e trilha: o estúdio prepara antes
As fotos (licença livre, crédito na tela) e a trilha em partes vêm prontas no pedido; você não busca nem roda nada. O
que não tiver foto usa outra do mesmo capítulo ou um fundo liso (`src` de outra foto com `tom: 'cinza'`). Pessoa real
só no contexto dela.

## Capa
O número mais forte do vídeo, grande, sobre a foto do protagonista tingida, com a pergunta em 2 linhas e a tarja
amarela na palavra-chave; o logo.

## Legenda do post
A de sempre (regras/LEGENDA.md), formato Análise: a pergunta que o vídeo responde; até 5 📌 com os números do vídeo e a
fonte; "Fontes:"; o convite; hashtags com #analise e #newsbr360.
