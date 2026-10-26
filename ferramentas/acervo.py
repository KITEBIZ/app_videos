"""O acervo do que já baixamos (25/10/2026, "aprovo o acervo"; ele: "pelo menos para saber de onde baixamos um
determinado video e poder buscar de novo mais rapidamente, não precisamos manter os videos nas nossas pastas"). No #382
o agente procurou na web o Lula falando do "marechal" e não achou, e os reels com essa fala já estavam transcritos aqui.

Guarda só texto: de onde veio (link, quem postou, data, duração, legenda), a transcrição com mm:ss e em que vídeo nosso
foi usado. O vídeo não precisa ficar: o link basta para baixar de novo (ferramentas/baixar.py). Sem IA: busca de texto
do SQLite (FTS5, sem acento e sem maiúscula), como o ferramentas/arquivo.py das checagens.

  python3 acervo.py juntar                     refaz o acervo com tudo o que está guardado (roda sozinho ao publicar)
  python3 acervo.py buscar "<palavras>" [n]    de onde baixamos, o trecho com mm:ss e se o vídeo ainda está aqui
  python3 acervo.py buscar "<palavras>" --json
  python3 acervo.py resumo                     quantos vídeos, falas e de onde
  python3 acervo.py trazer <número> <link>     o vídeo guardado em outra pasta passa a valer neste vídeo, sem baixar:
                                               material/<código>/ (o corte é "(início-fim material/<código>)")

Onde procura: referencias/ (o que o radar ouviu), videos/<n>/referencia/ (a pauta), videos/<n>/material/ (o que ele
mandou e o que o agente baixou) e o estúdio antigo (../../newsbr360-estudio, quando existe). O banco é ACERVO_DB, ou
radar/acervo.db.
"""
import json, os, re, sqlite3, sys, time
from datetime import datetime
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
DB = Path(os.environ.get("ACERVO_DB") or RAIZ / "radar/acervo.db")
ANTIGO = Path(os.environ.get("ACERVO_ANTIGO") or RAIZ.parent.parent / "newsbr360-estudio")
# pastas que nunca são um vídeo baixado (quadros, fotos, o que o estúdio gera)
PULA = {"quadros", "imagens", "fontes", "fotos", "olhos", "olho", "node_modules", "renders", "publicacao", "animacao",
        "narracao", "versoes", "revisao", "complementos", ".git", ".venv", "__pycache__", "estudio-web", "estudio-v2"}
LINHA = re.compile(r"^(?:(\d+):)?(\d+):(\d{2})\s+(.*\S)")
# a fala de um take citada no roteiro: "Vamos lá, meu general! (4,66-8,74 material/DesTCX7RyXn)"
CITA = re.compile(r"([^|]*?)\s*\((\d+(?:[.,]\d+)?)\s*-\s*(\d+(?:[.,]\d+)?)\s+material/([\w-]+)\)")
VIDEOS = ("video.mp4", "original.mp4")


def _json(p):
    try:
        return json.loads(p.read_text())
    except (OSError, ValueError):
        return {}


def chave(link):
    """O mesmo vídeo com links diferentes (?igsh=, youtu.be, /reel/ e /p/) vira uma chave só."""
    if not link:
        return ""
    m = re.search(r"instagram\.com/(?:[\w.]+/)?(?:reels?|p|tv)/([\w-]+)", link)
    if m:
        return "instagram:" + m.group(1)
    m = re.search(r"(?:youtu\.be/|youtube\.com/(?:watch\?(?:.*&)?v=|shorts/|live/|embed/))([\w-]{11})", link)
    if m:
        return "youtube:" + m.group(1)
    return re.sub(r"[?#].*$", "", link).rstrip("/").removeprefix("https://").removeprefix("http://").removeprefix("www.")


def _data(v):
    if not v:
        return ""
    if isinstance(v, (int, float)) or str(v).isdigit() and len(str(v)) > 8:
        return datetime.fromtimestamp(int(v)).strftime("%Y-%m-%d")
    v = str(v)
    return f"{v[:4]}-{v[4:6]}-{v[6:8]}" if re.fullmatch(r"\d{8}", v) else v[:10]


def dados(pasta):
    """De onde veio o vídeo desta pasta: o meta.json do estúdio (os nomes dos campos mudaram com o tempo) e, no que
    faltar, o .info.json do yt-dlp."""
    m = _json(pasta / "meta.json")
    info = {}
    for p in sorted(pasta.glob("*.info.json")):
        info = {**_json(p), **info}
    tit = info.get("title") or ""
    return {
        "link": m.get("link") or info.get("webpage_url") or info.get("original_url") or "",
        "quem": m.get("quem") or m.get("quem_postou") or m.get("author") or info.get("uploader") or info.get("channel") or "",
        "conta": m.get("conta") or m.get("canal") or info.get("channel") or info.get("uploader_id") or "",
        "postado": _data(m.get("postado") or m.get("publicado_data") or m.get("published") or info.get("upload_date")
                         or info.get("timestamp")),
        "duracao": m.get("duracao") or m.get("lengthSeconds") or info.get("duration") or "",
        "titulo": (m.get("legenda") or m.get("legenda_do_post") or m.get("title")
                   or ("" if tit.startswith("Video by") else tit) or info.get("description") or "")[:600],
    }


def falas(pasta):
    """[(segundo, texto)] da transcricao.txt (mm:ss ou h:mm:ss no começo de cada linha)."""
    for nome in ("transcricao.txt", "transcricao-original.txt"):
        p = pasta / nome
        if p.exists():
            out = []
            for l in p.read_text(errors="replace").splitlines():
                g = LINHA.match(l.strip())
                if g:
                    out.append((int(g.group(1) or 0) * 3600 + int(g.group(2)) * 60 + int(g.group(3)), g.group(4)))
            return out
    return []


def e_baixado(pasta):
    nomes = {p.name for p in pasta.iterdir()} if pasta.is_dir() else set()
    return bool(nomes & {"transcricao.txt", "meta.json", *VIDEOS}) or any(n.endswith(".info.json") for n in nomes)


def _abaixo(raiz, fundo):
    """As pastas de vídeo baixado dentro de raiz, até fundo níveis, sem entrar no que o estúdio gera."""
    if not raiz.is_dir():
        return
    pilha = [(raiz, 0)]
    while pilha:
        d, n = pilha.pop()
        try:
            filhos = sorted(p for p in d.iterdir() if p.is_dir() and p.name not in PULA and not p.name.startswith("_"))
        except OSError:
            continue
        for f in filhos:
            if e_baixado(f):
                yield f
            if n + 1 < fundo:
                pilha.append((f, n + 1))


def pastas():
    """(pasta, uso) de tudo o que já baixamos. uso: o vídeo nosso em que entrou, ou "" (o radar só ouviu)."""
    for p in _abaixo(RAIZ / "referencias", 1):
        yield p, ""
    for v in sorted((RAIZ / "videos").glob("*")):
        if not v.is_dir() or v.name.startswith("_"):
            continue
        f = _json(v / "ficha.json")
        rot = (v / "ROTEIRO.md").read_text(errors="replace") if (v / "ROTEIRO.md").exists() else ""
        pub = " (publicado)" if f.get("etapa") == "Publicado" else ""
        for p in _abaixo(v, 3):
            como = ("pauta" if p.name == "referencia" else
                    "take no roteiro" if f"material/{p.name}" in rot else "baixado para ele")
            yield p, f"#{v.name}{pub}: {como}"
    # o estúdio antigo (até 23/10/2026): referencias/<código> e <vídeo>/... com as referências de cada um
    for p in _abaixo(ANTIGO, 3):
        rel = p.relative_to(ANTIGO).parts
        yield p, "" if rel[0] == "referencias" else f"{rel[0]} (estúdio antigo)"


def citacoes(pasta_video):
    """{código: [(segundo, fim, fala)]} das falas de takes que o ROTEIRO.md cita. No #304 a transcrição automática do reel do
    Metrópoles saiu "hoje é dia de descanso"; o roteiro tem a fala certa: "Vamos lá, meu general!" (4,66 s)."""
    rot = pasta_video / "ROTEIRO.md"
    out = {}
    for m in CITA.finditer(rot.read_text(errors="replace") if rot.exists() else ""):
        fala = re.sub(r"\s+", " ", m.group(1)).strip(" \"'“”")
        if len(fala) > 3:
            out.setdefault(m.group(4), []).append((float(m.group(2).replace(",", ".")), float(m.group(3).replace(",", ".")), fala))
    return out


def banco(arq):
    c = sqlite3.connect(arq)
    c.executescript("""
    create table if not exists entradas(id integer primary key, chave text unique, link text, quem text, conta text,
        postado text, duracao text, titulo text, pastas text, usos text, video text);
    create virtual table if not exists busca using fts5(texto, entrada unindexed, seg unindexed, linha unindexed,
        tokenize='unicode61 remove_diacritics 2');
    """)
    return c


def juntar():
    """Refaz o acervo inteiro num banco novo e troca no fim (quem busca durante a troca vê o de antes, inteiro)."""
    t0 = time.time()
    tudo, por_pasta = {}, {}
    for p, uso in pastas():
        d = dados(p)
        k = chave(d["link"]) or "pasta:" + str(p.relative_to(p.anchor))
        e = tudo.setdefault(k, {**d, "pastas": [], "usos": [], "falas": [], "video": ""})
        for campo in ("link", "quem", "conta", "postado", "duracao", "titulo"):
            e[campo] = e[campo] or d[campo]
        e["pastas"].append(str(p))
        por_pasta[p] = k
        if uso and uso not in e["usos"]:
            e["usos"].append(uso)
        if not e["falas"]:
            e["falas"] = falas(p)
        if not e["video"]:
            e["video"] = next((str(p / n) for n in VIDEOS if (p / n).exists()), "")
    for v in sorted((RAIZ / "videos").glob("*")):
        for cod, fs in citacoes(v).items():
            k = por_pasta.get(v / "material" / cod) or por_pasta.get(v / "referencia" / "material" / cod)
            if k:
                # o corte inteiro: a trava das falas alheias (estudio.falas_alheias) aceita a fala conferida só com ele
                tudo[k].setdefault("citadas", []).extend(
                    (s, f"{f} (fala conferida no roteiro do #{v.name}; corte: ({s:g}-{fim:g} material/{cod}))") for s, fim, f in fs)
    DB.parent.mkdir(parents=True, exist_ok=True)
    novo = DB.with_suffix(".novo")
    novo.unlink(missing_ok=True)
    c = banco(novo)
    for k, e in tudo.items():
        cur = c.execute("insert into entradas(chave, link, quem, conta, postado, duracao, titulo, pastas, usos, video) "
                        "values (?,?,?,?,?,?,?,?,?,?)",
                        (k, e["link"], e["quem"], e["conta"], e["postado"], str(e["duracao"]), e["titulo"],
                         json.dumps(e["pastas"], ensure_ascii=False), json.dumps(e["usos"], ensure_ascii=False), e["video"]))
        i, fs = cur.lastrowid, e["falas"]
        # quem postou e a legenda também se buscam ("o vídeo do Janones"); cada fala vai com a de antes e a de depois,
        # para "Lula marechal" achar quando o nome está numa linha e a palavra na outra
        c.execute("insert into busca values (?,?,?,?)", (" ".join([e["quem"], e["conta"], e["titulo"]]), i, -1, ""))
        for j, (s, t) in enumerate(fs):
            janela = " ".join(x[1] for x in fs[max(0, j - 1):j + 2])
            c.execute("insert into busca values (?,?,?,?)", (janela, i, s, t))
        for s, t in e.get("citadas", []):
            c.execute("insert into busca values (?,?,?,?)", (t, i, s, t))
    c.commit()
    n = c.execute("select count(*) from entradas").fetchone()[0]
    nf = c.execute("select count(*) from busca where seg >= 0").fetchone()[0]
    c.close()
    os.replace(novo, DB)
    print(f"acervo: {n} vídeos, {nf} falas, em {time.time() - t0:.1f} s ({DB})")
    return n, nf


def _consulta(termos, juntar_com):
    ws = [w for w in re.findall(r"[\wÀ-ÿ]+", termos) if len(w) > 1]
    return f" {juntar_com} ".join(f'"{w}"' for w in ws)


def buscar(termos, n=6):
    """Os n vídeos com as falas mais parecidas: primeiro os que têm todas as palavras, depois os que têm parte delas
    (no #382, "Lula marechal general Janones": o reel que diz "o nosso marechal" não diz Janones)."""
    if not DB.exists() or not _consulta(termos, "OR"):
        return []
    c = sqlite3.connect(DB)
    por = {}
    for ordem, juntar_com in enumerate(("AND", "OR")):
        linhas = c.execute("select entrada, seg, linha, bm25(busca) from busca where busca match ? order by bm25(busca) "
                           "limit 400", (_consulta(termos, juntar_com),)).fetchall()
        for ent, seg, linha, nota in linhas:
            g = por.setdefault(ent, {"nota": (ordem, nota), "trechos": []})
            if seg >= 0 and len(g["trechos"]) < 3 and all(abs(seg - s) > 4 for s, _ in g["trechos"]):
                g["trechos"].append((seg, linha))
    out = []
    for ent, g in sorted(por.items(), key=lambda x: x[1]["nota"])[:n]:
        r = c.execute("select link, quem, conta, postado, duracao, titulo, usos, video from entradas where id = ?",
                      (ent,)).fetchone()
        out.append({"link": r[0], "quem": r[1], "conta": r[2], "postado": r[3], "duracao": r[4], "titulo": r[5],
                    "usos": json.loads(r[6]), "video": r[7] if r[7] and Path(r[7]).exists() else "",
                    "trechos": [{"mmss": f"{int(s) // 60}:{s % 60:05.2f}" if s % 1 else f"{int(s) // 60}:{int(s) % 60:02d}", "seg": s, "fala": t} for s, t in sorted(g["trechos"])]})
    c.close()
    return out


def texto(achados, termos):
    if not achados:
        return f'Nada no acervo para "{termos}". Procure na web.'
    out = [f'{len(achados)} vídeo(s) no acervo para "{termos}" (o mais parecido primeiro):']
    for i, a in enumerate(achados, 1):
        dur = f" · {float(a['duracao']):.0f} s" if re.fullmatch(r"[\d.]+", str(a["duracao"])) else ""
        out.append(f"\n{i}. {a['link'] or '(sem link guardado)'} · {a['quem'] or a['conta'] or '?'}"
                   + (f" (@{a['conta']})" if a["conta"] and a["conta"] != a["quem"] and not a["conta"].isdigit() else "")
                   + (f" · postado {a['postado']}" if a["postado"] else "") + dur)
        if a["titulo"]:
            out.append("   legenda: " + re.sub(r"\s+", " ", a["titulo"])[:160])
        for t in a["trechos"]:
            out.append(f"   {t['mmss']}  {t['fala']}")
        if a["usos"]:
            out.append("   usado: " + "; ".join(a["usos"]))
        out.append("   o vídeo está guardado: traga para este vídeo com  acervo.py trazer <número> " + a["link"]
                   if a["video"] else "   o vídeo não está guardado: baixe de novo pelo link (baixar.py)")
    return "\n".join(out)


def trazer(num, link):
    """25/10/2026 (#382: o agente pôs no corte o caminho do take do #304, "/srv/.../videos/304/material/DesTCX7RyXn", a
    voz parou em "trecho sem corte ou sem o áudio de origem", e baixar de novo não deu: o Instagram bloqueia a VPS). A
    pasta guardada vira material/<código>/ deste vídeo: ligação no disco (o mesmo arquivo, sem ocupar o dobro) ou cópia."""
    import shutil
    k = chave(link) or link
    if not DB.exists():
        return None, "o acervo ainda não existe"
    c = sqlite3.connect(DB)
    r = c.execute("select pastas, link from entradas where chave = ? or link = ?", (k, link)).fetchone()
    c.close()
    if not r:
        return None, f"não está no acervo: {link}"
    origem = next((Path(p) for p in json.loads(r[0]) if any((Path(p) / n).exists() for n in VIDEOS)), None)
    if not origem:
        return None, f"o vídeo não está mais guardado: baixe de novo pelo link ({r[1]})"
    destino = RAIZ / "videos" / str(num) / "material" / origem.name
    if destino.resolve() == origem.resolve() or destino.exists():
        return destino, f"já está neste vídeo: material/{origem.name}/"
    destino.parent.mkdir(parents=True, exist_ok=True)
    try:
        shutil.copytree(origem, destino, copy_function=os.link, ignore=shutil.ignore_patterns("quadros"))
    except OSError:
        shutil.rmtree(destino, ignore_errors=True)
        shutil.copytree(origem, destino, ignore=shutil.ignore_patterns("quadros"))
    return destino, (f"trazido de {origem.relative_to(RAIZ) if origem.is_relative_to(RAIZ) else origem} para "
                     f"material/{origem.name}/ deste vídeo. No corte: (início-fim material/{origem.name}); os segundos "
                     f"estão em material/{origem.name}/palavras.json")


def resumo():
    if not DB.exists():
        return "acervo ainda não existe: python3 acervo.py juntar"
    c = sqlite3.connect(DB)
    n, nf = c.execute("select count(*) from entradas").fetchone()[0], c.execute("select count(*) from busca where seg >= 0").fetchone()[0]
    sem = c.execute("select count(*) from entradas where link = ''").fetchone()[0]
    guard = c.execute("select count(*) from entradas where video != ''").fetchone()[0]
    usados = c.execute("select count(*) from entradas where usos != '[]'").fetchone()[0]
    return (f"acervo: {n} vídeos ({usados} usados em vídeos nossos, {n - sem} com link, {guard} com o vídeo ainda guardado), "
            f"{nf} falas com mm:ss · atualizado {datetime.fromtimestamp(DB.stat().st_mtime):%d/%m %H:%M}")


if __name__ == "__main__":
    a = sys.argv[1:]
    if a[:1] == ["juntar"]:
        juntar()
    elif a[:1] == ["buscar"] and len(a) > 1:
        nums = [x for x in a[2:] if x.isdigit()]
        achados = buscar(a[1], int(nums[0]) if nums else 6)
        print(json.dumps(achados, ensure_ascii=False, indent=1) if "--json" in a else texto(achados, a[1]))
    elif a[:1] == ["trazer"] and len(a) == 3:
        d, msg = trazer(a[1], a[2])
        print(msg)
        sys.exit(0 if d else 1)
    elif a[:1] == ["resumo"]:
        print(resumo())
    else:
        print(__doc__)
        sys.exit(1)
