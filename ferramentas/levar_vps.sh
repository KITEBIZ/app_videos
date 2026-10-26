#!/bin/bash
# Leva o que está registrado na cópia local para o estúdio no ar (25/10/2026, revisão de confiabilidade; ele: "pode
# fazer"). Antes eram passos à mão (push, merge, religar, testes, reset) e o código ia ao ar ANTES de ser testado na
# VPS: hoje um código reprovado ficou 2,5 min no ar, e duas vezes o disco e a memória ficaram com versões diferentes.
#
#   ferramentas/levar_vps.sh            testa numa cópia, espera o estúdio ficar livre, troca e confere; volta se falhar
#   ferramentas/levar_vps.sh --ver      só mostra o que mudaria (nada é enviado)
#
# Ordem: (1) aqui: árvore limpa e o último registro com "Testes: completos"; (2) na VPS: uma instalação por vez, disco,
# árvore limpa, serviço no ar; (3) envia e confere que chegou igual; (4) testa o candidato numa pasta à parte (git
# worktree), sem tocar no ar; (5) espera nenhum vídeo trabalhando, nenhuma mensagem sem resposta, nenhuma prévia sendo
# gravada e nenhum radar rodando (até 20 min); (6) troca o código e religa no mesmo passo e confere (responde, sem
# Traceback, o registro certo, o mapa de passos nas fichas reais); (7) falhou: volta ao registro de antes e religa.
# Cada vez fica uma linha em instalacoes.jsonl na VPS.
set -uo pipefail
VPS=usuario@SEU_SERVIDOR
NO_AR=/srv/kitebiz/projetos/conteudo/estudio-v2
CANDIDATO=/srv/kitebiz/projetos/conteudo/estudio-v2-candidato
AQUI=$(cd "$(dirname "$0")/.." && pwd)
SO_VER=${1:-}

falha() { echo "PAROU: $*"; exit 1; }

cd "$AQUI" || exit 1
[ -z "$(git status --porcelain)" ] || falha "a cópia local tem mudanças sem registro (rode o ferramentas/instalar.py antes)"
git log -1 --format=%B | grep -q "Testes: completos" || falha "o último registro não passou pela bateria completa (instalar.py --completo)"
NOVO=$(git rev-parse --short HEAD)
ANTES=$(ssh "$VPS" "git -C $NO_AR rev-parse --short HEAD") || falha "a VPS não respondeu"
[ "$ANTES" = "$NOVO" ] && { echo "nada a levar: a VPS já está em $NOVO"; exit 0; }
git merge-base --is-ancestor "$ANTES" HEAD || falha "o registro do ar ($ANTES) não é anterior ao daqui ($NOVO): alguém registrou na VPS"
echo "== de $ANTES para $NOVO:"; git log --format='   %h %s' "$ANTES..HEAD"
[ "$SO_VER" = "--ver" ] && exit 0

echo "1/6 · conferindo a VPS"
ssh "$VPS" bash -s <<EOF || falha "a VPS não está pronta para receber"
set -e
livre=\$(df --output=avail -BG / | tail -1 | tr -dc 0-9)
[ "\$livre" -ge 10 ] || { echo "disco com \${livre} GB livres (mínimo 10)"; exit 1; }
[ -z "\$(git -C $NO_AR status --porcelain --untracked-files=no)" ] || { echo "a VPS tem mudanças sem registro"; exit 1; }
systemctl --user is-active --quiet newsbr360-estudio-v2 || { echo "o serviço não está no ar"; exit 1; }
EOF

echo "2/6 · enviando"
git push -q origin "HEAD:vindo-do-mac" || falha "o envio falhou"
CHEGOU=$(ssh "$VPS" "git -C $NO_AR rev-parse --short vindo-do-mac")
[ "$CHEGOU" = "$NOVO" ] || falha "chegou $CHEGOU, esperava $NOVO"

# daqui em diante, na VPS (ferramentas/levar_vps_remoto.sh, copiado e rodado lá; uma instalação por vez)
scp -q "$AQUI/ferramentas/levar_vps_remoto.sh" "$VPS:/tmp/levar_vps_remoto.sh" || falha "não copiei o roteiro da VPS"
ssh "$VPS" bash /tmp/levar_vps_remoto.sh "$ANTES" "$NOVO"
