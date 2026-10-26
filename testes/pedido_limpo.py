"""pedido-limpo (21/10/2026): cada caso tem que FALHAR no código de antes e PASSAR no novo. Sem IA: maestro, animador e
voz são fingidos. Roda numa cópia do #316.   python3 teste_limpo.py <pasta do código>"""
import json, shutil, subprocess, sys, types
from pathlib import Path
COD = Path(sys.argv[1]); sys.path[:0] = [str(COD), str(COD / "ferramentas")]
import os; os.environ.setdefault("GEMINI_API_KEY", "teste")
import estudio as E
T = Path("/tmp/ca/limpo/itens") / COD.name; shutil.rmtree(T, ignore_errors=True); T.mkdir(parents=True)
subprocess.run(["rsync", "-a", "--exclude=animacao/versoes", "--exclude=animacao/chamadas", "--exclude=referencia",
                "--exclude=animacao/previa-*.mp4", "--exclude=*.leve.mp4", "--exclude=*.quadro.mp4", "--exclude=publicacao", "/srv/kitebiz/projetos/conteudo/estudio-v2/videos/316/", f"{T}/316/"], check=True)
E.VIDEOS = T
argv, sys.argv = sys.argv, [sys.argv[0], "4499"]
import servidor as S, animador_novo as AN, animacao as A
sys.argv = argv
ok = []
def caso(nome, cond):
    ok.append((nome, bool(cond)))

# A. o "ELE DISSE" coberto aos 3,5 s (#316 16:21) com as respostas guardadas de verdade do #316
ditos = json.loads((T / "316/animacao/respondidos.json").read_text())
q = {"t": 3.5, "tipo": "régua · escondido", "msg": "'ELE DISSE' com parte coberta por vmd"}
if hasattr(AN, "tempos"):
    some = AN.ja_respondido(q, ditos, AN.tempos(316))
else:                                               # o código de antes: ja_respondido(q, lista)
    some = AN.ja_respondido({**q, "tipo": "escondido"}, ditos)
caso("A1 · o grave novo aos 3,5 s não é descartado por respostas antigas de outro assunto", not some)
# o mesmo ponto que o animador disse não ser defeito, com a mesma voz, continua dispensado
if hasattr(AN, "tempos"):
    dispensado = [{"t": 3.4, "tipo": "NAO_E", "msg": "é a saída da capa", "tempos": AN.tempos(316),
                   "ponto_tipo": "régua · escondido", "ponto_msg": "'ELE DISSE' com parte coberta por vmd"}]
    caso("A2 · o mesmo ponto já dispensado (NAO_E, mesma voz) continua de fora", AN.ja_respondido(q, dispensado, AN.tempos(316)))
    caso("A3 · com a voz regravada, a dispensa antiga não vale", not AN.ja_respondido(q, dispensado, "outra-voz"))
else:
    caso("A2 · o mesmo ponto já dispensado (NAO_E, mesma voz) continua de fora", False)
    caso("A3 · com a voz regravada, a dispensa antiga não vale", False)

# B. troca de fala + tela na mesma ordem: uma passada só do animador
chamadas = []
S.maestro.decidir = lambda num, texto, msg_id=None: {"intencao": "ordem", "segundos": 1, "por_que": "teste",
    "acoes": [{"ferramenta": "mudar_fala", "instrucao": "troca a fala do bloco 1"}, {"ferramenta": "ajustar_video", "instrucao": "take em tela cheia"}]}
S.agente.responder = lambda num, msg, aviso="", modelo=None: (chamadas.append(("roteiro", modelo)), E.mexe_ficha(num, mudou=[1]))
S.voz.gravar = lambda num: {"problemas": [], "duracao": 70.0}
S.animacao.animar = lambda num, pedido=None, msg_id=None, **k: (chamadas.append(("animar", pedido, k.get("modo"))), "ok")[1]
msg = {"id": "t1", "texto": "troca a fala do bloco 1 e põe o take em tela cheia"}
S.maestro_atende(316, msg)
anims = [c for c in chamadas if c[0] == "animar"]
caso(f"B1 · troca de fala + tela anima uma vez só (animou {len(anims)}x)", len(anims) == 1)
caso("B2 · o pedido de tela vai junto nessa passada", bool(anims) and "tela cheia" in (anims[0][1] or ""))
caso("B3 · mudar a fala vai ao Opus direto (sem a classificação por palavras)", ("roteiro", "opus") in chamadas)

# C. revisão completa pelo nome, não por palavra
chamadas.clear()
S.maestro.decidir = lambda num, texto, msg_id=None: {"intencao": "ordem", "acoes": [{"ferramenta": "revisar_video", "instrucao": "revisa"}]}
S.maestro_atende(316, {"id": "t2", "texto": "dá uma geral no vídeo"})
caso("C1 · revisar_video chega à animação como modo revisar", any(c[0] == "animar" and c[2] == "revisar" for c in chamadas))
chamadas.clear()
S.maestro.decidir = lambda num, texto, msg_id=None: {"intencao": "ordem", "acoes": [{"ferramenta": "ajustar_video", "instrucao": "olha os erros do bloco 2 e conserta"}]}
S.maestro_atende(316, {"id": "t3", "texto": "olha os erros do bloco 2 e conserta"})
caso("C2 · 'olha os erros' num ajuste não vira revisão completa", any(c[0] == "animar" and c[2] != "revisar" for c in chamadas)
     and not (hasattr(AN, "PEDE_REVISAO") and AN.PEDE_REVISAO.search("olha os erros do bloco 2")))
caso("C3 · link ou 'baixa o vídeo' não desvia para o animador antigo", AN.serve("baixa o vídeo do UOL https://x.y e usa no bloco 1"))

# D. o maestro não respondeu: o chat pergunta, sem cair nas listas de palavras
chamadas.clear()
S.maestro.decidir = lambda num, texto, msg_id=None: {}
E.chat_add(316, "ele", "muda a capa pra outra", id_msg="t4")
E.mexe_ficha(316, etapa="Animação", passo="prévia pronta")
caiu = {"capa": 0}
S.fazer_capas = lambda num, msg=None: caiu.__setitem__("capa", caiu["capa"] + 1)
S.fazer_legenda = lambda num, msg=None: None
import threading
th = threading.Thread(target=S.trabalhador, args=(316,), daemon=True); th.start(); th.join(20)
resp = [m for m in E.chat(316) if m.get("responde") == "t4"]
caso(f"D1 · sem maestro, o chat pergunta (respostas: {len(resp)}) e nada roda pelas listas (capa {caiu['capa']}x, animar "
     f"{len(chamadas)}x{', ficou em laço' if th.is_alive() else ''})", len(resp) == 1 and caiu["capa"] == 0 and not chamadas and not th.is_alive())
if th.is_alive():                     # o código de antes fica em laço: o resto do teste segue sem ele
    S.maestro.decidir = lambda *a, **k: {"intencao": "duvida", "acoes": []}

# E. o grave que sobrou: nome na trava e "Aprovar mesmo assim"
cf = T / "316/animacao/conferencia.json"; c = json.loads(cf.read_text())
c["regua"] = [{"de": 3.5, "tipo": "escondido", "msg": "'ELE DISSE' com parte coberta por vmd"}]; cf.write_text(json.dumps(c))
E.mexe_ficha(316, passo="prévia pronta")
fl = S.faltas_aprovar(316)
caso(f"E1 · a trava diz qual é o grave ({[x for x in fl if 'régua' in x]})", any("ELE DISSE" in x for x in fl))
try:
    fl2 = S.faltas_aprovar(316, mesmo_assim=True)
    caso("E2 · 'Aprovar mesmo assim' tira só a trava da régua", not any("régua" in x for x in fl2))
except TypeError:
    caso("E2 · 'Aprovar mesmo assim' tira só a trava da régua", False)

# F. o aviso para ele: grave pelo nome, take ampliado demais, aviso do animador
if hasattr(AN, "aviso_para_ele"):
    txt = AN.aviso_para_ele(316, c["regua"], [("CUSTO", {"t": 3.0, "msg": "precisa refazer a capa"})])
    caso("F1 · o grave que sobrou sai pelo nome no chat", "ELE DISSE" in txt and "Aprovar mesmo assim" in txt)
    caso("F2 · o aviso do animador chega ao chat", "precisa refazer a capa" in txt)
    cena = T / "316/animacao/cena.html"; base = cena.read_text()
    cena.write_text(base + "\nT.take({src: 'material/wB9Fr3zawLY/video.mp4', ini: 3.3, fim: 4.9, corte: 43.7, cheia: {x: 160, y: 52, s: 7.4}});")
    caso(f"F3 · o plano aberto da Cultura ampliado ~3 vezes sobre o original é avisado ({AN.ampliados(316)})",
         "ampliado 3.1 vezes" in AN.aviso_para_ele(316, [], []))
    cena.write_text(base)
    caso(f"F4 · o close do UOL (4,6 na cópia leve, ~1,9 no original) não é avisado ({AN.ampliados(316)})", not AN.ampliados(316))
else:
    for n in ("F1 · o grave que sobrou sai pelo nome no chat", "F2 · o aviso do animador chega ao chat", "F3 · take ampliado é avisado",
              "F4 · close bom não é avisado"):
        caso(n, False)

# G. selo: com 4 dos pedidos na tela, a régua não cobra os que faltam
import regua as RG, ver
A._trechos = lambda num: [(0, 10)]
ver.regua = lambda num, de, ate, prefixo="", limpar=False: (None, [{"tipo": "falta-selo", "msg": f"bloco {n}: a coluna Tela pede o selo X e ele não aparece", "ini": n, "fim": n + 1} for n in (5, 6)])
ver.percorrer = lambda num, passo, d: (None, [], None)
A.trechos_vazios = lambda feitos: []
RG.selos_pedidos = lambda d: [(n, "CONFIRMADO", n, n + 1) for n in range(1, 7)]        # 6 pedidos, 2 faltando: 4 na tela
r = A._regua_inteira(316)
caso(f"G1 · com 4 selos na tela, a régua não cobra mais ({[x['tipo'] for x in r]})", not any(x["tipo"] == "falta-selo" for x in r))
RG.selos_pedidos = lambda d: [(n, "CONFIRMADO", n, n + 1) for n in range(1, 5)]        # 4 pedidos, 2 faltando: 2 na tela
r = A._regua_inteira(316)
caso("G2 · com 2 selos na tela, a régua ainda cobra os que faltam", sum(x["tipo"] == "falta-selo" for x in r) == 2)

# H. o leitor de respostas aceita faixa de tempo
h = A.respostas_do_animador("CUSTO: 3-8 s · nitidez ruim")["CUSTO"]
caso(f"H1 · 'CUSTO: 3-8 s' vira t=3 e a mensagem certa ({h})", h and h[0]["t"] == 3 and h[0]["msg"] == "nitidez ruim")

for n, b in ok:
    print("PASSOU" if b else "FALHOU", "·", n)
print(f"{sum(b for _, b in ok)} de {len(ok)}")
