"""Tipo A (sem IA, sem servidor no ar): mapa-de-passos parte 2 (24/10/2026). Ao religar, a ficha fora do mapa volta a
um passo que existe (o caso do #354 na VPS: "Aguardando · roteiro pronto · Publicar"), e o religar segue a tabela
("baixando e transcrevendo o vídeo que você mandou" sem mensagem pendente não fica parado para sempre). Tudo numa pasta
temporária com fichas de mentira. Calibrado: sem conserta_fora_do_mapa no retomar, o caso 1 falha."""
import json, os, sys, tempfile, time
from pathlib import Path
R = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(R), str(R / "ferramentas")]
import estudio as E
sys.argv = [sys.argv[0], "4497"]
import servidor as S
falhas = []
with tempfile.TemporaryDirectory() as d:
    E.VIDEOS = Path(d)
    S.garantir = lambda n: None                    # nada de trabalhador de verdade
    S.esperando_animacao = lambda n: "Aprovar o vídeo"
    def video(n, ficha, roteiro_depois=False, final_ok=True):
        p = Path(d) / str(n); (p / "publicacao").mkdir(parents=True)
        (p / "ficha.json").write_text(json.dumps({"num": n, "etapa": "", "passo": "", "esperando": "", **ficha}))
        (p / "chat.jsonl").write_text("")
        if final_ok:
            (p / "publicacao/final.json").write_text(json.dumps({"erros": []}))
        if roteiro_depois:
            time.sleep(.02); (p / "ROTEIRO.md").write_text("roteiro mudado depois do final")
    video(354, {"etapa": "Aguardando", "passo": "roteiro pronto", "esperando": "Publicar"}, roteiro_depois=True)
    video(355, {"etapa": "Aguardando", "passo": "roteiro pronto", "esperando": "Publicar"}, final_ok=False)
    video(356, {"etapa": "Animação", "passo": "baixando e transcrevendo o vídeo que você mandou", "esperando": ""})
    S.retomar()
    f = E.ler_ficha(354)
    if (f["passo"], f["esperando"]) != ("vídeo final pronto", "Publicar"):
        falhas.append(f"1: #354 ficou em {f['passo']!r} · {f['esperando']!r}, esperado vídeo final pronto · Publicar")
    if "roteiro mudou depois do vídeo final" not in (Path(d) / "354/chat.jsonl").read_text():
        falhas.append("1b: o #354 não avisou que o roteiro mudou depois do vídeo final")
    f = E.ler_ficha(355)
    if f["passo"] != "o vídeo final parou":
        falhas.append(f"2: sem vídeo final, o #355 ficou em {f['passo']!r}, esperado 'o vídeo final parou'")
    f = E.ler_ficha(356)
    if (f["passo"], f["esperando"]) != ("prévia pronta", "Aprovar o vídeo"):
        falhas.append(f"3: o #356 ficou em {f['passo']!r} · {f['esperando']!r}, esperado prévia pronta · Aprovar o vídeo")
print("passou · ao religar, a ficha fora do mapa e o download interrompido voltam a um passo que existe" if not falhas else "FALHOU · " + " | ".join(falhas))
sys.exit(1 if falhas else 0)
