"""O vídeo publicado também no Canal do WhatsApp (estúdio v2, 22/10/2026, "aprovo o plano do canal-whatsapp"; ele: "quero
mandar tudo que publicamos lá e pedir para curtir e compartilhar no canal").

Depois de publicar no Instagram e no Facebook, o servidor chama postar(num): vai ao Canal NewsBR360, pelo GOWA desta VPS
(aparelho "alex", o número pessoal dele, dono do canal), o VÍDEO final com uma frase que resume o vídeo e chama para
assistir, e o link do Reel embaixo (ele, 22/10: "coloca só o link com o preview do post e uma frase resumindo o que tem
no vídeo e instigando a pessoa a clicar e assistir"). A frase é da IA barata (haiku), só com o que está na legenda; sem
resposta dela, vai o primeiro parágrafo da legenda.
22/10/2026, 21:20 ("aprovo o plano canal-com-video"; ele: "o video da jandira que vc mandou vai com previa e até fica
rodando o video"): só o link (POST /send/link) chegou ao canal sem prévia nenhuma (#321, #330, #335); o da Jandira (#327)
tinha saído com o arquivo do vídeo (POST /send/video), e é esse que volta.
Travas: só o canal de CANAIS (nunca pessoa nem grupo), um post por vídeo (a ficha guarda canal_whatsapp) e, se falhar,
o chat do vídeo recebe o texto pronto para ele postar à mão.

  python3 canal.py <número>            mostra o texto que iria ao canal (não envia; a frase chama a IA)
O teste de 22/10 foi no canal "IA para Negócios"; depois ele pediu: "só manda nesse" (o NewsBR360), e o teste saiu daqui.
"""
import base64, json, re, subprocess, sys, urllib.request, uuid
from pathlib import Path

import estudio as E

GOWA = "http://127.0.0.1:8087"
APARELHO = "alex"                               # o número pessoal dele (avisar.py manda por ele para ele mesmo)
CANAL = "120363412418697706@newsletter"         # NewsBR360 (dono: o aparelho alex; 26 inscritos em 22/10/2026)
CANAIS = {CANAL: "NewsBR360"}                   # o único destino (ele, 22/10/2026: "só manda nesse")
ENV = Path("/etc/kitebiz/newsbr360.env")
PEDIR_FRASE = """Escreva UMA frase, de 12 a 28 palavras, em português do Brasil, para o post de um canal de WhatsApp que leva
ao vídeo abaixo. Ela resume o que o vídeo mostra e instiga a pessoa a clicar e assistir (curiosidade: o que a gente
conferiu e que o resultado surpreende), sem contar o veredito inteiro. Use só o que está no texto abaixo: nada de fato,
número ou nome novo. Sem travessão longo, sem hashtag, sem aspas em volta da frase, no máximo um emoji no fim.
Responda só a frase.

Título do vídeo: {titulo}
Legenda do post:
{legenda}"""


def credencial():
    for l in ENV.read_text().splitlines():
        if l.startswith("GOWA_AUTH="):
            return l.split("=", 1)[1].strip()
    raise RuntimeError("sem GOWA_AUTH em /etc/kitebiz/newsbr360.env")


def frase(num):
    """A frase de chamada (haiku, sem ferramentas). Sem resposta boa: o primeiro parágrafo da legenda."""
    f = E.ler_ficha(num)
    leg = (E.pasta(num) / "publicacao/legenda.txt").read_text()
    reserva = next((p.strip() for p in leg.split("\n\n") if p.strip() and not p.strip().startswith(("📌", "#", "Fontes:"))), "")
    import ia                                 # 25/10/2026: a chamada de IA de um lugar só (ia.py)
    r, _ = ia.chamar(PEDIR_FRASE.format(titulo=f.get("titulo") or "", legenda=leg[:4000]), "frase do canal do WhatsApp",
                     "haiku", num=num, limite=120)
    t = " ".join(r.split()).strip().strip('"“”')
    if not (8 <= len(t.split()) <= 40) or "—" in t:
        return reserva
    return t


def texto(num, com_frase=None):
    """O texto do post, embaixo do vídeo: a frase e o link do Reel (para curtir e compartilhar no Instagram)."""
    link = (E.ler_ficha(num).get("publicado") or {}).get("instagram")
    if not link:
        raise RuntimeError("o vídeo ainda não tem o link do Instagram (publique primeiro)")
    return f"{com_frase if com_frase is not None else frase(num)}\n\n👉 {link}"


def _mandar(destino, video, legenda):
    """POST multipart /send/video do GOWA, com o arquivo do vídeo final (sem precisar de endereço público)."""
    limite = "----estudio" + uuid.uuid4().hex
    campos = {"phone": destino, "caption": legenda, "compress": "false", "view_once": "false"}
    corpo = b"".join(f"--{limite}\r\nContent-Disposition: form-data; name=\"{k}\"\r\n\r\n{v}\r\n".encode() for k, v in campos.items())
    corpo += (f"--{limite}\r\nContent-Disposition: form-data; name=\"video\"; filename=\"video.mp4\"\r\n"
              f"Content-Type: video/mp4\r\n\r\n").encode() + Path(video).read_bytes() + f"\r\n--{limite}--\r\n".encode()
    req = urllib.request.Request(f"{GOWA}/send/video", data=corpo, method="POST", headers={
        "Content-Type": f"multipart/form-data; boundary={limite}", "X-Device-Id": APARELHO,
        "Authorization": "Basic " + base64.b64encode(credencial().encode()).decode()})
    try:
        with urllib.request.urlopen(req, timeout=300) as r:
            resp = json.loads(r.read())
    except urllib.error.HTTPError as e:
        resp = {"code": f"HTTP {e.code}", "message": e.read().decode(errors="replace")[:300]}
    if resp.get("code") != "SUCCESS":
        raise RuntimeError(f"o WhatsApp não aceitou: {resp.get('code')} {str(resp.get('message'))[:200]}")
    return resp.get("results") or {}


def _enviar(canal, video, legenda):
    if canal not in CANAIS:
        raise RuntimeError(f"canal fora da lista permitida: {canal}")
    return _mandar(canal, video, legenda)


def postar(num, canal=CANAL):
    """Posta o vídeo publicado no canal, uma vez por vídeo. Falhou: o chat recebe o texto pronto."""
    f = E.ler_ficha(num)
    feito = f.get("canal_whatsapp") or {}
    if feito.get("canal") == canal:
        return feito                                     # já foi: nunca repete (mesmo publicando de novo)
    legenda = ""
    try:
        legenda = texto(num)
        video = E.pasta(num) / "publicacao/final.mp4"
        if not video.exists():
            raise RuntimeError("falta publicacao/final.mp4")
        r = _enviar(canal, video, legenda)
    except Exception as ex:
        E.evento(num, f"canal do WhatsApp ({CANAIS.get(canal, canal)}): não saiu: {str(ex)[:200]}")
        E.chat_add(num, "sistema", f"O post no Canal NewsBR360 do WhatsApp não saiu ({str(ex)[:160]})."
                   + (f" Texto pronto para postar à mão:\n\n{legenda}" if legenda else ""))
        raise
    reg = {"quando": E.agora(), "canal": canal, "nome": CANAIS[canal], "id": r.get("message_id"), "texto": legenda}
    E.mexe_ficha(num, canal_whatsapp=reg)
    E.chat_add(num, "sistema", f"Postado também no Canal NewsBR360 do WhatsApp:\n\n{legenda}")
    E.evento(num, f"canal do WhatsApp ({CANAIS[canal]}): postado")
    return reg


if __name__ == "__main__":
    print(texto(int(sys.argv[1])))
