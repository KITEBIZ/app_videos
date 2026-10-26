#!/usr/bin/env python3
"""Analista da conta @newsbr360 (26/10/2026, ele: "poderíamos ter um agente que faria a leitura dos dados da conta
newsbr360 e pode ser o mesmo que responde as pessoas" e "sim"). Roda junto com o robô de respostas
(comentarios_whatsapp.py, cron de 5 em 5 min), DEPOIS dele e sem mexer nele: se a análise falhar, as respostas seguem.

  1. guarda TODOS os comentários dos posts recentes (só leitura da API) em comentarios/todos.jsonl, sem repetir;
  2. a cada 3 h, das 8h às 22h, uma leitura da IA junta os comentários novos com os números dos posts e reescreve
     radar/publico.md: o que o público está dizendo (temas, dúvidas que se repetem, objeções à página, o que pedem para
     checar, que vídeo puxou conversa). O estúdio usa esse arquivo: agente do chat, roteirista, legenda e capa
     (estudio.memoria) e o resumo de números do agente (ferramentas/desempenho.py).

  python3 publicador/analista.py            uma rodada (respeita o intervalo)
  python3 publicador/analista.py --agora    lê e analisa já"""
import json, sys, time, urllib.request
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

AQUI = Path(__file__).resolve().parent
RAIZ = AQUI.parent
sys.path.insert(0, str(AQUI))
import comentarios as C

TODOS = C.DIR / "todos.jsonl"
ESTADO = C.DIR / "analista.json"
PUBLICO = RAIZ / "radar/publico.md"
BR = ZoneInfo("America/Sao_Paulo")
INTERVALO = timedelta(hours=3)
HORARIO = (8, 22)
POSTS = 15


def agora():
    return datetime.now(BR)


def guardados():
    out = {}
    for l in (TODOS.read_text().splitlines() if TODOS.exists() else []):
        try:
            c = json.loads(l); out[c["id"]] = c
        except (ValueError, KeyError):
            pass
    return out


def ler():
    """Todos os comentários dos últimos posts (com os de poucas palavras e os ofensivos: a leitura é do público inteiro).
    Devolve quantos eram novos."""
    token, ig = C.acesso()
    ja = guardados()
    novos = []
    for m in C.get(f"{ig}/media", token, fields="id,permalink,caption,timestamp", limit=POSTS)["data"]:
        titulo = " ".join((m.get("caption") or "-").split())[:90]
        r = C.get(f"{m['id']}/comments", token, fields="id,text,username,timestamp,like_count", limit=50)
        for _ in range(4):
            for c in r.get("data", []):
                if c["id"] in ja or c.get("username") == "newsbr360" or not (c.get("text") or "").strip():
                    continue
                x = {"id": c["id"], "quando": c.get("timestamp"), "post": m["permalink"], "titulo": titulo,
                     "quem": c.get("username"), "texto": " ".join(c["text"].split())[:500], "curtidas": c.get("like_count", 0),
                     "lido": agora().isoformat(timespec="minutes")}
                ja[c["id"]] = x; novos.append(x)
            if not r.get("paging", {}).get("next"):
                break
            r = json.load(urllib.request.urlopen(r["paging"]["next"], timeout=30))
    if novos:
        C.DIR.mkdir(exist_ok=True)
        with TODOS.open("a") as f:
            for x in novos:
                f.write(json.dumps(x, ensure_ascii=False) + "\n")
    return len(novos)


def analisar():
    e = json.loads(ESTADO.read_text()) if ESTADO.exists() else {}      # lido de novo: a rodada acabou de gravar rodou_em
    desde = e.get("analisado_ate", "")
    todos = sorted(guardados().values(), key=lambda c: c.get("lido", ""))
    novos = [c for c in todos if c.get("lido", "") > desde]
    if not novos and PUBLICO.exists():
        return "nada novo"
    # a janela: os comentários dos últimos 7 dias, os mais curtidos primeiro (até 400), e os números dos posts
    corte = (agora() - timedelta(days=7)).isoformat()
    janela = sorted([c for c in todos if (c.get("quando") or "") >= corte[:10]], key=lambda c: -(c.get("curtidas") or 0))[:400]
    sys.path.insert(0, str(RAIZ / "ferramentas")); import desempenho
    tabela = desempenho.desempenho()
    antes = PUBLICO.read_text() if PUBLICO.exists() else "(primeira leitura)"
    lista = "\n".join(f"- [{c['titulo'][:50]}] ({c.get('curtidas') or 0} curtidas) {c['texto']}" for c in janela)
    prompt = f"""Você é o analista da página @newsbr360 no Instagram (notícia de política e economia "com prova": o documento
na tela, a fonte na legenda; lema "Fato, fonte e ponto."). Leia o que o público comentou nos últimos 7 dias e os números
dos posts, e escreva para a equipe O QUE O PÚBLICO ESTÁ DIZENDO. Quem lê é o editor e o roteirista dos próximos vídeos.

Regras: só o que está nos comentários e na tabela; conte (quantos comentários dizem aquilo) e dê 1 exemplo curto entre
aspas; comentário não é fato (ninguém prova "fraude" num comentário: registre como o que o público sente); sem nome de
quem comentou; português simples, sem jargão; até 45 linhas.
Xingamento, ofensa, desejo de violência e comentário repetido são ruído de rede (26/10/2026, ele: "comentários de
xingamento a gente deve relativizar"): não conte como tema, não destaque, não faça seção de moderação nem alerta.

Escreva em markdown, com estas partes:
## O clima (2 ou 3 frases: o humor do público agora e o que mudou desde a leitura anterior)
## O que mais se fala (os 5 temas com mais comentários, com a contagem e um exemplo)
## Dúvidas que se repetem (perguntas que várias pessoas fazem; cada uma pode virar vídeo)
## O que pedem para a gente checar (afirmação que circula e o público quer saber se é verdade)
## Críticas à página (o que reclamam de nós: viés, erro, tom; diga se tem razão pelo que dá para ver)
## Que vídeo puxou conversa (cruze comentários com a tabela: muito comentário e pouco envio, ou o contrário)
## Para os próximos vídeos (3 a 5 sugestões concretas tiradas disto)

A leitura anterior (para dizer o que mudou):
{antes[:4000]}

Números dos posts:
{tabela[:9000]}

Comentários dos últimos 7 dias ({len(janela)} de {len(todos)} guardados, os mais curtidos primeiro):
{lista[:40000]}"""
    sys.path.insert(0, str(RAIZ)); import ia
    resp, uso = ia.chamar(prompt, "analista da conta", "sonnet", limite=300, cwd=C.DIR)
    if not resp or "##" not in resp:
        raise RuntimeError(f"análise falhou: {(uso.get('erro') or resp or 'vazia')[:200]}")
    PUBLICO.parent.mkdir(exist_ok=True)
    PUBLICO.write_text(f"# O que o público está dizendo (analista da conta, {agora().strftime('%d/%m %H:%M')}; "
                       f"{len(janela)} comentários dos últimos 7 dias)\n\n" + resp[resp.index("##"):].strip() + "\n")
    e["analisado_ate"] = todos[-1].get("lido", "") if todos else ""
    e["analisado_em"] = agora().isoformat(timespec="minutes")
    ESTADO.write_text(json.dumps(e, ensure_ascii=False, indent=1))
    return f"análise nova com {len(janela)} comentários ({len(novos)} novos)"


def rodada(forcar=False):
    e = json.loads(ESTADO.read_text()) if ESTADO.exists() else {}
    ult = datetime.fromisoformat(e["rodou_em"]) if e.get("rodou_em") else agora() - INTERVALO * 2
    h = agora().hour
    if not forcar and (agora() - ult < INTERVALO or not HORARIO[0] <= h < HORARIO[1]):
        return
    e["rodou_em"] = agora().isoformat(timespec="minutes")    # antes de ler: se falhar, só tenta de novo em 3 h
    C.DIR.mkdir(exist_ok=True); ESTADO.write_text(json.dumps(e, ensure_ascii=False, indent=1))
    n = ler()
    print(f"{agora().isoformat(timespec='minutes')} analista: {n} comentários novos guardados; {analisar()}")


if __name__ == "__main__":
    rodada(forcar="--agora" in sys.argv[1:])
