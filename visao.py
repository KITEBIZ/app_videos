"""Olhar imagens sem IA: um quadro do vídeo e os rostos dele (25/10/2026, ele: "verifica tudo que está duplicado"; eram 5
detectores de rosto escritos cada um do seu jeito, na capa, na capa de reserva, no animador, nos takes da animação e na
montagem antiga, e o mesmo "tirar um quadro com o ffmpeg" repetido em cada um).

  quadro(video, t)               o quadro do segundo t (imagem do OpenCV, BGR) ou None
  rostos(img, limiar)            [(x, y, l, a, nota), ...] do maior para o menor
  maior(img, limiar)             (x, y, l, a) do maior rosto ou None
  nitidez(img)                   o quanto a imagem está nítida (variância do Laplaciano; borrado < ~150)
  melhor_rosto(video, de, ate)   o quadro com o maior rosto nítido entre de e ate: (img, (x, y, l, a), segundo) ou None
"""
import subprocess
from pathlib import Path

MODELO = Path(__file__).resolve().parent / "ferramentas/modelos/yunet.onnx"      # YuNet, o detector de rosto do OpenCV


def _cv2():
    import cv2
    try:
        cv2.utils.logging.setLogLevel(cv2.utils.logging.LOG_LEVEL_ERROR)     # o aviso de cada foto poluía o servidor.log
    except AttributeError:
        pass
    return cv2


def quadro(video, t):
    """O quadro do vídeo no segundo t. Pelo ffmpeg: o OpenCV não abre o vídeo do Instagram e devolvia nada, em silêncio."""
    import numpy as np
    cv2 = _cv2()
    png = subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-ss", f"{max(0.0, float(t)):.2f}", "-i", str(video), "-frames:v", "1",
                          "-f", "image2pipe", "-vcodec", "png", "-"], capture_output=True, timeout=120).stdout
    return cv2.imdecode(np.frombuffer(png, np.uint8), cv2.IMREAD_COLOR) if png else None


def rostos(img, limiar=.7):
    """Os rostos do quadro, do maior para o menor: [(x, y, l, a, nota)] (nota de 0 a 1 do detector)."""
    if img is None:
        return []
    cv2 = _cv2()
    det = cv2.FaceDetectorYN.create(str(MODELO), "", (img.shape[1], img.shape[0]), limiar)
    _, fs = det.detect(img)
    out = [tuple(float(v) for v in f[:4]) + (float(f[-1]),) for f in (fs if fs is not None else [])]
    return sorted(out, key=lambda r: -r[2] * r[3])


def maior(img, limiar=.7):
    rs = rostos(img, limiar)
    return tuple(int(v) for v in rs[0][:4]) if rs else None


def nitidez(img):
    cv2 = _cv2()
    return cv2.Laplacian(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), cv2.CV_64F).var()


def melhor_rosto(video, de, ate, passo=.25, limiar=.7):
    """De quarto em quarto de segundo entre de e ate, o quadro com o maior rosto nítido (nota = área x confiança x
    nitidez até 150). Devolve (img, (x, y, l, a), segundo) ou None."""
    melhor, k = None, max(0.0, de)
    while k <= ate + 1e-9:
        q = quadro(video, k)
        rs = rostos(q, limiar)
        if rs:
            x, y, l, a, conf = rs[0]
            nota = l * a * conf * min(1.0, nitidez(q) / 150)
            if not melhor or nota > melhor[0]:
                melhor = (nota, q, (int(x), int(y), int(l), int(a)), round(k, 3))
        k += passo
    return melhor[1:] if melhor else None
