"""Tipo A (sem IA, sem rede, sem servidor): o acervo do que já baixamos (25/10/2026, "aprovo o acervo"; #382: o Lula
falando do "general" estava num take do #304 e o agente procurou na web). Monta numa pasta temporária um estúdio de
mentira com o ferramentas/acervo.py de verdade: não lê nem grava nada dos vídeos reais.

  .venv/bin/python testes/acervo.py
"""
import json, os, shutil, subprocess, sys, tempfile
from pathlib import Path

RAIZ = Path(sys.argv[0]).resolve().parent.parent
T = Path(tempfile.mkdtemp()) / "estudio-v2"
(T / "ferramentas").mkdir(parents=True)
shutil.copy(RAIZ / "ferramentas/acervo.py", T / "ferramentas/acervo.py")


def pasta(rel, meta, trans="", video=False, info=None):
    d = T / rel
    d.mkdir(parents=True, exist_ok=True)
    (d / "meta.json").write_text(json.dumps(meta, ensure_ascii=False))
    if trans:
        (d / "transcricao.txt").write_text(trans)
    if video:
        (d / "video.mp4").write_bytes(b"x")
    if info:
        (d / "audio.info.json").write_text(json.dumps(info))


# o reel que o radar ouviu (só áudio): diz "marechal", não diz "Janones"
pasta("referencias/DexsRTkMx9y", {"link": "https://www.instagram.com/reel/DexsRTkMx9y/", "quem": "André Janones",
                                  "conta": "andrejanones", "postado": "2026-10-21T19:00:00-03:00", "duracao": 59.4},
      "0:35  Nós vamos receber, não o nosso general não.\n0:38  Nós vamos receber o nosso marechal.\n")
# o take do #304: a transcrição automática saiu errada; a fala certa está no roteiro
pasta("videos/304/material/DesTCX7RyXn", {"link": "https://www.instagram.com/reel/DesTCX7RyXn/?obrf=abc",
                                          "quem_postou": "Metrópoles", "conta": "metropoles", "postado": "2026-10-19"},
      "0:00  Hoje é dia de descanso, daquilo que a gente não quer.\n", video=True)
(T / "videos/304/ficha.json").write_text(json.dumps({"etapa": "Publicado"}))
(T / "videos/304/ROTEIRO.md").write_text("| 2 | O recado | Lula | Vamos lá, meu general! Vamos ativar o nosso exército. "
                                         "(4,66-8,74 material/DesTCX7RyXn) | vídeo do Lula |\n")
# o mesmo reel do #304 baixado de novo no #310 com outro link (?igsh=): um vídeo só no acervo, com os dois usos
pasta("videos/310/material/DesTCX7RyXn", {"link": "https://www.instagram.com/reel/DesTCX7RyXn/?igsh=xyz"})
(T / "videos/310/ficha.json").write_text(json.dumps({"etapa": "Animação"}))
# do estúdio antigo, só com o .info.json do yt-dlp (o meta.json de outra época, sem link)
pasta("antigo/janones-exercito/referencias/yJJUk_tyefI", {"title": "Debate"},
      "1:02:03  O exército digital do Lula começou em 2022.\n",
      info={"webpage_url": "https://www.youtube.com/watch?v=yJJUk_tyefI", "uploader": "Revista Oeste", "upload_date": "20261009"})
# o que o estúdio gera não é vídeo baixado
pasta("videos/304/animacao/quadros", {"link": "https://exemplo.com/nao-e-baixado"})

env = {**os.environ, "ACERVO_DB": str(T / "radar/acervo.db"), "ACERVO_ANTIGO": str(T / "antigo")}
rodar = lambda *a: subprocess.run([sys.executable, str(T / "ferramentas/acervo.py"), *a], capture_output=True, text=True,
                                  env=env, timeout=60)
falhas = []
j = rodar("juntar")
if j.returncode:
    falhas.append("juntar quebrou: " + j.stderr[-300:])
achar = lambda q: json.loads(rodar("buscar", q, "--json").stdout or "[]")

a = achar("Lula marechal general Janones")
if not any("DexsRTkMx9y" in x["link"] for x in a):
    falhas.append("o reel do 'marechal' (sem a palavra Janones) não apareceu")
r = achar("meu general exército")
um = next((x for x in r if "DesTCX7RyXn" in x["link"]), None)
if not um:
    falhas.append("o take do #304 não apareceu pela fala do roteiro")
else:
    if not any(t["fala"].startswith("Vamos lá, meu general!") and abs(t["seg"] - 4.66) < .01 for t in um["trechos"]):
        falhas.append(f"a fala conferida no roteiro não veio com 4,66 s: {um['trechos']}")
    if sorted(u.split(":")[0] for u in um["usos"]) != ["#304 (publicado)", "#310"]:
        falhas.append(f"o mesmo reel com dois links não virou um só com os dois usos: {um['usos']}")
    if not um["video"].endswith("videos/304/material/DesTCX7RyXn/video.mp4"):
        falhas.append(f"não disse onde o vídeo ainda está: {um['video']!r}")
y = achar("exercito digital")           # sem acento na busca, com acento na fala
if not y or "youtube.com/watch?v=yJJUk_tyefI" not in y[0]["link"] or y[0]["trechos"][0]["mmss"] != "62:03" \
        or not any("estúdio antigo" in u for u in y[0]["usos"]):
    falhas.append(f"o do estúdio antigo (link do .info.json, h:mm:ss, sem acento) não veio certo: {y[:1]}")
if any("nao-e-baixado" in x["link"] for x in achar("exemplo")):
    falhas.append("uma pasta que o estúdio gera (animacao/quadros) entrou como vídeo baixado")
if "Nada no acervo" not in rodar("buscar", "zzqxwvk").stdout:
    falhas.append("a busca sem resultado não manda procurar na web")

# 25/10/2026 (#382): o take guardado no #304 vale no #320 sem baixar (material/<código>/, o mesmo arquivo no disco)
(T / "videos/320").mkdir(parents=True, exist_ok=True)
tr = rodar("trazer", "320", "https://www.instagram.com/reel/DesTCX7RyXn/?igsh=outro")
novo = T / "videos/320/material/DesTCX7RyXn/video.mp4"
if tr.returncode or not novo.exists() or "material/DesTCX7RyXn" not in tr.stdout:
    falhas.append(f"trazer não pôs o take em material/ do #320: {tr.stdout.strip()} {tr.stderr[-200:]}")
elif novo.stat().st_ino != (T / "videos/304/material/DesTCX7RyXn/video.mp4").stat().st_ino:
    falhas.append("trazer copiou o vídeo em vez de ligar o mesmo arquivo (ocupa o dobro)")
if "já está" not in rodar("trazer", "320", "https://www.instagram.com/reel/DesTCX7RyXn/").stdout:
    falhas.append("trazer de novo não disse que já está")
if rodar("trazer", "320", "https://www.instagram.com/reel/DexsRTkMx9y/").returncode == 0:
    falhas.append("trazer um vídeo sem o arquivo guardado (só áudio) não recusou")
if "acervo.py trazer <número>" not in rodar("buscar", "meu general").stdout:
    falhas.append("a busca não diz como trazer o vídeo guardado")

shutil.rmtree(T.parent, ignore_errors=True)
if falhas:
    print("FALHOU · " + "; ".join(falhas))
    sys.exit(1)
print("passou · acervo: acha o 'marechal' sem a palavra Janones, a fala conferida do #304 com o segundo, junta o mesmo "
      "reel de dois links, lê o estúdio antigo, não pega o que o estúdio gera e traz o take guardado de outro vídeo")
