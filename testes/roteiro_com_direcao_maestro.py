"""roteiro-com-direcao, parte A: o maestro entende o pedido no Roteiro (Sonnet de verdade; nada executa).
Compara com o caminho de antes (classifica.py: "conversa" ia ao Sonnet que só conversa; o resto ao Opus que edita)."""
import json, sys, time
import estudio as E, maestro, pauta
N = int(sys.argv[1]) if len(sys.argv) > 1 else 301
E.mexe_ficha(N, etapa="Pauta", passo="roteiro pronto")
pauta.guardar_versao(N, "teste")
REESCREVI = "[agente 10:02] Reescrevi como Análise: 9 blocos, uns 58 s. O roteiro de antes ficou guardado."
DIRECOES = ("[agente 10:05] Direções para este vídeo: 1. **Cinco frases, um placar** (Checagem): \"O Lula fez cinco "
            "afirmações...\" 2. **O Brasil que ele recebeu** (Análise): \"Quebrado? O Tesouro diz outra coisa...\" 3. **A conta do "
            "seu bolso** (Fazer igual): \"Quanto a inflação tirou de você...\" Diga qual quer.")
CASOS = [  # (pedido do jeito dele, conversa antes, ferramenta esperada, direção esperada)
    ("acho que esse vídeo fica melhor explicando do que checando frase por frase", "", "reescrever_roteiro", "analise"),
    ("esse ângulo não tá bom, puxa mais pro lado do bolso de quem paga imposto", "", "reescrever_roteiro", "angulo"),
    ("tira o comecinho da fala do Lula no bloco 4, deixa só o brasil quebrado", "", "ajustar_roteiro", None),
    ("que outros caminhos dá pra fazer com esse material?", "", "propor_direcoes", None),
    ("faz naquele estilo que só eu falo, sem mostrar o vídeo do Lula", "", "reescrever_roteiro", "fazer_igual"),
    ("muda o que o Lula fala no bloco 2 pra ele dizer que o brasil tava ótimo", "", "responder", None),
    ("não gostei, volta como estava antes", REESCREVI, "voltar_versao", None),
    ("o bloco 3 tá muito comprido, enxuga", "", "ajustar_roteiro", None),
    ("o que tu achou desse roteiro? vale a pena?", "", "responder", None),
    ("faz a 2", DIRECOES, "reescrever_roteiro", "analise"),
    ("bora voltar pra checagem com placar no fim", REESCREVI, "reescrever_roteiro", "checagem"),
]
ANTES = {"conversa": "responder"}          # caminho de antes: o que o classifica decidia
novo = velho = 0
linhas = []
for texto, conversa, esp, dir_esp in CASOS:
    d = maestro.decidir(N, texto, conversa=conversa or "(nada ainda)")
    a = (d.get("acoes") or [{}])[0]
    f, dr = a.get("ferramenta") or d.get("intencao"), a.get("direcao")
    ok = f == esp and (dir_esp is None or dr == dir_esp)
    novo += ok
    import classifica
    t = classifica.tipo(texto)
    v = ANTES.get(t, "ajustar_roteiro")
    vok = v == esp
    velho += vok
    linhas.append((ok, texto, esp + (f"({dir_esp})" if dir_esp else ""), f + (f"({dr})" if dr else ""), vok, t))
    print(("PASSOU" if ok else "FALHOU"), "·", texto, "· esperado", esp, dir_esp or "", "· novo:", f, dr or "",
          "· antes:", t, "->", v, ("ok" if vok else "errado"), "·", str(d.get("por_que", ""))[:90], flush=True)
print(f"novo: {novo} de {len(CASOS)} · antes: {velho} de {len(CASOS)}")
gasto = [json.loads(l) for l in open(E.pasta(N) / "gasto.jsonl") if '"maestro"' in l][-len(CASOS):]
print("custo do maestro:", round(sum(x.get("usd") or 0 for x in gasto), 3), "US$ em", len(gasto), "chamadas")
