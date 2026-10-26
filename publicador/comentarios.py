#!/usr/bin/env python3
"""Leitor de comentários da @newsbr360, semiautomático (07/10/2026). Alexandre: "monta o leitor de comentários agora".
Combinado: o programa lê; o assistente redige cada resposta com a fonte; o Alexandre aprova em lote ("pode responder");
só então sai. Nada é respondido sem aprovação. Resposta 100% automática ficou de fora (perfil político em eleição:
uma resposta errada vira print; respostas iguais em quantidade o Instagram lê como spam).

  python3 comentarios.py ler                 busca comentários novos dos últimos posts -> comentarios/fila.json
  python3 comentarios.py mostrar             lista os pendentes, com a resposta proposta (quando houver)
  python3 comentarios.py propor ID "texto"   grava a resposta proposta de um comentário
  python3 comentarios.py aprovar ID [ID...]  marca como aprovado (só com o "pode responder" dele)
  python3 comentarios.py ignorar ID [ID...]  tira da fila sem responder (ofensa, spam, robô)
  python3 comentarios.py responder           envia SÓ os aprovados, um a cada 20 s, no máximo 10 por vez

Acesso: o mesmo token da Página do publicador (.env.instagram, permissão instagram_manage_comments).
Registro de tudo o que saiu: comentarios/respostas.jsonl."""
import json, sys, time, urllib.parse, urllib.request
from pathlib import Path

AQUI = Path(__file__).resolve().parent
DIR = AQUI / "comentarios"
FILA = DIR / "fila.json"
LOG = DIR / "respostas.jsonl"
API = "https://graph.facebook.com/v23.0/"
POSTS = 10            # quantos posts recentes olhar
MAX_POR_VEZ = 10      # respostas por execução (não parecer robô)
ESPERA = 20           # segundos entre uma resposta e outra


def acesso():
    env = dict(l.strip().split("=", 1) for l in (AQUI / ".env.instagram").read_text().splitlines() if "=" in l)
    return env["IG_TOKEN"], env["IG_ACCOUNT_ID"]


def get(caminho, token, **q):
    q["access_token"] = token
    return json.load(urllib.request.urlopen(API + caminho + "?" + urllib.parse.urlencode(q), timeout=30))


def post(caminho, token, **campos):
    campos["access_token"] = token
    req = urllib.request.Request(API + caminho, data=urllib.parse.urlencode(campos).encode(), method="POST")
    return json.load(urllib.request.urlopen(req, timeout=30))


def carregar():
    return json.loads(FILA.read_text()) if FILA.exists() else {}


def salvar(fila):
    DIR.mkdir(exist_ok=True)
    FILA.write_text(json.dumps(fila, ensure_ascii=False, indent=1))


def ler():
    token, ig = acesso()
    eu = get(ig, token, fields="username")["username"]
    fila = carregar()
    novos = ja_resp = 0
    midias = get(f"{ig}/media", token, fields="id,permalink,caption,timestamp", limit=POSTS)["data"]
    for m in midias:
        r = get(f"{m['id']}/comments", token, fields="id,text,username,timestamp,like_count,replies{id,username}", limit=50)
        while True:
            for c in r.get("data", []):
                if c.get("username") == eu:
                    continue
                respondido = any(x.get("username") == eu for x in c.get("replies", {}).get("data", []))
                if c["id"] in fila:
                    if respondido and fila[c["id"]]["status"] not in ("respondido", "ignorado"):
                        fila[c["id"]]["status"] = "respondido"
                    continue
                fila[c["id"]] = {"post": m["permalink"], "post_legenda": (m.get("caption") or "")[:90], "quem": c.get("username"),
                                 "texto": c.get("text"), "quando": c.get("timestamp"), "curtidas": c.get("like_count", 0),
                                 "status": "respondido" if respondido else "novo", "proposta": None}
                ja_resp += respondido
                novos += not respondido
            nxt = r.get("paging", {}).get("next")      # a URL seguinte já traz o token e os campos
            if not nxt:
                break
            r = json.load(urllib.request.urlopen(nxt, timeout=30))
    salvar(fila)
    pend = sum(1 for v in fila.values() if v["status"] in ("novo", "proposto", "aprovado"))
    print(f"{len(midias)} posts lidos · {novos} comentários novos para responder · {ja_resp} novos já respondidos no app · "
          f"{pend} pendentes na fila")


def mostrar():
    fila = carregar()
    pend = [(k, v) for k, v in fila.items() if v["status"] in ("novo", "proposto", "aprovado")]
    if not pend:
        print("nenhum comentário pendente"); return
    for k, v in sorted(pend, key=lambda kv: kv[1]["quando"]):
        print(f"[{v['status']}] {k} · @{v['quem']} · {v['quando'][:16]} · {v['post']}")
        print(f"   comentou: {v['texto']}")
        if v["proposta"]:
            print(f"   resposta: {v['proposta']}")
        print()


def mudar(ids, status, texto=None):
    fila = carregar()
    for i in ids:
        if i not in fila:
            raise SystemExit(f"comentário {i} não está na fila")
        if status == "aprovado" and not fila[i]["proposta"]:
            raise SystemExit(f"comentário {i} não tem resposta proposta; nada a aprovar")
        fila[i]["status"] = status
        if texto is not None:
            fila[i]["proposta"] = texto
    salvar(fila)
    print(f"{len(ids)} marcado(s) como {status}")


def responder():
    token, _ = acesso()
    fila = carregar()
    aprov = [(k, v) for k, v in fila.items() if v["status"] == "aprovado"][:MAX_POR_VEZ]
    if not aprov:
        print("nenhuma resposta aprovada"); return
    for n, (k, v) in enumerate(aprov):
        if n:
            time.sleep(ESPERA)
        r = post(f"{k}/replies", token, message=v["proposta"])
        v["status"], v["resposta_id"] = "respondido", r.get("id")
        salvar(fila)
        with LOG.open("a") as f:
            f.write(json.dumps({"quando": time.strftime("%Y-%m-%dT%H:%M:%S"), "comentario": k, "quem": v["quem"],
                                "post": v["post"], "resposta": v["proposta"], "resposta_id": r.get("id")}, ensure_ascii=False) + "\n")
        print(f"respondido @{v['quem']} ({k}) -> {r.get('id')}")


if __name__ == "__main__":
    a = sys.argv[1:] or ["mostrar"]
    {"ler": lambda: ler(), "mostrar": lambda: mostrar(),
     "propor": lambda: mudar([a[1]], "proposto", " ".join(a[2:])),
     "aprovar": lambda: mudar(a[1:], "aprovado"), "ignorar": lambda: mudar(a[1:], "ignorado"),
     "responder": lambda: responder()}[a[0]]()
