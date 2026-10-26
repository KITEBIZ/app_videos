#!/usr/bin/env python3
"""Palavra-chave FUNDADOR (24/10/2026; ele: "queremos vender tb", "pode fazer A, B, C e D", "FUNDADOR").
Quem comenta FUNDADOR num post recente recebe uma resposta privada (Direct) com a página de apoio, pela ferramenta
oficial da Meta (Private Replies: 1 mensagem por comentário, até 7 dias depois dele; cai em "pedidos" de quem não
segue), e uma resposta pública curta no comentário, que mostra aos outros que funciona. Regra da skill
instagram-agent (ig-dm, ig-reply): entregar primeiro, sem condição; nunca mandar mensagem a quem não comentou.

  python3 fundador.py --ensaio      lista quem receberia, sem mandar nada (padrão)
  python3 fundador.py --enviar      manda, 1 por minuto, só das 8h às 22h, no máximo 20 por vez; para em 2 recusas

Registro: comentarios/fundador.jsonl (quem recebeu não recebe de novo)."""
import json, re, sys, time, unicodedata, urllib.error, urllib.parse, urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import comentarios as C

AQUI = Path(__file__).resolve().parent
LOG = AQUI / "comentarios/fundador.jsonl"
PALAVRA = "fundador"
POSTS = 10
MAX_POR_VEZ = 20
DIAS = 7
PAGINA_APOIO = "https://institutobr360.com/#apoie"
TEXTO = ("Oi{nome}! Obrigado por querer apoiar. Os 100 primeiros doadores do Instituto BR360 viram Membro Fundador. "
         f"É por Pix, a partir de R$ 120 por ano (R$ 10 por mês): {PAGINA_APOIO}\n"
         "O Instituto não recebe dinheiro de partido, de político, de governo nem de emenda. Quem mantém o trabalho é quem "
         "doa. Qualquer dúvida, é só responder aqui.")
# respostas públicas curtas e variadas (iguais em quantidade o Instagram lê como spam)
PUBLICAS = ["Te mandei no Direct 👍", "Mandei no seu Direct, confere lá.", "Enviado no Direct. Obrigado pelo apoio!"]


def norm(t):
    return "".join(c for c in unicodedata.normalize("NFD", (t or "").lower()) if unicodedata.category(c) != "Mn")


def pediu(texto):
    return re.search(rf"\b{PALAVRA}\b", norm(texto)) is not None


def enviados():
    if not LOG.exists():
        return set()
    return {json.loads(l)["comentario"] for l in LOG.read_text().splitlines() if l.strip() and "erro" not in json.loads(l)}


def candidatos():
    """Os comentários com FUNDADOR nos últimos POSTS posts, dos últimos DIAS dias, que ainda não receberam."""
    token, conta = C.acesso()
    eu = C.get(conta, token, fields="username").get("username")
    limite = datetime.now(timezone.utc) - timedelta(days=DIAS)
    ja = enviados()
    out = []
    for m in C.get(f"{conta}/media", token, fields="id,permalink,timestamp", limit=POSTS).get("data", []):
        cs = C.get(f"{m['id']}/comments", token, fields="id,text,username,timestamp", limit=100).get("data", [])
        for c in cs:
            quando = datetime.fromisoformat(c["timestamp"].replace("+0000", "+00:00"))
            if c.get("username") == eu or quando < limite or c["id"] in ja or not pediu(c.get("text")):
                continue
            out.append({"comentario": c["id"], "quem": c.get("username"), "texto": c.get("text"), "post": m["permalink"],
                        "quando": c["timestamp"]})
    return out


def manda(p, k):
    token, _ = C.acesso()
    pagina = C.get("me", token, fields="id")["id"]      # privado.py, 10/10: a mensagem sai pelo id da Página
    nome = f", {p['quem']}" if p.get("quem") else ""
    corpo = urllib.parse.urlencode({"recipient": json.dumps({"comment_id": p["comentario"]}),
                                    "message": json.dumps({"text": TEXTO.format(nome=nome)}, ensure_ascii=False),
                                    "access_token": token}).encode()
    try:
        r = json.load(urllib.request.urlopen(urllib.request.Request(C.API + f"{pagina}/messages", data=corpo, method="POST"), timeout=30))
    except urllib.error.HTTPError as e:
        r = {"erro": f"HTTP {e.code}: " + e.read()[:400].decode(errors="replace")}
    if "erro" not in r:
        try:
            C.post(f"{p['comentario']}/replies", token, message=PUBLICAS[k % len(PUBLICAS)])
        except Exception as ex:                          # a pública é enfeite: falhar não desfaz o Direct
            r["publica"] = f"falhou: {str(ex)[:120]}"
    LOG.parent.mkdir(exist_ok=True)
    with LOG.open("a") as f:
        f.write(json.dumps({"enviado": time.strftime("%Y-%m-%dT%H:%M:%S"), **p, "resposta": r}, ensure_ascii=False) + "\n")
    return r


def main():
    a = sys.argv[1:] or ["--ensaio"]
    cs = candidatos()
    if "--enviar" not in a:
        print(f"ENSAIO: {len(cs)} comentário(s) com {PALAVRA.upper()} receberiam o Direct (nada foi enviado)")
        for p in cs:
            print(f"  @{p['quem']} · {p['quando'][:16]} · \"{(p['texto'] or '')[:60]}\" · {p['post']}")
        print("\nTexto do Direct:\n" + TEXTO.format(nome=", fulano"))
        return
    seguidas = 0
    for k, p in enumerate(cs[:MAX_POR_VEZ]):
        if not 8 <= datetime.now(ZoneInfo("America/Sao_Paulo")).hour < 22:
            print("fora do horário (8h-22h); parei"); return
        if k:
            time.sleep(60)
        r = manda(p, k)
        print(f"@{p['quem']}: {r}")
        seguidas = seguidas + 1 if "erro" in r else 0
        if seguidas >= 2:
            print("duas recusas seguidas; parei"); return


if __name__ == "__main__":
    main()
