"""Caderno de material do vídeo (26/10/2026, ele: "pode acontecer de colocar mais um link, enviar fotos pdf enfim, mais
informações; o agente tem que entender que isso é informação complementar e ver o que pode ser usado no texto"). Antes o
que chegava no chat ficava guardado na pasta, mas só o agente daquela mensagem via; o roteirista, na reescrita seguinte,
não sabia que existia, e quem precisasse abria e lia tudo de novo.

Cada coisa que chega (vídeo, foto, PDF, página, arquivo) vira UMA ficha, preparada uma vez, na hora em que chega: o que
é, de onde veio, onde está o texto inteiro e o que tem de útil para o vídeo. Todos (roteirista, proposta, editor, agente)
recebem o caderno pronto (texto()), ninguém relê o material.

  registrar(num, origem, tipo, texto="", arquivos=())   a ficha nova (ou a que já existe para a mesma origem)
  texto(num)                                            o caderno para os pedidos
  anexo(num, nome)                                      a ficha de um arquivo de anexos/
"""
import json, subprocess
from pathlib import Path

import estudio as E

INDICE = "material.json"
MD = "MATERIAL.md"

PEDIDO = """Você prepara a ficha de um material complementar de um vídeo curto da @newsbr360 (notícia com prova). O editor
mandou isto para ajudar no roteiro. Diga o que tem de ÚTIL para o vídeo, em até 6 linhas curtas, sem inventar:
- fatos que o material prova (com o número, a data, quem disse);
- falas com mm:ss que dariam um bom trecho (só em vídeo, com as palavras exatas);
- imagens que servem (o que mostram).
Se não tem nada útil para este vídeo, diga em uma linha. Não repita o que o roteiro já diz. Responda só o texto.

O vídeo de agora:
{assunto}

O material ({tipo}, de {origem}):
{conteudo}"""


def _ler(num):
    try:
        return json.loads((E.pasta(num) / INDICE).read_text())
    except (OSError, ValueError):
        return []


def itens(num):
    return _ler(num)


def _grava(num, xs):
    p = E.pasta(num)
    E._grava(p / INDICE, json.dumps(xs, ensure_ascii=False, indent=1))
    E._grava(p / MD, "# Material complementar do vídeo\n\n" + texto(num, xs=xs) + "\n")


def _assunto(num):
    p = E.pasta(num)
    partes = []
    for a in ("INTENCAO.md", "ROTEIRO.md"):
        if (p / a).exists():
            partes.append((p / a).read_text()[:2500])
    return "\n".join(partes) or "(o roteiro ainda não foi escrito)"


def registrar(num, origem, tipo, texto_inteiro="", arquivos=()):
    """A ficha do material (uma chamada curta do Sonnet, que olha as imagens e o PDF). Devolve a ficha."""
    xs = _ler(num)
    for x in xs:
        if x["origem"] == origem:
            return x
    p = E.pasta(num)
    arqs = [str(Path(a).relative_to(p)) if Path(a).is_absolute() and p in Path(a).parents else str(a) for a in arquivos]
    texto_arq = ""
    if texto_inteiro.strip():
        d = p / "material" / "textos"
        d.mkdir(parents=True, exist_ok=True)
        alvo = d / f"M{len(xs) + 1}.txt"
        alvo.write_text(texto_inteiro)
        texto_arq = str(alvo.relative_to(p))
    olhar = [a for a in arqs if a.lower().endswith((".jpg", ".jpeg", ".png", ".webp", ".pdf"))]
    conteudo = (texto_inteiro[:10000] or "(sem texto)") + (
        "\nArquivos para olhar com a ferramenta Read: " + ", ".join(olhar) if olhar else "")
    import ia
    util, uso = ia.chamar(PEDIDO.format(assunto=_assunto(num), tipo=tipo, origem=origem, conteudo=conteudo),
                          "caderno de material", "sonnet", num=num, limite=180, cwd=p,
                          **({"ferramentas": "Read", "permitidas": ["Read"]} if olhar else {}))
    util = (util or "").strip()
    if "<invoke" in util or "<parameter" in util:          # tentou usar ferramenta que não tinha: não é ficha
        util = ""
    x = {"id": f"M{len(xs) + 1}", "tipo": tipo, "origem": origem, "quando": E.agora(), "arquivos": arqs,
         "texto": texto_arq, "util": util or f"(a ficha não saiu{': ' + uso.get('erro', '')[:120] if uso.get('erro') else ''}; "
                                              "o material está guardado e pode ser aberto)"}
    xs.append(x)
    _grava(num, xs)
    E.evento(num, f"caderno de material: {x['id']} ({tipo}) de {origem[:80]}")
    return x


def anexo(num, nome):
    """A ficha de um arquivo de anexos/: PDF com o texto tirado pelo pdftotext, imagem para olhar, o resto pelo nome."""
    arq = E.pasta(num) / "anexos" / nome
    ext = arq.suffix.lower()
    txt, tipo = "", "arquivo"
    if ext == ".pdf":
        tipo = "PDF"
        try:
            txt = subprocess.run(["pdftotext", "-layout", str(arq), "-"], capture_output=True, text=True, timeout=60).stdout
        except (OSError, subprocess.SubprocessError):
            txt = ""
    elif ext in (".jpg", ".jpeg", ".png", ".webp", ".heic"):
        tipo = "foto"
    elif ext in (".txt", ".md", ".csv"):
        tipo, txt = "texto", arq.read_text(errors="ignore")
    return registrar(num, f"anexo {nome}", tipo, txt, [arq])


def texto(num, xs=None, lim=12000):
    """O caderno para os pedidos: cada ficha com o que tem de útil e onde está o texto inteiro."""
    xs = _ler(num) if xs is None else xs
    if not xs:
        return ""
    linhas = []
    for x in xs:
        onde = ", ".join(filter(None, [x.get("texto")] + list(x.get("arquivos") or [])))
        linhas.append(f"### {x['id']} · {x['tipo']} · {x['origem']}\n{x['util']}" + (f"\n(inteiro em: {onde})" if onde else ""))
    return "\n\n".join(linhas)[:lim]


def para_pedido(num):
    """O bloco que entra no pedido do roteirista, da proposta e do agente (vazio sem material)."""
    t = texto(num)
    return ("\n## MATERIAL COMPLEMENTAR que ele mandou (o caderno: já está resumido aqui, não abra de novo; abra o texto "
            "inteiro só se precisar de uma palavra exata). Use o que servir ao vídeo: fato do material vai para a "
            "checagem com a fonte; fala de outro vídeo entra na nossa voz, \"segundo\" quem disse.\n" + t + "\n") if t else ""
