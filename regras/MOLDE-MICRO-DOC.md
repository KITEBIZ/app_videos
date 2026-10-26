# Formato "Micro documentário" (24/10/2026)

Ele liga dizendo "faz como micro doc" (ou "micro documentário", "em colagem") e desliga com "volta ao molde normal".
Nasceu no #367 ("Do pau de arara ao Supremo"), montado à mão e aprovado por ele ("ficou bom, publica"; postado em
24/10). Pedido: "são micro documentarios e analise", "tem que permitir ao agente variar as cores e tudo mais. para cada
documentario ser unico. [...] mas tb temos que usar uma biblioteca para fazer rapido". Referências que ele mandou: o
tutorial de colagem da Brainstorm (youtube PC0fhvuR7GU) e o reel De0bSjaxHqP. Vale POR CIMA das outras regras, só neste
vídeo. O que NÃO muda: a voz, a checagem (todo fato na CHECAGEM.md com fonte), a legenda palavra a palavra.

## Roteiro (roteirista e agente do chat)
1. Uma história em **capítulos**, quase sempre em linha do tempo: a origem, a subida, o que deu certo, **a virada**,
   as consequências, onde estamos hoje, a conclusão (análise, selo ANÁLISE) e o convite. De 45 a 65 s.
2. **A virada é um bloco só**, com a frase que muda o rumo ("É inegável que... Mas..."). É onde a música troca.
3. Cada capítulo pede uma **imagem-ideia** (a metáfora): pense nela já no roteiro, na coluna Tela.
4. Opinião fica marcada como ANÁLISE e separada do fato. Número com fonte; estimativa diz que é estimativa.

## Animação (animador): colagem com a biblioteca
O pedido traz a cena inteira do #367 (aprovada por ele) e a peça `web/pecas/colagem.js`: o vídeo é montado com elas,
não desenhado do zero. **As fotos e a trilha o estúdio prepara antes de você começar** (vêm prontas no pedido, com o
crédito e o instante da virada): você não busca nem roda nada, só monta.

**Fixo (é a marca):** o papel de fundo (`T.colagem.papel`) com o logo do Instituto na etiqueta; títulos em Impact, em
CAIXA ALTA, em tiras de papel (`T.colagem.titulo`, tira branca/preta, marca-texto só na palavra-chave `<b>...</b>`);
a etiqueta de lugar/data com o crédito (`T.colagem.rotulo`, `claro: true` em papel escuro); a legenda em tira curta
(automática enquanto há papel na tela); a assinatura no fim (`T.assinatura()`).

**Varia a cada vídeo (é o que faz cada um único):**
- **As cores dos capítulos:** uma faixa rasgada por capítulo (`T.colagem.faixa`, vertical à direita/esquerda ou
  horizontal atrás do assunto), sempre das cores do canal (vermelho #ff4d5e, amarelo #ffc933, azul #9cbcff, azul-marinho
  #0a1748) e do papel (creme #efe6d2). Não repita a ordem de cores do último micro doc.
- **O fundo da virada:** o papel muda de cor no "Mas" (no #367, creme → azul-marinho rasgando por cima, e de volta).
- **A metáfora de cada capítulo:** mapa com rota (`T.colagem.mapa`), fotos recortadas entrando pelos lados
  (`recorte`), cartaz com fita (`cartaz`), recorte de manchete com a fonte (`manchete`, sem nome nem marca de jornal),
  risco vermelho sobre o que foi anulado (`risco`), seta à mão ligando causa e efeito (`seta`), objeto desenhado na cena
  (a balança do #367). Nada de repetir a estrutura de outro vídeo: o exemplo mostra o vocabulário, não o molde.

**Ritmo:** troca de capítulo com `T.colagem.capitulo(t)` (tudo sai empurrado e o novo entra); dentro do capítulo nada
sai, as peças se acumulam, **uma peça a cada palavra-chave** (`T.palavra`). A câmera aproxima devagar o vídeo inteiro
(`.peca-colagem` de 1 a 1,05). Tela parada mais de 1 s é defeito.

**Nossos elementos dentro da colagem:** o plenário do Supremo (`T.plenario`) e os selos entram num painel azul-marinho
rasgado (`T.colagem.painel`). Quando o centro do plenário muda de número, o centro antigo sai (`.pl1m`).

**Fotos:** só com direito de uso (domínio público, CC0, CC BY, CC BY-SA), já baixadas em `material/colagem/`, e o
crédito na tela. Retrato vem recortado (`-sem-fundo.png`, use `recorte`); foto de lugar ou cena vai como `cartaz`.
Pessoa real só no contexto dela: a foto de 2010 com indígenas de Roraima não serve de "retirante de 1952" (no #367 o
caminhão virou desenho). O que não tiver foto vira desenho, cartaz de texto, manchete ou mapa.

**Som (ele aprovou no #367, depois de tirar os que chiavam):** as peças já tocam o seu som: papel rasgando (`papel`
com `rasga`, `painel`), whoosh na troca de capítulo, fita no cartaz, clique suave no marca-texto dos títulos grandes e
na seta, carimbo no risco, máquina de escrever na manchete. Títulos entram calados. O tocador não deixa um efeito a
menos de 0,3 s de outro. **Não use** marca-texto, papel deslizando nem caneta (ele: "eles são ruins"; ficaram em
web/sons/fora/). Na virada, `T.som('impacto-doc', t)`.

**Trilha em partes (ele: "uma musica/estilo na primeira parte e depois outro estilo na parte dois"):** já montada em
`animacao/trilha.mp3` pelo catálogo `web/sons/trilhas/CATALOGO.md` (no #367: arquivo até o "Mas", tensão nos
escândalos, reflexão na conclusão). Troca na virada: ponha ali o impacto e a troca do fundo.

## Capa
Mesma colagem: o protagonista recortado em preto e branco grande, com fita, sobre a paleta do vídeo; a pergunta ou a tese
em 2 ou 3 tiras de Impact com marca-texto na palavra-chave; o logo. Duas opções de famílias de título diferentes.

## Legenda do post
A de sempre (regras/LEGENDA.md), formato Análise: abertura com a pergunta que o vídeo responde; até 5 📌 na ordem dos
capítulos, com número exato e fonte; "Fontes:"; o convite fixo; hashtags com #analise e #newsbr360. A do #367:
"Do pau de arara ao Planalto: como a história de Lula chegou ao Supremo de hoje?"
