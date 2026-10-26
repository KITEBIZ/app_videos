#!/usr/bin/env python3
"""Vigia de saúde do estúdio v2 (20/10/2026, ele: "pode fazer as duas"; veio da v1, ferramentas/saude.py de 09/10).
A cada 30 min (cron do alex na VPS 204), sem IA, confere o que o v2 usa e, quando um item fica vermelho, manda UMA linha
no WhatsApp dele (ferramentas/avisar.py), no máximo 1 aviso por item a cada 6 h.

  estúdio v2 no ar · robô de respostas a comentários · backup do dia · Google (voz) · fal com saldo · Groq com o modelo
  da transcrição · Instagram responde com o token · WhatsApp conectado · disco

Ficaram de fora os itens só da v1: a sessão do Claude no tmux, o X, a biblioteca no GitHub, o painel antigo e o Chrome
logado no Instagram. A saída pela casa (o Pi) voltou em 20/10/2026 (v2-baixa-pela-casa): o v2 passou a baixar por ela.

  python3 ferramentas/saude.py              confere, grava saude.json e avisa
  python3 ferramentas/saude.py --simular    confere e mostra; não grava estado nem avisa
"""
import json, os, shutil, subprocess, sys, time, urllib.error, urllib.request
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "ferramentas"))
ENV = Path("/etc/kitebiz/newsbr360.env")
SAIDA = RAIZ / "saude.json"
ESTADO = RAIZ / "saude-avisos.json"
COMENTARIOS = RAIZ / "publicador/comentarios"
BACKUP = Path.home() / "estudio-v2-web/ultimo-backup.txt"      # o estudio-v2-backup.sh (root) grava a data aqui
REAVISO_S = 6 * 3600
MODELO_GROQ = "whisper-large-v3"            # o mesmo de ferramentas/transcrever.py
FAL_MINIMO = 2.0                            # US$
DISCO_MIN_GB = 15                           # 25/10/2026 (revisão): por GB livres; a % não descontava a reserva do root
                                            # (85% contra os 89% do df) e só avisaria com ~7 GB, menos que um backup
BACKUP_MAX_H = 30


def chaves():
    k = dict(os.environ)
    if ENV.exists():
        for l in ENV.read_text().splitlines():
            if "=" in l and not l.startswith("#"):
                a, b = l.split("=", 1)
                k.setdefault(a.strip(), b.strip())
    return k


def http(url, headers=None, dados=None, timeout=20):
    req = urllib.request.Request(url, headers=headers or {}, data=json.dumps(dados).encode() if dados else None)
    if dados:
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read() or b"{}")


def erro_http(e):
    if isinstance(e, urllib.error.HTTPError):
        return f"HTTP {e.code}: {e.read()[:160].decode(errors='ignore')}"
    return str(e)[:160]


# ---- cada conferência devolve (ok, detalhe) ----
def estudio(k):
    # 20/10/2026 (achado v2-baixa-pela-casa.1, alarme falso às 13:30): no cron o systemctl --user não acha o serviço sem
    # o XDG_RUNTIME_DIR ("serviço ?"); e /entrar de 127.0.0.1 dá 404 (a entrada com Face ID não vale dentro da VPS): a tela é "/"
    amb = dict(os.environ, XDG_RUNTIME_DIR=os.environ.get("XDG_RUNTIME_DIR") or f"/run/user/{os.getuid()}")
    ativo = subprocess.run(["systemctl", "--user", "is-active", "newsbr360-estudio-v2"], capture_output=True, text=True, env=amb).stdout.strip()
    try:
        with urllib.request.urlopen("http://127.0.0.1:4400/", timeout=10) as r:
            tela = r.status == 200
    except Exception:
        tela = False
    return ativo == "active" and tela, "no ar" if ativo == "active" and tela else f"serviço {ativo or '?'}, tela {'ok' if tela else 'não abre'}"


def comentarios(k):
    """20/10 (o robô veio para o v2 com volume maior): vermelho se o freio desligou o robô ou se a última rodada quebrou."""
    parado = COMENTARIOS / "lotes.DESLIGADO"
    if parado.exists():
        return False, "desligado: " + parado.read_text().strip()[:120]
    log = COMENTARIOS / "lotes.log"
    ult = log.read_text().strip().splitlines()[-1] if log.exists() and log.stat().st_size else ""
    if "Error" in ult or "falhou" in ult:
        return False, "a última rodada quebrou: " + ult[-140:]
    return True, "respondendo"


def backup(k):
    if not BACKUP.exists():
        return False, "nenhum backup registrado"
    horas = (time.time() - BACKUP.stat().st_mtime) / 3600
    return horas <= BACKUP_MAX_H, f"último há {horas:.0f} h" + ("" if horas <= BACKUP_MAX_H else " (devia ser todo dia às 03:50)")


def google(k):
    chave = k.get("GEMINI_API_KEY")
    if not chave:
        return False, "sem GEMINI_API_KEY"
    try:   # gerar 1 token num modelo de texto: é o que acusa "crédito acabou" (402), como em 08/10
        ms = http(f"https://generativelanguage.googleapis.com/v1beta/models?key={chave}&pageSize=200").get("models", [])
        txt = next((m["name"] for m in ms if "flash" in m["name"] and not any(x in m["name"] for x in ("tts", "image", "live", "audio"))
                    and "generateContent" in m.get("supportedGenerationMethods", [])), None)
        if not txt:
            return False, "nenhum modelo flash de texto na lista"
        http(f"https://generativelanguage.googleapis.com/v1beta/{txt}:generateContent?key={chave}",
             dados={"contents": [{"parts": [{"text": "ok"}]}], "generationConfig": {"maxOutputTokens": 1}})
        return True, f"gera ({txt.split('/')[-1]})"
    except Exception as e:
        return False, erro_http(e)


def fal(k):
    try:
        import fal_cliente
        s = fal_cliente.saldo(k.get("FAL_KEY", ""))
        return s >= FAL_MINIMO, f"saldo US$ {s:.2f}" + ("" if s >= FAL_MINIMO else f" (abaixo de {FAL_MINIMO:.0f})")
    except Exception as e:
        return False, erro_http(e)


def groq(k):
    try:
        ms = [m["id"] for m in http("https://api.groq.com/openai/v1/models",
                                    headers={"Authorization": f"Bearer {k.get('GROQ_API_KEY', '')}", "User-Agent": "kitebiz-estudio"})["data"]]
        return MODELO_GROQ in ms, f"{MODELO_GROQ} {'existe' if MODELO_GROQ in ms else 'SUMIU da lista'}"
    except Exception as e:
        return False, erro_http(e)


def instagram(k):
    try:
        sys.path.insert(0, str(RAIZ / "publicador"))
        import comentarios as c
        t, ig = c.acesso()
        n = c.get(ig, t, fields="followers_count")["followers_count"]
        return True, f"token responde ({n} seguidores)"
    except Exception as e:
        return False, erro_http(e)


def whatsapp(k):
    try:
        import base64
        cred = base64.b64encode(k.get("GOWA_AUTH", "").encode()).decode()
        ds = http("http://127.0.0.1:8087/devices", headers={"Authorization": f"Basic {cred}"}).get("results") or []
        on = [x for x in ds if x.get("state") == "logged_in"]
        return bool(on), "conectado" if on else f"{len(ds)} aparelho(s), nenhum logado"
    except Exception as e:
        return False, erro_http(e)


def disco(k):
    u = shutil.disk_usage("/srv")
    livre = u.free / 1e9
    return livre >= DISCO_MIN_GB, f"{livre:.0f} GB livres"


def videos_parados(k):
    """25/10/2026 (revisão de confiabilidade: ninguém ficava sabendo quando um vídeo parava): os vídeos que pararam
    (passo do tipo "parou" no mapa) nas últimas 2 h."""
    sys.path.insert(0, str(RAIZ))
    import estudio as E, passos as M
    limite = datetime.fromtimestamp(time.time() - 2 * 3600).isoformat(timespec="seconds")
    parados = []
    for n in E.numeros():
        f = E.ler_ficha(n)
        if (M.PASSOS.get(f.get("passo")) or {}).get("tipo") == M.P and str(f.get("atualizado") or "") >= limite:
            parados.append(f"#{n} {f.get('passo')}" + (f" ({str(f.get('erro'))[:60]})" if f.get("erro") else ""))
    return not parados, "; ".join(parados[:4]) if parados else "nenhum parado nas últimas 2 h"


def erros_do_servidor(k):
    """25/10/2026: Traceback no registro do estúdio na última meia hora (antes só ficavam no journal, entre milhares de
    linhas de acesso)."""
    amb = dict(os.environ, XDG_RUNTIME_DIR=os.environ.get("XDG_RUNTIME_DIR") or f"/run/user/{os.getuid()}")
    reg = subprocess.run(["journalctl", "--user", "-u", "newsbr360-estudio-v2", "--since", "-30 min", "--no-pager", "-o", "cat"],
                         capture_output=True, text=True, env=amb, timeout=60).stdout.splitlines()
    n = sum(1 for l in reg if l.startswith("Traceback"))
    ultimo = next((l.strip() for l in reversed(reg) if l and not l.startswith((" ", "Traceback", '"')) and ("Error" in l or "Exception" in l)), "")
    return n == 0, f"{n} erro(s) na última meia hora" + (f": {ultimo[:120]}" if ultimo else "")


def saida_casa(k):
    """20/10/2026 ("aprovo o plano v2-baixa-pela-casa"): a saída pela casa dele (o Pi), por onde o v2 baixa do YouTube e
    do Instagram. Vermelho = os downloads foram para a IPRoyal (paga por GB): ver se o Pi está ligado e no Wi-Fi."""
    import saida_casa as sc
    if not sc.endereco():
        return False, "não configurada (falta ~/.config/kitebiz/saida-casa)"
    if sc.no_ar(espera=8):
        return True, f"no ar (downloads saem pela casa) · IPRoyal no mês: {sc.gasto_mes():.0f} de {sc.TETO_MES_MB} MB"
    return False, f"fora do ar; downloads na IPRoyal ({sc.gasto_mes():.0f} de {sc.TETO_MES_MB} MB no mês)"


ITENS = [("Saída pela casa (Pi)", saida_casa), ("Estúdio v2", estudio), ("Respostas a comentários", comentarios), ("Backup", backup), ("Google (voz)", google),
         ("fal (imagens e música)", fal), ("Groq (transcrição e alinhamento)", groq), ("Instagram", instagram),
         ("WhatsApp", whatsapp), ("Disco", disco), ("Vídeos parados", videos_parados), ("Erros do estúdio", erros_do_servidor)]


def main():
    simular = "--simular" in sys.argv
    k = chaves()
    agora = datetime.now().strftime("%Y-%m-%d %H:%M")
    linhas = []
    for nome, f in ITENS:
        try:
            ok, det = f(k)
        except Exception as e:
            ok, det = False, f"a conferência quebrou: {str(e)[:120]}"
        linhas.append({"item": nome, "ok": bool(ok), "detalhe": det, "quando": agora})
        print(f"{'OK ' if ok else 'XX '} {nome}: {det}")
    if simular:
        return
    SAIDA.write_text(json.dumps(linhas, ensure_ascii=False, indent=1))
    # aviso com freio (lição do falha-escalate: anti-spam): 1 por item a cada 6 h enquanto continuar vermelho
    est = json.loads(ESTADO.read_text()) if ESTADO.exists() else {}
    agora_s = time.time()
    novos = [l for l in linhas if not l["ok"] and agora_s - est.get(l["item"], 0) > REAVISO_S]
    for l in linhas:
        if l["ok"]:
            est.pop(l["item"], None)          # voltou ao normal: o próximo vermelho avisa de novo
    if novos:
        txt = "NewsBR360 · saúde do estúdio v2 com problema: " + "; ".join(f"{l['item']}: {l['detalhe']}" for l in novos)
        r = subprocess.run([sys.executable, str(RAIZ / "ferramentas/avisar.py"), txt[:400]], capture_output=True, text=True)
        print("aviso:", (r.stdout or r.stderr).strip()[:200])
        if r.returncode == 0:
            for l in novos:
                est[l["item"]] = agora_s
    ESTADO.write_text(json.dumps(est, indent=1))


if __name__ == "__main__":
    main()
