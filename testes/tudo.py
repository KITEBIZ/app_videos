"""Todos os testes sem gasto de IA, num comando só (23/10/2026, "aprovo o plano historico-e-testes").

  .venv/bin/python testes/tudo.py              rápido (~3 s): os testes que não mexem em vídeo, no próprio estúdio
  .venv/bin/python testes/tudo.py --completo   + os que mexem em vídeo, numa cópia temporária feita do gabarito

O gabarito (~/estudio-v2-web/gabarito-testes/videos) são vídeos congelados no estado que os testes esperam (pauta parada,
vídeo na Animação...): os vídeos de verdade mudam com o uso e o teste quebraria sem defeito. Sai 0 se tudo passou, 1 se
algum falhou; a última linha diz quantos.
"""
import os, shutil, subprocess, sys, tempfile, time
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
GABARITO = Path.home() / "estudio-v2-web/gabarito-testes/videos"
PY = str(RAIZ / ".venv/bin/python")
RAPIDOS = ["fomos_conferir.py", "regras_tela.py", "conserto_sem_reescrever.py", "caderno_material.py", "ajuste_mesmas_regras.py", "roteirista_etapa_a.py", "roteiro_com_direcao_servidor.py", "ia_chamar.py", "so_animador_novo.py", "rapidez.py", "solidez.py", "olhos_enquadramento.py", "fala_conferida.py", "fontes_link_solto.py", "acervo.py", "capa_dois_rostos.py", "cena_mudou_mantem_takes.py", "micro_doc.py", "molde_numeros.py", "mapa_passos.py", "mapa_conserto.py", "inicio_no_chat.py", "intencao_viva.py", "consertos_369.py", "animacao_rapida.py", "baixar_insiste.py", "porteiro_completo.py", "olhos_conserta.py", "passo_depois_do_pedido.py", "regra_resposta_no_fim.py", "resposta_com_detalhes.py",
           "olho_unico.py {com_previa}"]
NA_COPIA = ["consertos_revisao.py", "faixa_preta.py", "travas.py {copia}", "capa_sem_tarja.py"]


def ambiente():
    env = dict(os.environ)
    for arq in ("/etc/kitebiz/newsbr360.env", str(Path.home() / ".estudio-v2.env")):
        try:
            for linha in open(arq):
                linha = linha.strip()
                if linha and not linha.startswith("#") and "=" in linha:
                    k, v = linha.split("=", 1)
                    env[k.removeprefix("export ").strip()] = v.strip().strip('"').strip("'")
        except OSError:
            pass
    return env


def com_previa(raiz):
    """O primeiro vídeo (em ordem numérica) com prévia: um .jpg em animacao/, o que testes/olho_unico.py procura
    primeiro (23/10/2026, "opção 1, aprovo o plano teste-video-com-previa": o 335 fixo não existia na cópia local)."""
    nums = sorted(int(p.name) for p in (raiz / "videos").glob("*") if p.name.isdigit())
    return next((n for n in nums if next((raiz / "videos" / str(n) / "animacao").glob("*.jpg"), None)), None)


def roda(raiz, linha, env, limite):
    nome, *args = linha.split()
    arq = raiz / "testes" / nome
    if not arq.exists():
        return None, "não existe neste estúdio (pulado)"
    n = com_previa(raiz) if any("{com_previa}" in a for a in args) else None
    if any("{com_previa}" in a for a in args) and n is None:
        return None, "nenhum vídeo com prévia neste estúdio (pulado)"
    t0 = time.time()
    try:
        r = subprocess.run([PY, str(arq), *[a.format(copia=raiz, com_previa=n) for a in args]], cwd=raiz, env=env,
                           capture_output=True, text=True, timeout=limite)
        fim = (r.stdout.strip().splitlines() or [""])[-1][:110]
        return r.returncode == 0, f"{time.time() - t0:.0f} s · " + (f"vídeo #{n} · " if n else "") + fim
    except subprocess.TimeoutExpired:
        return False, f"passou de {limite} s"


def copia():
    """Uma cópia do estúdio de agora (o código que está no disco, inclusive o que vai ser instalado) com os vídeos do
    gabarito; o .venv é o mesmo (atalho)."""
    d = Path(tempfile.mkdtemp(prefix="estudio-teste-")) / "estudio-v2"
    d.mkdir()
    subprocess.run(["rsync", "-a", "--exclude=videos", "--exclude=.venv", "--exclude=__pycache__", "--exclude=.git",
                    "--exclude=estudio-v2", "--exclude=testes/referencias", "--exclude=testes/tela_igual",
                    "--exclude=publicador/enviados", "--exclude=referencias", f"{RAIZ}/", f"{d}/"], check=True)
    (d / ".venv").symlink_to(RAIZ / ".venv")
    subprocess.run(["rsync", "-a", f"{GABARITO}/", f"{d}/videos/"], check=True)
    olhos = RAIZ.parent / "olhos"
    if olhos.exists():
        subprocess.run(["rsync", "-a", "--exclude=__pycache__", f"{olhos}/", f"{d.parent}/olhos/"], check=True)
    (d / "olho").mkdir(exist_ok=True); (d / "olho/DESLIGADO").write_text("cópia de teste")
    return d


def main():
    env = ambiente()
    # 25/10/2026 (revisão de confiabilidade: 306 pastas tmp* e 3,5 GB no /tmp da VPS, deixadas pelos testes): tudo o que os
    # testes criam no temporário vai para uma pasta desta rodada, apagada no fim
    tmp = tempfile.mkdtemp(prefix="estudio-testes-")
    env["TMPDIR"] = tmp
    try:
        _rodar(env)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _rodar(env):
    resultados = []
    for t in RAPIDOS:
        resultados.append((t, *roda(RAIZ, t, env, 180)))
    if "--completo" in sys.argv:
        if not GABARITO.exists():
            resultados.append(("gabarito", False, f"não existe: {GABARITO}"))
        else:
            c = copia()
            try:
                for t in NA_COPIA:
                    resultados.append((t.split()[0], *roda(c, t, env, 1200)))
            finally:
                shutil.rmtree(c.parent, ignore_errors=True)
    falhas = [r for r in resultados if r[1] is False]
    for nome, ok, txt in resultados:
        print(f"{'PASSOU' if ok else 'pulado' if ok is None else 'FALHOU'} · {nome} · {txt}")
    print(f"{sum(1 for r in resultados if r[1])} passaram, {len(falhas)} falharam, "
          f"{sum(1 for r in resultados if r[1] is None)} pulados")
    sys.exit(1 if falhas else 0)


if __name__ == "__main__":
    main()
