"""A ponte para os Olhos (17/10/2026, "aprovo o plano olhos"). Os Olhos moram em conteudo/olhos/, com código próprio,
e rodam como programa separado: o estúdio só passa o vídeo e lê o resultado. Ele não manda nada do que sabe (regras,
roteiro, intenção) e nunca muda o vídeo por causa da opinião; só mostra."""
import json, subprocess, sys
from pathlib import Path

OLHOS = Path(__file__).resolve().parent.parent / "olhos"
# opiniao.py roda com -E e não -I (19/10/2026): os mosaicos precisam da biblioteca de imagem (PIL), que neste Mac
# está na pasta do usuário, e o -I a esconde; o -E ainda ignora as variáveis PYTHON* do ambiente


def _anota(pasta, op, quem):
    """19/10/2026: o gasto dos Olhos entra no gasto do vídeo (a pasta fica dentro de videos/<número>/)."""
    try:
        import estudio as E
        partes = Path(pasta).resolve().parts
        num = int(partes[partes.index("videos") + 1])
        if op.get("limite"):
            E.guarda_limite(op["limite"])
        if op.get("uso"):
            E.anota_gasto(num, quem, op.get("modelo") or "olhos", op["uso"])
    except (ValueError, IndexError):
        pass


def assistir(entrada, saida):
    """Vídeo (arquivo ou link) → saida/folha.json, saida/quadros/, saida/opiniao.json. Devolve a opinião."""
    saida = Path(saida); saida.mkdir(parents=True, exist_ok=True)
    subprocess.run([sys.executable, "-I", str(OLHOS / "assistir.py"), str(entrada), str(saida)], check=True, capture_output=True, timeout=1200)
    subprocess.run([sys.executable, "-E", str(OLHOS / "opiniao.py"), str(saida)], check=True, capture_output=True, timeout=1500)
    op = json.loads((saida / "opiniao.json").read_text())
    _anota(saida, op, "Olhos (vídeo inteiro)")
    return op


def opinar(pasta, modelo=None):
    """Pasta já com folha.json e quadros/ (17/10/2026, "aprovo o plano olhos-na-animacao": a prévia da animação, que não
    é um MP4) → os Olhos opinam. modelo: "opus" ou "sonnet" (sem ele, o padrão dos Olhos). Devolve a opinião."""
    subprocess.run([sys.executable, "-E", str(OLHOS / "opiniao.py"), str(pasta)] + ([modelo] if modelo else []),
                   check=True, capture_output=True, timeout=1500)
    op = json.loads((Path(pasta) / "opiniao.json").read_text())
    _anota(pasta, op, "Olhos (prévia)")
    return op


def ler(pasta):
    a = Path(pasta) / "opiniao.json"
    return json.loads(a.read_text()) if a.exists() else None


def ler_material(pasta, texto=None):
    """17/10/2026 ("aprovo o plano material-qualquer"): material sem som (carrossel, PDF, página web) → pasta/leitura.json.
    Os Olhos (conteudo/olhos/ler.py) leem cada imagem na ordem; as imagens ficam (o roteiro e a animação usam)."""
    cmd = [sys.executable, "-I", str(OLHOS / "ler.py"), str(pasta)] + ([str(texto)] if texto else [])
    subprocess.run(cmd, check=True, capture_output=True, timeout=1500)
    return json.loads((Path(pasta) / "leitura.json").read_text())
