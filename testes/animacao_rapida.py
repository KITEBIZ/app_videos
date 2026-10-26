"""Tipo A (sem IA): animacao-mais-rapida-e-certa (24/10/2026, "faz os concertos por favor"). (1) duas gravações do mesmo
arquivo ao mesmo tempo não se apagam (a tarja do #370 falhou 3 vezes assim); (2) a Tela pesada é reconhecida e o pedido
do plano troca a instrução final; (3) os Olhos, o editor e o olho único olham ao mesmo tempo e o olho único entra no
conserto; (4) as capas começam quando a cena existe. Calibrado: com o .tmp de nome único desligado, o caso 1 falha."""
import inspect, sys, tempfile, threading
from pathlib import Path
R = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(R), str(R / "ferramentas")]
import estudio as E, animador_novo as N
falhas = []
arq = Path(tempfile.mkdtemp()) / "tarjas.json"
erros = []
def grava(k):
    try:
        for i in range(60):
            E._grava(arq, f'{{"k": {k}, "i": {i}}}')
    except Exception as ex:
        erros.append(str(ex)[:80])
ts = [threading.Thread(target=grava, args=(k,)) for k in range(6)]
[t.start() for t in ts]; [t.join() for t in ts]
if erros:
    falhas.append(f"1: gravações ao mesmo tempo falharam {len(erros)} vez(es): {erros[0]}")
E.VIDEOS = Path(tempfile.mkdtemp()) / "videos"; E.LIXEIRA = E.VIDEOS / "_lixeira"
num, _ = E.criar_item("igual", texto="teste")
linha = lambda n, tela: f"| {n} | B{n} | nós | fala {n} | {tela} |"
(E.pasta(num) / "ROTEIRO.md").write_text("| # | Bloco | Quem | Fala | Tela |\n|---|---|---|---|---|\n" + "\n".join(linha(n, "x" * 400) for n in range(1, 9)) + "\n")
if not N.tela_pesada(num):
    falhas.append("2a: Tela de 3.200 caracteres não foi reconhecida como pesada")
(E.pasta(num) / "ROTEIRO.md").write_text("| # | Bloco | Quem | Fala | Tela |\n|---|---|---|---|---|\n" + "\n".join(linha(n, "x" * 100) for n in range(1, 9)) + "\n")
if N.tela_pesada(num):
    falhas.append("2b: Tela de 800 caracteres foi tratada como pesada")
fonte = inspect.getsource(N.primeira)
if "replace(PRIMEIRA, PLANO)" not in fonte or "animador novo (plano da cena)" not in fonte:
    falhas.append("2c: a primeira animação não faz o plano na Tela pesada")
if "ThreadPoolExecutor(3)" not in fonte or '"olho único"' not in fonte:
    falhas.append("3: Olhos, editor e olho único não olham juntos, ou o olho único não entra no conserto")
import servidor as S
if "capas_quando_houver_cena" not in inspect.getsource(S.animar):
    falhas.append("4: as capas não começam quando a cena existe")
print("passou · gravação sem colisão, Tela pesada com plano, olhos juntos com o olho único no conserto, capas cedo"
      if not falhas else "FALHOU · " + " | ".join(falhas))
sys.exit(1 if falhas else 0)
