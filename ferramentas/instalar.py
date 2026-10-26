"""O único jeito de instalar uma mudança no estúdio (23/10/2026, "aprovo o plano historico-e-testes").

  .venv/bin/python ferramentas/instalar.py "<nome>" "<autorização dele, com as palavras>" [--completo]
  .venv/bin/python ferramentas/instalar.py --desfazer "<por quê>"
  .venv/bin/python ferramentas/instalar.py --religar        o religar que ficou para depois (vídeo trabalhando na hora)

Instalar: as mudanças já estão nos arquivos (git status). Confere que nenhum vídeo está trabalhando; guarda uma cópia do
que mudou; roda os testes (rápidos, ou --completo) e RECUSA se algum falhar (as mudanças vão para o "stash", com a cópia
guardada); registra no histórico com o nome e a autorização; reinicia só se mudou programa (.py); confere que o estúdio
subiu (responde e sem erro no registro). Se não subir, VOLTA sozinho para o registro anterior.
Desfazer: volta a última instalação (git revert), reinicia se precisar e confere.

Para provar numa cópia: ESTUDIO_PORTA (padrão 4400) e ESTUDIO_REINICIAR (o comando que reinicia; padrão o serviço).
No Mac (cópia local, sem systemctl nem journalctl; 23/10/2026, "sim, conserta o instalador"): reinicia parando quem
escuta a porta e ligando de novo pelo ../ligar.sh, e os erros ao subir são os Traceback novos do ../servidor.log.
"""
import json, os, shutil, subprocess, sys, time, urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
PY = str(RAIZ / ".venv/bin/python")
PORTA = int(os.environ.get("ESTUDIO_PORTA", "4400"))
SERVICO = "newsbr360-estudio-v2"
NO_MAC = shutil.which("systemctl") is None and (RAIZ.parent / "ligar.sh").exists()
LOG = RAIZ.parent / "servidor.log"                      # o registro da cópia local (o ligar.sh escreve aqui)
REINICIAR_MAC = (f"lsof -ti tcp:{PORTA} -sTCP:LISTEN | xargs kill 2>/dev/null; "
                 f"for i in $(seq 1 20); do lsof -ti tcp:{PORTA} -sTCP:LISTEN >/dev/null || break; sleep 0.5; done; "
                 f"nohup '{RAIZ.parent / 'ligar.sh'}' >/dev/null 2>&1 &")
REINICIAR = os.environ.get("ESTUDIO_REINICIAR") or (REINICIAR_MAC if NO_MAC else f"systemctl --user restart {SERVICO}")
EM_PRODUCAO = "ESTUDIO_REINICIAR" not in os.environ
# mapa-de-passos (24/10/2026): os passos em que um vídeo está trabalhando vêm da tabela (passos.py); antes, uma lista
# à parte que não tinha "baixando e transcrevendo o vídeo que você mandou" (o instalador reiniciava no meio do download)
sys.path.insert(0, str(RAIZ))
import passos
OCUPADOS = passos.TRABALHANDO
os.environ.setdefault("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}")


def precisa_reiniciar(arquivos):
    """Só programa que o servidor carrega pede reinício: testes e este comando, não; páginas e regras são lidas na hora."""
    return any(a.endswith(".py") and not a.startswith("testes/") and a != "ferramentas/instalar.py" for a in arquivos)


def git(*a, ok=True):
    r = subprocess.run(["git", *a], cwd=RAIZ, capture_output=True, text=True)
    if ok and r.returncode:
        sys.exit(f"git {' '.join(a)} falhou: {r.stderr.strip()[:300]}")
    return r.stdout


def ocupados():
    saida = []
    for f in sorted((RAIZ / "videos").glob("*/ficha.json")):
        try:
            p = json.loads(f.read_text()).get("passo")
        except (OSError, ValueError):
            continue
        if p in OCUPADOS:
            saida.append(f"#{f.parent.name} ({p})")
    return saida


def responde(segundos=25):
    fim = time.time() + segundos
    while time.time() < fim:
        try:
            with urllib.request.urlopen(f"http://127.0.0.1:{PORTA}/api/funil", timeout=3) as r:
                if r.status == 200:
                    return True
        except Exception:
            pass
        time.sleep(1)
    return False


def erros_desde(quando, log_antes=0):
    if not EM_PRODUCAO:
        return 0
    if NO_MAC:                                           # só o que o servidor escreveu depois do reinício
        try:
            with open(LOG, "rb") as f:
                f.seek(log_antes)
                return f.read().decode("utf-8", "replace").count("Traceback")
        except OSError:
            return 0
    r = subprocess.run(["journalctl", "--user", "-u", SERVICO, "--since", quando, "--no-pager", "-o", "cat"],
                       capture_output=True, text=True)
    return sum(1 for linha in r.stdout.splitlines() if "Traceback" in linha)


def reinicia_e_confere():
    quando = time.strftime("%Y-%m-%d %H:%M:%S")
    log_antes = LOG.stat().st_size if NO_MAC and LOG.exists() else 0
    subprocess.run(REINICIAR, shell=True, check=False)
    time.sleep(3)
    ok = responde()
    n = erros_desde(quando, log_antes)
    return ok and n == 0, f"responde={'sim' if ok else 'NÃO'}, erros ao subir={n}"


ESPERA_MAX = 900


def espera_livre(maximo=ESPERA_MAX, passo=10):
    """True quando nenhum vídeo está trabalhando (espera até `maximo` s, olhando a cada `passo`)."""
    fim = time.time() + maximo
    avisou = False
    while ocupados():
        if time.time() >= fim:
            return False
        if not avisou:
            print("esperando para religar: vídeo trabalhando agora: " + ", ".join(ocupados()), flush=True); avisou = True
        time.sleep(passo)
    return True


def instalar(nome, autorizacao, completo):
    mudou = [l[3:] for l in git("status", "--porcelain").splitlines() if l.strip()]
    if not mudou:
        sys.exit("nada a instalar (nenhum arquivo mudou)")
    oc = ocupados()
    if oc:
        sys.exit("não instalei: vídeo trabalhando agora: " + ", ".join(oc) + ". Espere terminar e rode de novo.")
    copia = Path.home() / "estudio-v2-web/pacotes" / f"{nome}-{time.strftime('%Y%m%d-%H%M%S')}"
    for rel in mudou:
        src = RAIZ / rel.strip('"')
        if src.is_file():
            (copia / rel).parent.mkdir(parents=True, exist_ok=True); shutil.copy2(src, copia / rel)
    print(f"cópia do que mudou: {copia}")
    t = subprocess.run([PY, str(RAIZ / "testes/tudo.py"), *(["--completo"] if completo else [])], cwd=RAIZ,
                       capture_output=True, text=True)
    print(t.stdout.strip().splitlines()[-1] if t.stdout.strip() else t.stderr[-300:])
    if t.returncode:
        git("stash", "push", "--include-untracked", "-m", f"recusado: {nome}")
        print(t.stdout)
        sys.exit(f"RECUSADO: teste falhou. Nada mudou no estúdio; as mudanças estão no stash ('recusado: {nome}') e em {copia}.")
    git("add", "-A")
    git("commit", "-q", "-m", f"{nome}\n\nAutorização: {autorizacao}\nTestes: {'completos' if completo else 'rápidos'} · "
                              f"{t.stdout.strip().splitlines()[-1]}\nArquivos: {', '.join(mudou)}")
    registro = git("rev-parse", "--short", "HEAD").strip()
    if not precisa_reiniciar(mudou):
        print(f"INSTALADO {registro} ({nome}) sem reiniciar: nenhum programa do servidor mudou")
        return
    # 24/10/2026 (#373: uma pauta chegou durante os testes e o religar matou o download): confere de novo logo antes de
    # religar; com vídeo trabalhando, espera; se não liberar, fica registrado e o religar fica para depois
    if not espera_livre():
        print(f"REGISTRADO {registro} ({nome}), mas NÃO religuei: vídeo trabalhando ({', '.join(ocupados())}). "
              f"Quando terminar: {PY} ferramentas/instalar.py --religar")
        return
    ok, como = reinicia_e_confere()
    if ok:
        print(f"INSTALADO {registro} ({nome}): {como}")
        return
    print(f"o estúdio não subiu direito ({como}): voltando")
    git("revert", "--no-edit", "HEAD")
    ok2, como2 = reinicia_e_confere()
    sys.exit(f"VOLTOU para antes de {nome}: {como2}" + ("" if ok2 else " · ATENÇÃO: nem a volta subiu, chame alguém"))


def desfazer(porque):
    oc = ocupados()
    if oc:
        sys.exit("não desfiz: vídeo trabalhando agora: " + ", ".join(oc))
    ultimo = git("log", "-1", "--format=%h %s").strip()
    mudou = git("diff", "--name-only", "HEAD~1", "HEAD").split()
    git("revert", "--no-edit", "HEAD")
    git("commit", "--amend", "-q", "-m", f"desfeito: {ultimo}\n\nPor quê: {porque}")
    if precisa_reiniciar(mudou):
        ok, como = reinicia_e_confere()
        print(f"DESFEITO {ultimo}: {como}")
        if not ok:
            sys.exit(1)
    else:
        print(f"DESFEITO {ultimo} sem reiniciar")


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["--desfazer"] and len(a) >= 2:
        desfazer(a[1])
    elif a[:1] == ["--religar"]:
        # 24/10/2026: o religar que ficou para depois (o registro já foi feito); com vídeo trabalhando, espera
        if not espera_livre():
            sys.exit("não religuei: vídeo trabalhando agora: " + ", ".join(ocupados()))
        ok, como = reinicia_e_confere()
        print(("RELIGADO: " if ok else "o estúdio não subiu direito: ") + como)
    elif len(a) >= 2 and not a[0].startswith("-"):
        instalar(a[0], a[1], "--completo" in a)
    else:
        sys.exit(__doc__)
