"""A tela Regras (26/10/2026, ele: "onde fica as regras? talvez eu tenha que poder ver esse caderno de regras caso queira
mudar algo" e "pode fazer"). Ele lê os cadernos de regras/ no celular e, em cada um, dita o que quer mudar: o estúdio
mostra a mudança (o que sai e o que entra) e só grava com o ok dele; a versão de antes fica em regras/versoes/ para
desfazer. As decisões de cada vídeo (INTENCAO.md) aparecem junto, só para ler.

Os cadernos gerados por programa (o PUBLICO.md, "não editar à mão") são só leitura: a mudança neles se perderia."""
import hashlib, json, re, time
from pathlib import Path

import estudio as E

PASTA = E.RAIZ / "regras"
VERSOES = PASTA / "versoes"
PROPOSTAS = PASTA / ".propostas"
HISTORICO = PASTA / "historico.jsonl"
NOME = re.compile(r"[A-Z][A-Z0-9-]{1,40}")

PARA_QUE = {
    "ROTEIRISTA": "Como o roteiro é escrito: duração, selos, falas, o que não pode",
    "RECEITA": "A receita geral dos vídeos da página",
    "PUBLICO": "O que o público gosta (gerado pelos números; só leitura)",
    "AGENTE": "Como o agente do chat responde",
    "ANIMADOR": "Como a animação é feita",
    "CAPA": "A capa do post",
    "LEGENDA": "O texto do post no Instagram",
    "IDENTIDADE": "O visual da página: cores, letras, selos",
    "GANCHOS": "As aberturas por assunto",
    "MOLDE-FOMOS-CONFERIR": "Formato Fomos conferir",
    "MOLDE-MICRO-DOC": "Formato Micro documentário",
    "MOLDE-NUMEROS": "Molde Números",
    "MOLDE-CURSO": "Molde Curso",
}


def _arq(nome):
    if not NOME.fullmatch(nome or "") or not (PASTA / f"{nome}.md").is_file():
        raise ValueError("caderno não existe")
    return PASTA / f"{nome}.md"


def _marca(texto):
    return hashlib.sha1(texto.encode()).hexdigest()


def so_leitura(nome, texto=None):
    texto = texto if texto is not None else _arq(nome).read_text()
    return "não editar à mão" in texto[:400].lower()


def _versoes(nome):
    return sorted(VERSOES.glob(f"{nome}-*.md")) if VERSOES.exists() else []


def listar():
    out = []
    for a in sorted(PASTA.glob("*.md"), key=lambda a: (list(PARA_QUE).index(a.stem) if a.stem in PARA_QUE else 99, a.stem)):
        t = a.read_text()
        out.append({"nome": a.stem, "titulo": re.sub(r"^#+\s*", "", t.splitlines()[0] if t else a.stem),
                    "para_que": PARA_QUE.get(a.stem, ""), "linhas": t.count("\n") + 1, "so_leitura": so_leitura(a.stem, t),
                    "versoes": len(_versoes(a.stem)), "proposta": (PROPOSTAS / f"{a.stem}.json").exists()})
    return out


def ler(nome):
    a = _arq(nome)
    t = a.read_text()
    prop = PROPOSTAS / f"{nome}.json"
    hist = [json.loads(l) for l in HISTORICO.read_text().splitlines() if l.strip()] if HISTORICO.exists() else []
    return {"nome": nome, "texto": t, "so_leitura": so_leitura(nome, t), "versoes": len(_versoes(nome)),
            "proposta": json.loads(prop.read_text()) if prop.exists() else None,
            "mudancas": [h for h in hist if h.get("nome") == nome][-5:]}


def decisoes(num):
    """As decisões dele que valem para o vídeo inteiro (a seção do INTENCAO.md)."""
    arq = E.pasta(num) / "INTENCAO.md"
    t = arq.read_text() if arq.exists() else ""
    if E.DECISOES not in t:
        return []
    return [l[2:].strip() for l in t.split(E.DECISOES, 1)[1].splitlines() if l.startswith("- ")]


PEDIDO = """Você cuida do caderno de regras "{nome}" do estúdio de vídeos da @newsbr360 (o texto inteiro está abaixo). O editor
pediu uma mudança. Faça SÓ o que ele pediu, no lugar certo do caderno, no mesmo estilo (frases curtas, a data e as
palavras dele entre parênteses quando for regra nova, como as outras). Não reescreva o que ele não pediu.

O PEDIDO DELE: "{pedido}"

Responda SÓ um JSON:
{{"resumo": "<em 1 ou 2 frases, para ele: o que muda na prática nos vídeos>",
 "trocas": [{{"antes": "<trecho EXATO do caderno, copiado letra por letra, que muda>", "depois": "<como fica>"}}],
 "conflito": "<se o pedido bate de frente com outra regra do caderno, qual; senão vazio>"}}
Para ACRESCENTAR uma regra, "antes" é a linha exata depois da qual ela entra, e "depois" é essa mesma linha seguida da nova.
Para TIRAR, "depois" fica vazio.

O CADERNO {nome}.md:
{texto}"""


def propor(nome, pedido):
    a = _arq(nome)
    if so_leitura(nome):
        raise ValueError("este caderno é gerado pelos números e não se muda à mão")
    pedido = " ".join(str(pedido).split())[:2000]
    if not pedido:
        raise ValueError("diga o que quer mudar")
    texto = a.read_text()
    import ia
    resp, uso = ia.chamar(PEDIDO.format(nome=nome, pedido=pedido, texto=texto), f"regras ({nome})", "opus", limite=240,
                          cwd=E.RAIZ)
    R = ia.json_de(resp) or {}
    trocas = [t for t in R.get("trocas") or [] if isinstance(t, dict) and t.get("antes")]
    ruins = [t["antes"][:80] for t in trocas if texto.count(t["antes"]) != 1]
    if not trocas or ruins:
        raise RuntimeError("não consegui montar a mudança com segurança" + (f" (trecho não achado: {ruins[0]})" if ruins else "")
                           + ". Tente dizer de outro jeito, apontando a regra.")
    prop = {"nome": nome, "pedido": pedido, "resumo": str(R.get("resumo") or ""), "conflito": str(R.get("conflito") or ""),
            "trocas": [{"antes": t["antes"], "depois": str(t.get("depois") or "")} for t in trocas],
            "quando": E.agora(), "base": _marca(texto)}
    PROPOSTAS.mkdir(exist_ok=True)
    (PROPOSTAS / f"{nome}.json").write_text(json.dumps(prop, ensure_ascii=False, indent=1))
    return prop


def aplicar(nome):
    a = _arq(nome)
    pa = PROPOSTAS / f"{nome}.json"
    if not pa.exists():
        raise ValueError("não há mudança esperando")
    prop = json.loads(pa.read_text())
    texto = a.read_text()
    if prop.get("base") != _marca(texto):
        pa.unlink()
        raise RuntimeError("o caderno mudou depois da proposta; peça a mudança de novo")
    novo = texto
    for t in prop["trocas"]:
        if novo.count(t["antes"]) != 1:
            raise RuntimeError("um trecho da mudança não está mais no caderno; peça de novo")
        novo = novo.replace(t["antes"], t["depois"], 1)
    VERSOES.mkdir(exist_ok=True)
    (VERSOES / f"{nome}-{time.strftime('%Y%m%d-%H%M%S')}.md").write_text(texto)
    E._grava(a, novo)
    pa.unlink()
    with HISTORICO.open("a") as f:
        f.write(json.dumps({"quando": E.agora(), "nome": nome, "acao": "mudou", "pedido": prop["pedido"],
                            "resumo": prop["resumo"]}, ensure_ascii=False) + "\n")
    return {"ok": True, "resumo": prop["resumo"]}


def cancelar(nome):
    _arq(nome)
    (PROPOSTAS / f"{nome}.json").unlink(missing_ok=True)
    return {"ok": True}


def desfazer(nome):
    a = _arq(nome)
    vs = _versoes(nome)
    if not vs:
        raise ValueError("não há mudança para desfazer")
    E._grava(a, vs[-1].read_text())
    vs[-1].rename(vs[-1].with_suffix(".desfeita"))
    with HISTORICO.open("a") as f:
        f.write(json.dumps({"quando": E.agora(), "nome": nome, "acao": "desfez", "resumo": "voltou à versão anterior"},
                           ensure_ascii=False) + "\n")
    return {"ok": True}
