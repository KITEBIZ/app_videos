0
# Estúdio v2 (@newsbr360)

Estúdio que faz reels checados da pauta à publicação. **Leia `docs/CODEBASE_MAP.md` antes de mexer no código**: estrutura, fluxo do vídeo, onde mexer e cuidados. O estado do dia está no `PASSAGEM-<data>.md` mais novo.

## Visão do código
Servidor Python stdlib (`servidor.py`, porta 4400) com um trabalhador por vídeo; estado só em arquivos de `videos/<n>/`;
IA pelo CLI `claude -p` (Opus no roteiro, animação e legenda; Sonnet no maestro, capa e Olhos; Haiku no radar), voz no
Gemini, transcrição na Groq. Prévia e render pelo `web/tocador.html` (GSAP + peças de `web/pecas/`), render com
Playwright + ffmpeg. Esta pasta é a cópia local (`../ligar.sh`, sem radar, WhatsApp nem publicação); a oficial é a VPS.

## Nunca
- Reiniciar o serviço com vídeo em andamento (passo GRAVANDO, ANIMANDO, CAPANDO, LEGENDANDO, RENDERIZANDO ou PUBLICANDO).
- Chamar `/publicar` — publicar é só pelo botão dele.
- Usar outro usuário de SSH além de `alex` (fail2ban bloqueia a casa toda).
- Criar ou mexer em vídeo editando arquivos: use a API (ver `PASSAGEM-<data>.md` e `COMO-USAR.md`).

## Instalar e desfazer (desde 23/10/2026, "aprovo o plano historico-e-testes")
A pasta tem histórico (git, só local; vídeos, segredos e dados ficam de fora). **Toda mudança entra por um comando só**,
nunca copiando arquivo por cima nem reiniciando à mão:

```bash
.venv/bin/python testes/tudo.py [--completo]          # os testes sem gasto de IA (rápido ~3 s; completo ~40 s, numa cópia)
.venv/bin/python ferramentas/instalar.py "<nome-do-plano>" "<a frase dele que autorizou>" [--completo]
.venv/bin/python ferramentas/instalar.py --desfazer "<por quê>"
```

O instalar confere que nenhum vídeo está trabalhando, roda os testes e RECUSA se algum falhar, registra com nome e
autorização, reinicia só se mudou programa do servidor e volta sozinho se o estúdio não subir. Mude os arquivos e
instale na mesma hora (enquanto não instala, o arquivo no disco já é o novo). Teste novo que vale rodar sempre entra em
`testes/tudo.py`. Os testes completos partem do gabarito congelado em `~/estudio-v2-web/gabarito-testes/`.

## Mapa em dia
No começo de uma sessão que vai mexer no código, confira (sem gasto de IA) o que mudou desde o mapa:

```bash
find . -newer docs/CODEBASE_MAP.md -type f \( -name '*.py' -o -name '*.md' -o -name '*.js' -o -name '*.html' \) -not -path './videos/*' -not -path './.venv/*' -not -path './testes/referencias/*' -not -path './testes/tela_igual/*' -not -name 'PASSAGEM-*' -not -path './docs/*' -not -name CLAUDE.md
```

Se entrou ou saiu arquivo, ou mudou o papel de algum módulo, avise e proponha atualizar só a parte afetada do mapa. Edição dentro de um arquivo que já existe não pede atualização.
