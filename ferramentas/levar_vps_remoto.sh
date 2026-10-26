#!/bin/bash
# A parte do ferramentas/levar_vps.sh que roda NA VPS (25/10/2026): bash levar_vps_remoto.sh <registro de antes> <novo>
set -uo pipefail
ANTES=$1; NOVO=$2
NO_AR=/srv/kitebiz/projetos/conteudo/estudio-v2
CANDIDATO=/srv/kitebiz/projetos/conteudo/estudio-v2-candidato
exec 9>/tmp/levar-estudio-v2.lock
flock -n 9 || { echo "PAROU: outra instalação está em andamento"; exit 1; }
cd $NO_AR
set -a; . /etc/kitebiz/newsbr360.env; . ~/.estudio-v2.env; set +a
registro() { echo "{\"quando\": \"$(date -Iseconds)\", \"de\": \"$ANTES\", \"para\": \"$NOVO\", \"resultado\": \"$1\"}" >> $NO_AR/instalacoes.jsonl; }

echo "3/6 · testando o candidato numa cópia (fora do ar)"
git worktree remove --force $CANDIDATO 2>/dev/null; rm -rf $CANDIDATO
git worktree add -q --detach $CANDIDATO vindo-do-mac || { registro "candidato não montou"; echo "PAROU: o candidato não montou"; exit 1; }
ln -s $NO_AR/.venv $CANDIDATO/.venv
( cd $CANDIDATO && timeout 900 .venv/bin/python testes/tudo.py --completo > /tmp/levar-testes.txt 2>&1 )
r=$?
git worktree remove --force $CANDIDATO
if [ $r -ne 0 ]; then
  grep -E "FALHOU|passaram|passou de" /tmp/levar-testes.txt
  registro "reprovou no candidato"; echo "PAROU: o candidato reprovou; nada mudou no ar"; exit 1
fi
echo "   $(tail -1 /tmp/levar-testes.txt)"

echo "4/6 · esperando o estúdio ficar livre (até 20 min)"
for i in $(seq 1 120); do
  ocupado=$(.venv/bin/python - <<'PY'
import sys; sys.path[:0] = [".", "ferramentas"]; sys.argv = ["x"]
import estudio as E, instalar
o = list(instalar.ocupados()) + [f"#{n} com mensagem sem resposta" for n in E.numeros() if E.pendentes(n)]
print("; ".join(map(str, o)))
PY
)
  # a prévia em vídeo não entra: o religar a interrompe e ela é refeita sozinha (esperá-la, num estúdio movimentado, não
  # deixava achar folga: em 25/10 a entrega esperou 20 min e desistiu por causa dela)
  pgrep -f "radar.py" >/dev/null && ocupado="$ocupado; radar rodando"
  ocupado=$(echo "$ocupado" | sed 's/^; //')
  [ -z "$ocupado" ] && break
  [ $((i % 6)) -eq 1 ] && echo "   ocupado: $ocupado"
  sleep 10
done
[ -z "$ocupado" ] || { registro "não ficou livre"; echo "PAROU: não ficou livre em 20 min ($ocupado); nada mudou no ar"; exit 1; }

echo "5/6 · trocando e religando"
inicio=$(date '+%Y-%m-%d %H:%M:%S')
git merge -q --ff-only vindo-do-mac && systemctl --user restart newsbr360-estudio-v2
ok=1
for i in $(seq 1 30); do curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:4400/api/funil | grep -q 200 && break; sleep 1; done
curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:4400/api/funil | grep -q 200 || { echo "   não respondeu"; ok=0; }
sleep 5
n=$(journalctl --user -u newsbr360-estudio-v2 --since "$inicio" --no-pager | grep -c Traceback)
[ "$n" -eq 0 ] || { echo "   $n Traceback ao subir"; ok=0; }
[ "$(git rev-parse --short HEAD)" = "$NOVO" ] || { echo "   o registro no ar não é o $NOVO"; ok=0; }
.venv/bin/python testes/mapa_passos.py > /tmp/levar-mapa.txt 2>&1 || { tail -3 /tmp/levar-mapa.txt; ok=0; }

if [ $ok -eq 1 ]; then
  registro "no ar"; echo "6/6 · NO AR: $NOVO (era $ANTES)"
else
  echo "6/6 · voltando a $ANTES"
  git reset -q --hard $ANTES && systemctl --user restart newsbr360-estudio-v2
  sleep 8
  curl -s -o /dev/null -w "   depois de voltar, responde: %{http_code}\n" http://127.0.0.1:4400/api/funil
  registro "voltou"; echo "PAROU: voltei a $ANTES"; exit 1
fi
