#!/usr/bin/env python3
"""
Publica um Reel da página @newsbr360 no Instagram, pela API oficial da Meta (06/10/2026).
Cópia do publicador dos Farrapos (editor_ia/farrapos/publicar-instagram.py), com acesso próprio
e as regras de texto desta página. Alexandre: "pode seguir com o SDrMorini" (o app que já publica
pela KITEBIZ; o token desta página é outro, de usuário, gerado por ele no Explorador da Graph API).

  python3 publicar-instagram.py VIDEO --legenda legenda.txt --conta newsbr360 \
      [--capa-imagem capa.jpg] [--simular]

  --facebook  depois do Instagram, publica o mesmo MP4 com a mesma legenda como reel na pagina
              News BR360 do Facebook (08/10/2026, "aprovo o plano"; reel de pagina aceita 3 a 90 s).
  --x         por ultimo, publica no X (@newsbr360) a copia pelas boas praticas do X e o texto tirado da
              legenda, ate 280 caracteres, sem link e sem hashtag (09/10/2026, "aprovo o plano X").
  --teste     publica como reel de teste (trial reel): aparece primeiro so para quem nao segue; passar para os
              seguidores e' manual, no app (16/10/2026, teste A/B do #126; doc da Meta, IG User Media, trial_params:
              graduation_strategy MANUAL). Sem Facebook e sem X.
  --simular   roda todos os portoes e mostra o que seria enviado, sem falar com a Meta.
  --conta     o @ que voce ESPERA publicar. Se a conta do acesso tiver outro nome,
              para antes de enviar qualquer coisa.
  --conferir-conta   so le o @ da conta do acesso.

Acesso: newsbr360/.env.instagram (so desta pagina, permissao 600), duas linhas:
  IG_TOKEN=...           (token com instagram_content_publish da @newsbr360)
  IG_ACCOUNT_ID=...      (id numerico da conta Instagram profissional @newsbr360)
  FB_PAGE_ID=...         (id da pagina News BR360; o IG_TOKEN e' da pagina, com pages_manage_posts)

Publicar continua exigindo o "pode postar" dele. Sem impulsionar ate 25/10 (Lei 9.504, art. 57-C).
"""
import argparse
import datetime
import json
import pathlib
import re
import subprocess
import sys
import time
import urllib.error
import urllib.parse
import urllib.request

AQUI = pathlib.Path(__file__).resolve().parent
ACESSO = AQUI / ".env.instagram"
REGISTRO = AQUI / "publicacoes.jsonl"
GRAPH = "https://graph.facebook.com/v21.0"


# --- portoes -------------------------------------------------------------------

def portao_legenda(txt):
    """Regras do CLAUDE.md que valem para texto publicado (as dos Farrapos ficaram de fora)."""
    erros = []
    if "—" in txt:
        erros.append("tem travessao longo (regra: texto publicado usa ponto ou virgula)")
    for proibido in ("claude", "anthropic", "openai", "chatgpt", "lovable"):
        if proibido in txt.lower():
            erros.append(f"cita '{proibido}' (autoria e' da KITEBIZ)")
    if len(txt) > 2200:
        erros.append(f"{len(txt)} caracteres; o Instagram aceita 2200")
    # 16/10/2026 (legenda-sem-criador; ele: "coloca como regra não citar @ que não seja da newsbr360"): no #126 a
    # legenda automática citou o criador do vídeo que só inspirou a pauta
    for arroba in sorted(set(re.findall(r"@[\w.]*\w", txt))):
        if arroba.lower() != "@newsbr360":
            erros.append(f"cita {arroba}: a legenda só cita a @newsbr360")
    tags = re.findall(r"#\w+", txt)
    # 24/10/2026 (aprender-com-ig-agent, D): o Instagram limitou a 5 hashtags por post em 18/12/2025 (Tecnoblog, Social
    # Samosa); antes o portão só barrava acima de 30
    if len(tags) > 5:
        erros.append(f"{len(tags)} hashtags; o Instagram aceita no máximo 5 por post desde 18/12/2025")
    return erros


def portao_video(v):
    erros = []
    info = json.loads(subprocess.run(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration,size:stream=codec_type,codec_name,width,height",
         "-of", "json", str(v)], capture_output=True, text=True, check=True).stdout)
    fmt = info["format"]
    vid = next((s for s in info["streams"] if s["codec_type"] == "video"), None)
    aud = next((s for s in info["streams"] if s["codec_type"] == "audio"), None)
    dur, mb = float(fmt["duration"]), int(fmt["size"]) / 1e6
    if not vid:
        return ["sem faixa de video"], {}
    w, h = vid["width"], vid["height"]
    if abs(w / h - 9 / 16) > 0.01:
        erros.append(f"{w}x{h} nao e' 9:16")
    if vid["codec_name"] != "h264":
        erros.append(f"video em {vid['codec_name']}, o Reels quer h264")
    if not aud:
        erros.append("sem audio")
    elif aud["codec_name"] != "aac":
        erros.append(f"audio em {aud['codec_name']}, o Reels quer aac")
    if not 3 <= dur <= 900:
        erros.append(f"{dur:.1f} s fora de 3 s a 15 min")
    # 100 MB e' o limite que a ferramenta do KITE AI anota; a Meta documenta mais para
    # Reels, mas nao conferi o numero atual, entao fica o menor.
    if mb > 100:
        erros.append(f"{mb:.0f} MB acima de 100 MB")
    # Volume, portao novo em 22/9/2026: o cap. 6 foi ao ar a -17,1 LUFS porque o masterizar.py
    # nao rodou, 3 dB abaixo dos cinco anteriores. A regra 17 existia e era cumprida na mao.
    i = None
    if aud:
        saida = subprocess.run(["ffmpeg", "-i", str(v), "-filter:a", "ebur128=framelog=quiet", "-f", "null", "-"],
                               capture_output=True, text=True).stderr
        m = re.search(r"I:\s+(-?[\d.]+) LUFS", saida[saida.rfind("Summary:"):])
        if not m:
            erros.append("nao consegui medir o volume (ebur128 sem resumo)")
        else:
            i = round(float(m.group(1)), 1)
            if abs(i - (-14.0)) > 1.0:
                erros.append(f"{i} LUFS fora de -14 +-1")
    return erros, {"largura": w, "altura": h, "segundos": round(dur, 2), "mb": round(mb, 1), "lufs": i}


# --- Meta ------------------------------------------------------------------------

def acesso():
    if not ACESSO.exists():
        sys.exit(f"sem {ACESSO}: crie com IG_TOKEN= e IG_ACCOUNT_ID= da @newsbr360")
    d = dict(l.split("=", 1) for l in ACESSO.read_text().splitlines() if "=" in l and not l.startswith("#"))
    t, c = d.get("IG_TOKEN", "").strip(), d.get("IG_ACCOUNT_ID", "").strip()
    if not (t and c):
        sys.exit(f"{ACESSO.name} precisa de IG_TOKEN e IG_ACCOUNT_ID")
    return t, c


def pagina_facebook():
    d = dict(l.split("=", 1) for l in ACESSO.read_text().splitlines() if "=" in l and not l.startswith("#"))
    p = d.get("FB_PAGE_ID", "").strip()
    if not p:
        sys.exit(f"{ACESSO.name} precisa de FB_PAGE_ID para --facebook")
    return p


def publicar_facebook(video, legenda, token, pagina):
    """Reel na pagina do Facebook, em 3 etapas (doc da Meta "Reels Publishing API", atualizada em 30/07/2026):
    abrir sessao, mandar o arquivo para rupload.facebook.com, fechar com video_state=PUBLISHED."""
    vid = meta("POST", f"{pagina}/video_reels", token, upload_phase="start")["video_id"]
    print(f"== Facebook: sessao {vid}; enviando o video", flush=True)
    dados = pathlib.Path(video).read_bytes()
    req = urllib.request.Request(f"https://rupload.facebook.com/video-upload/{GRAPH.rsplit('/', 1)[1]}/{vid}",
                                 data=dados, method="POST",
                                 headers={"Authorization": f"OAuth {token}", "offset": "0",
                                          "file_size": str(len(dados))})
    try:
        r = json.load(urllib.request.urlopen(req, timeout=300))
    except urllib.error.HTTPError as e:
        sys.exit(f"Facebook recusou o envio do video: {e.code} {e.read().decode()[:300]}")
    if not r.get("success"):
        sys.exit(f"Facebook nao confirmou o envio do video: {r}")
    meta("POST", f"{pagina}/video_reels", token, upload_phase="finish", video_id=vid,
         video_state="PUBLISHED", description=legenda)
    for _ in range(30):
        st = meta("GET", vid, token, fields="status")["status"]
        fase = st.get("publishing_phase", {}).get("status")
        erro = st.get("processing_phase", {}).get("error")
        if erro:
            sys.exit(f"Facebook recusou o reel: {erro}")
        if fase == "complete":
            break
        time.sleep(10)
    else:
        print(f"  5 min e o reel {vid} ainda nao aparece como publicado; conferir na pagina")
    url = meta("GET", vid, token, fields="permalink_url").get("permalink_url", "")
    return vid, ("https://www.facebook.com" + url if url.startswith("/") else url)


def meta(metodo, caminho, token, **campos):
    campos["access_token"] = token
    dados = urllib.parse.urlencode(campos).encode()
    if metodo == "GET":
        req = urllib.request.Request(f"{GRAPH}/{caminho}?{dados.decode()}")
    else:
        req = urllib.request.Request(f"{GRAPH}/{caminho}", data=dados, method="POST")
    try:
        return json.load(urllib.request.urlopen(req, timeout=120))
    except urllib.error.HTTPError as e:
        corpo = e.read().decode()
        try:
            corpo = json.loads(corpo)["error"]["message"]
        except Exception:
            pass
        sys.exit(f"Meta respondeu {e.code} em {caminho.split('?')[0]}: {str(corpo)[:300]}")
    except (urllib.error.URLError, TimeoutError, ConnectionError, OSError) as e:
        # 25/10/2026 (revisão de solidez): sem resposta (rede, prazo) também vira SystemExit, para o media_publish
        # conferir o container antes de dar erro (antes só o HTTPError conferia: o Reel podia ter saído)
        sys.exit(f"sem resposta da Meta em {caminho.split('?')[0]}: {str(e)[:200]}")


# --- principal ---------------------------------------------------------------------

def main():
    if sys.argv[1:] == ["--conferir-conta"]:
        # So le o @ da conta do acesso. Nao envia nada.
        token, conta = acesso()
        r = meta("GET", conta, token, fields="username,name,followers_count")
        print(f"o acesso publica em @{r.get('username')} ({r.get('name')}, {r.get('followers_count')} seguidores)")
        return
    a = argparse.ArgumentParser()
    a.add_argument("video")
    a.add_argument("--legenda", required=True, help="arquivo de texto com a descricao")
    a.add_argument("--conta", required=True, help="@ esperado da conta que publica, sem o @")
    a.add_argument("--colaborador", action="append", default=[], help="@ convidado como coautor (ate 3)")
    a.add_argument("--capa-ms", type=int, default=None, help="milissegundo do video usado como capa")
    # cover_url (doc da Meta, 18/9/2026): JPEG, ate 8 MB, 9:16 recomendado; se vier junto com
    # thumb_offset, a Meta usa o cover_url e ignora o outro. Capa do molde: gerar-capa.py.
    a.add_argument("--capa-imagem", default=None, help="JPEG 9:16 ate 8 MB usado como capa (ganha de --capa-ms)")
    a.add_argument("--facebook", action="store_true", help="publica tambem como reel na pagina do Facebook")
    a.add_argument("--x", action="store_true", help="publica tambem no X (@newsbr360), depois do Instagram e do Facebook")
    a.add_argument("--teste", action="store_true", help="reel de teste: so para quem nao segue; passar aos seguidores no app")
    a.add_argument("--simular", action="store_true")
    args = a.parse_args()
    if args.teste and (args.facebook or args.x):
        sys.exit("reel de teste vai so para o Instagram: tire --facebook e --x")

    video = pathlib.Path(args.video)
    legenda = pathlib.Path(args.legenda).read_text().strip()
    colab = [c.lstrip("@") for c in args.colaborador]
    if len(colab) > 3:
        sys.exit("o Instagram aceita ate 3 colaboradores")

    print("== portao da legenda")
    el = portao_legenda(legenda)
    for e in el:
        print("  ERRO", e)
    print("  ok" if not el else "")
    print("== portao do video")
    ev, info = portao_video(video)
    for e in ev:
        print("  ERRO", e)
    print(f"  {info}" + ("  ok" if not ev else ""))
    capa = pathlib.Path(args.capa_imagem) if args.capa_imagem else None
    if capa:
        print("== portao da capa")
        from PIL import Image
        with Image.open(capa) as ci:
            ec = []
            if ci.format != "JPEG":
                ec.append(f"capa em {ci.format}; a Meta pede JPEG")
            if abs(ci.width / ci.height - 9 / 16) > 0.01:
                ec.append(f"capa {ci.width}x{ci.height} nao e' 9:16")
        if capa.stat().st_size > 8e6:
            ec.append("capa acima de 8 MB")
        for e in ec:
            print("  ERRO", e)
        print("  ok" if not ec else "")
        ev = ev + ec
    if args.facebook:
        print("== portao do Facebook")
        ef = [] if info.get("segundos", 0) <= 90 else [f"{info['segundos']} s; reel de pagina aceita ate 90 s"]
        for e in ef:
            print("  ERRO", e)
        print("  ok" if not ef else "")
        ev = ev + ef
    texto_x = ""
    if args.x:
        # 09/10/2026, "aprovo o plano X": texto do X tirado da legenda (ferramentas/x_publicar.texto_x)
        sys.path.insert(0, str(AQUI.parent / "ferramentas"))
        import x_publicar
        print("== portao do X")
        texto_x = x_publicar.texto_x(legenda)
        ex = [f"X: {e}" for e in portao_legenda(texto_x)]
        if not texto_x or len(texto_x) > 280:
            ex.append(f"texto do X com {len(texto_x)} caracteres (1 a 280)")
        if (antes := x_publicar.ja_no_x(video)):
            ex.append(f"este video ja esta no X: {antes}")
        for e in ex:
            print("  ERRO", e)
        print(f"  texto ({len(texto_x)} caracteres): {texto_x}" + ("  ok" if not ex else ""))
        ev = ev + ex
    if el or ev:
        sys.exit("reprovado nos portoes: nada foi enviado")

    pedido = {"media_type": "REELS", "caption": legenda, "share_to_feed": "true"}
    if args.teste:
        pedido["trial_params"] = json.dumps({"graduation_strategy": "MANUAL"})
    if colab:
        pedido["collaborators"] = json.dumps(colab)
    if args.capa_ms is not None:
        pedido["thumb_offset"] = str(args.capa_ms)
    print(f"== pedido: conta @{args.conta.lstrip('@')} | colaboradores {colab or 'nenhum'} | "
          f"capa {capa.name if capa else str(args.capa_ms) + ' ms'} | legenda {len(legenda)} caracteres | "
          f"Facebook {'sim' if args.facebook else 'nao'} | X {'sim' if args.x else 'nao'}"
          + (" | REEL DE TESTE (so quem nao segue; passar aos seguidores no app)" if args.teste else ""))
    if args.simular:
        print("\nSIMULACAO: portoes aprovados, nada enviado a Meta nem a fal.")
        return

    # Trava de duplicata: o atalho do trailer continua no disco depois de publicado.
    if REGISTRO.exists():
        for l in REGISTRO.read_text().splitlines():
            r = json.loads(l)
            if pathlib.Path(r["video"]).name == video.name:
                sys.exit(f"TRAVA: {video.name} ja foi publicado em {r['quando']}: {r['link']}. Nada foi enviado.")

    token, conta = acesso()
    pagina = pagina_facebook() if args.facebook else None
    nome = meta("GET", conta, token, fields="username").get("username", "")
    print(f"== a conta do acesso e' @{nome}")
    if nome.lower() != args.conta.lstrip("@").lower():
        sys.exit(f"TRAVA: esperava @{args.conta.lstrip('@')} e o acesso e' de @{nome}. Nada foi enviado.")

    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent.parent / "ferramentas"))   # fal_cliente (cópia de editor_ia/farrapos, 08/10/2026)
    import fal_cliente as fal
    print("== subindo o video para um link publico (fal)")
    pedido["video_url"] = fal.subir(video, fal.chave())
    if capa:
        pedido["cover_url"] = fal.subir(capa, fal.chave())

    cont = meta("POST", f"{conta}/media", token, **pedido)["id"]
    print(f"== container {cont}; esperando o Instagram processar", flush=True)
    for _ in range(60):
        time.sleep(10)
        st = meta("GET", cont, token, fields="status_code,status").get("status_code")
        if st == "FINISHED":
            break
        if st == "ERROR":
            sys.exit(f"o Instagram recusou o video: {meta('GET', cont, token, fields='status')}")
    else:
        sys.exit(f"10 min e o container {cont} nao ficou pronto; nada foi publicado")

    try:
        mid = meta("POST", f"{conta}/media_publish", token, creation_id=cont)["id"]
    except SystemExit as falha:
        # 18/9/2026, trailer: media_publish devolveu 500 "unexpected error" e o Reel saiu mesmo
        # assim. Antes de dar erro (e de alguem tentar de novo e publicar duas vezes), olha o
        # estado do container.
        # 11/10/2026, Erika: o container ainda não dizia PUBLISHED logo depois do 500 e o Reel saiu; o script parou
        # antes do Facebook e do X. Espera até 1 min pelo estado antes de desistir.
        for _ in range(6):
            if meta("GET", cont, token, fields="status_code").get("status_code") == "PUBLISHED":
                break
            time.sleep(10)
        else:
            raise
        print(f"  a Meta respondeu erro ({falha}), mas o container ficou PUBLISHED: seguindo")
        mid = meta("GET", f"{conta}/media", token, fields="id", limit="1")["data"][0]["id"]
    # 25/10/2026 (revisão de solidez): o link vem DEPOIS do registro. Antes, um erro só no pedido do link (com o Reel já
    # no ar) não gravava a trava nem dizia PUBLICADO: o estúdio mostrava "falhou" e o Publicar de novo postava duas vezes
    try:
        link = meta("GET", mid, token, fields="permalink").get("permalink", "")
    except SystemExit as falha:
        print(f"  o Reel saiu (mídia {mid}), mas o link não veio ({falha}); confira no Instagram")
        link = ""
    with REGISTRO.open("a") as f:
        f.write(json.dumps({"quando": datetime.datetime.now().isoformat(timespec="seconds"),
                            "conta": nome, "video": str(video), "midia": mid, "link": link,
                            "colaboradores": colab, "legenda": legenda, "teste": args.teste}, ensure_ascii=False) + "\n")
    print(f"\nPUBLICADO: {link or f'https://www.instagram.com/{nome}/ (mídia {mid}; o link não veio)'}")
    if colab:
        print(f"Convite de colaboracao enviado a {', '.join('@' + c for c in colab)}: aceitar no app.")
    if pagina:
        # Depois do Instagram: se o Facebook falhar, o Reel ja saiu e esta no registro.
        fid, flink = publicar_facebook(video, legenda, token, pagina)
        with REGISTRO.open("a") as f:
            f.write(json.dumps({"quando": datetime.datetime.now().isoformat(timespec="seconds"), "rede": "facebook",
                                "pagina": pagina, "video": str(video), "midia": fid, "link": flink},
                               ensure_ascii=False) + "\n")
        print(f"PUBLICADO NO FACEBOOK: {flink}")
    if args.x:
        # Por ultimo: se o X falhar, Instagram e Facebook ja sairam e estao no registro.
        try:
            xlink = x_publicar.publica(str(video), texto_x, video.resolve().parent.parent.name)
            print(f"PUBLICADO NO X: {xlink}")
        except (Exception, SystemExit) as e:
            print(f"X FALHOU (Instagram e Facebook ja publicados): {e}")


if __name__ == "__main__":
    main()
