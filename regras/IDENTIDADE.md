# Identidade visual da @newsbr360 (estúdio v2)

16/10/2026, Alexandre: "faltou levar em consideração as diretrizes de design que temos hoje [...] não quero mudar a
dinâmica que o agente de design criou, mas tem nossos logos e cores que penso que devemos continuar usando."
Juntado do que a v1 já usava (ferramentas/newsbr360.py, RECEITA.md "Tela" e "Capa", decisão marca-e-convite de 16/10).
O animador é livre na dinâmica e nas peças novas; a IDENTIDADE abaixo vale sempre.

## Cores (as da v1, exatas)
| Nome | Cor | Uso |
|---|---|---|
| Fundo escuro | #0a1748 | fundo, caixas escuras |
| Fundo claro | #1c3fae | centro do gradiente do fundo |
| Branco | #F4F6FF | texto principal |
| Amarelo | #ffc933 | destaque, palavra-chave, grifo de marca-texto |
| Azul claro | #9cbcff | rótulo, texto secundário, crédito |
| Vermelho | #ff4d5e (carimbo: #ff3b4a) | ERRADO, FALSO, SEM PROVA, alerta |
| Verde | #3ddc84 | VERDADE, CONFIRMADO |
| Laranja | #ff9f43 | EXAGERO, MEIA-VERDADE |
| Roxo | #b9a6ff | OPINIÃO, PREVISÃO |
Nada de cor fora desta tabela, a não ser a das fotos e prints.

## Fundo (o tocador já desenha; não cubra com fundo de outra cor)
Gradiente radial do #1c3fae (centro) ao #0a1748, com faixas diagonais brancas a 4,5% andando devagar. Cena pode pôr
caixa ou cartão por cima, mas o fundo da página continua sendo esse.

## Letras
Títulos: Impact (classe `im`), MAIÚSCULAS, branco com a palavra-chave em amarelo. Texto e rótulos: Montserrat 700-900.

## Logos (arquivos em /logos/, use com esse caminho)
- `/logos/newsbr360.png`: a bolinha da página. Vai no MIOLO do selo VERDADE/FALSO e onde a página assina.
- `/logos/instituto-br360.png`: o logo do Instituto BR360 (fundo transparente). Vai no fecho, no convite para ser membro
  e onde houver chamada do Instituto.

## Peças com cara de @newsbr360 (estão desenhadas em regras/exemplo-animacao-v1.html; copie o desenho)
- **Verdadômetro** (o veredito, desde 16/10/2026, "aprovo o plano v2-verdadometro"; substitui o carimbo de cartório):
  disco azul escuro com aro na cor do veredito; o símbolo do Instituto (24 bolinhas) vira medidor, acende até o nível e
  um ponteiro para ali; faixa com a palavra atravessando o círculo; embaixo INSTITUTO br360 nas cores do logo (b verde
  #009c3b, r amarelo #ffdf00, 360 branco). Peça pronta: `T.selo(...)` (ANIMADOR.md). PNGs em regras/pecas/verdadometro/.
- **Selo da capa** (desde 17/10/2026): o Verdadômetro sem ponteiro, com o formato (`/logos/selo-capa-checagem.png` ou
  `/logos/selo-capa-analise.png`). O selo VERDADE/FALSO abaixo saiu de uso.
- **Selo VERDADE/FALSO** (antigo, fora de uso): disco com metade de cima verde (VERDADE) e de baixo vermelha (FALSO), anel branco, e o logo
  `/logos/newsbr360.png` no miolo; a metade do veredito acende.
- **Print com crédito**: borda branca arredondada, crédito em azul claro embaixo ("Fonte: ... · data"), grifo amarelo
  de marca-texto no trecho citado, aproximação lenta de 4% (tela nunca parada).
- **Foto de pessoa em bolinha** com aro e nome numa pílula; disputa com "VS".
- **Assinatura** (o último momento de todo vídeo, desde 16/10/2026, "aprovo o plano v2-assinatura"): tela limpa com o logo
  do Instituto se montando (cadeiras vazias acendem em leque, INSTITUTO br360 bate como carimbo, FATO, FONTE / E PONTO.
  palavra por palavra com o ponto amarelo, @newsbr360). Peça pronta `T.assinatura()`; estudo aprovado em
  regras/pecas/assinatura/estudo.html. Substitui o fecho desenhado à mão abaixo.
- **Fecho** (antigo, só como referência): "FATO, FONTE / E PONTO." (branco / amarelo, 100 px) com a lista de fontes e @newsbr360, e o logo do
  Instituto BR360 em cima.
- **O fim do vídeo, como foi ao ar no #126** (abra os exemplos com Read): `regras/exemplos/fim-1-compartilhe.jpg`
  (COMPARTILHE branco / COM QUEM PRECISA VER amarelo, tela limpa), `fim-2-membro.jpg` (logo do Instituto, SEJA MEMBRO,
  AJUDE O NOSSO MOVIMENTO em amarelo, pílula "link na bio") e `fim-3-fato-fonte.jpg` (logo do Instituto, FATO, FONTE /
  E PONTO., "Fontes" e a lista das fontes, @newsbr360). Uma tela de cada vez, letra grande, nada disputando.
- **Convite**: "COMPARTILHE / COM QUEM PRECISA VER" e, se o roteiro pedir, "SEJA MEMBRO / AJUDE O NOSSO MOVIMENTO /
  link na bio" com o logo do Instituto.
