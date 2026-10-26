#!/usr/bin/env python3
"""Conferência de fluidez do roteiro, por programa, sem IA (24/10/2026, "aprovo o plano roteiro-fluido"; ele: "o
roteiro esta duro e repetir as coisas"). Medido antes em 62 roteiros da VPS: "Manda para quem te passou o vídeo" em 20,
"a gente foi" em 22 falas, "Em dois mil" abrindo 16 falas, e 40 de 62 com a mesma palavra forte em 3 ou mais blocos.

  problemas(blocos, gastas)   [frases]: começo igual em falas nossas seguidas, palavra forte (6+ letras, fora nomes
                              próprios) em 3 ou mais falas, expressão gasta dos últimos roteiros
  gastas(raiz)                [expressões] de 3 palavras que aparecem em 5 ou mais dos últimos 15 roteiros publicados
                              (radar/falas.json, que a memória da página guarda)
  python3 ferramentas/fluidez.py <número>   confere o ROTEIRO.md do vídeo
"""
import json, re, sys, unicodedata
from collections import Counter
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent

COMUNS = set("""porque quando depois também ainda sobre contra entre durante desde governo brasil presidente ministro
ministros supremo federal pessoas segundo primeiro primeira número números milhões bilhões disse dizer falou fazer
estava estavam ninguém alguém outra outro outras outros nossa nosso mesmo mesma assim agora antes""".split())
# números por extenso e conectivos não contam como expressão gasta (a data é dita por extenso por regra)
NUMERAL = re.compile(r"\b(mil|dois|duas|tres|quatro|cinco|seis|sete|oito|nove|dez|onze|doze|vinte|trinta|quarenta|cinquenta|"
                     r"sessenta|setenta|oitenta|noventa|cem|cento|duzentos|trezentos|novecentos|um|uma|zero)\b")


def norm(t):
    t = "".join(c for c in unicodedata.normalize("NFD", t.lower()) if unicodedata.category(c) != "Mn")
    return re.sub(r"[^a-z0-9 ]", " ", re.sub(r"\(.*?\)", " ", t))


def _nossas(blocos):
    return [b for b in blocos if re.fullmatch(r"n[oó]s", (b.get("quem") or "").strip(), re.I) and (b.get("fala") or "").strip()]


def gastas(raiz=RAIZ, ultimos=15, minimo=5):
    try:
        falas = json.loads((raiz / "radar/falas.json").read_text())
    except (OSError, ValueError):
        return []
    itens = sorted(falas, key=lambda k: int(k) if k.isdigit() else 0)[-ultimos:]
    conta = Counter()
    for it in itens:
        vistos = set()
        for f in falas[it]:
            w = norm(f).split()
            for i in range(len(w) - 2):
                tri = " ".join(w[i:i + 3])
                if not NUMERAL.search(tri) and len(tri) >= 10:
                    vistos.add(tri)
        conta.update(vistos)
    return [e for e, q in conta.most_common(40) if q >= minimo][:12]


def problemas(blocos, gastas_=()):
    nossas = _nossas(blocos)
    out = []
    # 1) duas falas nossas seguidas que começam com as mesmas duas palavras (ou as duas pela data)
    for a, b in zip(nossas, nossas[1:]):
        wa, wb = norm(a["fala"]).split()[:2], norm(b["fala"]).split()[:2]
        if wa and wa == wb:
            out.append(f"as falas dos blocos {a.get('n', '?')} e {b.get('n', '?')} começam iguais (\"{' '.join(wa)}\"): mude o começo de uma")
        elif wa and wb and wa[0] == wb[0] == "em" and NUMERAL.search(" ".join(wa + wb)):
            out.append(f"os blocos {a.get('n', '?')} e {b.get('n', '?')} começam pela data: leve a data para o meio da frase")
    # 2) a mesma palavra forte em 3 ou mais falas (fora nomes próprios e palavras comuns do assunto)
    nomes = {norm(m).strip() for b in blocos for m in re.findall(r"\b[A-ZÁÉÍÓÚÂÊÔÃÕ][\wáéíóúâêôãõç]+", b.get("fala") or "")}
    conta = Counter(p for b in nossas for p in set(x for x in norm(b["fala"]).split() if len(x) >= 6 and x not in COMUNS and x not in nomes and not NUMERAL.fullmatch(x)))
    for p, q in conta.most_common():
        if q >= 3:
            onde = [str(b.get("n", "?")) for b in nossas if p in norm(b["fala"]).split()]
            out.append(f"\"{p}\" aparece em {q} falas (blocos {', '.join(onde)}): troque por outra palavra ou pronome em pelo menos uma")
    # 3) expressão gasta dos últimos roteiros
    for e in gastas_:
        for b in nossas:
            if e in norm(b["fala"]):
                out.append(f"o bloco {b.get('n', '?')} usa \"{e}\", que já apareceu em muitos vídeos: diga de outro jeito")
                break
    return out


if __name__ == "__main__":
    sys.path.insert(0, str(RAIZ))
    import estudio as E
    ps = problemas(E.blocos(int(sys.argv[1])), gastas())
    print("\n".join(ps) if ps else "fluido: nada a acertar")
