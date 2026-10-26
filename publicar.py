"""Publicar (estúdio v2, 16/10/2026, "aprovo o plano v2-parte4-publicar"; ele: "depois que clicar no botão tem que
publicar. não precisa mais de comando via chat").

  python3 publicar.py <número>               ensaio: manda à VPS e roda o publicador sem enviar nada à Meta
Publicar de verdade só pelo botão da tela (servidor.py chama fazer(num, simular=False)); a linha de comando nunca publica.

Usa o publicador da VPS (publicador/publicar-instagram.py; até 20/10/2026 era o da v1, em newsbr360-estudio):
conta @newsbr360, colaborador alexandremota.digital, capa escolhida e o reel também no Facebook. Cada linha do
publicador vira um passo na ficha (a tela mostra a animação de cada etapa); os links saem das linhas PUBLICADO.
"""
import re, subprocess, sys

import estudio as E

VPS = "usuario@SEU_SERVIDOR"          # como o publicador roda na v1 (o dono dos arquivos do estúdio)
# as chaves (FAL_KEY para o link público do vídeo, e as da Meta) vêm deste arquivo, como no teste A/B do #126 em
# 16/10; sem ele o publicador para em "sem FAL_KEY" (aconteceu na 1ª publicação do #202, 23:05, nada enviado)
CHAVES = "/etc/kitebiz/newsbr360.env"
# 20/10/2026 (ele: "traz pra dentro do v2"): o publicador, o acesso da Meta (.env.instagram) e o registro
# (publicacoes.jsonl) moram em publicador/; na v1 ficaram links para cá (metricas.py e os vigias da v1 ainda leem)
PUBLICADOR = "/srv/kitebiz/projetos/conteudo/estudio-v2/publicador"

# linha do publicador -> passo na tela (as que não casam não aparecem)
PASSOS = [(r"^== portao", "conferindo legenda, vídeo e capa"), (r"^== a conta do acesso", "conta @newsbr360 conferida"),
          (r"^== subindo o video", "enviando o vídeo"), (r"^== container", "Instagram processando o vídeo"),
          (r"^PUBLICADO: ", "publicado no Instagram"), (r"^== Facebook", "enviando ao Facebook"),
          (r"^PUBLICADO NO FACEBOOK", "publicado no Facebook"), (r"^SIMULACAO", "ensaio aprovado: nada foi enviado")]


def fazer(num, simular=False, ao_passo=None):
    p = E.pasta(num) / "publicacao"
    for arq in ("final.mp4", "capa.jpg", "legenda.txt"):
        if not (p / arq).exists():
            raise RuntimeError(f"falta publicacao/{arq}")
    # 24/10/2026: fora da VPS (a cópia local publica por ssh) o envio leva "local" no nome; o publicador barra repetido pelo
    # nome do arquivo, e o #370 local travaria o #370 da VPS (a numeração das duas é separada)
    marca = "" if E.NA_VPS else "local-"
    d = f"{PUBLICADOR}/enviados/{marca}{int(num)}"
    subprocess.run(E.na_vps(f"mkdir -p {d}"), check=True, capture_output=True, timeout=60)
    if ao_passo:
        ao_passo("enviando os arquivos para o servidor")
    # 17/10/2026: a trava de duplicata do publicador compara pelo NOME do arquivo; com todo vídeo da v2 chamado
    # final.mp4, o #204 foi barrado como se fosse o #202 (nada enviado). Cada vídeo sobe com nome próprio.
    nome = f"v2-{marca}{int(num)}-final.mp4"
    for local, remoto in (("final.mp4", nome), ("capa.jpg", f"v2-{marca}{int(num)}-capa.jpg"), ("legenda.txt", f"v2-{marca}{int(num)}-legenda.txt")):
        subprocess.run(E.para_vps(p / local, f"{d}/{remoto}"), check=True, capture_output=True, timeout=600)
    cmd = (f"export PATH=$HOME/.local/bin:$PATH; set -a; . {CHAVES}; set +a; cd {PUBLICADOR} && python3 -u publicar-instagram.py "
           f"{d}/{nome} --legenda {d}/v2-{marca}{int(num)}-legenda.txt --conta newsbr360 --colaborador alexandremota.digital "
           f"--capa-imagem {d}/v2-{marca}{int(num)}-capa.jpg --facebook" + (" --simular" if simular else ""))
    proc = subprocess.Popen(E.na_vps(cmd), stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, start_new_session=True)
    # 25/10/2026 (revisão de solidez): prazo de verdade (o wait(1800) só vinha depois de a saída fechar); o publicador
    # espera até 10 min o container, então 30 min é folga. Parado, o resultado é "falhou" com o que já saiu nos links
    prazo = E.prazo(proc, 30 * 60)
    linhas, links = [], {}
    for linha in proc.stdout:
        linha = linha.rstrip(); linhas.append(linha)
        for padrao, passo in PASSOS:
            if re.search(padrao, linha) and ao_passo:
                ao_passo(passo)
        if linha.startswith("PUBLICADO NO FACEBOOK:"):
            links["facebook"] = linha.split(":", 1)[1].strip()
        elif linha.startswith("PUBLICADO:"):
            links["instagram"] = linha.split(":", 1)[1].strip()
    try:
        proc.wait(timeout=60)
    except subprocess.TimeoutExpired:
        E.mata(proc)
    prazo.cancel()
    if getattr(prazo, "estourou", False):
        linhas.append("o publicador passou de 30 min e foi parado; confira no Instagram antes de publicar de novo")
    ok = proc.returncode == 0 and (("instagram" in links) if not simular else any(l.startswith("SIMULACAO") for l in linhas))
    E.evento(num, ("ensaio de publicação" if simular else "PUBLICAÇÃO") + f": {'ok' if ok else 'falhou'} {links}")
    if ok and not simular:
        try:
            limpar(num)
        except Exception as e:
            E.evento(num, f"limpeza depois de publicar não rodou: {str(e)[:160]}")
    return {"ok": ok, "links": links, "simulado": simular, "saida": linhas[-25:]}


# 20/10/2026 ("aprovo o plano render-rapido"; ele: "tem que colocar um recurso para limpar a pasta depois de publicar um
# video"): só o que o estúdio refaz sozinho. Ficam publicacao/, a cena e as versões, roteiro, voz, chat e os vídeos
# originais (referencia/ e material/), para corrigir e republicar.
LIMPAR_PASTAS = ("animacao/antes", "animacao/depois", "animacao/revisao-quadros", "animacao/revisao-mosaicos", "animacao/olhar")
LIMPAR_ARQUIVOS = ("*.quadro.mp4", "*.leve.mp4", "previa-*.mp4")     # previa-*.mp4: previa-em-video (21/10/2026)


def limpar(num):
    """Apaga da pasta do vídeo publicado os arquivos de trabalho e anota no histórico quanto liberou. Devolve os MB."""
    import shutil
    p = E.pasta(num); soma = lambda xs: sum(f.stat().st_size for f in xs if f.is_file())
    total = 0
    for sub in LIMPAR_PASTAS:
        d = p / sub
        if d.is_dir() and not d.is_symlink():
            total += soma(d.rglob("*")); shutil.rmtree(d)
    for padrao in LIMPAR_ARQUIVOS:
        for f in p.rglob(padrao):
            if f.is_file() and not f.is_symlink():
                total += f.stat().st_size; f.unlink()
    mb = round(total / 1e6, 1)
    E.evento(num, f"limpeza depois de publicar: {mb} MB de arquivos de trabalho apagados")
    return mb


if __name__ == "__main__":
    import json
    r = fazer(int(sys.argv[1]), simular=True, ao_passo=lambda s: print("·", s))
    print(json.dumps(r, ensure_ascii=False, indent=1))
