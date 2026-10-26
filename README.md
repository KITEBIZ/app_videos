# app_videos: estúdio de vídeos curtos da @newsbr360

Um app que leva um vídeo curto de notícia (Reels) da pauta até a publicação, conversando com o editor pelo celular.
O editor manda um link ou uma ideia; o estúdio baixa o vídeo de referência, transcreve, pesquisa e confere os fatos,
escreve o roteiro, grava a voz, anima, faz a capa e a legenda, e publica no Instagram e no Facebook quando o editor
aprova. Cada etapa espera o ok dele, e tudo pode ser pedido em linguagem natural no chat do vídeo.

Esta pasta é uma cópia do código de 26/10/2026, sem o histórico, sem os vídeos e sem segredos. Endereços de servidor,
telefone e e-mail foram trocados por textos genéricos (`SEU_SERVIDOR`, `5500000000000`, `seu-email@exemplo.com`,
`/caminho/local/`).

## Por onde começar
1. **`docs/CODEBASE_MAP.md`**: o mapa do código (estrutura, fluxo do vídeo, onde mexer). Foi gerado em 25/10; a
   segunda opinião (monitor.py) citada nele saiu em 26/10.
2. **`COMO-USAR.md`**: como o editor usa o app.
3. **`regras/`**: os cadernos de regras que cada agente de IA recebe (roteirista, agente do chat, animador, capa,
   legenda e os formatos). O app tem uma tela para ler e mudar essas regras.
4. **`CLAUDE.md`**: as instruções de trabalho para quem mexe no código (testes e instalação).

## As peças, em uma linha cada
| Arquivo | O que faz |
|---|---|
| `servidor.py` | Servidor HTTP (Python, só biblioteca padrão), um trabalhador por vídeo, vigias |
| `web/index.html` | O app: lista por etapa, tela do vídeo e chat |
| `web/tocador.html` + `web/pecas/` | A prévia e o render da animação (HTML + GSAP) |
| `passos.py` | O mapa das etapas e passos de cada vídeo (o caminho é do programa, não da IA) |
| `maestro.py` | Lê cada mensagem do editor e decide o que fazer (responder, ajustar, mudar a direção…) |
| `pauta.py` | Roteirista: análise, checagem dos fatos e roteiro |
| `agente.py` | Agente do chat do vídeo |
| `caderno.py` | O material que o editor junta (links, fotos, anexos) |
| `animador_novo.py`, `animacao.py` | Animação e as conferências dela |
| `voz.py`, `capa*.py`, `legenda_post.py` | Voz, capas e texto do post |
| `render.py`, `publicar.py`, `publicador/` | Vídeo final e publicação |
| `publicador/analista.py` | Lê os comentários e escreve o que o público está dizendo |
| `radar.py` | Acha pautas em contas monitoradas |
| `ia.py` | Toda chamada de IA (CLI `claude -p`; Opus, Sonnet e Haiku conforme a tarefa) |
| `regras_tela.py` | A tela de regras (ler, propor mudança, gravar, desfazer) |
| `testes/` | Testes sem gasto de IA: `testes/tudo.py` |

## Como roda
- Python 3.12 e as bibliotecas de `requirements-vps.txt` (inclui Playwright/Chromium para o render).
- `python3 servidor.py 4400` sobe o app em `http://127.0.0.1:4400`. Com `V2_PROVA=1`, sobe sem iniciar nenhum
  trabalho de IA (bom para olhar as telas).
- Precisa, para trabalhar de verdade: o CLI `claude` logado, as chaves de voz (Gemini) e de transcrição (Groq) e, para
  publicar, o token da página (arquivo `.env` no `publicador/`, fora desta cópia).
- `python3 testes/tudo.py` roda os testes rápidos; `--completo` roda todos (alguns precisam de vídeos de exemplo, que
  não vêm nesta cópia, e vão falhar ou pular).

Os comentários do código são datados e trazem a frase do editor que motivou cada regra ("ele: ..."): é o jeito mais
rápido de entender por que algo é como é.
