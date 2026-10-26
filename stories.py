"""O Story do vídeo publicado (estúdio v2, 22/10/2026, "aprovo o plano publicar-nos-stories"; ele: "e os stories, está
publicando o que a gente publica?").

Depois do Reel, o servidor chama publicar(num): os primeiros 15 s do vídeo final, com a faixa "CHECAGEM NOVA NO PERFIL",
viram um Story do @newsbr360 pela API oficial (media_type=STORIES; a API não compartilha o Reel no Story nem põe
figurinha de link, documentação da Meta lida em 22/10/2026). O vídeo sobe para um link público da fal, como o do Reel.
Travas: o acesso tem que ser da @newsbr360 (como no publicador), um Story por vídeo (a ficha guarda story) e, se falhar,
o chat do vídeo diz o motivo.

  python3 stories.py <número> --ensaio   faz o recorte e o contêiner na Meta, sem publicar (confere a permissão)
"""
import json, subprocess, sys, time, urllib.error, urllib.parse, urllib.request

import estudio as E

GRAPH = "https://graph.facebook.com/v21.0"      # a mesma versão do publicador
ACESSO = E.RAIZ / "publicador/.env.instagram"
CONTA = "newsbr360"
SEGUNDOS = 15
FONTE = "/usr/share/fonts/truetype/montserrat/Montserrat-ExtraBold.ttf"
FAIXA = "CHECAGEM NOVA NO PERFIL"
FAIXA_Y, FAIXA_ALTO = 1500, 120                  # dentro da zona que o Story não cobre (acima da barra de resposta)


def acesso():
    d = dict(l.split("=", 1) for l in ACESSO.read_text().splitlines() if "=" in l and not l.startswith("#"))
    return d["IG_TOKEN"].strip(), d["IG_ACCOUNT_ID"].strip()


def meta(metodo, caminho, token, **campos):
    campos["access_token"] = token
    dados = urllib.parse.urlencode(campos)
    req = (urllib.request.Request(f"{GRAPH}/{caminho}?{dados}") if metodo == "GET"
           else urllib.request.Request(f"{GRAPH}/{caminho}", data=dados.encode(), method="POST"))
    try:
        return json.load(urllib.request.urlopen(req, timeout=120))
    except urllib.error.HTTPError as e:
        corpo = e.read().decode(errors="replace")
        try:
            corpo = json.loads(corpo)["error"]["message"]
        except Exception:
            pass
        raise RuntimeError(f"a Meta respondeu {e.code}: {str(corpo)[:240]}")


def recorte(num):
    """publicacao/story.mp4: os primeiros SEGUNDOS do vídeo final, com a faixa e o fim suave."""
    p = E.pasta(num) / "publicacao"
    saida = p / "story.mp4"
    vf = (f"drawbox=x=60:y={FAIXA_Y}:w=960:h={FAIXA_ALTO}:color=0xFFC933@1:t=fill,"
          f"drawtext=fontfile={FONTE}:text='{FAIXA}':fontcolor=0x0A1748:fontsize=56:x=(w-text_w)/2:"
          f"y={FAIXA_Y}+({FAIXA_ALTO}-text_h)/2,fade=t=out:st={SEGUNDOS - 0.6}:d=0.6")   # "d=.6" o ffmpeg não aceita
    subprocess.run(["ffmpeg", "-nostdin", "-v", "error", "-y", "-i", str(p / "final.mp4"), "-t", str(SEGUNDOS), "-vf", vf,
                    "-af", f"afade=t=out:st={SEGUNDOS - 1}:d=1", "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
                    "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "128k", "-movflags", "+faststart", str(saida)], check=True)
    return saida


def publicar(num, ensaio=False):
    """Publica o Story (uma vez por vídeo). ensaio: para no contêiner pronto, sem publicar."""
    f = E.ler_ficha(num)
    if f.get("story") and not ensaio:
        return f["story"]
    if not (f.get("publicado") or {}).get("instagram"):
        raise RuntimeError("o vídeo ainda não foi publicado no Instagram")
    try:
        token, conta = acesso()
        nome = meta("GET", conta, token, fields="username").get("username", "")
        if nome.lower() != CONTA:
            raise RuntimeError(f"o acesso é de @{nome}, não da @{CONTA}: nada foi enviado")
        clipe = recorte(num)
        sys.path.insert(0, str(E.RAIZ / "ferramentas"))
        import fal_cliente as fal
        url = fal.subir(clipe, fal.chave())
        cont = meta("POST", f"{conta}/media", token, media_type="STORIES", video_url=url)["id"]
        for _ in range(30):
            time.sleep(10)
            st = meta("GET", cont, token, fields="status_code,status")
            if st.get("status_code") == "FINISHED":
                break
            if st.get("status_code") == "ERROR":
                raise RuntimeError(f"o Instagram recusou o Story: {st.get('status')}")
        else:
            raise RuntimeError("o Instagram não terminou de processar o Story em 5 min")
        if ensaio:
            E.evento(num, f"story: ensaio ok, contêiner {cont} pronto e não publicado")
            return {"ensaio": True, "conteiner": cont}
        mid = meta("POST", f"{conta}/media_publish", token, creation_id=cont)["id"]
    except Exception as ex:
        E.evento(num, f"story: não saiu: {str(ex)[:200]}")
        if not ensaio:
            E.chat_add(num, "sistema", f"O Story do Instagram não saiu ({str(ex)[:200]}). O Reel continua publicado.")
        raise
    reg = {"quando": E.agora(), "id": mid}
    E.mexe_ficha(num, story=reg)
    E.chat_add(num, "sistema", "Story publicado no @newsbr360: os primeiros 15 s do vídeo com a faixa \"Checagem nova no perfil\".")
    E.evento(num, f"story: publicado ({mid})")
    return reg


if __name__ == "__main__":
    print(json.dumps(publicar(int(sys.argv[1]), ensaio="--ensaio" in sys.argv), ensure_ascii=False))
