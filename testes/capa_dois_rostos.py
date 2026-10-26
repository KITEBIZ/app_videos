"""Capa com dois rostos (25/10/2026, #373, ele: "pedi uma imagem metade Lula metade o sargento e não obedeceu"): o take
do Lula tinha o rótulo "AO VIVO NA GLOBO", sem o nome, e a foto dele caía; a capa saía só com o sargento. Sem IA; abre a
prévia do #373 por trás (precisa do servidor da cópia local no ar)."""
import sys
from pathlib import Path
R = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(R), str(R / "ferramentas")]
import estudio as E
p = E.pasta(373)
if not (p / "animacao/cena.html").exists():
    print("pulado · sem o #373 nesta cópia"); sys.exit(0)
import capa_agente as CA
tk = CA._takes(373); d = p / "animacao/teste-capa"; d.mkdir(exist_ok=True)
falhas = []
lula = CA.foto(373, {"t": 6, "quem": "Lula"}, tk, d / "l.jpg", outros=["Sargento Kaiak"])
if not (lula and lula[5]["src"] == "referencia/video.mp4"):
    falhas.append(f"a foto do Lula (take sem o nome no rótulo) não saiu: {lula}")
sgt = CA.foto(373, {"t": 6, "quem": "Kaiak"}, tk, d / "s.jpg", outros=["Lula"])
if not (sgt and "De4TJ1kxgH0" in sgt[5]["src"]):
    falhas.append(f"o sargento pedido no segundo do Lula não foi ao take dele: {sgt and sgt[5]}")
# 25/10/2026 ("pode fazer"): o selo fora dos rostos, a barra do título vira linha, um crédito por linha
import re
if lula and sgt:
    s = CA.foto(373, {"t": 2, "quem": "Sargento Kaiak"}, tk, d / "s2.jpg", outros=["Lula"])
    op = {"desenho": "dois_rostos", "titulo": "LULA PROMETEU ACABAR COM A POLÍCIA / E O SARGENTO RESPONDEU", "destaque": "DE QUE LADO VOCÊ ESTÁ?"}
    x, y = CA._lugar_do_selo(op, [lula, s])
    em_cima = [r for r in CA._rostos_na_capa(op, [lula, s]) if min(x + 220, r[2]) > max(x, r[0]) and min(y + 188, r[3]) > max(y, r[1])]
    if em_cima:
        falhas.append(f"o selo em ({x}, {y}) cobre um rosto: {em_cima}")
    svg = CA.svg(9, op, [lula, s], "")
    titulo = re.findall(r'<text x="540" y="\d+">([^<]+)', svg)
    if any("/" in l for l in titulo):
        falhas.append(f"a barra apareceu no título: {titulo}")
    creds = re.findall(r'<text x="60" y="\d+">(Vídeo[^<]+)', svg)
    if len(creds) != 2 or any(len(c) > 72 for c in creds):
        falhas.append(f"o crédito não saiu em duas linhas inteiras: {creds}")
print("passou · Lula e sargento, cada um do seu take; selo fora dos rostos, título sem barra, crédito inteiro" if not falhas
      else "FALHOU · " + " · ".join(falhas))
sys.exit(1 if falhas else 0)
