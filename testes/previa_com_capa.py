"""previa-com-capa: trocar a capa muda a versão da prévia em vídeo (nome novo do arquivo); nada mudou, mesma versão."""
import importlib.util, shutil, subprocess, sys
from pathlib import Path
R = Path("/srv/kitebiz/projetos/conteudo/estudio-v2"); sys.path[:0] = [str(R), str(R / "ferramentas")]
import estudio as E
T = Path("/tmp/ca/pcc/itens"); shutil.rmtree(T, ignore_errors=True); T.mkdir(parents=True)
subprocess.run(["rsync", "-a", "--exclude=animacao/versoes", "--exclude=animacao/chamadas", "--exclude=material", "--exclude=referencia",
                "--exclude=animacao/previa-*.mp4", f"{R}/videos/316/", f"{T}/316/"], check=True)
E.pasta = lambda n: T / str(int(n))
def carrega(arq):
    spec = importlib.util.spec_from_file_location("render_" + Path(arq).parent.name, arq); m = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(m); return m
a = T / "316/animacao"
for nome, arq in (("antes", "/tmp/ca/pcc/render.antes.py"), ("novo", "/tmp/ca/pcc/render.py")):
    r = carrega(arq)
    shutil.copy(a / "capa-1.jpg", a / "capa.jpg"); v1 = r.versao_previa(316); v1b = r.versao_previa(316)
    shutil.copy(a / "capa-2.jpg", a / "capa.jpg"); v2 = r.versao_previa(316)
    print(f"{nome}: nada mudou -> {'mesma' if v1 == v1b else 'MUDOU'}; trocou a capa -> {'nova versão' if v1 != v2 else 'mesma versão'}")
