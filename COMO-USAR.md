# Estúdio v2 · como usar (para outra sessão)

17/10/2026. O estúdio v2 da @newsbr360 roda SÓ neste Mac (ainda não está na VPS nem no git).

- **Pasta:** `/caminho/local/Projetos/KITEBIZ/conteudo/estudio-v2/` · **tela:** http://127.0.0.1:4400
- **Subir o servidor** (se não estiver no ar): `cd` na pasta e `nohup python3 servidor.py >> servidor.log 2>&1 &`.
  Reiniciar: `lsof -ti tcp:4400 | xargs kill` e subir de novo. Não reinicie com vídeo "animando", "gravando",
  "gerando o vídeo final" ou "publicando" (o trabalho no meio se perde ou, na publicação, para de propósito).
- **Os Olhos** (espectador independente): `conteudo/olhos/` (assistir.py + opiniao.py).

## Para CRIAR um vídeo, use o estúdio, não edite o código
Outra sessão mexendo no código ao mesmo tempo que esta quebra o trabalho das duas. Para fazer um vídeo, use a tela ou
a API, como o Alexandre faria:
1. Pauta: `POST /api/pauta` com `{"id": "<único>", "texto": "<link + o que ele quer>", "tipo": "igual" | "analisar"}`
   (sem link: `"tipo": "ideia"`). Responde o número do vídeo.
2. Conversar com o agente do vídeo: `POST /api/item/<n>/mensagem` com `{"id": "<único>", "texto": "..."}`.
   Ver o estado: `GET /api/item/<n>` (ficha, roteiro, chat, animação, capas, legenda).
3. Aprovar, na ordem: `POST /api/item/<n>/aprovar-roteiro` → voz → `aprovar-voz` → animação, capas e legenda →
   `escolher-capa` (`{"op": 1}`) → `aprovar-video` → vídeo final.
4. **Publicar é só do Alexandre** (botão de dois toques na tela). Nenhuma sessão chama `/publicar`.

## Onde está o resto
- Regras de cada agente: `regras/` (ROTEIRISTA, AGENTE, ANIMADOR, CAPA, LEGENDA, IDENTIDADE, RECEITA).
- Peças prontas: Verdadômetro (`T.selo`), assinatura (`T.assinatura`) em `web/pecas/`.
- Cada vídeo é uma pasta: `videos/<n>/` (ficha.json, chat.jsonl, ROTEIRO.md, narracao/, animacao/, publicacao/).
- Decisões e provas: `../.pronto.md` (de baixo para cima é o mais novo). Achados abertos: `ACHADOS.md`.
