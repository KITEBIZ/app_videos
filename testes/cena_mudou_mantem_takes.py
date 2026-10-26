"""Tipo A (sem IA, sem servidor): mudou a cena, a primeira montagem mantém a faixa e o rosto dos takes que continuam
(25/10/2026, #373: tirar o borrão mudou a cena e o Lula voltou com a faixa preta e fora do enquadramento; a lista lida
do texto perdia o take com corte em conta). Roda no #373 da cópia local, sem gravar nada além dos caches de medida."""
import json, sys
from pathlib import Path
R = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(R), str(R / "ferramentas")]
import estudio as E, animacao as A

p = E.pasta(373)
if not (p / "animacao/takes.json").exists():
    print("pulado · sem o #373 nesta cópia"); sys.exit(0)
cena = (p / "animacao/cena.html").read_text() + "\n<!-- mudou -->\n"
assert A.takes_conhecidos(373, cena) is None, "a cena mudada não pode bater com takes.json"
lula = [f'{x["src"]}@{max(0.0, float(x["corte"])):.2f}' for x in json.loads((p / "animacao/takes.json").read_text())["takes"]
        if x["src"] == "referencia/video.mp4"]
tj = A.tarjas_dos_videos(373, cena)
ro = A.rostos_dos_takes(373, cena, so_guardado=True)
falta_t = [k for k in lula if k not in tj]
falta_r = [k for k in lula if k not in ro]
ok = not falta_t and not falta_r
print(("passou" if ok else "FALHOU") + f" · takes do Lula {len(lula)} · sem faixa medida {falta_t} · sem rosto {falta_r}")
sys.exit(0 if ok else 1)
