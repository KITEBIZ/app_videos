#!/bin/bash
# 14/10/2026 ("faz a atualização semanal do programa de download", A-youtube.2): o YouTube muda e o yt-dlp antigo passa a
# levar 403. Toda segunda (cron) baixa a versão nova numa cópia, testa lendo um vídeo conhecido pela saída da IPRoyal e
# só troca se o teste passar; a anterior fica em yt-dlp.anterior. Falhou: fica a atual e a linha ERRO vai para o log.
set -u
B="$HOME/.local/bin"; ATUAL="$B/yt-dlp"; NOVO="$B/yt-dlp.teste"   # 20/10/2026: o v2 usa o yt-dlp (a v1 atualizava o yt-dlp.novo)
RAIZ="$(cd "$(dirname "$0")/.." && pwd)"
agora() { date +%Y-%m-%dT%H:%M:%S; }
curl -sfL -o "$NOVO" https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp || { echo "$(agora) ERRO: não baixou a versão nova"; exit 1; }
chmod 755 "$NOVO"
v_atual=$("$ATUAL" --version 2>/dev/null || echo nenhuma); v_nova=$("$NOVO" --version 2>/dev/null || echo quebrada)
if [ "$v_atual" = "$v_nova" ]; then rm -f "$NOVO"; echo "$(agora) já na última ($v_atual)"; exit 0; fi
# teste: o título do vídeo do UOL (14/10, calibrado: "Lula diz que 'enquanto viver...'")
IFS=: read -r H P U S < "$HOME/.config/kitebiz/youtube-proxy"
PX="http://$U:${S%%_*}_country-br_session-$(head -c4 /dev/urandom | od -An -tx1 | tr -d ' \n')_lifetime-30m@$H:$P"
t=$(timeout 120 "$NOVO" --no-warnings --proxy "$PX" --extractor-args youtube:lang=pt --print "%(title)s" "https://www.youtube.com/watch?v=h11ZHC8sEwQ" 2>&1 | tail -1)
if [[ "$t" == *"enquanto viver"* ]]; then
  cp -p "$ATUAL" "$B/yt-dlp.anterior"; mv "$NOVO" "$ATUAL"
  echo "$(agora) atualizado $v_atual -> $v_nova (teste ok: $t)"
else
  rm -f "$NOVO"; echo "$(agora) ERRO: a versão $v_nova não passou no teste; fica a $v_atual ($t)"; exit 1
fi
