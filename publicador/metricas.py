#!/usr/bin/env python3
"""Métricas da @newsbr360 em 24 h (08/10/2026). Alexandre: "pode fazer" (ANALISE-GERADOR.md, item 6). Para cada reel com
mais de 24 h que ainda não foi medido, grava uma linha em metricas.jsonl (visualizações, alcance, curtidas, comentários,
compartilhamentos, salvos, tempo médio assistido e retenção = tempo médio / duração) e, por dia, as visitas ao perfil e
os seguidores. Refaz METRICAS.md (a tabela que a RECEITA cita). Só lê da API: não publica nem responde nada.

  python3 newsbr360/metricas.py            mede o que falta e refaz a tabela
  python3 newsbr360/metricas.py --tabela   só refaz a tabela
Roda sozinho na VPS todo dia às 10h (cron do usuário alex)."""
import datetime, json, subprocess, sys, urllib.error
from pathlib import Path

AQUI = Path(__file__).resolve().parent         # estudio-v2/publicador (20/10/2026; era newsbr360-estudio/newsbr360)
sys.path.insert(0, str(AQUI))
import comentarios as c

REG = AQUI / "metricas.jsonl"
TAB = AQUI / "METRICAS.md"
BR = datetime.timezone(datetime.timedelta(hours=-3))
METRICAS = ["views", "reach", "likes", "comments", "shares", "saved", "ig_reels_avg_watch_time"]


def lidos():
    return [json.loads(l) for l in REG.read_text().splitlines()] if REG.exists() else []


def duracao(legenda):
    """Duração do MP4 publicado, achado pelo registro do publicador (publicacoes.jsonl) pela legenda."""
    reg = AQUI / "publicacoes.jsonl"
    if not reg.exists():
        return None
    for l in reg.read_text().splitlines():
        r = json.loads(l)
        if r.get("legenda", "")[:80] == (legenda or "")[:80] and r.get("video"):
            v = Path(r["video"])
            v = v if v.is_absolute() else AQUI.parent / v
            for cand in (v, AQUI.parent / Path(*v.parts[-3:])):
                if cand.exists():
                    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration",
                                                          "-of", "csv=p=0", str(cand)]))
    return None


def medir():
    t, ig = c.acesso()
    agora = datetime.datetime.now(BR)
    feitos = {r["midia"] for r in lidos() if r.get("tipo") == "reel"}
    novos = []
    for m in c.get(ig + "/media", t, fields="id,caption,timestamp,permalink,media_product_type", limit=50)["data"]:
        quando = datetime.datetime.strptime(m["timestamp"], "%Y-%m-%dT%H:%M:%S%z").astimezone(BR)
        if m["id"] in feitos or agora - quando < datetime.timedelta(hours=24):
            continue
        r = {"tipo": "reel", "midia": m["id"], "link": m.get("permalink"), "postado": quando.isoformat(timespec="minutes"),
             "medido": agora.isoformat(timespec="minutes"), "horas": round((agora - quando).total_seconds() / 3600, 1),
             "titulo": (m.get("caption") or "").split("\n")[0][:70]}
        for met in METRICAS:
            try:
                r[met] = c.get(m["id"] + "/insights", t, metric=met)["data"][0]["values"][0]["value"]
            except (urllib.error.HTTPError, KeyError, IndexError):
                r[met] = None
        d = duracao(m.get("caption"))
        r["duracao"] = round(d, 1) if d else None
        r["retencao"] = round(r["ig_reels_avg_watch_time"] / 1000 / d, 3) if d and r.get("ig_reels_avg_watch_time") else None
        novos.append(r)
    # conta: ontem (visitas ao perfil e seguidores), uma linha por dia
    ontem = (agora - datetime.timedelta(days=1)).date()
    if not any(r.get("tipo") == "conta" and r["dia"] == ontem.isoformat() for r in lidos()):
        ini = int(datetime.datetime.combine(ontem, datetime.time(0), BR).timestamp())
        fim = ini + 86400
        conta = {"tipo": "conta", "dia": ontem.isoformat(), "medido": agora.isoformat(timespec="minutes"),
                 "seguidores": c.get(ig, t, fields="followers_count")["followers_count"]}
        for met in ("profile_views", "reach"):
            try:
                conta[met] = c.get(ig + "/insights", t, metric=met, period="day", metric_type="total_value",
                                   since=ini, until=fim)["data"][0]["total_value"]["value"]
            except (urllib.error.HTTPError, KeyError, IndexError):
                conta[met] = None
        novos.append(conta)
    with REG.open("a") as f:
        for r in novos:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    print(f"{len(novos)} linhas novas em {REG.name}")


def tabela():
    rs = lidos()
    reels = sorted((r for r in rs if r["tipo"] == "reel"), key=lambda r: r["postado"])
    contas = sorted((r for r in rs if r["tipo"] == "conta"), key=lambda r: r["dia"])
    n = lambda v: "" if v is None else f"{v:,}".replace(",", ".")
    p = lambda v: "" if v is None else f"{v * 100:.0f}%"
    linhas = ["# Métricas da @newsbr360 (gerado por newsbr360/metricas.py; não editar à mão)", "",
              "## Reels (medidos uma vez, depois de 24 h)",
              "| Postado | Vídeo | h | Visualizações | Alcance | Curtidas | Comentários | Compart. | Salvos | Tempo médio | Duração | Retenção |",
              "|---|---|---|---|---|---|---|---|---|---|---|---|"]
    for r in reels:
        tm = r.get("ig_reels_avg_watch_time")
        tm_s = "" if tm is None else f"{tm / 1000:.0f} s"
        du_s = "" if not r.get("duracao") else f"{r['duracao']:.0f} s"
        linhas.append(f"| {r['postado'][:16].replace('T', ' ')} | [{r['titulo'][:40]}]({r['link']}) | {r['horas']:.0f} | {n(r['views'])} | "
                      f"{n(r['reach'])} | {n(r['likes'])} | {n(r['comments'])} | {n(r['shares'])} | {n(r['saved'])} | "
                      f"{tm_s} | {du_s} | {p(r.get('retencao'))} |")
    linhas += ["", "## Conta, por dia", "| Dia | Seguidores (ao medir) | Visitas ao perfil | Alcance |", "|---|---|---|---|"]
    for r in contas:
        linhas.append(f"| {r['dia']} | {n(r['seguidores'])} | {n(r.get('profile_views'))} | {n(r.get('reach'))} |")
    TAB.write_text("\n".join(linhas) + "\n")
    print(f"{TAB.name}: {len(reels)} reels, {len(contas)} dias")


if __name__ == "__main__":
    if "--tabela" not in sys.argv:
        medir()
    tabela()
