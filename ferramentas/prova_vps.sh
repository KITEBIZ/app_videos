#!/bin/bash
# A prova do estúdio desta cópia local numa CÓPIA da VPS (24/10/2026, "pode fazer tudo isso"; antes de levar ao ar).
# Não mexe no estúdio no ar: o código daqui e os dados de lá (fichas, conversas, radar) numa pasta e porta separadas, em
# modo prova (V2_PROVA=1: religa as fichas pelo mapa e mostra as telas, mas não trabalha sozinho, não chama IA e nunca
# publica). As mídias (vídeo, áudio, imagem) ficam ligadas às de lá, sem cópia; fichas e textos são cópias próprias.
#
#   ferramentas/prova_vps.sh            monta a cópia, sobe, confere e mostra o resultado (a cópia fica no ar para olhar)
#   ferramentas/prova_vps.sh --parar    para a cópia e apaga a pasta
#
# Para abrir a cópia no navegador: ssh -L 4495:127.0.0.1:4495 usuario@SEU_SERVIDOR  e  http://127.0.0.1:4495
set -uo pipefail
VPS=usuario@SEU_SERVIDOR
NO_AR=/srv/kitebiz/projetos/conteudo/estudio-v2
PROVA=/srv/kitebiz/projetos/conteudo/estudio-v2-prova
PORTA=4495         # 4494 é a do testes/travas.py
AQUI=$(cd "$(dirname "$0")/.." && pwd)

if [ "${1:-}" = "--parar" ]; then
  ssh "$VPS" "pkill -f '[s]ervidor.py $PORTA'; rm -rf $PROVA"
  echo "cópia parada e apagada"; exit 0
fi

echo "1/5 · montando a cópia em $PROVA (o código daqui, os dados de lá)"
ssh "$VPS" "pkill -f '[s]ervidor.py $PORTA'; rm -rf $PROVA && mkdir -p $PROVA" || exit 1
(cd "$AQUI" && git ls-files -z | rsync -a --from0 --files-from=- ./ "$VPS:$PROVA/") || exit 1
ssh "$VPS" bash -s <<EOF || exit 1
set -e
cd $PROVA
ln -s $NO_AR/.venv .venv
rsync -a $NO_AR/radar/ radar/
cp -al $NO_AR/videos videos
# fichas, conversas e textos viram cópias próprias (a ligação só fica nas mídias, que a prova não regrava)
find videos -type f \( -name '*.json' -o -name '*.jsonl' -o -name '*.md' -o -name '*.txt' -o -name '*.html' \) \
  -exec sh -c 'cp -p "\$0" "\$0.t" && mv "\$0.t" "\$0"' {} \;
echo "   fichas: \$(ls videos/*/ficha.json | wc -l)"
EOF

echo "2/5 · subindo a cópia na porta $PORTA, em modo prova"
ssh "$VPS" "cd $PROVA && set -a && . /etc/kitebiz/newsbr360.env && . ~/.estudio-v2.env && set +a && \
  export V2_PROVA=1 V2_RADAR=0 V2_PUBLICAR_SIMULA=1 && unset V2_ENTRADA && \
  nohup .venv/bin/python servidor.py $PORTA > prova.log 2>&1 < /dev/null &" || exit 1
sleep 8

echo "3/5 · conferindo o que subiu"
ssh "$VPS" bash -s <<EOF
cd $PROVA
curl -s -o /dev/null -w "   funil: %{http_code} em %{time_total}s\n" http://127.0.0.1:$PORTA/api/funil
curl -s http://127.0.0.1:$PORTA/api/funil | python3 -c "import json,sys; d=json.load(sys.stdin); print('   vídeos:', d['contagem'], '· posts do canal:', len(d.get('canal', {}).get('posts', [])))"
erros=0
for n in \$(ls videos | grep -E '^[0-9]+$' | sort -n | tail -15); do
  c=\$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:$PORTA/api/item/\$n); [ "\$c" = "200" ] || { echo "   #\$n respondeu \$c"; erros=\$((erros+1)); }
done
echo "   itens abertos: os 15 mais novos, \$erros com erro"
echo "   religar: \$(grep -h 'fora do mapa consertado' videos/*/historico.jsonl 2>/dev/null | wc -l) ficha(s) consertada(s) pelo mapa"
echo "   erros no registro da cópia: \$(grep -c Traceback prova.log)"
EOF

echo "4/5 · o mapa de passos nas fichas reais"
ssh "$VPS" "cd $PROVA && .venv/bin/python testes/mapa_passos.py | tail -8"

echo "5/5 · a bateria completa de testes, dentro da cópia"
ssh "$VPS" "cd $PROVA && set -a && . /etc/kitebiz/newsbr360.env && . ~/.estudio-v2.env && set +a && .venv/bin/python testes/tudo.py --completo | tail -4"

echo
echo "A cópia continua no ar para você olhar: ssh -L $PORTA:127.0.0.1:$PORTA $VPS  e  http://127.0.0.1:$PORTA"
echo "Para parar e apagar: ferramentas/prova_vps.sh --parar"
