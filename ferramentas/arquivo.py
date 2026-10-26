"""Arquivo de checagens da @newsbr360 (19/10/2026; ele: "a gente poderia criar um rag disso? [...] tem que ser na vps" e
"pode fazer o arquivo na vps"). A memória da página: todo fato já checado, com fonte, trecho e veredito, e as páginas já
lidas. Mora na VPS (/srv/kitebiz/projetos/newsbr360-estudio/arquivo/); os estúdios consultam por SSH. Sem IA: busca de
texto do SQLite (FTS5, sem acento e sem maiúscula).

Cada CHECAGEM.md vira trechos (uma linha de tabela, ou um parágrafo/seção), porque os formatos mudaram ao longo do tempo
("Afirmação | Fonte | Veredito", "Fala | O que a fonte diz | Carimbo", texto corrido com seções...).

  python3 arquivo.py importar-pasta <raiz> <origem>    todas as */CHECAGEM*.md da raiz (o vídeo = a pasta)
  python3 arquivo.py importar <CHECAGEM.md> <origem> <vídeo> [título]
  python3 arquivo.py buscar "<texto>" [n]              os trechos mais parecidos (JSON)
  python3 arquivo.py pagina <url>                      o texto guardado de uma página (JSON; vazio se não tem)
  python3 arquivo.py guardar-pagina <url>              guarda o texto que vier pela entrada padrão
  python3 arquivo.py resumo                            quantos vídeos, trechos e páginas
O banco é ARQUIVO_DB, ou arquivo.db ao lado deste programa.
"""
import hashlib, json, os, re, sqlite3, sys, time
from pathlib import Path

DB = Path(os.environ.get("ARQUIVO_DB") or Path(__file__).resolve().parent / "arquivo.db")
VEREDITOS = ["MEIA-VERDADE", "SEM PROVA", "VERDADE", "ERRADO", "FALSO", "EXAGERO", "CONFIRMADO", "PREVISÃO", "OPINIÃO",
             "ELE MESMO DISSE", "ELA MESMO DISSE"]
LINK = re.compile(r"\[([^\]]*)\]\((https?://[^)\s]+)\)|(https?://[^\s)\]>]+)")


def banco():
    c = sqlite3.connect(DB)
    c.executescript("""
    create table if not exists trechos(id integer primary key, origem text, video text, titulo text, data text,
        veredito text, links text, texto text);
    create virtual table if not exists trechos_fts using fts5(texto, titulo, video, content='trechos', content_rowid='id',
        tokenize='unicode61 remove_diacritics 2');
    create trigger if not exists t_ai after insert on trechos begin
        insert into trechos_fts(rowid, texto, titulo, video) values (new.id, new.texto, new.titulo, new.video); end;
    create trigger if not exists t_ad after delete on trechos begin
        insert into trechos_fts(trechos_fts, rowid, texto, titulo, video) values ('delete', old.id, old.texto, old.titulo, old.video); end;
    create table if not exists fontes(origem text, video text, hash text, quando text, primary key(origem, video));
    create table if not exists paginas(url text primary key, texto text, quando text);
    """)
    return c


def trechos_de(md):
    """O CHECAGEM.md em trechos: cada linha de tabela (com o nome das colunas na frente) e cada parágrafo ou item de
    lista fora de tabela (com o título da seção na frente). Trechos curtos demais saem."""
    out, cab, secao, par = [], None, "", []

    def fecha():
        t = " ".join(par).strip()
        if len(t) > 40:
            out.append((secao + ": " if secao else "") + t)
        par.clear()
    for l in md.splitlines():
        s = l.strip()
        if s.startswith("|"):
            fecha()
            cel = [c.strip() for c in s.strip("|").split("|")]
            if all(set(c) <= set("-: ") for c in cel):
                continue
            if cab is None:
                cab = cel
                continue
            out.append(" · ".join(f"{cab[i] if i < len(cab) else ''}: {c}" for i, c in enumerate(cel) if c))
            continue
        cab = None if not s.startswith("|") and s else cab
        if s.startswith("#"):
            fecha(); secao = s.lstrip("# ").strip()[:80]
        elif not s:
            fecha()
        elif s.startswith(("- ", "* ", "• ")) or re.match(r"^\d+\.\s", s):
            fecha(); par.append(s)
        else:
            par.append(s)
    fecha()
    return [t[:1500] for t in out]


def veredito_de(t):
    tu = t.upper()
    return next((v for v in VEREDITOS if v in tu), "")


def importar(c, arq, origem, video, titulo="", data=""):
    md = Path(arq).read_text(errors="replace")
    h = hashlib.md5(md.encode()).hexdigest()
    antes = c.execute("select hash from fontes where origem=? and video=?", (origem, video)).fetchone()
    if antes and antes[0] == h:
        return 0                                                   # nada mudou
    c.execute("delete from trechos where origem=? and video=?", (origem, video))
    titulo = titulo or next((l.lstrip("# ").strip() for l in md.splitlines() if l.startswith("#")), video)
    data = data or time.strftime("%Y-%m-%d", time.localtime(Path(arq).stat().st_mtime))
    n = 0
    for t in trechos_de(md):
        links = [m[1] or m[2] for m in LINK.findall(t)]
        c.execute("insert into trechos(origem, video, titulo, data, veredito, links, texto) values (?,?,?,?,?,?,?)",
                  (origem, video, titulo[:200], data, veredito_de(t), json.dumps(links), LINK.sub(lambda m: m[1] or m[3], t)))
        n += 1
    c.execute("insert or replace into fontes values (?,?,?,?)", (origem, video, h, time.strftime("%Y-%m-%dT%H:%M")))
    c.commit()
    return n


def importar_pasta(c, raiz, origem):
    tot = vids = 0
    for arq in sorted(Path(raiz).glob("**/CHECAGEM*.md")):
        if any(p in arq.parts for p in ("versoes", "_lixeira", "node_modules")):
            continue
        video = arq.parent.name
        titulo = ""
        ficha = arq.parent / "ficha.json"
        if ficha.exists():
            try:
                titulo = json.loads(ficha.read_text()).get("titulo") or ""
            except ValueError:
                pass
        n = importar(c, arq, origem, video, titulo)
        tot += n; vids += 1 if n else 0
    return {"videos_novos_ou_mudados": vids, "trechos": tot}


def buscar(c, consulta, n=5):
    """Os trechos mais parecidos pela busca de texto (BM25). Palavras de 3 letras ou mais, ligadas por OU: um fato
    parecido aparece mesmo sem ter todas as palavras."""
    palavras = [w for w in re.findall(r"[\wÀ-ú]{3,}", consulta.lower()) if not w.isdigit() or len(w) == 4]
    if not palavras:
        return []
    q = " OR ".join(f'"{w}"' for w in dict.fromkeys(palavras))
    linhas = c.execute("""select t.origem, t.video, t.titulo, t.data, t.veredito, t.links, t.texto, bm25(trechos_fts) as r
                          from trechos_fts join trechos t on t.id = trechos_fts.rowid where trechos_fts match ?
                          order by r limit ?""", (q, n)).fetchall()
    return [{"origem": o, "video": v, "titulo": ti, "data": d, "veredito": ve, "links": json.loads(li), "texto": tx[:700],
             "relevancia": round(-r, 2)} for o, v, ti, d, ve, li, tx, r in linhas]


def main(a):
    c = banco()
    if a[0] == "importar-pasta":
        print(json.dumps(importar_pasta(c, a[1], a[2]), ensure_ascii=False))
    elif a[0] == "importar":
        print(json.dumps({"trechos": importar(c, a[1], a[2], a[3], a[4] if len(a) > 4 else "")}))
    elif a[0] == "buscar":
        print(json.dumps(buscar(c, a[1], int(a[2]) if len(a) > 2 else 5), ensure_ascii=False))
    elif a[0] == "pagina":
        r = c.execute("select texto, quando from paginas where url=?", (a[1],)).fetchone()
        print(json.dumps({"texto": r[0], "quando": r[1]} if r else {}, ensure_ascii=False))
    elif a[0] == "guardar-pagina":
        c.execute("insert or replace into paginas values (?,?,?)", (a[1], sys.stdin.read(), time.strftime("%Y-%m-%dT%H:%M"))); c.commit()
        print("{}")
    elif a[0] == "resumo":
        print(json.dumps({"videos": c.execute("select count(*) from fontes").fetchone()[0],
                          "trechos": c.execute("select count(*) from trechos").fetchone()[0],
                          "paginas": c.execute("select count(*) from paginas").fetchone()[0],
                          "por_origem": dict(c.execute("select origem, count(*) from fontes group by origem").fetchall())}, ensure_ascii=False))


if __name__ == "__main__":
    main(sys.argv[1:])
