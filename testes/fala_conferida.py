"""Tipo A (sem IA, sem rede, sem servidor): a fala de outra pessoa conferida num roteiro nosso vale em outro vídeo
(25/10/2026, "pode fazer"; #382: o take do Metrópoles veio do #304 pelo acervo, a transcrição automática dele ouve "hoje
é dia de descanso" e a trava desfez a fala certa, "Vamos lá, meu general!", conferida à mão no #304). Usa uma pasta de
vídeos temporária: não mexe em nenhum vídeo de verdade.

  .venv/bin/python testes/fala_conferida.py
"""
import json, sys, tempfile
from pathlib import Path

sys.path.insert(0, str(Path(sys.argv[0]).resolve().parent.parent))
import estudio as E
E.VIDEOS = Path(tempfile.mkdtemp()) / "videos"
E.LIXEIRA = E.VIDEOS / "_lixeira"

CAB = "| # | Parte | Quem | Fala | Tela |\n|---|---|---|---|---|\n"
ERRADA = [[0.0, 0.5, "Hoje"], [0.5, 0.9, "é"], [0.9, 1.3, "dia"], [1.3, 1.6, "de"], [1.6, 2.4, "descanso"],
          [4.66, 5.0, "Vamos"], [5.0, 5.3, "lá,"], [5.3, 5.6, "meu"], [5.6, 6.3, "querido."], [6.3, 8.7, "Vamos lá."]]


def video(num, linha):
    d = E.VIDEOS / str(num)
    (d / "material/DesTCX7RyXn").mkdir(parents=True, exist_ok=True)
    (d / "material/DesTCX7RyXn/palavras.json").write_text(json.dumps(ERRADA))
    (d / "ficha.json").write_text(json.dumps({"num": str(num), "etapa": "Pauta"}))
    (d / "ROTEIRO.md").write_text(CAB + "| 1 | Abertura | nós | O presidente gravou um recado. | texto |\n" + linha)


FALA = "Vamos lá, meu general! Vamos ativar o nosso exército."
video(304, f"| 2 | O recado | Lula | {FALA} (4,66-8,74 material/DesTCX7RyXn) | vídeo do Lula |\n")
falhas = []
casos = [("a fala e o corte conferidos no #304", f"{FALA} (4.66-8.74 material/DesTCX7RyXn)", None),
         ("o corte que acaba antes", f"{FALA} (4.66-7.5 material/DesTCX7RyXn)", "use esse corte"),
         ("uma palavra trocada", FALA.replace("general", "marechal") + " (4.66-8.74 material/DesTCX7RyXn)", "nunca troque palavra")]
for nome, fala, espera in casos:
    video(382, f"| 2 | O recado | Lula | {fala} | vídeo do Lula |\n")
    erros = E.falas_alheias(382)
    if espera is None and erros:
        falhas.append(f"{nome}: recusou ({erros[0][:140]})")
    if espera and not any(espera in e for e in erros):
        falhas.append(f"{nome}: devia recusar com '{espera}', deu {erros}")
# sem um roteiro nosso que confira, a transcrição automática continua valendo (a trava de antes)
(E.VIDEOS / "304/ROTEIRO.md").write_text(CAB + "| 1 | Abertura | nós | Outra coisa. | texto |\n")
video(382, f"| 2 | O recado | Lula | {FALA} (4.66-8.74 material/DesTCX7RyXn) | vídeo do Lula |\n")
if not E.falas_alheias(382):
    falhas.append("sem conferência em outro roteiro, a fala que não está na transcrição passou")

if falhas:
    print("FALHOU · " + "; ".join(falhas))
    sys.exit(1)
print("passou · a fala conferida no roteiro de outro vídeo vale com o mesmo corte; corte diferente diz qual usar; palavra "
      "trocada e fala sem conferência continuam recusadas")
