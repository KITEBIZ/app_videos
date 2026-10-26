"""capa-depois-da-animacao: (A) sem takes o agente recusa; (B) na primeira animação a capa sai depois dela."""
import shutil, subprocess, sys, threading, time
from pathlib import Path
R = Path("/srv/kitebiz/projetos/conteudo/estudio-v2"); sys.path[:0] = ["/tmp/ca/cda", str(R), str(R / "ferramentas"), str(R / "testes")]
import estudio as E
T = Path("/tmp/ca/cda/itens"); shutil.rmtree(T, ignore_errors=True); T.mkdir()
subprocess.run(["rsync", "-a", "--exclude=animacao/versoes", "--exclude=animacao/chamadas", "--exclude=material", "--exclude=animacao/previa-*.mp4",
                f"{R}/videos/316/", f"{T}/316/"], check=True)
E.pasta = lambda n: T / str(int(n))
ok = []
# (A) a cena sem nenhum take: o agente não pode entregar capa só com texto
import capa_agente as CA
CA._takes = lambda num: []
for f in (T / "316/animacao/rostos").glob("rosto-*.jpg"):
    f.unlink()
try:
    CA.fazer(316); ok.append(("A: sem takes o agente recusa", False))
except RuntimeError as ex:
    ok.append((f"A: sem takes o agente recusa ({ex})", "foto" in str(ex)))
# (B) a ordem na primeira animação, com o animador e as capas fingidos (sem IA)
import importlib.util
for m in ("servidor", "capa", "capa_agente"):          # o arquivo novo, não o do estúdio (um import pôs a pasta dele na frente)
    sys.modules.pop(m, None)
sys.path.insert(0, "/tmp/ca/cda")
import servidor as S
assert S.__file__.startswith("/tmp/ca/cda") and S.capa.__file__.startswith("/tmp/ca/cda"), (S.__file__, S.capa.__file__)
print("carregou:", S.__file__, S.capa.__file__)
ordem = []
S.animacao.animar = lambda num, pedido: (ordem.append("animação"), time.sleep(1), "ok")[2]
S.capa.opcoes = lambda num: []
import traceback
S.capa.fazer = lambda *a, **k: (ordem.append("capa"), print("CAPA CHAMADA POR:", "".join(traceback.format_stack(limit=4)[:-1])), "x")[2]
S.legenda_post.ler = lambda num: ""
S.legenda_post.fazer = lambda num: (ordem.append("legenda"), "leg")[1]
S.esperando_animacao = lambda num: ""
S.animar(316, msg=None)
passo = E.ler_ficha(316)["passo"]
ok.append((f"B: a capa não roda junto com a animação (ordem {ordem})", "capa" not in ordem))
ok.append((f"B: depois da animação o item fica em 'fazendo as capas' (passo: {passo})", passo == S.CAPANDO))
ordem.clear(); S.fazer_capas(316, msg=None)
ok.append((f"B: o vigia faz as capas nesse passo (ordem {ordem})", ordem == ["capa"]))
for txt, b in ok:
    print("PASSOU" if b else "FALHOU", "·", txt)
