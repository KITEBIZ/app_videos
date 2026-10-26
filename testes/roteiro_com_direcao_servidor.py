"""roteiro-com-direcao: o trabalhador do servidor leva cada decisão do maestro à função certa e responde no chat (sem IA)."""
import sys, tempfile
from pathlib import Path
sys.argv = ["servidor.py", "4499"]
sys.path[:0] = [str(Path(__file__).resolve().parent.parent)]
import estudio as E
E.VIDEOS = Path(tempfile.mkdtemp()) / "videos"            # 25/10/2026: pasta temporária (era o #318 da pasta de verdade)
E.LIXEIRA = E.VIDEOS / "_lixeira"
import maestro, pauta, agente
import servidor as S
N, _ = E.criar_item("ideia", texto="teste")
chamou = []
pauta.reescrever = lambda n, d, t: chamou.append(("reescrever", d)) or "Reescrevi (fingido)."
pauta.propor = lambda n, t: chamou.append(("propor",)) or "Direções (fingido)."
pauta.voltar_versao = lambda n: chamou.append(("voltar",)) or "Voltei (fingido)."
pauta.propor_mudanca = lambda n, d, t: chamou.append(("proposta", d)) or "Proposta (fingido)."
pauta.aplicar_proposta = lambda n, t="": chamou.append(("aplicar",)) or "Apliquei (fingido)."
def resp(n, m, aviso="", modelo="opus", modo=None):
    chamou.append(("agente", modelo, "NÃO mude" in aviso) + ((modo,) if modo else ())); E.chat_add(n, "agente", "ok (fingido)", responde=m["id"])
agente.responder = resp
casos = [({"intencao": "ordem", "acoes": [{"ferramenta": "reescrever_roteiro", "direcao": "analise", "instrucao": "x"}]}, ("reescrever", "analise")),
         ({"intencao": "pergunta", "acoes": [{"ferramenta": "propor_direcoes", "instrucao": "x"}]}, ("propor",)),
         ({"intencao": "ordem", "acoes": [{"ferramenta": "voltar_versao", "instrucao": "x"}]}, ("voltar",)),
         ({"intencao": "ordem", "acoes": [{"ferramenta": "ajustar_roteiro", "instrucao": "x"}]}, ("agente", "opus", False)),
         ({"intencao": "pergunta", "acoes": [{"ferramenta": "responder", "instrucao": "x"}]}, ("agente", "sonnet", True)),
         ({"intencao": "duvida", "acoes": [], "pergunta_para_ele": "Você quer X ou Y?"}, None),
         ({"intencao": "ordem", "acoes": [{"ferramenta": "propor_mudanca", "direcao": "analise", "instrucao": "x"}]}, ("proposta", "analise")),
         ({"intencao": "ordem", "acoes": [{"ferramenta": "aplicar_proposta", "instrucao": "x"}]}, ("aplicar",)),
         ("botao", ("aplicar",)),
         ({"intencao": "pergunta", "acoes": [{"ferramenta": "conversar", "instrucao": "x"}]}, ("agente", "opus", True, "editor")),
         ({}, "falha")]
ok = 0
for d, esp in casos:
    E.mexe_ficha(N, etapa="Pauta", passo="roteiro pronto", proposta={"direcao": "analise", "texto": "t", "pedido": "p"} if d == "botao" else None)
    # o botão Aprovar a direção não passa pelo maestro: se passar, o maestro "decide" outra coisa e o caso falha
    maestro.decidir = lambda n, t, msg_id=None, conversa=None, _d=d: ({"intencao": "ordem", "acoes": [{"ferramenta": "voltar_versao"}]}
                                                                    if _d == "botao" else dict(_d, segundos=0.1) if _d else {})
    chamou.clear()
    m, _ = E.chat_add(N, "ele", "teste", **({"acao": "aprovar-direcao"} if d == "botao" else {}))
    S.trabalhador(N)
    r = [x for x in E.chat(N) if x.get("responde") == m["id"]]
    f = E.ler_ficha(N)
    certo = (("Não consegui entender" in r[-1]["texto"]) if esp == "falha" and r else True) and (chamou == ([esp] if isinstance(esp, tuple) else [])) and len(r) >= 1 and not E.pendentes(N) and f["passo"] != "trabalhando no seu pedido"
    ok += certo
    d = {"acoes": [{"ferramenta": "botão Aprovar a direção"}]} if d == "botao" else d
    print("PASSOU" if certo else "FALHOU", "·", (d.get("acoes") or [{}])[0].get("ferramenta") or d.get("intencao") or "maestro mudo",
          "· chamou", chamou, "· chat:", r[-1]["texto"][:70] if r else "-", "· passo:", f["passo"])
# 26/10/2026: "quero fazer um vídeo parecido" com o link vira Fazer igual
frases = {"quero fazer um video parecido": True, "faz um igual a esse": True, "o que ele disse é falso": False}
if any(bool(S.PARECIDO.search(f)) != v for f, v in frases.items()):
    ok -= 1; print("FALHOU · a frase de vídeo parecido")
print(f"{ok} de {len(casos)} passaram")
sys.exit(0 if ok == len(casos) else 1)
