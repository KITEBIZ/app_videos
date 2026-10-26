"""baixa-com-som: o vídeo de ontem do #308 (só imagem, sem som) numa cópia; a pauta tem que buscar o áudio e seguir.
   python3 teste_som.py <pasta do código>"""
import shutil, subprocess, sys
from pathlib import Path
COD = Path(sys.argv[1]); sys.path[:0] = [str(COD), str(COD / "ferramentas")]
import os; os.environ.setdefault("GEMINI_API_KEY", "teste")
import estudio as E
T = Path("/tmp/ca/som/itens") / COD.name; shutil.rmtree(T, ignore_errors=True); (T / "308/referencia").mkdir(parents=True)
R = Path("/srv/kitebiz/projetos/conteudo/estudio-v2/videos/308")
for f in ("ficha.json", "historico.jsonl", "chat.jsonl"):
    shutil.copy(R / f, T / "308" / f)
for f in ("video.mp4", "video.info.json"):
    shutil.copy(R / "referencia" / f, T / "308/referencia" / f)
E.VIDEOS = T
import pauta
v = T / "308/referencia/video.mp4"
som = lambda a: bool(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of", "csv=p=0", str(a)],
                                    capture_output=True, text=True).stdout.strip())
print("antes: o vídeo tem som?", som(v))
try:
    meta = pauta.baixar_pauta(308, "https://www.instagram.com/reel/DesCSFNCgj0/")
    a = T / "308/referencia/audio.m4a"
    ok = a.exists() and som(a) and som(v)
    print(("PASSOU" if ok else "FALHOU"), "· a pauta seguiu: vídeo com som", som(v), "· audio.m4a", a.exists(), "· duração", meta.get("duracao"))
except Exception as e:
    print("FALHOU · a pauta parou:", str(e)[:200])
