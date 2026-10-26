#!/usr/bin/env python3
"""Saída pela casa do Alexandre no estúdio v2 (20/10/2026, "aprovo o plano v2-baixa-pela-casa"; ele: "tem que resolver, o
estúdio antigo não existe mais"). Veio da v1 (ferramentas/saida_casa.py e youtube.py de 19/10, "aprovo o plano
saida-pelo-pi"), agora sem nada da pasta da v1.

O YouTube recusa endereço de data center ("Sign in to confirm you're not a bot"). Um Raspberry Pi na casa dele mantém um
túnel até aqui: na VPS ele aparece em 127.0.0.1:8898 (~/.config/kitebiz/saida-casa). Todo yt-dlp do v2 passa por yt():
  1. a casa, quando responde de ponta a ponta;
  2. a IPRoyal (paga por GB; ~/.config/kitebiz/youtube-proxy), até 2 endereços, enquanto o mês não passar de 1 GB;
  3. direto da VPS, por último.
Por onde saiu fica em saida-uso.jsonl; o que baixou (MB e saída) em youtube-uso.jsonl, que continua o da v1 (o teto do
mês soma os dois). Falhou tudo por bloqueio: o erro diz "o YouTube bloqueou", e não "não achei vídeo".

  python3 ferramentas/saida_casa.py         diz se a saída pela casa está no ar e por qual endereço ela sai
  python3 ferramentas/saida_casa.py uso     quanto a IPRoyal e a casa baixaram no mês
"""
import datetime, json, re, secrets, socket, subprocess, sys, time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
ENDERECO = Path.home() / ".config/kitebiz/saida-casa"
LINHA = Path.home() / ".config/kitebiz/youtube-proxy"
REGISTRO = RAIZ / "saida-uso.jsonl"
USO = RAIZ / "youtube-uso.jsonl"
TETO_MES_MB = 1024
TESTE = "www.youtube.com:443"
# o vídeo não existe para ninguém: não adianta trocar de saída
INDISPONIVEL = re.compile(r"Private video|privado|Video unavailable|indispon[ií]vel|removed|removido|members-only|membros|"
                          r"confirm your age|confirmar sua idade|Unsupported URL|404", re.I)
BLOQUEIO = re.compile(r"not a bot|não é um bot|Sign in|Faça login|429|403|50[234]|timed? ?out|Connection|reset|Tunnel|"
                      r"proxy|login required|rate.?limit", re.I)


def endereco():
    if not ENDERECO.exists():
        return None
    host, porta = ENDERECO.read_text().strip().rsplit(":", 1)
    return host, int(porta)


def no_ar(espera=4):
    """(host, porta) da saída pela casa se ela responde de ponta a ponta (túnel, repassador e internet de casa); senão None.
    Só abrir a porta não basta: o túnel pode estar de pé com o repassador do Pi parado."""
    e = endereco()
    if not e:
        return None
    try:
        with socket.create_connection(e, timeout=espera) as s:
            s.settimeout(espera)
            s.sendall(f"CONNECT {TESTE} HTTP/1.1\r\nHost: {TESTE}\r\n\r\n".encode())
            resposta = s.recv(200)
    except OSError:
        return None
    return e if resposta.split(b"\r\n", 1)[0].split()[1:2] == [b"200"] else None


def _linha(arq, d):
    with arq.open("a") as f:
        f.write(json.dumps({"quando": datetime.datetime.now().isoformat(timespec="seconds"), **d}, ensure_ascii=False) + "\n")


def anotar(quem, saida, detalhe=""):
    _linha(REGISTRO, {"quem": quem, "saida": saida, "detalhe": detalhe})


def gasto_mes(saida="iproyal"):
    """MB do mês por uma saída. O teto vale só para a IPRoyal (19/10/2026, ele: "pode contar so o que sai pela iproyal no
    teto"). Linha antiga, sem "saida", foi pela IPRoyal."""
    mes = datetime.date.today().strftime("%Y-%m")
    if not USO.exists():
        return 0.0
    linhas = [json.loads(l) for l in USO.read_text().splitlines() if l.strip()]
    return sum(u.get("mb", 0) for u in linhas if u.get("quando", "").startswith(mes) and u.get("saida", "iproyal") == saida)


def iproyal():
    """Endereço novo a cada chamada, no Brasil; None sem a linha da IPRoyal."""
    if not LINHA.exists():
        return None
    host, porta, usuario, senha = LINHA.read_text().strip().split(":", 3)
    base = senha.split("_session-")[0].split("_country-")[0]
    return f"http://{usuario}:{base}_country-br_session-{secrets.token_hex(4)}_lifetime-30m@{host}:{porta}"


def _pasta_de_saida(cmd):
    if "-o" in cmd and cmd.index("-o") + 1 < len(cmd):
        return Path(cmd[cmd.index("-o") + 1]).parent
    return None


def _mb_novos(pasta, desde):
    if not pasta or not pasta.is_dir():
        return 0.0
    return sum(f.stat().st_size for f in pasta.iterdir() if f.is_file() and f.stat().st_mtime >= desde) / 1e6


# 24/10/2026 ("autorizo e isso tem que ficar como regra, tentar mais vezes até conseguir baixar ou avisar que tentou x
# vezes e não conseguiu"; #373: o reel De3F49etFbn só abre logado): fora da VPS, o último caminho é o login do Instagram
# do Chrome dele (yt-dlp --cookies-from-browser chrome; o macOS pode pedir, uma vez, para liberar a senha guardada do
# Chrome). Tudo o que falhou por bloqueio ou login tenta de novo numa segunda rodada, depois de PAUSA s.
RODADAS, PAUSA = 2, 15
NA_VPS = socket.gethostname() == "kitebiz-prod"        # o mesmo teste do estudio.NA_VPS
LOGIN = re.compile(r"logged.?in|log ?in|login|cookies|sign in|requires? authentication|age-restricted", re.I)


def _tem_chrome():
    import os
    return os.path.exists("/Applications/Google Chrome.app") or bool(__import__("shutil").which("google-chrome"))


def yt(cmd, quem="v2", **kw):
    """Roda o yt-dlp (cmd = [yt-dlp, args..., link], os mesmos argumentos de subprocess.run) pela casa, pela IPRoyal,
    direto e, fora da VPS, com o login do Chrome dele, nessa ordem, em até RODADAS rodadas; devolve o CompletedProcess da
    tentativa que deu certo (ou o da última, com o erro explicado: quantas tentativas, por quais caminhos e por quê)."""
    check = kw.pop("check", False)
    timeout = kw.get("timeout")
    kw.setdefault("capture_output", True)
    kw.setdefault("text", True)
    casa = no_ar()
    tentativas = []
    if casa:
        tentativas.append(("casa", f"http://{casa[0]}:{casa[1]}"))
    else:
        anotar(quem, "iproyal", "casa fora do ar" if endereco() else "casa não configurada")
    if gasto_mes() < TETO_MES_MB and LINHA.exists():
        tentativas += [("iproyal", None), ("iproyal", None)]
    tentativas.append(("direto", None))
    if not NA_VPS and _tem_chrome():
        tentativas.append(("login do Chrome", None))
    pasta, motivos, r = _pasta_de_saida(cmd), [], None
    feitas, pular = 0, False
    rodada_de = list(tentativas)
    for rodada in range(RODADAS):
        if rodada:
            # a segunda rodada só refaz o que falhou por bloqueio, login ou tempo (vídeo que não existe não volta)
            rodada_de = [x for x in tentativas if any(m.startswith(x[0] + ":") and (BLOQUEIO.search(m) or LOGIN.search(m) or "passou de" in m) for m in motivos)]
            if not rodada_de or pular:
                break
            time.sleep(PAUSA)
        for saida, proxy in rodada_de:
            r_ok, r, pular = _tenta(cmd, kw, quem, saida, proxy, pasta, motivos, timeout, r)
            feitas += 1
            if r_ok:
                return r
            if pular:
                break
    if r is not None and r.returncode and motivos:
        caminhos = ", ".join(dict.fromkeys(m.split(":")[0] for m in motivos))
        explica = (f"tentei {feitas} vez(es), por {caminhos}, e não consegui"
                   + (" (o post só abre logado)" if any(LOGIN.search(m) for m in motivos) else "")
                   + ": " + "; ".join(motivos[-6:]))
        if gasto_mes() >= TETO_MES_MB:
            explica += f"; a IPRoyal já passou do teto do mês ({TETO_MES_MB} MB)"
        if not casa and endereco():
            explica += "; a saída pela casa (o Pi) está fora do ar"
        r.stderr = ((r.stderr if isinstance(r.stderr, str) else "") or "") + "\n" + explica
    if r is None:
        raise subprocess.TimeoutExpired(cmd, timeout)
    r.args = cmd
    if check and r.returncode:
        raise subprocess.CalledProcessError(r.returncode, cmd, r.stdout, r.stderr)
    return r


def _tenta(cmd, kw, quem, saida, proxy, pasta, motivos, timeout, r):
    """Uma tentativa por uma saída. Devolve (deu_certo, r, pular_o_resto)."""
    if True:
        if saida == "iproyal":
            proxy = iproyal()
        t0 = time.time()
        extra = ["--cookies-from-browser", "chrome"] if saida == "login do Chrome" else []
        # 25/10/2026 (revisão de segurança): o link vem do chat e do agente; sem "--" um "link" que começa com "-" vira
        # opção do yt-dlp (há opções que rodam comandos), e o yt-dlp lia um yt-dlp.conf da pasta do vídeo. Agora o link
        # vai depois de "--" e a configuração de fora é ignorada
        resto = list(cmd[1:])
        if resto and isinstance(resto[-1], str) and not resto[-1].startswith("-"):
            resto = resto[:-1] + ["--", resto[-1]]
        args = [cmd[0], "--ignore-config", *(["--proxy", proxy] if proxy else []), *extra, *resto]
        try:
            r = subprocess.run(args, **kw)
        except subprocess.TimeoutExpired:
            motivos.append(f"{saida}: passou de {timeout} s")
            anotar(quem, saida, "tempo esgotado")
            return False, r, False
        erro = r.stderr if isinstance(r.stderr, str) else (r.stderr or b"").decode(errors="ignore")
        if r.returncode == 0:
            mb = round(_mb_novos(pasta, t0 - 1) * 1.2, 2)          # 1,2: como na v1 (cabeçalhos e o que não ficou)
            if saida != "casa" or mb:
                _linha(USO, {"quem": quem, "saida": saida, "mb": mb, "link": cmd[-1]})
            if saida != "casa":
                anotar(quem, saida, f"deu certo ({mb} MB)")
            r.args = cmd
            return True, r, False
        ultima = (erro.strip().splitlines() or ["?"])[-1][:200]
        if INDISPONIVEL.search(erro) and not BLOQUEIO.search(erro) and not LOGIN.search(erro):
            motivos.append(f"{saida}: {ultima}")
            return False, r, True                                   # o vídeo não existe para ninguém
        motivos.append(f"{saida}: {ultima}")
        anotar(quem, saida, "falhou: " + ultima)
        return False, r, False


def baixar_url(url, quem="v2", limite_mb=15, timeout=60):
    """22/10/2026 ("aprovo o plano agente-baixa-foto"; #330: o agente tentou curl para baixar foto, sem permissão, e o
    baixar.py só aceitava vídeo): baixa UM arquivo (a foto) pela casa, pela IPRoyal ou direto, nessa ordem, como o yt().
    Devolve (bytes, tipo do conteúdo, saída). Para no limite_mb (não baixa arquivo gigante)."""
    import urllib.request
    casa = no_ar()
    tentativas = ([("casa", f"http://{casa[0]}:{casa[1]}")] if casa else [])
    if gasto_mes() < TETO_MES_MB and LINHA.exists():
        tentativas.append(("iproyal", None))
    tentativas.append(("direto", None))
    motivos = []
    for saida, proxy in tentativas:
        if saida == "iproyal":
            proxy = iproyal()
        abre = urllib.request.build_opener(urllib.request.ProxyHandler({"http": proxy, "https": proxy} if proxy else {}))
        # a Wikimedia exige um nome de programa com contato e dá 429 a quem se diz navegador (teste de 22/10/2026)
        wiki = "wikimedia.org" in url or "wikipedia.org" in url
        ua = ("NewsBR360-estudio/1.0 (https://newsbr360.com) python-urllib" if wiki else
              "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15")
        req = urllib.request.Request(url, headers={"User-Agent": ua, "Accept": "image/*,*/*;q=0.8"})
        try:
            with abre.open(req, timeout=timeout) as r:
                tipo = r.headers.get("Content-Type", "")
                dados = r.read(limite_mb * 1024 * 1024 + 1)
        except Exception as ex:
            motivos.append(f"{saida}: {str(ex)[:120]}")
            anotar(quem, saida, f"foto falhou: {str(ex)[:120]}")
            continue
        if len(dados) > limite_mb * 1024 * 1024:
            raise RuntimeError(f"o arquivo passa de {limite_mb} MB")
        if saida != "casa":
            _linha(USO, {"quem": quem, "saida": saida, "mb": round(len(dados) / 1e6 * 1.2, 2), "link": url})
            anotar(quem, saida, f"foto deu certo ({len(dados) / 1e6:.1f} MB)")
        return dados, tipo, saida
    raise RuntimeError("a foto não baixou em nenhuma saída (" + "; ".join(motivos) + ")")


if __name__ == "__main__":
    if sys.argv[1:2] == ["uso"]:
        print(f"IPRoyal: {gasto_mes():.1f} MB no mês (teto {TETO_MES_MB} MB) · casa (Pi): {gasto_mes('casa'):.1f} MB (sem teto)")
        raise SystemExit
    e = no_ar()
    if not e:
        print("saída pela casa FORA DO AR" if endereco() else f"saída pela casa não configurada (falta {ENDERECO})")
        raise SystemExit(1)
    import urllib.request
    t = time.time()
    abre = urllib.request.build_opener(urllib.request.ProxyHandler({"https": f"http://{e[0]}:{e[1]}"}))
    ip = abre.open("https://api.ipify.org", timeout=15).read().decode()
    print(f"saída pela casa no ar: sai como {ip} ({time.time() - t:.1f} s)")
