"""O agente baixa um vídeo que ele mesmo achou (estúdio v2, 17/10/2026, "aprovo o plano agente-baixa"; ele: "a gente
construiu essa ferramenta na v1").

  python3 baixar.py <número> <link>

Link de FOTO (22/10/2026, "aprovo o plano agente-baixa-foto"): a foto vai para material/fotos/ (crédito opcional
depois do link: python3 baixar.py <número> <link da foto> <veículo, data>).

Usa o mesmo downloader dos links que ele manda (agente.material: áudio, dados do post, transcrição palavra a palavra e o
vídeo inteiro em material/<código>/). Limites: só link de vídeo, até 15 minutos, no máximo 6 por pedido dele (era 3 até 17/10).
Imprime a transcrição com mm:ss e diz como escrever o corte: "(início-fim material/<código>)".
"""
import json, sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ)); sys.path.insert(0, str(RAIZ / "ferramentas"))
import estudio as E

MAX_SEGUNDOS = 15 * 60
MAX_POR_PEDIDO = 6              # 17/10/2026 (material-qualquer): um carrossel com 6 assuntos pede um vídeo por assunto


FOTO_EXT = (".jpg", ".jpeg", ".png", ".webp")
MAX_FOTOS = 10                  # por pedido dele (22/10/2026, agente-baixa-foto)
MAX_FOTO_MB = 15


def link_de_fora(link):
    import ipaddress, re
    from urllib.parse import urlparse
    if not re.match(r"^https?://[^\s]+$", link):
        return False
    host = (urlparse(link).hostname or "").lower()
    if not host or host == "localhost" or host.endswith((".local", ".internal", ".localhost")):
        return False
    try:
        ip = ipaddress.ip_address(host)
        return not (ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast)
    except ValueError:
        return True


def e_foto(link):
    """O link é de uma imagem? Pela extensão; sem extensão de imagem, segue como vídeo (o caminho de antes)."""
    from urllib.parse import urlparse
    return urlparse(link).path.lower().endswith(FOTO_EXT)


def foto(num, link, credito=""):
    """22/10/2026 ("aprovo o plano agente-baixa-foto"; ele: "porque foi bloqueado, temos o py para isso e também a segunda
    opção do proxy"; #330: o agente tentou curl, sem permissão): a foto vai para material/fotos/ do vídeo, pelas mesmas
    saídas do vídeo (saida_casa.baixar_url). Só imagem de verdade (o Pillow abre), até MAX_FOTO_MB, até MAX_FOTOS."""
    import hashlib, io
    import saida_casa
    from PIL import Image
    f = E.ler_ficha(num)
    feitas = f.get("fotos_pedido", 0)
    if feitas >= MAX_FOTOS:
        sys.exit(f"não baixo: já foram {feitas} fotos neste pedido (máximo {MAX_FOTOS}); diga a ele o que achou")
    if not link.lower().startswith(("http://", "https://")):
        sys.exit("não baixo: o link tem que começar com http:// ou https://")
    try:
        dados, tipo, saida = saida_casa.baixar_url(link, quem="agente baixa (foto)", limite_mb=MAX_FOTO_MB)
    except RuntimeError as ex:
        sys.exit(f"não baixo agora: {ex}. Diga isso a ele e, se puder, procure a mesma foto em outro site")
    try:
        im = Image.open(io.BytesIO(dados)); im.load()
    except Exception:
        sys.exit(f"não baixo: o link não é uma imagem (veio {tipo or 'outra coisa'}); abra a página com WebFetch e ache o link da foto")
    pasta = E.pasta(num) / "material/fotos"; pasta.mkdir(parents=True, exist_ok=True)
    nome = hashlib.md5(link.encode()).hexdigest()[:10] + ".jpg"
    im.convert("RGB").save(pasta / nome, quality=92)
    (pasta / (nome[:-4] + ".json")).write_text(json.dumps({"link": link, "credito": credito, "saida": saida, "quando": E.agora(),
                                                           "tamanho": list(im.size)}, ensure_ascii=False))
    E.mexe_ficha(num, fotos_pedido=feitas + 1)
    E.evento(num, f"o agente baixou a foto {nome} ({im.size[0]}x{im.size[1]}) de {link[:120]} (saída: {saida})")
    print(f"foto baixada: material/fotos/{nome} ({im.size[0]}x{im.size[1]} px, pela saída {saida}). Abra com Read para ver. "
          f"Na Tela do bloco: \"foto material/fotos/{nome}\" e o crédito ({credito or 'veículo e data'}).")


def main(num, link, credito=""):
    import agente, analisar_reel as A
    link = link.strip().rstrip(".,;)")
    # 25/10/2026 (revisão de segurança): só link de verdade da internet; nada que pareça opção ("--...") nem endereço da
    # própria máquina ou da rede interna (o agente lia o estúdio por 127.0.0.1 sem login)
    if not link_de_fora(link):
        sys.exit(f"não baixo: {link[:80]} não é um link http(s) da internet")
    if e_foto(link):
        return foto(num, link, credito)
    f = E.ler_ficha(num)
    feitos = f.get("baixados_pedido", 0)
    if feitos >= MAX_POR_PEDIDO:
        sys.exit(f"não baixo: já foram {feitos} downloads neste pedido (máximo {MAX_POR_PEDIDO}); diga a ele o que achou e peça o próximo passo")
    r = A.yt([A.ytdlp(), "-q", "--no-warnings", "--skip-download", "--print", "duration", link],
             quem="agente baixa (duração)", capture_output=True, text=True, timeout=120)
    try:
        dur = float(r.stdout.strip().splitlines()[0])
    except (ValueError, IndexError):
        dur = None
    # 20/10/2026 (v2-baixa-pela-casa; #306: o YouTube bloqueou 4 links e a mensagem dizia "não achei vídeo", e o agente
    # desistiu de link bom): bloqueio diz que foi bloqueio
    if dur is None and "bloqueou" in (r.stderr or ""):
        sys.exit(f"não baixo agora: {(r.stderr or '').strip().splitlines()[-1]}. O link parece bom: diga isso a ele, sem dizer que o vídeo não existe")
    if dur is None:      # o downloader não achou vídeo no link: pode ser foto sem extensão no endereço (agente-baixa-foto)
        return foto(num, link, credito)
    if dur > MAX_SEGUNDOS:
        sys.exit(f"não baixo: o vídeo tem {dur / 60:.0f} minutos (máximo 15)")
    E.mexe_ficha(num, baixados_pedido=feitos + 1)
    texto = agente.baixar_video(num, link)
    codigo = A.codigo(link)
    print(texto)
    print(f"\nPara usar um trecho deste vídeo no roteiro: a Fala termina com \"(início-fim material/{codigo})\", em segundos "
          f"de material/{codigo}/palavras.json (o corte vai da primeira à última palavra do trecho).")


if __name__ == "__main__":
    main(int(sys.argv[1]), sys.argv[2], " ".join(sys.argv[3:]))
