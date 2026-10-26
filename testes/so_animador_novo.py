"""Tipo A (sem IA, sem rede): só o animador novo (25/10/2026, ele: "limpa o animador antigo e prepara o novo para fazer
quando falha a primeira vez"). Antes, quando o novo falhava, caía no antigo (até 36 min e US$ 1 a 2), e o "roteiro refeito"
ia sempre ao antigo. Usa uma pasta de vídeos temporária e o animador novo fingido.

  .venv/bin/python testes/so_animador_novo.py
"""
import sys, tempfile
from pathlib import Path

RAIZ = Path(sys.argv[0]).resolve().parent.parent
sys.path[:0] = [str(RAIZ), str(RAIZ / "ferramentas")]
import estudio as E
E.VIDEOS = Path(tempfile.mkdtemp()) / "videos"
E.LIXEIRA = E.VIDEOS / "_lixeira"
import animacao as A, animador_novo as AN

A.preparar = lambda n: None
A.fotos_dos_blocos = lambda n, q: None
falhas, chamadas = [], []


def fingido(nome, resultados):
    seq = list(resultados)
    def f(num, *a):
        chamadas.append(nome)
        ok = seq.pop(0) if seq else True
        if ok and nome == "primeira":
            (E.pasta(num) / "animacao/cena.html").write_text("<script>function montar(){} /* nova */</script>")
        return ok, (f"{nome} feita" if ok else f"{nome} falhou")
    return f


def video(com_cena):
    num, _ = E.criar_item("igual", texto="teste")
    (E.pasta(num) / "animacao").mkdir(parents=True, exist_ok=True)
    if com_cena:
        (E.pasta(num) / "animacao/cena.html").write_text("<script>function montar(){} /* antiga */</script>")
    return num

# 1. o ajuste falha na 1ª e dá certo na 2ª: uma resposta só, dizendo que tentou de novo
num = video(True); chamadas.clear()
AN.ajustar = fingido("ajustar", [False, True])
r = A.animar(num, "troca a cor do título")
if chamadas != ["ajustar", "ajustar"] or "deu certo na 2ª" not in r:
    falhas.append(f"ajuste com 1 falha: chamadas={chamadas}, resposta={r!r}")

# 2. falha nas duas: o erro sobe e a cena de antes fica
num = video(True); chamadas.clear()
AN.ajustar = fingido("ajustar", [False, False])
try:
    A.animar(num, "troca a cor do título")
    falhas.append("falhou duas vezes e não avisou")
except RuntimeError as ex:
    if "falhou duas vezes" not in str(ex):
        falhas.append(f"o erro não diz que falhou duas vezes: {ex}")
cena = E.pasta(num) / "animacao/cena.html"
if not cena.exists() or "antiga" not in cena.read_text():
    falhas.append("depois de 2 falhas a cena de antes não ficou")

# 3. o roteiro refeito: a cena sai inteira pelo animador novo (antes, sempre pelo antigo)
num = video(True); chamadas.clear()
AN.primeira = fingido("primeira", [True])
A.animar(num, "O ROTEIRO FOI REFEITO (ele voltou ao roteiro, aprovou o novo e a voz foi regravada). Refaça a animação INTEIRA")
if chamadas != ["primeira"] or "nova" not in (E.pasta(num) / "animacao/cena.html").read_text():
    falhas.append(f"roteiro refeito não foi ao animador novo do zero: {chamadas}")

# 4. pedido num vídeo sem cena: é a primeira animação (antes, o ajuste falhava e caía no antigo)
num = video(False); chamadas.clear()
AN.primeira = fingido("primeira", [False, True])
A.animar(num, "faz a animação")
if chamadas != ["primeira", "primeira"]:
    falhas.append(f"pedido sem cena não virou primeira animação com nova tentativa: {chamadas}")

# 5. o caminho antigo não existe mais
fonte = (RAIZ / "animacao.py").read_text()
if "agente.trabalhar" in fonte or "def regua_conserta" in fonte or "def olhos_conserta" in fonte:
    falhas.append("o animador antigo ainda está no animacao.py")

if falhas:
    print("FALHOU · " + "; ".join(falhas))
    sys.exit(1)
print("passou · só o animador novo: tenta de novo uma vez, avisa e mantém a cena se falhar 2x, faz o roteiro refeito e a "
      "primeira animação; o caminho antigo saiu")
