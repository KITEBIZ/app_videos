#!/usr/bin/env python3
"""O convite novo ajudou ou atrapalhou? (24/10/2026; ele: "em relação ao que a gente tinha e que fazia nossos videos
viralizar, mudou muito?"). Compara os vídeos publicados a partir de uma data com os de antes, pelo que o radar mede:
múltiplo da mediana da página, envios a cada 100 visualizações e quem pula aos 3 s; e, dentro de cada grupo, os
convites com destinatário ("manda para quem...", "compartilha com o amigo...") contra os outros. Sem IA.

  python3 ferramentas/medir_convite.py 2026-10-25        os vídeos de 25/10 em diante contra os de antes
"""
import json, re, statistics, sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DESTINO = re.compile(r"\b(manda|mande|compartilh\w*|envia|encaminh\w*)\b.{0,40}\b(quem|amigo|amiga|grupo|famil\w*|tio|tia|mae|pai|irmao)\b")


def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def norm(t):
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", (t or "").lower()) if unicodedata.category(c) != "Mn")


def resumo(nome, ps):
    if not ps:
        return f"{nome}: nenhum vídeo"
    med = lambda k: statistics.median([v for v in (p[k] for p in ps) if v is not None] or [0])
    return (f"{nome}: {len(ps)} vídeos · múltiplo mediano {med('mult'):.2f}x · envios/100 mediano {med('envios'):.2f} · "
            f"pula aos 3 s mediano {med('pula'):.0f}%")


def main(desde):
    pag = json.loads((RAIZ / "radar/pagina.json").read_text())
    cv = json.loads((RAIZ / "radar/convites.json").read_text()) if (RAIZ / "radar/convites.json").exists() else {}
    ps = [p for p in pag.get("posts", []) if num(p.get("visualizacoes"))]
    base = statistics.median(num(p["visualizacoes"]) for p in ps)
    linhas = []
    for p in ps:
        c = cv.get(str(p.get("item") or ""), "")
        linhas.append({"data": p.get("postado") or "", "mult": num(p["visualizacoes"]) / base, "envios": num(p.get("envios_100")),
                       "pula": num(p.get("pula_3s")), "destino": bool(DESTINO.search(norm(c))) if c else None})
    antes = [l for l in linhas if l["data"] < desde]; depois = [l for l in linhas if l["data"] >= desde]
    print(f"mediana da página: {base:.0f} visualizações ({len(ps)} posts lidos pelo radar)")
    print(resumo(f"antes de {desde}", antes)); print(resumo(f"de {desde} em diante", depois))
    for nome, g in (("antes", antes), ("depois", depois)):
        print("  " + resumo(f"{nome}, convite com destinatário", [l for l in g if l["destino"] is True]))
        print("  " + resumo(f"{nome}, convite sem destinatário", [l for l in g if l["destino"] is False]))
    if len(depois) < 10:
        print(f"(com {len(depois)} vídeo(s) depois, ainda é cedo: a comparação vale a partir de uns 10)")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "2026-10-25")
