"""Os números do reel publicado (estúdio v2, 16/10/2026, "aprovo o plano v2-publicado").

  python3 numeros.py <número>        lê agora na API do Instagram e grava publicacao/numeros.json

Só leitura. Roda na VPS, como o metricas.py da v1 (publicador/comentarios.py: acesso() e get(); as mesmas métricas):
acha a mídia pelo link do post no registro do publicador (publicacoes.jsonl) e pede os insights. Retenção = tempo médio
assistido / duração do vídeo final.
"""
import json, subprocess, sys

import estudio as E

VPS = "usuario@SEU_SERVIDOR"
PUBLICADOR = "/srv/kitebiz/projetos/conteudo/estudio-v2/publicador"   # 20/10/2026, era o da v1
METRICAS = ["views", "reach", "likes", "comments", "shares", "saved", "ig_reels_avg_watch_time",
            "reels_skip_rate"]   # 22/10/2026 (fluxo-viral-util): % que pula nos 3 s (Meta, 03/12/2025: "estimada e em desenvolvimento")

REMOTO = r'''
import json, sys, urllib.error
sys.path.insert(0, ".")
import comentarios as c
link = sys.argv[1]; metricas = sys.argv[2].split(",")
reg = [json.loads(l) for l in open("publicacoes.jsonl") if l.strip()]
m = next((r for r in reversed(reg) if r.get("link", "").rstrip("/") == link.rstrip("/")), None)
if not m:
    print(json.dumps({"erro": "o post não está no registro do publicador"})); sys.exit()
t, ig = c.acesso()
r = {"midia": m["midia"]}
for met in metricas:
    try:
        r[met] = c.get(m["midia"] + "/insights", t, metric=met)["data"][0]["values"][0]["value"]
    except (urllib.error.HTTPError, KeyError, IndexError) as ex:
        r[met] = None
print(json.dumps(r))
'''


def _mediana_pagina():
    try:
        return json.loads((E.RAIZ / "radar/pagina.json").read_text()).get("mediana")
    except (OSError, ValueError):
        return None


def ler(num):
    a = E.pasta(num) / "publicacao/numeros.json"
    return json.loads(a.read_text()) if a.exists() else None


def medir(num):
    f = E.ler_ficha(num)
    link = (f.get("publicado") or {}).get("instagram")
    if not link:
        raise RuntimeError("o vídeo não tem link do Instagram")
    cmd = (f"set -a; . /etc/kitebiz/newsbr360.env; set +a; cd {PUBLICADOR} && python3 - {link} {','.join(METRICAS)}")
    r = subprocess.run(E.na_vps(cmd), input=REMOTO, capture_output=True, text=True, timeout=120)
    dados = json.loads(r.stdout.strip().splitlines()[-1]) if r.stdout.strip() else {"erro": (r.stderr or "sem resposta")[-300:]}
    if "erro" in dados:
        raise RuntimeError(dados["erro"])
    fj = E.pasta(num) / "publicacao/final.json"
    dur = json.loads(fj.read_text())["duracao"] if fj.exists() else None
    media = dados.get("ig_reels_avg_watch_time")
    dados.update(quando=E.agora(), link=link, duracao=dur,
                 retencao=round(media / 1000 / dur, 3) if media and dur else None,
                 # fluxo-viral-util: envios a cada 100 visualizações e a mediana da página (radar/pagina.json) para comparar
                 envios_100=round(100 * (dados.get("shares") or 0) / dados["views"], 2) if dados.get("views") else None,
                 mediana=_mediana_pagina())
    E._grava(E.pasta(num) / "publicacao/numeros.json", json.dumps(dados, ensure_ascii=False, indent=1))
    return dados


if __name__ == "__main__":
    print(json.dumps(medir(int(sys.argv[1])), ensure_ascii=False, indent=1))
