#!/usr/bin/env python3
"""O que a página já publicou, para o agente consultar (26/10/2026, ele: "tem como a gente dar para o agente a capacidade
de ler o que ele disse que não pode ler?" e "pode fazer a parte dos números e comentários pro agente"). Sem IA.

  radar/desempenho.md    todos os posts lidos pelo radar: data, título, visualizações, envios por 100, tempo médio,
                         quem pula nos 3 s, comentários e o roteiro do estúdio (videos/<item>/ROTEIRO.md) quando houver
  radar/comentarios.md   o texto dos comentários dos últimos posts, os mais curtidos primeiro (desde 26/10/2026 do que o
                         analista da conta guardou, publicador/analista.py; esta ferramenta não lê mais a API)

  python3 ferramentas/desempenho.py            refaz os dois"""
import json, sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DES = RAIZ / "radar/desempenho.md"
COM = RAIZ / "radar/comentarios.md"
POSTS_COM = 15             # quantos posts recentes ler os comentários


def _titulo(p):
    return " ".join(str(p.get("legenda") or "-").split())[:80]


def desempenho(raiz=RAIZ):
    arq = raiz / "radar/pagina.json"
    if not arq.exists():
        return ""
    pag = json.loads(arq.read_text())
    posts = sorted(pag.get("posts") or [], key=lambda p: str(p.get("quando") or p.get("postado") or ""), reverse=True)
    med = pag.get("mediana") if isinstance(pag.get("mediana"), dict) else {}
    num = lambda v: "" if v is None else f"{v:,}".replace(",", ".") if isinstance(v, int) else str(v)
    linhas = [f"# Desempenho dos posts da @newsbr360 (radar lido em {str(pag.get('medido', ''))[:16]}; "
              f"{len(posts)} posts, mais novo primeiro; mediana dos últimos {med.get('posts', '?')}: {num(int(med.get('visualizacoes') or 0))} visualizações, "
              f"{med.get('envios_100', 0):.2f} envios/100, {med.get('pula_3s', '?')}% pulam nos 3 s)", "",
              "Envios/100 = compartilhamentos a cada 100 visualizações (o sinal mais forte). Pula 3 s = % que sai nos 3 "
              "primeiros segundos. Roteiro = o texto falado do vídeo, quando foi feito no estúdio.", "",
              "| Data | Post | Visualizações | Envios/100 | Tempo médio | Pula 3 s | Comentários | Roteiro |",
              "|---|---|---|---|---|---|---|---|"]
    for p in posts:
        it = str(p.get("item") or "")
        rot = raiz / "videos" / it / "ROTEIRO.md"
        linhas.append(f"| {str(p.get('postado') or '')[:10]} | [{_titulo(p)}]({p.get('link', '')}) | {num(p.get('visualizacoes'))} | "
                      f"{num(p.get('envios_100'))} | {num(p.get('tempo_medio_s'))} s | {num(p.get('pula_3s'))} | "
                      f"{num(p.get('comentarios'))} | {rot if it and rot.exists() else ''} |")
    texto = "\n".join(linhas) + "\n"
    (raiz / "radar").mkdir(exist_ok=True)
    (raiz / "radar/desempenho.md").write_text(texto)
    return texto


def comentarios(agora=False):
    """Os comentários que o analista da conta guardou (publicador/analista.py; uma leitura só da API, a dele), dos
    últimos 15 posts, os mais curtidos primeiro. agora= ficou por compatibilidade: quem lê a API é o analista."""
    arq = RAIZ / "publicador/comentarios/todos.jsonl"
    if not arq.exists():
        return ""
    por_post = {}
    for l in arq.read_text().splitlines():
        try:
            c = json.loads(l)
        except ValueError:
            continue
        por_post.setdefault(c["post"], {"titulo": c.get("titulo", ""), "quando": "", "cs": []})
        por_post[c["post"]]["cs"].append(c)
        por_post[c["post"]]["quando"] = max(por_post[c["post"]]["quando"], c.get("quando") or "")
    posts = sorted(por_post.items(), key=lambda kv: kv[1]["quando"], reverse=True)[:POSTS_COM]
    linhas = [f"# Comentários dos últimos {len(posts)} posts da @newsbr360 (guardados pelo analista da conta; os mais "
              "curtidos primeiro)", ""]
    for link, v in posts:
        cs = sorted(v["cs"], key=lambda c: -(c.get("curtidas") or 0))
        linhas += [f"## {v['quando'][:10]} · {v['titulo']}", f"{link} · {len(cs)} comentários guardados"]
        linhas += [f"- ({c.get('curtidas') or 0} curtidas) {c['texto'][:300]}" for c in cs[:50]]
        linhas.append("")
    texto = "\n".join(linhas)
    COM.write_text(texto)
    return texto


def _poucos_comentarios(texto, por_post=8):
    """Os 8 mais curtidos de cada post (o arquivo inteiro fica para o Read)."""
    out, n = [], 0
    for l in texto.splitlines():
        if l.startswith("#"):
            n = 0; out.append(l)
        elif l.startswith("- "):
            n += 1
            if n <= por_post:
                out.append(l)
        elif l.strip():
            out.append(l)
    return "\n".join(out)


def para_agente():
    """O que vai no pedido do agente. 26/10/2026 (#408, 12:29: com só o endereço dos arquivos, o Sonnet respondeu sem
    abrir nenhum e disse de novo "não tenho os comentários nem os últimos dez dias"): a tabela inteira e os comentários
    mais curtidos vão DENTRO do pedido; os arquivos completos ficam para o Read."""
    tab = com = ""
    try:
        tab = desempenho()
    except Exception as ex:
        print(f"desempenho: {ex}", file=sys.stderr)
    try:
        com = _poucos_comentarios(comentarios())
    except Exception as ex:
        print(f"comentarios: {ex}", file=sys.stderr)
    if not tab and not com:
        return ""
    return ("\n\n## Dados da página (você TEM estes dados: use-os quando a pergunta for sobre desempenho, público, o que "
            "viraliza, o que já fizemos ou o que as pessoas comentam; nunca diga que não tem números recentes ou comentários)\n"
            f"{tab}\n{com}\n"
            f"Mais detalhe, se precisar: {COM} (todos os comentários), {RAIZ / 'publicador/METRICAS.md'} (alcance, salvos, "
            "duração e retenção de cada reel) e o ROTEIRO.md da tabela (como o vídeo falava). Não temos: stories, nem quem "
            "é o seguidor (idade, cidade); diga isso só se perguntarem.")

if __name__ == "__main__":
    print(desempenho()[:400])
    print(comentarios()[:1500])
