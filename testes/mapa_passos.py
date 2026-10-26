"""Tipo A (sem IA, sem servidor): o mapa de passos (24/10/2026, "aprovo o plano mapa-de-passos", parte 1). Confere a
tabela (passos.py) contra o código e as fichas e lista os becos. Na parte 1 era só relatório; na parte 2 (os achados
resolvidos) entrou no tudo.py: o código e as fichas locais têm de bater com o mapa.

  .venv/bin/python testes/mapa_passos.py                     o código e as fichas da cópia local
  .venv/bin/python testes/mapa_passos.py <estados.txt>       e também estados de fora, uma linha "etapa | passo | esperando"
                                                            (ex.: os da VPS)
"""
import re, sys
from pathlib import Path
R = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(R), str(R / "ferramentas")]
import passos as M
import estudio as E

achados = []


def acha(grupo, msg):
    achados.append((grupo, msg))


def fonte(*arqs):
    return "\n".join((R / a).read_text() for a in arqs if (R / a).exists())


# 1) todo passo que o código grava está na tabela
py = fonte("servidor.py", "pauta.py", "agente.py", "radar.py", "estudio.py", "publicar.py", "animacao.py", "animador_novo.py")
srv = (R / "servidor.py").read_text()
consts = dict(re.findall(r'^([A-Z_]+) = "([^"]+)"', srv, re.M))
gravados = set(re.findall(r'passo=f?"([^"{]+)"', py)) | set(re.findall(r'\bpasso\(num, "([^"]+)"', py))
gravados |= {consts[c] for c in re.findall(r'passo=([A-Z_]+)\b', py) if c in consts}
gravados |= set(re.findall(r'"([^"]+)"', re.search(r"EM_ANDAMENTO = \(([^)]*)\)", srv, re.S).group(1)))
gravados.add("sugerida pelo radar")
for p in sorted(gravados - set(M.PASSOS)):
    acha("passo fora do mapa", f"o código grava o passo {p!r}, que não está na tabela")
for nome, valor in sorted(consts.items()):
    if nome in ("GRAVANDO", "ANIMANDO", "CAPANDO", "LEGENDANDO", "RENDERIZANDO", "PRONTO", "PUBLICANDO") and valor not in gravados:
        acha("passo sem uso", f"servidor.{nome} = {valor!r} existe mas nunca é gravado como passo")

# 2) as listas de "está trabalhando" espalhadas pelo código, contra a tabela
trab = set(M.TRABALHANDO)


def lista(nome, itens):
    itens = {consts.get(x, x) for x in itens}
    falta, sobra = trab - itens, itens - trab
    if falta or sobra:
        acha("lista de trabalhando", f"{nome}: " + "; ".join(x for x in (
            f"não tem {', '.join(sorted(falta))}" if falta else "", f"tem a mais {', '.join(sorted(sobra))}" if sobra else "") if x))


# parte 2: as listas vêm da tabela; o laço do trabalhador só faz parte delas (o resto ele faz fora do laço)
ins = (R / "ferramentas/instalar.py").read_text()
if "OCUPADOS = passos.TRABALHANDO" not in ins:
    acha("lista de trabalhando", "ferramentas/instalar.py: OCUPADOS não vem da tabela")
m = re.search(r'while E\.pendentes\(num\) or E\.ler_ficha\(num\)\["passo"\] in \(([^)]*)\)', srv)
laco = {consts.get(x, x) for x in re.findall(r"[A-Z_]+", m.group(1))}
if laco - trab:
    acha("lista de trabalhando", f"servidor.trabalhador: o laço trata {', '.join(sorted(laco - trab))}, que não é trabalho na tabela")
for nome, padrao in (("servidor.retomar", r"MAPA\.religar\("), ("servidor.pode_excluir", r"ocupado = f\[\"passo\"\] in MAPA\.TRABALHANDO"),
                     ("servidor.voltar_roteiro", r'if f\["passo"\] in MAPA\.TRABALHANDO:'), ("servidor (os botões)", r"acao not in MAPA\.botoes\(")):
    if not re.search(padrao, srv):
        acha("lista de trabalhando", f"{nome} não usa a tabela")
html = (R / "web/index.html").read_text()
for k, m in enumerate(re.finditer(r"\[((?:'[^']+',\s*){2,}'[^']+')\]\.includes\(f\.passo\)", html)):
    lista(f"web/index.html (lista {k + 1})", re.findall(r"'([^']+)'", m.group(1)))
if "item.mapa.trabalhando" not in html:
    acha("lista de trabalhando", "web/index.html não usa a lista do servidor (item.mapa)")

# 3) as ações da tabela existem no servidor, e as do servidor estão na tabela
rotas = set(re.findall(r'if acao == "([a-z-]+)"', srv)) | set(re.findall(r'acao in \("([a-z-]+)", "([a-z-]+)"\)', srv)[0] if re.search(r'acao in \("', srv) else ())
rotas -= {"mensagem", "anexo", "estado", "senha", "opcoes-entrar", "entrar", "sair", "opcoes-cadastro", "cadastrar"}
usadas = {b for p in M.PASSOS for e in M.PASSOS[p]["etapas"] for b in M.botoes(p, e)}
for a in sorted(usadas - rotas):
    acha("botão sem ação", f"a tabela tem o botão {a!r}, que o servidor não conhece")
for a in sorted(rotas - usadas):
    acha("ação fora do mapa", f"o servidor aceita {a!r}, mas nenhum passo da tabela tem esse botão")

# 4) as fichas de verdade: cada estado existe no mapa e tem saída
estados = []
for n in E.numeros():
    f = E.ler_ficha(n)
    estados.append((f"#{n} local", f.get("etapa"), f.get("passo"), f.get("esperando") or ""))
if len(sys.argv) > 1:
    for k, l in enumerate(Path(sys.argv[1]).read_text().splitlines()):
        if l.count("|") >= 2:
            o, e, p, s = (["?"] + [x.strip() for x in l.split("|")])[-4:] if l.count("|") == 3 else (f"linha {k + 1}", *[x.strip() for x in l.split("|")])
            estados.append((o, e, p, s))
for origem, e, p, s in estados:
    for d in M.confere(e, p, s):
        acha("ficha fora do mapa", f"{origem}: {e} · {p} · {s or '(sem espera)'}: {d}")

if not achados:
    print("passou · o código, a tela e as fichas batem com o mapa de passos")
else:
    grupos = {}
    for g, msg in achados:
        grupos.setdefault(g, []).append(msg)
    print(f"ACHADOS · {len(achados)} becos ou diferenças com o mapa")
    for g, ms in grupos.items():
        print(f"\n## {g} ({len(ms)})")
        for x in ms:
            print(f"- {x}")
sys.exit(1 if achados else 0)
