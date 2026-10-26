#!/usr/bin/env python3
"""Aviso no WhatsApp do Alexandre quando a sessão do estúdio para esperando decisão dele (08/10/2026, "aprovo o plano").
A notificação do app não chega da VPS (2 de 2: "controle remoto não está ativo"); este manda uma linha para o próprio
número dele pelo WhatsApp da KITEBIZ na VPS 204 (GOWA em 127.0.0.1:8087).

  python3 ../ferramentas/avisar.py "NewsBR360 · prévia do <vídeo> pronta, dá play e aprova: <link>"

Quando usar (ESTUDIO-NA-NUVEM.md, "Avisar"): decisão dele (roteiro, prévia, "pode publicar", pergunta que trava, algo
que só ele resolve), vídeo publicado (com o link do post), pauta analisada e problema de saúde. Sempre com link: sem
link no texto, vai o do painel. Um aviso por acontecimento; andamento ("etapa 3 de 7") não avisa.
O destino é fixo: só o número dele. Não existe opção de mandar para outra pessoa, de propósito."""
import base64, json, os, sys, urllib.request
from pathlib import Path

DESTINO = "5500000000000"          # o próprio Alexandre (MEMORY: WhatsApp só para quem já contatou; aqui, só ele)
GOWA = "http://127.0.0.1:8087"
ENV = Path("/etc/kitebiz/newsbr360.env")


def credencial():
    a = os.environ.get("GOWA_AUTH")
    if not a and ENV.exists():
        for l in ENV.read_text().splitlines():
            if l.startswith("GOWA_AUTH="):
                a = l.split("=", 1)[1].strip()
    if not a:
        sys.exit("sem GOWA_AUTH (variável ou /etc/kitebiz/newsbr360.env)")
    return a


PAINEL = "https://admin.newsbr360.com/"   # 23/10/2026: a tela "Processo e gasto" saiu; o link vai para o estúdio


def avisar(texto, limite=400, linhas=False):
    # 12/10 (radar): o aviso do radar leva 3 links e quebra de linha; os demais seguem numa linha de até 400 letras
    texto = ("\n".join(" ".join(l.split()) for l in texto.splitlines() if l.strip()) if linhas else " ".join(texto.split()))[:limite]
    # 09/10: "toda vez que tiver alguma informação manda o link no meu whatsapp": aviso sem link leva o do painel
    if "https://" not in texto:
        texto = f"{texto[:340]} · Estúdio: {PAINEL}"
    req = urllib.request.Request(f"{GOWA}/send/message", method="POST",
                                 data=json.dumps({"phone": f"{DESTINO}@s.whatsapp.net", "message": texto}).encode(),
                                 headers={"Content-Type": "application/json", "X-Device-Id": "alex",
                                          "Authorization": "Basic " + base64.b64encode(credencial().encode()).decode()})
    with urllib.request.urlopen(req, timeout=20) as r:
        resp = json.loads(r.read())
    print("enviado" if resp.get("code") == "SUCCESS" else f"falhou: {resp}")
    return resp


if __name__ == "__main__":
    # 08/10: "--help" foi parar no WhatsApp dele; argumento que começa com "-" ou curto demais não é aviso
    if len(sys.argv) != 2 or sys.argv[1].strip().startswith("-") or len(sys.argv[1].strip()) < 15:
        sys.exit(__doc__)
    # 25/10/2026 (revisão de confiabilidade): envio que falha sai com erro (antes saía 0 e o saude.py dava como avisado)
    try:
        ok = avisar(sys.argv[1]).get("code") == "SUCCESS"
    except Exception as e:
        print(f"falhou: {e}"); ok = False
    sys.exit(0 if ok else 1)
