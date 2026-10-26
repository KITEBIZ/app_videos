#!/usr/bin/env python3
"""A trilha de um vídeo em partes (24/10/2026; ele: "tem que ser uma musica/estilo na primeira parte e depois outro estilo
na parte dois" e "eu quero que vc consiga decidir quais musicas de background usar").

Junta trilhas da biblioteca (web/sons/trilhas/<estilo>.mp3, catálogo em web/sons/trilhas/CATALOGO.md) numa só, em
animacao/trilha.mp3 do vídeo, que a prévia e o vídeo final tocam no lugar da trilha de sempre (abaixando sob a voz,
como sempre). Na troca de parte: a de antes some em 0,35 s, um respiro de silêncio, e a nova entra em 0,4 s. O impacto
da virada é um efeito à parte, na cena: T.som('impacto-doc', instante).

  python3 ferramentas/trilha.py <número> arquivo@0 tensao@20.7 reflexao@49.1
  python3 ferramentas/trilha.py <número> --sem             volta à trilha de sempre (apaga animacao/trilha.mp3)
"""
import json, subprocess, sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
import estudio as E

BIB = RAIZ / "web/sons/trilhas"
SAI, RESPIRO, ENTRA = .35, .3, .4


def duracao(arq):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(arq)]))


def montar(num, partes, fim=None):
    """partes: [(estilo, início em s)], em ordem. Grava animacao/trilha.mp3 e devolve o caminho."""
    p = E.pasta(num)
    if fim is None:
        fim = json.loads((p / "narracao/completo.json").read_text())["duracao"] + 6     # a assinatura vem depois da voz
    entradas, filtros = [], []
    for k, (estilo, ini) in enumerate(partes):
        arq = BIB / f"{estilo}.mp3"
        if not arq.exists():
            raise SystemExit(f"não existe a trilha {estilo} (veja {BIB / 'CATALOGO.md'})")
        ate = partes[k + 1][1] if k + 1 < len(partes) else fim
        comeco = ini + (RESPIRO if k else 0)
        dur = max(.5, ate - comeco)
        if dur > duracao(arq):
            raise SystemExit(f"a trilha {estilo} tem {duracao(arq):.0f} s e a parte pede {dur:.0f} s")
        entradas += ["-i", str(arq)]
        f = f"[{k}:a]atrim=0:{dur:.3f},asetpts=PTS-STARTPTS"
        if k:
            f += f",afade=t=in:d={ENTRA}"
        if k + 1 < len(partes):
            f += f",afade=t=out:st={max(0, dur - SAI - RESPIRO):.3f}:d={SAI}"
        else:
            f += f",afade=t=out:st={max(0, dur - 2):.3f}:d=2"
        f += f",adelay={int(comeco * 1000)}:all=1[p{k}]"
        filtros.append(f)
    mix = "".join(f"[p{k}]" for k in range(len(partes))) + f"amix=inputs={len(partes)}:normalize=0[a]"
    saida = p / "animacao/trilha.mp3"
    saida.parent.mkdir(exist_ok=True)
    subprocess.run(["ffmpeg", "-v", "error", "-y", *entradas, "-filter_complex", ";".join(filtros + [mix]), "-map", "[a]",
                    "-t", f"{fim:.2f}", "-b:a", "192k", str(saida)], check=True)
    (p / "animacao/trilha.json").write_text(json.dumps({"partes": partes, "quando": E.agora()}, ensure_ascii=False))
    return saida


if __name__ == "__main__":
    num = int(sys.argv[1])
    if sys.argv[2:3] == ["--sem"]:
        for f in ("trilha.mp3", "trilha.json"):
            (E.pasta(num) / "animacao" / f).unlink(missing_ok=True)
        print("trilha de sempre")
    else:
        partes = [(a.split("@")[0], float(a.split("@")[1])) for a in sys.argv[2:]]
        print(montar(num, partes))
