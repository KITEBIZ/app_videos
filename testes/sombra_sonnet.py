"""Teste sombra Sonnet x Opus (20/10/2026; ele: "se eu tivesse certeza que o sonnet vai fazer o mesmo trabalho do opus eu
trocaria" e "pode deixar o teste rodando nos próximos vídeos").

Cada pedido do chat que o Opus atendeu mudando o roteiro é refeito no Sonnet numa CÓPIA do estúdio, com o roteiro e o
chat como estavam na hora do pedido; o estúdio de verdade não é tocado. O resultado vai para testes/sombra-resultado.jsonl
e a tela /teste.html mostra os casos às cegas (A e B) para ele escolher (testes/sombra-votos.json). Os 10 casos do teste
de 20/10 de manhã entram como os primeiros.

  python3 testes/sombra_sonnet.py            refaz os pedidos novos (o cron chama a cada 10 min; até 3 por vez)
  python3 testes/sombra_sonnet.py --placar   quantos casos, votos e quem ganhou (só aqui; a tela não revela)
"""
import fcntl, hashlib, json, re, shutil, subprocess, sys, time
from datetime import datetime, timedelta
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
RESULTADO = RAIZ / "testes/sombra-resultado.jsonl"
VOTOS = RAIZ / "testes/sombra-votos.json"
COPIAS = Path.home() / "estudio-v2-web/sombra"        # as cópias ficam fora do estúdio (e do backup) e saem no fim
DESDE = datetime(2026, 10, 20, 8, 0)                  # os pedidos de antes já estão no teste da manhã
POR_VEZ = 3
LINHA = re.compile(r"^\|\s*(\d+)\s*\|(.*)\|\s*$")
PY = str(RAIZ / ".venv/bin/python")


def ts(s):
    return datetime.fromisoformat(s[:19])


def blocos(md):
    out = {}
    for l in md.splitlines():
        m = LINHA.match(l.strip())
        if m:
            c = [x.strip() for x in m.group(2).split("|")]
            out[m.group(1)] = {"bloco": c[0] if c else "", "quem": c[1] if len(c) > 1 else "",
                               "fala": c[2] if len(c) > 2 else "", "tela": c[3] if len(c) > 3 else ""}
    return out


def mudou(antes, depois):
    a, d = blocos(antes), blocos(depois)
    return sorted((n for n in set(a) | set(d) if a.get(n) != d.get(n)), key=int)


def lado_a_e_opus(chave):
    """A ou B para o Opus, fixo por caso (o mesmo em toda abertura da tela) e sem padrão que dê para decorar."""
    return int(hashlib.sha256(("sombra:" + chave).encode()).hexdigest(), 16) % 2 == 0


def feitos():
    return {json.loads(l)["chave"] for l in open(RESULTADO)} if RESULTADO.exists() else set()


def pendentes():
    """Pedidos do chat atendidos pelo Opus que mudaram o roteiro, já terminados, e ainda sem caso."""
    ja, out = feitos(), []
    for p in sorted((RAIZ / "videos").glob("[0-9]*")):
        h = p / "historico.jsonl"
        if not h.exists():
            continue
        ev = [json.loads(l) for l in open(h) if l.strip()]
        cur = None
        for e in ev:
            t = e.get("texto") or ""
            if t.startswith("pedido: "):
                cur = {"q": e["quando"], "p": t[8:]}
            elif cur and t.startswith("agente do chat no "):
                cur["m"] = t[18:]
            elif cur and t.startswith("respondido ("):
                k = int(t.split("(")[1].split(" ")[0])
                chave = f"{p.name}@{cur['q'][:19]}"
                if (cur.get("m") == "opus" and k > 0 and ts(cur["q"]) >= DESDE and chave not in ja
                        and datetime.now() - ts(e["quando"]) > timedelta(minutes=2)):
                    out.append((int(p.name), cur["q"][:19], e["quando"][:19], chave))
                cur = None
    return out


def refazer(num, quando, respondido, chave):
    p = RAIZ / "videos" / str(num)
    versoes = sorted((datetime.strptime(v.name[8:23], "%Y%m%d-%H%M%S"), v) for v in (p / "versoes").glob("ROTEIRO-*.md"))
    antes = next(v for t, v in versoes if t >= ts(quando)).read_text()
    depois = next((v for t, v in versoes if t > ts(respondido)), p / "ROTEIRO.md").read_text()
    ev = [json.loads(l) for l in open(p / "historico.jsonl") if l.strip()]
    pedido = next(e["texto"][8:] for e in ev if e["quando"].startswith(quando) and e["texto"].startswith("pedido: "))
    chat = [json.loads(l) for l in open(p / "chat.jsonl") if l.strip()]
    msg = max((m for m in chat if m["quem"] == "ele" and ts(m["quando"]) <= ts(quando) and pedido[:40] in m["texto"]),
              key=lambda m: m["quando"])
    resp_opus = next((m["texto"] for m in chat if m.get("responde") == msg["id"]), "")
    copia = COPIAS / chave.replace("@", "_").replace(":", "")
    shutil.rmtree(copia, ignore_errors=True); (copia / "videos").mkdir(parents=True)
    try:
        subprocess.run(["rsync", "-a", "--exclude", "videos/", "--exclude", ".venv/", "--exclude", "*.log", "--exclude", "publicador/",
                        "--exclude", "testes/sombra-*", "--exclude", "estudio-v2/", f"{RAIZ}/", f"{copia}/"], check=True)
        subprocess.run(["rsync", "-a", "--exclude", "*.mp4", "--exclude", "*.mp3", "--exclude", "*.m4a", "--exclude", "*.webm",
                        "--exclude", "*.wav", f"{p}/", f"{copia}/videos/{num}/"], check=True)
        q = copia / "videos" / str(num)
        (q / "ROTEIRO.md").write_text(antes)
        with open(q / "chat.jsonl", "w") as f:
            for m in chat:
                if ts(m["quando"]) < ts(msg["quando"]) or m["id"] == msg["id"]:
                    f.write(json.dumps(m, ensure_ascii=False) + "\n")
        r = subprocess.run([PY, "-c", f"import json, agente; agente.responder({num}, json.loads({json.dumps(json.dumps(msg))}), modelo='sonnet')"],
                           cwd=copia, capture_output=True, text=True, timeout=1500)
        son = (q / "ROTEIRO.md").read_text()
        resp_son = next((m["texto"] for m in map(json.loads, open(q / "chat.jsonl")) if m.get("responde") == msg["id"]), "")
        g = [json.loads(l) for l in open(q / "gasto.jsonl")] if (q / "gasto.jsonl").exists() else []
        usd = g[-1].get("usd") if g and g[-1].get("modelo") == "sonnet" else None
    finally:
        shutil.rmtree(copia, ignore_errors=True)
    opus_usd = next((x.get("usd") for x in map(json.loads, open(p / "gasto.jsonl"))
                     if x.get("quem") == "agente do chat" and 0 <= (ts(x["quando"]) - ts(quando)).total_seconds() < 900), None)
    return {"chave": chave, "video": num, "quando": quando, "pedido": msg["texto"], "antes": blocos(antes),
            "opus": {"blocos": blocos(depois), "mudou": mudou(antes, depois), "resposta": resp_opus, "usd": opus_usd},
            "sonnet": {"blocos": blocos(son), "mudou": mudou(antes, son), "resposta": resp_son, "usd": usd,
                       "erro": r.stderr[-400:] if r.returncode else ""}}


def para_tela():
    """Os casos às cegas: A e B sem dizer qual é qual, com o voto dele em cada um."""
    votos = json.loads(VOTOS.read_text()) if VOTOS.exists() else {}
    casos = []
    for l in open(RESULTADO) if RESULTADO.exists() else []:
        r = json.loads(l)
        if "falhou" in r or r["sonnet"].get("erro"):
            continue
        va, vb = (r["opus"], r["sonnet"]) if lado_a_e_opus(r["chave"]) else (r["sonnet"], r["opus"])
        ns = sorted(set(va["mudou"]) | set(vb["mudou"]), key=int)
        casos.append({"chave": r["chave"], "video": r["video"], "quando": r["quando"], "pedido": r["pedido"].strip().rstrip("\\").strip(),
                      "respA": va["resposta"], "respB": vb["resposta"], "mudouA": len(va["mudou"]), "mudouB": len(vb["mudou"]),
                      "blocos": [{"n": int(n), "antes": r["antes"].get(n) or {}, "A": va["blocos"].get(n) or {}, "B": vb["blocos"].get(n) or {}}
                                 for n in ns],
                      "voto": (votos.get(r["chave"]) or {}).get("escolha")})
    return casos


def votar(chave, escolha):
    if escolha not in ("A", "B", "igual") or chave not in feitos():
        raise ValueError("voto inválido")
    votos = json.loads(VOTOS.read_text()) if VOTOS.exists() else {}
    votos[chave] = {"escolha": escolha, "quando": datetime.now().isoformat(timespec="seconds")}
    tmp = VOTOS.with_suffix(".tmp"); tmp.write_text(json.dumps(votos, indent=1)); tmp.replace(VOTOS)


def placar():
    votos = json.loads(VOTOS.read_text()) if VOTOS.exists() else {}
    res = [r for r in (json.loads(l) for l in open(RESULTADO)) if "falhou" not in r] if RESULTADO.exists() else []
    conta = {"opus": 0, "sonnet": 0, "igual": 0}
    for r in res:
        v = (votos.get(r["chave"]) or {}).get("escolha")
        if v == "igual":
            conta["igual"] += 1
        elif v in ("A", "B"):
            conta["opus" if (v == "A") == lado_a_e_opus(r["chave"]) else "sonnet"] += 1
    us = lambda m: round(sum((r[m].get("usd") or 0) for r in res), 2)
    print(f"{len(res)} casos, {len(votos)} votados · melhor: Opus {conta['opus']}, Sonnet {conta['sonnet']}, tanto faz {conta['igual']}"
          f" · gasto equivalente: Opus US$ {us('opus')}, Sonnet US$ {us('sonnet')}")


def main():
    if "--placar" in sys.argv:
        return placar()
    with open("/tmp/sombra-sonnet.lock", "w") as trava:
        try:
            fcntl.flock(trava, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return
        for num, quando, respondido, chave in pendentes()[:POR_VEZ]:
            if (RAIZ / "videos" / str(num) / "ficha.json").exists() and \
                    json.loads((RAIZ / "videos" / str(num) / "ficha.json").read_text()).get("passo") == "trabalhando no seu pedido":
                continue                                  # ele está mexendo neste vídeo agora: fica para a próxima rodada
            try:
                r = refazer(num, quando, respondido, chave)
            except Exception as ex:                       # anota para não tentar de novo a cada 10 min
                r = {"chave": chave, "video": num, "quando": quando, "falhou": str(ex)[:300]}
                print(f"{datetime.now():%Y-%m-%d %H:%M} {chave}: falhou ({str(ex)[:200]})")
                with open(RESULTADO, "a") as f:
                    f.write(json.dumps(r, ensure_ascii=False) + "\n")
                continue
            with open(RESULTADO, "a") as f:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
            print(f"{datetime.now():%Y-%m-%d %H:%M} {chave}: ok (Opus {len(r['opus']['mudou'])} bloco(s), Sonnet {len(r['sonnet']['mudou'])})")


if __name__ == "__main__":
    main()
