"""Da pauta ao roteiro v1, sozinho (estúdio v2, 16/10/2026, "aprovo o plano v2-parte1").

  python3 pauta.py <número>      roda (ou retoma) a pauta do vídeo <número>

Passos, cada um gravado na ficha (o funil mostra "baixando", "transcrevendo", "escrevendo o roteiro"):
  1. com link: baixa só o áudio e 6 quadros (ferramentas/analisar_reel.py da v1) em referencia/;
  2. transcreve na Groq, palavra por palavra (ferramentas/transcrever.py da v1);
  3. o roteirista (regras/ROTEIRISTA.md) confere na web e devolve análise, checagem e roteiro em blocos;
  4. confere o que ele devolveu (Fazer igual sem trecho de ninguém, corte dentro do áudio) e grava os arquivos;
  5. o item fica em Pauta esperando "Aprovar o roteiro". Parou? A ficha diz onde e por quê, e o chat conta.
"""
import json, re, subprocess, sys, time
from pathlib import Path

import estudio as E
import caderno

FERR = E.RAIZ / "ferramentas"
sys.path.insert(0, str(FERR))


def passo(num, nome):
    E.mexe_ficha(num, passo=nome, passo_desde=E.agora(), erro="")
    E.evento(num, nome)


class SemVideo(RuntimeError):
    pass


def tem_som(arq):
    """O arquivo tem trilha de áudio? (ffprobe)"""
    r = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "a", "-show_entries", "stream=index", "-of", "csv=p=0", str(arq)],
                       capture_output=True, text=True)
    return bool(r.stdout.strip())


def som_a_parte(num, link, video, ref):
    """21/10/2026 ("aprovo o plano baixa-com-som"; #308: o Instagram mandou só os formatos de vídeo, o reel veio mudo e a
    pauta parou no ffmpeg; no dia seguinte o mesmo reel já trazia o áudio): baixa só o áudio, pelas saídas do v2 (casa,
    IPRoyal, direto), e junta ao vídeo. Sem áudio em nenhuma tentativa: o item diz que o reel veio sem som."""
    import analisar_reel as A
    E.evento(num, "o vídeo veio sem som; baixando o áudio à parte")
    for k in range(2):
        if k:
            time.sleep(5)
        for f in ref.glob("som.*"):
            f.unlink()
        A.yt([A.ytdlp(), "-q", "--no-warnings", "--retries", "5", "-f", "ba[ext=m4a]/ba", "-o", str(ref / "som.%(ext)s"), link],
             quem="pauta (áudio à parte)", capture_output=True, text=True, timeout=600)
        som = next((f for f in ref.glob("som.*") if f.suffix != ".json" and tem_som(f)), None)
        if som:
            junto = ref / "video.junto.mp4"
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(video), "-i", str(som), "-map", "0:v:0", "-map", "1:a:0",
                            "-c:v", "copy", "-c:a", "aac", "-b:a", "128k", "-shortest", str(junto)], check=True)
            junto.replace(video); som.unlink()
            E.evento(num, "áudio baixado à parte e juntado ao vídeo")
            return
    raise RuntimeError("o reel veio sem som: o Instagram não mandou a trilha de áudio em nenhuma tentativa. Tente de novo "
                       "mais tarde, ou mande outro link do mesmo vídeo")


def baixar_pauta(num, link):
    """17/10/2026 ("aprovo o plano olhos-na-pauta"): UM download do vídeo inteiro (referencia/video.mp4, que a animação
    também usa nos trechos); dele saem o áudio, os dados do post e os 6 quadros, e o mesmo arquivo vai aos Olhos.
    Se o vídeo não vier, cai no caminho antigo (só o áudio)."""
    import analisar_reel as A
    ref = E.pasta(num) / "referencia"; ref.mkdir(parents=True, exist_ok=True)
    video = ref / "video.mp4"
    if not video.exists():
        # 19/10/2026 (#301): com "height<=720" e a ordem padrão, o yt-dlp pegava 360x640 do reel do Metrópoles, que tinha
        # 480x854; "-S res,br" escolhe a maior resolução (medido: 480x854). No #302 o filtro de altura deixava passar os
        # formatos sem tamanho ("1", "2", "3", 720x1280) e perdia o de 1080x1920: a ordem "res:1080" faz o limite
        for k, fmt in enumerate(("bv+ba/b", "b", "bv*+ba/b")):
            if k:
                time.sleep(3)
            r = A.yt([A.ytdlp(), "-q", "--no-warnings", "--retries", "5", "-S", "res:1080,br", "-f", fmt, "--merge-output-format", "mp4",
                      "--write-info-json", "-o", str(ref / "video.%(ext)s"), link], quem="pauta (vídeo)", capture_output=True, text=True, timeout=900)
            if not r.returncode and video.exists():
                break
            # 17/10/2026 (material-qualquer; #297, carrossel do Mises): post sem vídeo; vai para o material na hora
            if "No video formats found" in (r.stderr or ""):
                raise SemVideo("o link não tem vídeo")
        else:
            E.evento(num, "o vídeo inteiro não baixou; sigo só com o áudio")
            return baixar(num, link)
    audio = ref / "audio.m4a"
    if not audio.exists():
        if not tem_som(video):
            som_a_parte(num, link, video, ref)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(video), "-vn", "-c:a", "aac", "-b:a", "128k", str(audio)], check=True)
    info = json.loads((ref / "video.info.json").read_text()) if (ref / "video.info.json").exists() else {}
    if info and not (ref / "audio.info.json").exists():
        (ref / "audio.info.json").write_text(json.dumps(info, ensure_ascii=False))
    dur = info.get("duration") or float(subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(video)]))
    ts = info.get("timestamp")
    meta = {"link": link, "quem_postou": info.get("uploader") or info.get("channel"),
            "conta": info.get("channel") or info.get("uploader_id"),
            "postado": time.strftime("%Y-%m-%d", time.localtime(ts)) if ts else info.get("upload_date"),
            "duracao": round(dur, 1), "legenda_do_post": (info.get("description") or "")[:2000]}
    (ref / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1))
    if not (ref / "imagens").exists():
        A.extrai_quadros(video, ref / "imagens", dur)
    return meta


def baixar(num, link, ref=None, quadros=True):
    """Áudio, dados do post e (com quadros) 6 quadros do link em `ref` (padrão: referencia/ do vídeo)."""
    import analisar_reel as A
    ref = ref or E.pasta(num) / "referencia"; ref.mkdir(parents=True, exist_ok=True)
    audio = ref / "audio.m4a"
    if not audio.exists():
        # 17/10/2026: o YouTube devolveu 403 ao pedido só de áudio do vídeo do SBT (#204) e, um minuto depois, o mesmo
        # comando baixou; agora tenta de novo e com outros formatos (vídeo inteiro, de onde sai o áudio) antes de desistir
        erros = []
        for k, fmt in enumerate(("ba[ext=m4a]/ba/b", "b", "bv*[height<=720]+ba/b")):
            if k:
                time.sleep(3)
            r = A.yt([A.ytdlp(), "-q", "--no-warnings", "--retries", "5", "-S", "res:1080,br", "-f", fmt, "--write-info-json", "-o",
                      str(ref / "audio.%(ext)s"), link], quem="pauta (áudio)", capture_output=True, text=True, timeout=600)
            if not r.returncode and any(p.suffix != ".json" for p in ref.glob("audio.*")):
                break
            erros.append((r.stderr or "").strip()[-160:])
        else:
            raise RuntimeError("não consegui baixar o áudio do link (3 tentativas): " + erros[-1])
        baixado = next(p for p in ref.glob("audio.*") if p.suffix != ".json")
        if baixado != audio:
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(baixado), "-vn", "-c:a", "aac", str(audio)], check=True)
            baixado.unlink()
    info = json.loads((ref / "audio.info.json").read_text()) if (ref / "audio.info.json").exists() else {}
    dur = info.get("duration") or float(subprocess.check_output(
        ["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(audio)]))
    ts = info.get("timestamp")
    meta = {"link": link, "quem_postou": info.get("uploader") or info.get("channel"),
            "conta": info.get("channel") or info.get("uploader_id"),
            "postado": time.strftime("%Y-%m-%d", time.localtime(ts)) if ts else info.get("upload_date"),
            "duracao": round(dur, 1), "legenda_do_post": (info.get("description") or "")[:2000]}
    (ref / "meta.json").write_text(json.dumps(meta, ensure_ascii=False, indent=1))
    if quadros and not (ref / "imagens").exists():
        A.quadros(link, ref, dur)
    return meta


def transcrever(num, ref=None):
    from transcrever import palavras, texto_com_tempo
    ref = ref or E.pasta(num) / "referencia"
    if not (ref / "palavras.json").exists():
        ws, _ = palavras(ref / "audio.m4a")
        (ref / "palavras.json").write_text(json.dumps(ws, ensure_ascii=False))
        (ref / "transcricao.txt").write_text(texto_com_tempo(ws) + "\n")
    return (ref / "transcricao.txt").read_text()


def olhos_texto(p):
    """O que um espectador independente viu na referência (conteudo/olhos), para o Fazer igual."""
    a = p / "referencia/olhos/opiniao.json"
    if not a.exists():
        return ""
    return ("\nComo um espectador independente ASSISTIU a referência (quadros a cada 0,5 s no gancho; não sabe nada do "
            "nosso estúdio). Use para copiar a ESTRUTURA (gancho, ritmo, texto na tela), não as palavras:\n" + a.read_text()[:4000] + "\n")


def material_texto(p):
    """17/10/2026 ("aprovo o plano material-qualquer"): carrossel, PDF, imagem ou página web, sem som."""
    m = p / "referencia/material"
    if not m.exists():
        return ""
    ims = sorted(x for x in m.iterdir() if x.suffix == ".jpg")
    tx = (m / "texto.txt").read_text()[:14000] if (m / "texto.txt").exists() else ""
    lei = (m / "leitura.json").read_text()[:6000] if (m / "leitura.json").exists() else ""
    return ("\n## O material desta pauta NÃO TEM ÁUDIO (carrossel, PDF, imagem ou página web)\n"
            "Não há transcrição nem trecho de outra pessoa para cortar: todas as falas são do Alexandre (quem = nós).\n"
            "Imagens do material, na ordem (leia com Read; elas podem entrar no vídeo): "
            + ", ".join(str(x.relative_to(p)) for x in ims) + "\n"
            + (f"\nTexto que veio com o material (legenda do post, texto do PDF ou da página):\n{tx}\n" if tx else "")
            + (f"\nComo um leitor independente LEU o material (os Olhos; não sabe nada do nosso estúdio):\n{lei}\n" if lei else ""))


# 19/10/2026 (ele: "esse vídeo não é bem de placar", #304 Janones; "é um tipo de vídeo de conteúdo, ou análise"): o
# botão Análise ao colar o link
ANALISE_PEDIDA = ("FORMATO PEDIDO POR ELE: ANÁLISE (\"formato\": \"analise\"). Não é checagem frase a frase: sem carimbo "
                  "em cada fala e SEM PLACAR. Conta o caso em ordem, com documento em cada passo, separa o que está provado "
                  "do que foi esticado e fecha com UMA conclusão curta, seguida de um pedido só.")


# 22/10/2026 ("aprovo o plano fluxo-viral-util"; ele: "no futuro vamos fazer vídeos para mais nichos"): o nicho escolhe a
# seção de regras/GANCHOS.md; por enquanto todo vídeo é da @newsbr360
NICHO_PADRAO = "Política e checagem"


def pedir_roteiro(num, ficha, meta, transcricao, extra=""):
    """extra: o que vem depois do material (22/10/2026, roteiro-com-direcao: o pedido de reescrever com o roteiro de agora)."""
    p = E.pasta(num)
    imagens = sorted((p / "referencia/imagens").glob("*.jpg")) if (p / "referencia/imagens").exists() else []
    nicho = ficha.get("nicho") or NICHO_PADRAO
    prompt = f"""{(E.RAIZ / 'regras/ROTEIRISTA.md').read_text()}{E.molde(num)}{E.regra_idioma(num)}{E.memoria(num)}

{(E.RAIZ / 'regras/GANCHOS.md').read_text() if (E.RAIZ / 'regras/GANCHOS.md').exists() else ''}

## Esta pauta
Nicho: {nicho}
Tipo: {E.TIPOS[ficha['tipo']]}
Link: {ficha.get('link') or '(sem link)'}
O que o Alexandre escreveu junto: {ficha.get('texto_dele') or '(nada)'}
{ANALISE_PEDIDA if E.ler_ficha(num).get("formato_pedido") == "analise" else ""}
Dados do post: {json.dumps(meta, ensure_ascii=False) if meta else '(sem post)'}
{"Quadros do vídeo (leia com a ferramenta Read): " + ", ".join(str(i) for i in imagens) if imagens else ""}

Transcrição (mm:ss frase):
{transcricao[:14000] if transcricao else '(sem áudio)'}
{olhos_texto(p)}{material_texto(p)}{caderno.para_pedido(num)}{extra}"""
    (p / "referencia").mkdir(exist_ok=True)
    (p / "referencia/pedido-roteiro.txt").write_text(prompt)
    # 25/10/2026: a chamada de IA de um lugar só (ia.py); o Read do roteirista passou a ter caminho (antes, lia qualquer
    # arquivo da máquina, e ele lê páginas da web que podem trazer instrução maliciosa)
    import ia
    texto, uso = ia.chamar(prompt, "roteirista", "opus", num=int(p.name), limite=1500, ferramentas="WebSearch,WebFetch,Read",
                           cwd=p, dirs=[E.RAIZ / "regras"])
    (p / "referencia/resposta-roteiro.txt").write_text(texto + ("\n--- erro ---\n" + uso["erro"] if uso["erro"] else ""))
    d = ia.json_de(texto)
    if not d:
        raise RuntimeError("o roteirista não devolveu o roteiro: " + (uso["erro"] or texto or "resposta vazia")[-200:].strip())
    return d


def _norm(p):
    import unicodedata
    p = "".join(c for c in unicodedata.normalize("NFD", str(p).lower()) if unicodedata.category(c) != "Mn")
    return re.sub(r"[^\w]", "", p)


PAUSA_FIM = .7          # s de silêncio depois da última palavra que contam como fim de frase (a transcrição nem sempre pontua)


def fim_de_frase(ws, j):
    """22/10/2026 ("aprovo o plano trecho-frase-inteira"; #327: "A UFRJ comprovou num estudo que a meta," cortado na
    vírgula e ele: "perdeu o contexto da frase"): a palavra j fecha a frase? Ponto, interrogação, exclamação ou
    reticências; a próxima palavra começando com maiúscula (fala rápida em lista, como a do Lula no #301, vem sem ponto:
    "Temos a menor inflação Temos a maior"); uma pausa de PAUSA_FIM s; ou o fim do áudio. Vírgula no fim é meio de frase."""
    if j + 1 >= len(ws):
        return True
    ultima, prox = ws[j][2].strip(), ws[j + 1][2].strip()
    if re.search(r"[.!?…]$", ultima):
        return True
    if ultima.endswith((",", ";", ":")):
        return False
    return prox[:1].isupper() or ws[j + 1][0] - ws[j][1] >= PAUSA_FIM


def acerta_corte(num, b):
    """O corte do trecho sai das PALAVRAS do trecho achadas na transcrição, não do número que a IA deu (16/10/2026: no
    #201 a IA deu 8,00-18,00 e 44,00-54,00; o primeiro começava em "vem comigo" e o segundo cortava "reforma" no meio,
    o mesmo defeito do #111 na v1). Acha as 3 primeiras e as 3 últimas palavras em sequência e corta do começo da
    primeira ao fim da última. Devolve o erro em português ou "" (b["corte"] fica acertado)."""
    arq = E.pasta(num) / "referencia/palavras.json"
    alvo = [_norm(x) for x in (b.get("trecho") or "").split() if _norm(x)]
    if not arq.exists() or len(alvo) < 4:
        return "trecho sem as palavras exatas (mínimo 4) para achar o corte"
    ws = [w for w in json.loads(arq.read_text()) if _norm(w[2])]
    ditas = [_norm(w[2]) for w in ws]
    k = 3
    inicios = [i for i in range(len(ditas) - k + 1) if ditas[i:i + k] == alvo[:k]]
    if not inicios:
        return f"as primeiras palavras do trecho (\"{' '.join(b['trecho'].split()[:3])}\") não estão na transcrição"
    perto = (b.get("corte") or [0])[0]
    i0 = min(inicios, key=lambda i: abs(ws[i][0] - float(perto)))
    fins = [j for j in range(i0 + k - 1, min(len(ditas), i0 + len(alvo) + 15)) if ditas[j - k + 1:j + 1] == alvo[-k:]]
    if not fins:
        return f"as últimas palavras do trecho (\"{' '.join(b['trecho'].split()[-3:])}\") não estão logo depois do começo"
    j = fins[0]
    # a folga não invade a palavra vizinha (16/10, #201: o fim +0,08 s pegava o "tudo" da frase seguinte)
    # 22/10/2026 (trecho-frase-inteira.1; #327 bloco 4): quando a transcrição dá as palavras SOBREPOSTAS ("meta." até
    # 46,80 e "Mas" de 46,32 a 46,56), o "não invadir a vizinha" empurrava o corte para depois da 1ª palavra e o som perdia
    # o "Mas" que o texto tem. Com sobreposição, o corte fica na própria palavra
    antes_fim = ws[i0 - 1][1] if i0 > 0 else 0
    ini = max(0, ws[i0][0] - .05, antes_fim + .02 if antes_fim < ws[i0][0] else 0)
    depois_ini = ws[j + 1][0] if j + 1 < len(ws) else None
    fim = min(ws[j][1] + .08, depois_ini - .02) if depois_ini is not None and depois_ini > ws[j][1] else ws[j][1] + (.08 if depois_ini is None else 0)
    b["corte"] = [round(ini, 2), round(fim, 2)]
    b["trecho"] = " ".join(w[2] for w in ws[i0:j + 1])          # o texto do bloco é o que ele disse, palavra por palavra
    if not fim_de_frase(ws, j):
        return (f"o trecho termina no meio da frase (\"...{' '.join(w[2] for w in ws[max(i0, j - 3):j + 1])}\", e ela continua "
                f"\"{' '.join(w[2] for w in ws[j + 1:j + 4])}...\"): vá até o fim da frase, mesmo que passe de 6 s")
    return ""


def confere(R, ficha, meta, num=None):
    """O que está errado no que o roteirista devolveu (vazio = ok)."""
    erros = []
    bs = R.get("blocos") or []
    nossos = [b for b in bs if re.fullmatch(r"n[oó]s", (b.get("quem") or "").strip(), re.I)]
    outros = [b for b in bs if b not in nossos]
    if len(nossos) < 3:
        erros.append(f"só {len(nossos)} falas nossas (mínimo 3)")
    if any(not (b.get("fala") or "").strip() for b in nossos):
        erros.append("fala nossa vazia")
    if ficha["tipo"] != "analisar" and outros:
        erros.append(f"{E.TIPOS[ficha['tipo']]} é só com a voz do Alexandre, e veio com {len(outros)} trecho(s) de outra pessoa")
    dur = (meta or {}).get("duracao") or 0
    if (meta or {}).get("tipo_material") and outros:
        erros.append(f"o material não tem áudio (é {meta['tipo_material']}): todas as falas são nossas, e veio com {len(outros)} trecho(s) de outra pessoa")
        return erros
    for b in outros:
        if num is not None:
            e = acerta_corte(num, b)
            if e:
                erros.append(e)
                continue
        c = b.get("corte") or []
        if len(c) != 2 or not (0 <= float(c[0]) < float(c[1]) <= dur + .5):
            erros.append(f"trecho \"{(b.get('trecho') or '')[:40]}\" com corte fora do áudio ({c}; o áudio tem {dur} s)")
        elif not 1.2 <= float(c[1]) - float(c[0]) <= 15:
            erros.append(f"trecho \"{(b.get('trecho') or '')[:40]}\" com {float(c[1]) - float(c[0]):.1f} s (a frase de impacto inteira, até 15 s)")
    # 22/10/2026 ("aprovo o plano roteiro-com-direcao"): a duração conta (9 de 11 primeiras versões passavam de 60 s);
    # 6 s de folga sobre o alvo do formato (o Fomos conferir vai até 70 s) antes de pedir de novo
    alvo = 70 if (num is not None and E.ler_ficha(num).get("molde") == "conferir") else 60
    # 26/10/2026 (ele: "as regras são uma orientação [...] o agente não pode se negar"): o tamanho que ele pediu manda
    pedido = E.ler_ficha(num).get("alvo_segundos") if num is not None else None
    if isinstance(pedido, int) and pedido > 0:
        alvo = pedido
    est = sum(len((b.get("fala") or "").split()) / 2.9 for b in nossos) + sum(
        float(b["corte"][1]) - float(b["corte"][0]) for b in outros if len(b.get("corte") or []) == 2)
    # 26/10/2026 (ele: "pode ser que tenha vídeo que fique mais longo se eu colocar mais assunto, isso vai servir inclusive
    # para testar outros formatos"): com material que ele acrescentou (o caderno) ou tamanho pedido por ele, passar do alvo
    # é aviso para ele decidir, não corte (cortaria o que ele trouxe)
    dele = num is not None and (bool(caderno.itens(num)) or isinstance(pedido, int) and pedido > 0)
    if est > alvo + 6 and dele:
        E.evento(num, f"tamanho: o roteiro tem uns {est:.0f} s, acima do alvo de {alvo} s; fica para ele decidir (material dele)")
    elif est > alvo + 6:
        erros.append(f"o roteiro tem uns {est:.0f} s e o alvo é até {alvo} s: corte afirmação fraca, bloco que repete ou trecho longo")
    if re.search(r"@\w", json.dumps(bs, ensure_ascii=False)):
        erros.append("o roteiro cita um @")
    if "—" in json.dumps(R, ensure_ascii=False):
        erros.append("tem travessão longo")
    return erros


# --- um escritor, as mesmas regras (Etapa C, 26/10/2026, ele: "pode seguir"): o ajuste do agente do chat passa pela
# mesma conferência do roteirista (duração, cortes, travessão, @); antes só se via se a tabela estava inteira ---------

CORTE_NA_FALA = re.compile(r"^(.*?)\s*\((\d+(?:[,.]\d+)?)-(\d+(?:[,.]\d+)?)\)\s*$")


def regras_quebradas(num, texto=None):
    """O que a conferência do roteirista (confere) acha no ROTEIRO.md de agora (ou em `texto`)."""
    bs = []
    for b in E.blocos(num, texto):
        if "material/" in b["fala"]:          # trecho de outro vídeo baixado, que ele pediu: tem a conferência dele
            continue
        x = {"bloco": b["bloco"], "quem": b["quem"], "fala": b["fala"], "tela": b["tela"]}
        m = CORTE_NA_FALA.match(b["fala"]) if not b["nosso"] else None
        if m:
            x.update(trecho=m.group(1), corte=[float(m.group(2).replace(",", ".")), float(m.group(3).replace(",", "."))])
        bs.append(x)
    try:
        meta = json.loads((E.pasta(num) / "referencia/meta.json").read_text())
    except (OSError, ValueError):
        meta = {}
    return confere({"blocos": bs}, E.ler_ficha(num), meta, num)


def tipo_do_erro(e):
    return re.sub(r"\d+(?:[,.]\d+)?", "#", e)


def conserta_roteiro_md(num):
    """O conserto mecânico (travessão, @) direto nas linhas da tabela do ROTEIRO.md. Devolve o que consertou."""
    arq = E.pasta(num) / "ROTEIRO.md"
    if not arq.exists():
        return []
    feitos, linhas = set(), []
    for l in arq.read_text().split("\n"):
        if l.startswith("| "):
            n = re.sub(r"\s*—\s*", ", ", l)
            if n != l:
                feitos.add("travessão")
            m = re.sub(r"@(\w)", r"\1", n)
            if m != n:
                feitos.add("@")
            l = m
        linhas.append(l)
    if feitos:
        E._grava(arq, "\n".join(linhas))
    return sorted(feitos)


def grava(num, R, ficha, reescrita=False):
    """reescrita (Etapa B, 26/10/2026): a ANALISE.md fica e a CHECAGEM.md só ganha as linhas de "fatos_novos"."""
    p = E.pasta(num)
    linhas = [f"# Roteiro v1 · #{num} · {R.get('titulo', '')}", "",
              f"Ângulo: {R.get('angulo', '')}", "",
              "| # | Bloco | Quem | Fala | Tela |", "|---|---|---|---|---|"]
    for i, b in enumerate(R["blocos"], 1):
        quem = (b.get("quem") or "").strip()
        fala = " ".join((b.get("fala") or b.get("trecho") or "").split())
        if b.get("corte"):
            a_, z_ = (f"{float(x):.2f}".replace(".", ",") for x in b["corte"])
            fala = f"{' '.join((b.get('trecho') or fala).split())} ({a_}-{z_})"
        cel = lambda s: " ".join(str(s).split()).replace("|", "/")
        linhas.append(f"| {i} | {cel(b.get('bloco', ''))} | {cel(quem)} | {cel(fala)} | {cel(b.get('tela', ''))} |")
    if (p / "ROTEIRO.md").exists():
        E.foto_roteiro(num)
    E._grava(p / "ROTEIRO.md", "\n".join(linhas) + "\n")          # atômico (25/10/2026)
    if reescrita:
        antes = (p / "CHECAGEM.md").read_text() if (p / "CHECAGEM.md").exists() else ""
        if R.get("checagem_md"):
            E.evento(num, "o roteirista devolveu a checagem inteira na reescrita; ficou a de antes (só os fatos novos entram)")
        E._grava(p / "CHECAGEM.md", junta_fatos(antes, R.get("fatos_novos")))
    else:
        E._grava(p / "ANALISE.md", (R.get("analise_md") or "").strip() + "\n")
        E._grava(p / "CHECAGEM.md", (R.get("checagem_md") or "").strip() + "\n")
    q = R.get("quem_fala") or {}
    # intencao-viva (24/10/2026): as decisões dele anotadas pelo porteiro ficam quando o roteiro é reescrito
    antes = (p / "INTENCAO.md").read_text() if (p / "INTENCAO.md").exists() else ""
    decisoes = antes[antes.index(E.DECISOES):].rstrip() + "\n" if E.DECISOES in antes else ""
    (p / "INTENCAO.md").write_text(f"# O que queremos mostrar\n\nÂngulo: {R.get('angulo', '')}\n"
                                   + (f"\nO Alexandre escreveu na pauta: \"{ficha['texto_dele']}\"\n" if ficha.get("texto_dele") else "")
                                   + (f"\nQuem fala no vídeo da pauta: {q.get('nome')} ({q.get('quem_e', '')}). Prova: {q.get('prova', '')}\n" if q.get("nome") else "")
                                   + (f"\n{decisoes}" if decisoes else ""))


def capa_original(num):
    """17/10/2026 ("aprovo o plano referencia-na-lista"): a capa do original para o cartão da lista
    (referencia/capa-original.jpg): a 1ª imagem do material; senão a capa do post (thumbnail do yt-dlp); senão um
    quadro do vídeo ou o 1º dos 6 quadros."""
    import io, urllib.request
    from PIL import Image
    ref = E.pasta(num) / "referencia"; alvo = ref / "capa-original.jpg"
    def grava(im):
        im = im.convert("RGB"); im.thumbnail((480, 600)); im.save(alvo, quality=85); return alvo
    m = ref / "material"
    ims = sorted(x for x in m.glob("*.jpg")) if m.exists() else []
    if ims:
        return grava(Image.open(ims[0]))
    for nome in ("video.info.json", "audio.info.json"):
        if (ref / nome).exists():
            info = json.loads((ref / nome).read_text())
            url = info.get("thumbnail") or next((x.get("url") for x in reversed(info.get("thumbnails") or []) if x.get("url")), None)
            if url:
                try:
                    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
                    return grava(Image.open(io.BytesIO(urllib.request.urlopen(req, timeout=30).read())))
                except Exception:
                    pass
    if (ref / "video.mp4").exists():
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", "1", "-i", str(ref / "video.mp4"), "-frames:v", "1", str(alvo)], check=True)
        return grava(Image.open(alvo))
    q = sorted((ref / "imagens").glob("*.jpg")) if (ref / "imagens").exists() else []
    return grava(Image.open(q[0])) if q else None


def material_da_pauta(num, link):
    """17/10/2026 ("aprovo o plano material-qualquer"): baixa o material (ou fotografa a tela) e os Olhos leem."""
    import material, olhos_ponte
    passo(num, "baixando o material")
    meta = material.baixar(num, link)
    passo(num, "lendo o material")
    m = E.pasta(num) / "referencia/material"
    try:
        olhos_ponte.ler_material(m, m / "texto.txt" if (m / "texto.txt").exists() else None)
    except Exception as ex:
        E.evento(num, f"os Olhos não leram o material: {str(ex)[:200]}")
    return meta


def conserta_mecanico(R):
    """26/10/2026 (Etapa A da revisão do roteirista, ele: "pode fazer"): o que se corrige no texto sem chamar o roteirista
    de novo (das 14 recusas da conferência, várias eram travessão ou @ e custavam o roteiro inteiro, 2 a 3 min).
    Travessão longo vira vírgula; "@nome" vira "nome". Devolve o que consertou."""
    feitos = set()

    def limpa(v, arroba=False):
        if isinstance(v, str):
            n = re.sub(r"\s*—\s*", ", ", v)
            if n != v:
                feitos.add("travessão")
            m = re.sub(r"@(\w)", r"\1", n) if arroba else n          # @ só nos blocos (a checagem pode ter e-mail)
            if m != n:
                feitos.add("@")
            return m
        if isinstance(v, list):
            return [limpa(x, arroba) for x in v]
        if isinstance(v, dict):
            return {k: limpa(x, arroba) for k, x in v.items()}
        return v
    R.update({k: limpa(v, k == "blocos") for k, v in R.items()})
    return sorted(feitos)


CONSERTO = """Você é o roteirista da @newsbr360. O roteiro abaixo está quase pronto, mas a conferência achou problemas.
CONSERTE SÓ ESSES PROBLEMAS e mantenha todo o resto como está: os mesmos blocos, a mesma ordem, as mesmas falas, telas,
trechos e selos onde não há problema. Não pesquise: os fatos que você pode usar são os da CHECAGEM abaixo. Se o problema é
o tempo, corte ou junte blocos (a fala de outra pessoa só se corta, nunca se troca). Se é um fato sem fonte, troque pelo
que a CHECAGEM confirma ou tire.

OS PROBLEMAS:
{problemas}

{regras}

CHECAGEM.md (os fatos com fonte):
{checagem}

O ROTEIRO (JSON):
{roteiro}

Devolva SÓ o mesmo JSON, com os mesmos campos, consertado."""


def consertar(num, R, problemas):
    """26/10/2026 (#408: três reescritas inteiras de 4 min e US$ 0,80 a 1,19 cada, para trocar "mais da metade" por "maior
    bancada" e cortar 20 s; ele: "não deveria refazer tudo"): o problema pontual se conserta no roteiro que já existe,
    sem pesquisa nova. Devolve o R consertado (ou o mesmo, se o conserto não veio)."""
    import ia
    regras = (E.RAIZ / "regras/ROTEIRISTA.md").read_text() + E.molde(num) + E.regra_idioma(num)
    resp, _ = ia.chamar(CONSERTO.format(problemas="\n".join(f"- {x}" for x in problemas), regras=regras,
                                        checagem=_ler(E.pasta(num), "CHECAGEM.md", 40000),
                                        roteiro=json.dumps(R, ensure_ascii=False)),
                        "roteirista (conserto)", "sonnet", num=num, limite=240)
    novo = ia.json_de(resp)
    if not isinstance(novo, dict) or not novo.get("blocos"):
        E.evento(num, "o conserto não veio; fica a versão de antes para a reescrita")
        return None
    for k, v in R.items():                       # o que o conserto não devolveu fica como estava
        novo.setdefault(k, v)
    return novo


def _roteiro_texto(R):
    return "\n".join(f"{i}. {b.get('bloco', '')} · {b.get('quem', '')}: {b.get('fala', '')} | Tela: {b.get('tela', '')}"
                     for i, b in enumerate(R.get("blocos") or [], 1))


def escrever(num, ficha, meta, trans, extra="", reescrita=False, proposta=None):
    """O roteirista escreve e o roteiro é gravado; devolve a ficha. Se a conferência recusa (ou, com proposta, o roteiro
    foge dela), desde 26/10/2026 o roteiro se CONSERTA (consertar, sem pesquisa); só se o conserto não vier o roteirista
    escreve de novo."""
    import fluidez
    gastas = fluidez.gastas(E.RAIZ)
    R = None
    # 1: escreve · 2: confere o conserto (ou a reescrita de fluidez) · 3: só se o conserto não resolveu, escreve de novo
    for tentativa in (1, 2, 3):
        if R is None:
            R = pedir_roteiro(num, ficha, meta, trans, extra)
        feitos = conserta_mecanico(R)
        if feitos:
            E.evento(num, "consertado no texto, sem pedir de novo: " + ", ".join(feitos))
        erros = confere(R, ficha, meta, num)
        fuga = [] if erros or not proposta else _confere_proposta(num, proposta, _roteiro_texto(R))
        if fuga and tentativa > 1:               # como antes: fugir um pouco da proposta depois de corrigir é aviso
            E.evento(num, "ainda diferente da proposta (aviso): " + "; ".join(fuga))
            fuga = []
        erros += [f"fugiu da proposta: {x}" for x in fuga]
        # 24/10/2026 ("aprovo o plano roteiro-fluido"): sem erro, o programa confere a fluidez; o que achar volta ao
        # roteirista uma vez ("reescreva só esses trechos"), e na segunda vez fica como aviso (não trava o vídeo)
        flu = [] if erros else fluidez.problemas(R.get("blocos") or [], gastas)
        if not erros and (not flu or tentativa > 1):
            if flu:
                E.evento(num, "fluidez: ficou assim (aviso): " + "; ".join(flu))
            break
        if tentativa == 3:
            raise RuntimeError("o roteiro veio com problema mesmo depois do conserto: " + "; ".join(erros))
        if erros and tentativa == 1:
            E.evento(num, "roteiro com problema, consertando só isso (sem reescrever): " + "; ".join(erros))
            R = consertar(num, R, erros)
            if R is None:
                ficha = dict(ficha, texto_dele=(ficha.get("texto_dele") or "") +
                             "\n\nA VERSÃO ANTERIOR FOI RECUSADA. Corrija: " + "; ".join(erros))
        elif erros:
            E.evento(num, "o conserto não resolveu, escrevendo de novo: " + "; ".join(erros))
            R = None
            ficha = dict(ficha, texto_dele=(ficha.get("texto_dele") or "") +
                         "\n\nA VERSÃO ANTERIOR FOI RECUSADA. Corrija: " + "; ".join(erros))
        else:
            R = None
            E.evento(num, "fluidez: pedindo para reescrever só os trechos: " + "; ".join(flu))
            ficha = dict(ficha, texto_dele=(ficha.get("texto_dele") or "") +
                         "\n\nA VERSÃO ANTERIOR ESTAVA CERTA NOS FATOS, MAS DURA. Mantenha os mesmos fatos, provas, trechos e blocos e "
                         "reescreva só estes pontos de fluidez: " + "; ".join(flu))
    grava(num, R, E.ler_ficha(num), reescrita=reescrita)
    # os 3 ganchos (fluxo-viral-util): ficam na ficha (o cérebro do radar aprende qual família rende) e no Resumo da tela
    gs = [g for g in (R.get("ganchos") or []) if isinstance(g, dict) and g.get("texto")][:3]
    if gs:
        rec = next((g for g in gs if g.get("recomendado")), gs[0])
        E.mexe_ficha(num, nicho=ficha.get("nicho") or NICHO_PADRAO, ganchos=gs, gancho_familia=rec.get("familia") or "livre")
        an = E.pasta(num) / "ANALISE.md"
        an.write_text(an.read_text().rstrip() + "\n\n## Ganchos (3 opções)\n" + "\n".join(
            f"- {'**(o que abre)** ' if g is rec else ''}\"{g['texto']}\" · família {g.get('familia') or 'livre'}" for g in gs) + "\n")
    formato = R.get("formato") if R.get("formato") in ("checagem", "analise") else ("checagem" if ficha["tipo"] == "analisar" else "analise")
    if E.ler_ficha(num).get("formato_pedido") in ("checagem", "analise"):      # 19/10/2026: o botão Análise manda
        formato = E.ler_ficha(num)["formato_pedido"]
    return E.mexe_ficha(num, titulo=R.get("titulo", "")[:80], nota=R.get("nota"), formato=formato, passo="roteiro pronto",
                        passo_desde=E.agora(), esperando="Aprovar o roteiro", mudou=[])


# --- reescrever com outra direção (22/10/2026, "aprovo o plano roteiro-com-direcao"; ele: "posso pedir para reescrever
# como Análise ou Fazer igual. e ainda depois de escrito posso pedir ajustes. e o roteirista tem que entender esse meu
# pedido e pensar em novas direções para o roteiro") ---------------------------------------------------------------

DIRECOES = {
    "checagem": "CHECAGEM: alguém disse algo e a gente confere cada afirmação, com o veredito de cada uma e o placar no fim.",
    "analise": "ANÁLISE: parte de um fato com fonte, mostra as consequências com dados e fecha com a NOSSA conclusão; "
               "carimbos do tipo de informação (fato oficial, previsão, opinião), sem placar.",
    "fazer_igual": "FAZER IGUAL: o vídeo da pauta é só a referência de formato e assunto; o NOSSO vídeo, todas as falas na "
                   "voz do Alexandre, sem nenhum trecho da referência e sem citar quem aparece nela.",
    "angulo": "o MESMO formato de agora, com outro ângulo, gancho ou tese, como ele pediu.",
}
ARQS_ROTEIRO = ("ROTEIRO.md", "CHECAGEM.md", "ANALISE.md", "INTENCAO.md")
CAMPOS_ROTEIRO = ("tipo", "formato", "formato_pedido", "molde", "titulo", "nota")


def guardar_versao(num, motivo):
    """O roteiro inteiro de agora (os 4 arquivos e o formato da ficha) em versoes/roteiro-<quando>/. Devolve a pasta."""
    p = E.pasta(num)
    from datetime import datetime
    # microssegundos: "volta" duas vezes no mesmo segundo dava o mesmo nome e a versão guardada era apagada (teste, 22/10)
    d = p / "versoes" / f"roteiro-{datetime.now():%Y%m%d-%H%M%S-%f}"
    d.mkdir(parents=True)
    for a in ARQS_ROTEIRO:
        if (p / a).exists():
            (d / a).write_text((p / a).read_text())
    f = E.ler_ficha(num)
    (d / "ficha.json").write_text(json.dumps({"motivo": motivo, **{k: f.get(k) for k in CAMPOS_ROTEIRO}}, ensure_ascii=False, indent=1))
    return d


def _ler(p, nome, lim=12000):
    return (p / nome).read_text()[:lim] if (p / nome).exists() else "(não existe)"


def _volta_para_roteiro(num):
    """Na etapa Roteiro e voz a voz já foi gravada: o roteiro novo volta a esperar "Aprovar o roteiro" (a voz regrava
    depois, como em voltar_roteiro)."""
    if E.ler_ficha(num)["etapa"] == "Roteiro e voz":
        E.mexe_ficha(num, etapa="Pauta")


# --- mudança de direção: proposta antes (25/10/2026, ele: "o roteirista receber meu pedido e antes de mudar, propor
# como poderia ficar. aí eu aprovo e ele muda"; #393: "até os aliados estão se voltando contra ele" saiu com a abertura
# e o fecho novos e o meio da checagem antiga, porque o roteiro velho ia inteiro como base) ---------------------------

PEDIDO_PROPOSTA = """Você é o roteirista da @newsbr360. As regras da página estão abaixo. Ele (o editor) quer MUDAR A
DIREÇÃO deste vídeo. Antes de escrever, mostre a ele como entendeu, para ele aprovar ou corrigir. Não escreva o roteiro.

O PEDIDO DELE (é isto que manda; as regras só dizem como fazer bem, não mudam o que ele quer):
"{instrucao}"
{anterior}
Direção: {direcao}

A proposta segue a TESE e a ORDEM que ele disse, nas palavras dele. Se ele deu uma sequência ("primeiro X, aí entra a
fala dela, aí a gente conclui"), os blocos seguem essa sequência. O roteiro de agora é só de onde tirar fatos: o que não
serve para a tese dele SAI, e diga o que sai. Se uma regra da página bate de frente com o pedido (ex.: a regra manda
avisar de uma investigação e ele não quer), não decida por ele: ponha em "pergunta". Tom mais duro ou crítico pedido
por ele: siga, e avise do risco em "pergunta" se houver (alertar sim, barrar não). Se a mensagem parece cortada no
meio (ditado), diga em "pergunta" o que entendeu da parte final.

{regras}

Formato de agora: {formato} · tipo de pauta: {tipo}
O roteiro de agora (ROTEIRO.md):
{roteiro}

CHECAGEM.md (os fatos com fonte):
{checagem}

Transcrição do vídeo da pauta (as falas que podem entrar como trecho):
{trans}
{material}
{conversa}
Responda SÓ um JSON:
{{"tese": "<a frase que o vídeo defende>", "blocos": ["<bloco 1 em uma linha: o que diz e quem fala>", "..."],
"sai": ["<o que sai do roteiro de agora>"], "fica": ["<os fatos de agora que continuam>"], "segundos": 45,
"pergunta": "<só se precisa da decisão dele; senão vazio>"}}"""


def _construido(num, ant):
    """26/10/2026 (#408, ele: "eu sempre vou tentar construir textos únicos com base em ideias e referências"): o que ele
    e o agente conversaram desde a proposta anterior (as peças que ele acrescentou e o que a pesquisa achou) entra na
    proposta nova; antes só ia a última mensagem."""
    desde = (ant or {}).get("quando", "")
    xs = [m for m in E.chat(num) if m.get("quem") in ("ele", "agente") and m.get("quando", "") > desde][-16:]
    if not xs:
        return ""
    linhas = "\n".join(f"- {'ELE' if m['quem'] == 'ele' else 'AGENTE'}: {m['texto'][:1200]}" for m in xs)
    return ("\nO QUE ELE CONSTRUIU NA CONVERSA (as peças que acrescentou e o que a pesquisa achou; tudo que ele trouxe "
            "entra na proposta, cada fato com o que a pesquisa disse dele; o que não foi confirmado entra como opinião nossa "
            "ou pergunta):\n" + linhas + "\n")


def propor_mudanca(num, direcao, instrucao):
    """A proposta curta da mudança de direção (Opus, sem busca): fica na ficha ("proposta") esperando ele aprovar no
    chat; aprovar chama aplicar_proposta. Devolve a mensagem para o chat."""
    if direcao not in DIRECOES:
        direcao = "angulo"
    p = E.pasta(num)
    f = E.ler_ficha(num)
    ant = f.get("proposta")
    anterior = (f"\nA PROPOSTA ANTERIOR, que ele está corrigindo agora (mantenha o que ele não mandou mudar):\n{ant['texto']}\n"
                f"O pedido original dele: \"{ant.get('pedido', '')[:1500]}\"\n") if ant else ""
    pedido = PEDIDO_PROPOSTA.format(instrucao=instrucao.strip()[:2500], anterior=anterior, direcao=DIRECOES[direcao],
                                    regras=(E.RAIZ / "regras/ROTEIRISTA.md").read_text() + E.molde(num) + E.regra_idioma(num),
                                    formato=f.get("formato") or "?", tipo=E.TIPOS.get(f.get("tipo"), f.get("tipo")),
                                    roteiro=_ler(p, "ROTEIRO.md"), checagem=_ler(p, "CHECAGEM.md"),
                                    trans=_ler(p, "referencia/transcricao.txt", 6000), material=caderno.para_pedido(num),
                                    conversa=_construido(num, ant))
    import ia
    resp, _ = ia.chamar(pedido, "roteirista (proposta)", "opus", num=num, limite=300, cwd=p)
    R = ia.json_de(resp) or {}
    if not R.get("blocos"):
        return "Não consegui montar a proposta agora (o roteirista não respondeu). Pode pedir de novo?"
    nome = {"checagem": "Checagem", "analise": "Análise", "fazer_igual": "Fazer igual"}.get(direcao, "outro ângulo")
    texto = (f"**Tese:** {R.get('tese', '')}\n\n**Ordem:**\n" +
             "\n".join(f"{i}. {re.sub(r'^\s*\d+\s*[·.)-]\s*', '', str(b))}" for i, b in enumerate(R["blocos"], 1)) +
             ("\n\n**Sai:**\n" + "\n".join(f"- {x}" for x in R["sai"]) if R.get("sai") else "") +
             ("\n\n**Fica:**\n" + "\n".join(f"- {x}" for x in R["fica"]) if R.get("fica") else "") +
             f"\n\nUns {R.get('segundos') or '?'} s, como {nome}.")
    pedido_dele = (ant.get("pedido", "") + "\n\nCorreção dele: " + instrucao) if ant else instrucao
    E.mexe_ficha(num, proposta={"direcao": direcao, "texto": texto, "pedido": pedido_dele[:4000], "quando": E.agora(),
                                "tese": str(R.get("tese") or "")[:400]})
    E.evento(num, f"proposta de mudança ({direcao}) esperando ele")
    perg = (R.get("pergunta") or "").strip()
    return ("Entendi como **mudança de direção**. Antes de reescrever, veja se é isto:\n\n" + texto +
            (f"\n\n**Preciso que você decida:** {perg}" if perg else "") +
            "\n\nSe estiver certo, toque em Aprovar a direção (ou responda \"aprovo\"). Se não, diga o que mudar que eu refaço a proposta.")


def aplicar_proposta(num, aprovacao=""):
    """Ele aprovou: o roteiro sai seguindo a proposta (esqueleto obrigatório). aprovacao: a mensagem do "aprovo", que
    pode trazer a resposta à pergunta da proposta ("aprovo, sem a linha na tela")."""
    pr = E.ler_ficha(num).get("proposta")
    if not pr:
        return "Não há proposta esperando. Diga como quer o vídeo que eu monto uma."
    texto = pr["texto"] + (f"\n\nAO APROVAR, ELE DISSE (vale junto com a proposta): \"{aprovacao.strip()[:1500]}\""
                           if aprovacao.strip() else "")
    return reescrever(num, pr["direcao"], pr["pedido"], proposta=texto)


CONFERE_PROPOSTA = """Compare o ROTEIRO com a PROPOSTA que o editor aprovou. O roteiro segue a tese e a ordem dos blocos
da proposta, e deixou de fora o que a proposta tirou? Pequenas diferenças de palavras e um bloco a mais ou a menos de
ligação estão certos. Responda SÓ um JSON: {{"segue": true|false, "faltas": ["<o que fugiu da proposta, curto>"]}}

PROPOSTA:
{proposta}

ROTEIRO:
{roteiro}"""


def _confere_proposta(num, proposta, roteiro=None):
    import ia
    resp, _ = ia.chamar(CONFERE_PROPOSTA.format(proposta=proposta, roteiro=roteiro or _ler(E.pasta(num), "ROTEIRO.md")),
                        "conferência da proposta", "sonnet", num=num, limite=120)
    R = ia.json_de(resp) or {}
    return [] if R.get("segue", True) else [str(x) for x in R.get("faltas") or []][:6]


# 26/10/2026 (Etapa B da revisão do roteirista; ele: "ler tudo de novo para refazer coisas, acho que pode ter erro ai"):
# na reescrita a CHECAGEM é um caderno que só cresce. Antes ela era escrita de novo inteira a cada reescrita: 91% do texto
# já existia (lento), e no #405 os fatos das três AIJEs viraram uma linha "já conferidos antes" e sumiram do caderno.
RESPOSTA_REESCRITA = """
## RESPOSTA DESTA REESCRITA (vale no lugar da seção "Resposta" das regras)
A CHECAGEM acima é o caderno de fatos do vídeo: NÃO a reescreva, não resuma, não tire linha. Use os fatos dela nas falas.
Fato NOVO que você pesquisar agora vai em "fatos_novos", uma linha por fato, no mesmo formato da tabela
("| afirmação | fonte original com link | tipo |"); ele é acrescentado no fim do caderno. Não devolva "checagem_md" nem
"analise_md" (a análise da pauta fica como está). Responda SÓ um JSON:
{"titulo": "", "formato": "checagem ou analise", "nota": 0, "ganchos": [{"texto": "", "familia": "", "recomendado": true}],
 "angulo": "", "quem_fala": {}, "fatos_novos": ["| ... | ... | ... |"], "blocos": [...como nas regras...]}
"""


def junta_fatos(antes, novos):
    """O caderno de fatos com as linhas novas no fim (só linhas de tabela que ainda não estão lá). Devolve o texto."""
    linhas = [" ".join(str(x).split()) for x in novos or [] if str(x).strip().startswith("|")]
    linhas = [l for l in linhas if l not in antes]
    if not linhas:
        return antes
    if "|---" not in antes:
        antes = antes.rstrip() + ("\n\n" if antes.strip() else "") + "| Afirmação | Fonte original | Tipo |\n|---|---|---|"
    return antes.rstrip() + "\n" + "\n".join(linhas) + "\n"


def reescrever(num, direcao, instrucao, proposta=None):
    """O roteirista (Opus, com a busca) escreve o vídeo de novo na direção pedida, com a checagem que já existe. O
    roteiro de antes fica em versoes/. Devolve a mensagem para o chat. proposta: a que ele aprovou (25/10/2026): vira o
    esqueleto obrigatório, o roteiro de agora não vai como base e o resultado é conferido contra ela."""
    if direcao not in DIRECOES:
        direcao = "angulo"
    p = E.pasta(num)
    f = E.ler_ficha(num)
    antes = guardar_versao(num, f"antes de reescrever ({direcao}): {instrucao[:200]}")
    tem_fala = (p / "referencia/palavras.json").exists()
    # a direção muda o formato (e o tipo, no Fazer igual); o Fomos conferir é Checagem, então sai na Análise e no Fazer igual
    if direcao == "checagem":
        E.mexe_ficha(num, formato_pedido="checagem", **({"tipo": "analisar"} if tem_fala else {}))
    elif direcao == "analise":
        E.mexe_ficha(num, formato_pedido="analise", molde="")
    elif direcao == "fazer_igual":
        E.mexe_ficha(num, formato_pedido="analise", molde="", tipo="igual")
    f = E.ler_ficha(num)
    E.evento(num, f"reescrevendo o roteiro ({direcao}); o de antes em {antes.relative_to(p)}")
    try:
        meta = json.loads((p / "referencia/meta.json").read_text())
    except (OSError, ValueError):
        meta = {}
    trans = _ler(p, "referencia/transcricao.txt", 14000) if (p / "referencia/transcricao.txt").exists() else ""
    if proposta:
        extra = f"""

## REESCREVER ESTE ROTEIRO SEGUINDO A PROPOSTA QUE ELE APROVOU (é a ordem principal; acima de qualquer regra de estilo)
Direção: {DIRECOES[direcao]}
O pedido dele: "{instrucao.strip()[:2500]}"

A PROPOSTA APROVADA (tese e ordem dos blocos: siga as duas; o que ela tirou não entra):
{proposta}

É um vídeo novo, não remendo do roteiro antigo (o antigo não vai aqui de propósito: no #393 ele virou molde e o meio
saiu igual). Os fatos da CHECAGEM abaixo já foram conferidos com fonte: use os que a proposta pede e confira na web só o
que for novo. A fala de outra pessoa continua sendo as palavras exatas da transcrição. Trecho só do vídeo da pauta.

CHECAGEM.md (o caderno de fatos; fica como está):
{_ler(p, 'CHECAGEM.md', 60000)}
{RESPOSTA_REESCRITA}
LEMBRE: a tese e a ordem são as da proposta aprovada acima.
"""
    else:
        extra = f"""

## REESCREVER ESTE ROTEIRO (pedido dele, agora)
Direção: {DIRECOES[direcao]}
O pedido dele: "{instrucao.strip()[:2000]}"

Não é remendo: escreva o vídeo de novo nesta direção, seguindo as regras acima (duração, falas, trechos, fecho). Os
fatos da CHECAGEM abaixo já foram conferidos com fonte: aproveite o que servir e confira na web só o que for novo. A
fala de outra pessoa continua sendo as palavras exatas da transcrição. Trecho só do vídeo da pauta (a transcrição
acima): os trechos do roteiro de agora com "material/" no corte vêm de outros vídeos baixados e não entram aqui (no
#306, 22/10, um deles fez a primeira versão ser recusada); o que eles provam pode ir na nossa voz, com a fonte.

O roteiro de agora (ROTEIRO.md):
{_ler(p, 'ROTEIRO.md')}

CHECAGEM.md (o caderno de fatos; fica como está):
{_ler(p, 'CHECAGEM.md', 60000)}

ANALISE.md:
{_ler(p, 'ANALISE.md', 4000)}
{RESPOSTA_REESCRITA}"""
    E.mexe_ficha(num, passo="escrevendo o roteiro", passo_desde=E.agora(), erro="")
    etapa0 = f["etapa"]
    _volta_para_roteiro(num)              # antes de gravar: o vigia regravaria a voz em Roteiro e voz
    try:
        # 26/10/2026: a conferência da proposta vai dentro do escrever, antes de gravar; o que fugiu se conserta
        escrever(num, f, meta, trans, extra, reescrita=True, proposta=proposta)
        if proposta:
            # 26/10/2026 (Etapa A): a tese aprovada fica como decisão do vídeo (INTENCAO.md, que todos leem); o pedido
            # seguinte parte dela, não da linha antiga
            tese = (E.ler_ficha(num).get("proposta") or {}).get("tese")
            if tese:
                E.anota_decisao(num, f"Direção aprovada: {tese}", instrucao)
            E.mexe_ficha(num, proposta=None)
    except Exception as ex:
        # escrever só grava os arquivos no fim, com o roteiro aceito: aqui eles não mudaram; volta o formato e a etapa
        campos = json.loads((antes / "ficha.json").read_text())
        E.mexe_ficha(num, etapa=etapa0, **{k: campos.get(k) for k in CAMPOS_ROTEIRO})
        raise RuntimeError(f"o roteiro novo não saiu ({str(ex)[:200]}); o de antes continua") from ex
    bs = E.blocos(num)
    nome = {"checagem": "Checagem", "analise": "Análise", "fazer_igual": "Fazer igual"}.get(direcao, "um ângulo novo")
    if proposta:
        return (f"Reescrevi seguindo a proposta que você aprovou: {len(bs)} blocos, uns {E.segundos(bs)} s. O roteiro de "
                "antes ficou guardado. Se estiver bom, toque em Aprovar o roteiro.")
    return (f"Reescrevi como {nome}: {len(bs)} blocos, uns {E.segundos(bs)} s. O roteiro de antes ficou guardado; se "
            "quiser ele de volta, é só pedir. Se estiver bom, toque em Aprovar o roteiro.")


def voltar_versao(num, pasta_versao=None, guardar=True):
    """Volta o roteiro inteiro guardado (o último, sem pasta_versao). O de agora também fica guardado, para ir e voltar."""
    p = E.pasta(num)
    vs = sorted(x for x in (p / "versoes").glob("roteiro-*") if x.is_dir()) if (p / "versoes").exists() else []
    d = pasta_versao or (vs[-1] if vs else None)
    if not d:
        return "Não há versão anterior guardada deste roteiro."
    if guardar:
        guardar_versao(num, f"antes de voltar a {d.name}")
    _volta_para_roteiro(num)
    for a in ARQS_ROTEIRO:
        if (d / a).exists():
            (p / a).write_text((d / a).read_text())
    campos = json.loads((d / "ficha.json").read_text())
    E.mexe_ficha(num, **{k: campos.get(k) for k in CAMPOS_ROTEIRO}, passo="roteiro pronto", passo_desde=E.agora(),
                 esperando="Aprovar o roteiro", mudou=[])
    E.evento(num, f"roteiro voltou à versão {d.name}")
    bs = E.blocos(num)
    return f"Voltei o roteiro de antes ({len(bs)} blocos, uns {E.segundos(bs)} s). O que estava agora também ficou guardado."


PEDIDO_DIRECOES = """Você é o roteirista da @newsbr360. As regras da página estão abaixo. Ele leu o roteiro deste vídeo e
quer ver OUTRAS DIREÇÕES antes de escolher. Não escreva o roteiro: proponha de 2 a 3 direções bem diferentes entre si
(formato, gancho, tese ou público), que este material e esta checagem sustentam. Para cada uma: um nome curto, o formato
(checagem, analise ou fazer_igual), a primeira frase que a voz diria, e por que pode render, em uma linha, comparando
com o que já rendeu na página. Use só fatos da CHECAGEM (nada novo sem fonte).

Responda SÓ um JSON: {{"direcoes": [{{"nome": "", "formato": "checagem|analise|fazer_igual", "gancho": "", "por_que": ""}}]}}

{regras}

## Este vídeo (#{num}) · formato de agora: {formato} · tipo de pauta: {tipo}
O pedido dele: "{instrucao}"

ROTEIRO.md:
{roteiro}

CHECAGEM.md:
{checagem}

Transcrição do vídeo da pauta (mm:ss frase):
{trans}
"""


def propor(num, instrucao):
    """De 2 a 3 direções novas para ele escolher (Opus, sem busca: só o material e a checagem que já existem)."""
    p = E.pasta(num)
    f = E.ler_ficha(num)
    pedido = PEDIDO_DIRECOES.format(regras=(E.RAIZ / "regras/ROTEIRISTA.md").read_text() + E.molde(num) + E.regra_idioma(num) + E.memoria(num), num=num,
                                    formato=f.get("formato") or "?", tipo=E.TIPOS.get(f.get("tipo"), f.get("tipo")),
                                    instrucao=instrucao.strip()[:1500], roteiro=_ler(p, "ROTEIRO.md"), checagem=_ler(p, "CHECAGEM.md"),
                                    trans=_ler(p, "referencia/transcricao.txt", 6000), material=caderno.para_pedido(num))
    import ia                                 # 25/10/2026: a chamada de IA de um lugar só (ia.py)
    resp, _ = ia.chamar(pedido, "roteirista (direções)", "opus", num=num, limite=600, cwd=p)
    ds = (ia.json_de(resp) or {}).get("direcoes") or []
    if not ds:
        return "Não consegui pensar nas direções agora (o roteirista não respondeu). Pode pedir de novo?"
    (p / "referencia").mkdir(exist_ok=True)
    (p / "referencia/direcoes.json").write_text(json.dumps(ds, ensure_ascii=False, indent=1))
    nomes = {"checagem": "Checagem", "analise": "Análise", "fazer_igual": "Fazer igual"}
    linhas = [f"{i}. **{d.get('nome', '')}** ({nomes.get(d.get('formato'), d.get('formato', ''))}): \"{d.get('gancho', '')}\" "
              f"{d.get('por_que', '')}" for i, d in enumerate(ds[:3], 1)]
    return "Direções para este vídeo:\n" + "\n".join(linhas) + "\n\nDiga qual quer (ex.: \"faz a 2\") que eu reescrevo."


def rodar(num):
    ficha = E.ler_ficha(num)
    try:
        meta, trans = {}, ""
        import material
        if ficha.get("link") and not material.e_material(ficha["link"]):
            passo(num, "baixando o vídeo")
            try:
                meta = baixar_pauta(num, ficha["link"])
            except SemVideo:
                E.evento(num, "o link não tem vídeo: vou pegar o material (imagens e texto)")
                meta = None
        if ficha.get("link") and (material.e_material(ficha["link"]) or meta is None):
            meta = material_da_pauta(num, ficha["link"])
        elif ficha.get("link"):
            # 17/10/2026 ("aprovo o plano olhos-na-pauta"): um espectador independente (conteudo/olhos, programa
            # separado) assiste o MESMO arquivo enquanto a pauta transcreve; o roteirista recebe as duas leituras
            video = E.pasta(num) / "referencia/video.mp4"
            olhos = None
            if video.exists():
                import threading, olhos_ponte
                def assistir():
                    try:
                        olhos_ponte.assistir(video, E.pasta(num) / "referencia/olhos")
                    except Exception as ex:
                        E.evento(num, f"olhos não assistiu a referência: {str(ex)[:200]}")
                olhos = threading.Thread(target=assistir, daemon=True); olhos.start()
            passo(num, "transcrevendo e assistindo" if olhos else "transcrevendo")
            trans = transcrever(num)
            # 23/10/2026 ("aprovo o plano olho-unico-observacao"): o caderno do olho único sai enquanto o roteiro é escrito
            import threading, olho_unico
            threading.Thread(target=olho_unico.na_pauta, args=(num,), daemon=True).start()
            if olhos:
                olhos.join(timeout=900)
        if ficha.get("link"):
            try:
                capa_original(num)
            except Exception as ex:
                E.evento(num, f"capa do original não saiu: {str(ex)[:160]}")
        # 26/10/2026 (caderno de material, parte 2; ele: "quero poder colocar mais de um link para ele analisar na
        # pauta"): os outros links do texto dele são complementares; viram fichas do caderno antes do primeiro roteiro
        extras = [l.rstrip(".,;)\"'") for l in re.findall(r"https?://\S+", ficha.get("texto_dele") or "")]
        if extras:
            passo(num, "baixando o material")
            import agente
            try:
                agente.material(num, {"texto": " ".join(dict.fromkeys(extras))})
            except Exception as ex:
                E.evento(num, f"material complementar não veio: {str(ex)[:160]}")
        passo(num, "escrevendo o roteiro")
        f = escrever(num, ficha, meta, trans)
        bs = E.blocos(num)
        E.evento(num, f"roteiro v1 pronto: {len(bs)} blocos, uns {E.segundos(bs)} s")
        E.chat_add(num, "sistema", f"Roteiro v1 pronto: {len(bs)} blocos, uns {E.segundos(bs)} s. "
                                   f"Para mudar, é só dizer o que quer. Se estiver bom, toque em Aprovar o roteiro.")
        return f
    except Exception as ex:
        msg = str(ex)[:400]
        # 24/10/2026 (ele: "veja essa msg de erro"): o erro do download em português; o técnico fica no histórico
        if re.search(r"logged.?in|login|cookies|empty media response", msg, re.I):
            msg = ("o Instagram só mostra este post para quem está logado, e o download não conseguiu"
                   + (re.search(r"(tentei \d+ vez\(es\)[^;:]*)", str(ex)) and "; " + re.search(r"(tentei \d+ vez\(es\)[^;:]*)", str(ex)).group(1) or ""))
            E.evento(num, f"erro técnico do download: {str(ex)[:300]}")
        onde = E.ler_ficha(num).get("passo") or "começo"
        E.mexe_ficha(num, passo="parou", erro=msg)
        E.evento(num, f"parou em {onde}: {msg}")
        E.chat_add(num, "sistema", f"A pauta parou em \"{onde}\": {msg}. "
                                   "Toque em Baixar de novo, ou mande outro link.")
        raise


if __name__ == "__main__":
    rodar(int(sys.argv[1]))
