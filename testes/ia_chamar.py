"""Tipo A (sem IA, sem rede): a chamada de IA de um lugar só (ia.py, 25/10/2026, ele: "pode fazer"). Um "claude" de
mentira no PATH responde como o de verdade (stream-json), dá erro, trava ou não diz nada; a chamada tem de devolver o
texto, anotar o gasto, guardar o uso da conta, respeitar o prazo e dizer o erro. Usa uma pasta de vídeos temporária.

  .venv/bin/python testes/ia_chamar.py
"""
import json, os, sys, tempfile, time
from pathlib import Path

RAIZ = Path(sys.argv[0]).resolve().parent.parent
sys.path[:0] = [str(RAIZ)]
import estudio as E
E.VIDEOS = Path(tempfile.mkdtemp()) / "videos"
E.LIXEIRA = E.VIDEOS / "_lixeira"
E.LIMITE = Path(tempfile.mkdtemp()) / "limite.json"
import ia

bin_ = Path(tempfile.mkdtemp())
(bin_ / "claude").write_text('''#!/usr/bin/env python3
import json, os, sys, time
modo = os.environ.get("FINGE", "ok"); entrada = sys.stdin.read()
if modo == "erro":
    sys.stderr.write("Error: limite da conta atingido"); sys.exit(1)
if modo == "trava":
    time.sleep(60)
if modo == "vazio":
    sys.exit(0)
print(json.dumps({"type": "assistant", "message": {"content": [{"type": "tool_use", "name": "WebSearch", "input": {"query": "x"}}]}}), flush=True)
print(json.dumps({"type": "rate_limit_event", "rate_limit_info": {"status": "allowed", "unifiedWindows": {"five_hour": {"utilization": .4}}}}))
print(json.dumps({"type": "result", "result": "resposta: " + ("blocos" if entrada.startswith("{") else "texto") + ' {"ok": 1}',
                  "total_cost_usd": 0.0123, "usage": {"input_tokens": 10}, "duration_ms": 900, "is_error": False}))
''')
(bin_ / "claude").chmod(0o755)
os.environ["PATH"] = f"{bin_}:{os.environ['PATH']}"
falhas = []
num, _ = E.criar_item("igual", texto="teste")

os.environ["FINGE"] = "ok"
t, u = ia.chamar("oi", "teste", "sonnet", num=num, limite=30)
if not t.startswith("resposta: texto") or u["erro"] or u["usd"] != 0.0123:
    falhas.append(f"texto: {t!r} {u}")
if ia.json_de(t) != {"ok": 1} or ia.json_de("nada") is not None or ia.json_de('x [1, 2] y', "[") != [1, 2]:
    falhas.append("json_de não tirou o JSON do texto")
t, u = ia.chamar([{"type": "text", "text": "oi"}], "teste blocos", "sonnet", num=num, limite=30, registro=E.pasta(num) / "r.jsonl")
if not t.startswith("resposta: blocos") or not (E.pasta(num) / "r.jsonl").exists():
    falhas.append(f"blocos/registro: {t!r}")
gastos = [json.loads(l) for l in (E.pasta(num) / "gasto.jsonl").read_text().splitlines()]
if [g["quem"] for g in gastos][:2] != ["teste", "teste blocos"] or gastos[0]["usd"] != 0.0123:
    falhas.append(f"o gasto não foi anotado: {gastos}")
if not E.LIMITE.exists():
    falhas.append("o uso da conta não foi guardado")

# o aviso de cada passo enquanto a resposta chega (o agente do chat mostra os passos na tela)
vistos = []
t, u = ia.chamar("oi", "teste passos", "sonnet", limite=30, ao_evento=lambda ev: vistos.append(ev.get("type")))
if "assistant" not in vistos or "result" not in vistos or not t:
    falhas.append(f"o aviso dos passos não chegou: {vistos}")
# o agente do chat pela chamada única: os passos vão para a ficha e a resposta volta
import agente
r, cod = agente.trabalhar(num, "oi", quem="agente do chat", modelo="sonnet")
if cod or not r.startswith("resposta:") or not any("buscando na web" in p["texto"] for p in E.ler_ficha(num).get("passos") or []):
    falhas.append(f"agente do chat: código {cod}, resposta {r!r}, passos {E.ler_ficha(num).get('passos')}")

os.environ["FINGE"] = "erro"
t, u = ia.chamar("oi", "teste", "sonnet", num=num, limite=30)
if t or "limite da conta" not in u["erro"]:
    falhas.append(f"erro do claude: {t!r} {u['erro']!r}")
os.environ["FINGE"] = "trava"
t0 = time.time(); t, u = ia.chamar("oi", "teste", "sonnet", limite=2)
if t or "passou de 2 s" not in u["erro"] or time.time() - t0 > 15:
    falhas.append(f"prazo: {u['erro']!r} em {time.time() - t0:.0f} s")
os.environ["FINGE"] = "vazio"
t, u = ia.chamar("oi", "teste", "sonnet", limite=30)
if t or not u["erro"]:
    falhas.append(f"resposta vazia sem erro: {u}")

cmd = ia.comando("sonnet", "WebSearch,WebFetch,Read")
perm = cmd[cmd.index("--allowedTools") + 1:cmd.index("--disallowedTools")]
if "Read" in perm or not any(p.startswith("Read(") for p in perm) or "--permission-mode" not in cmd:
    falhas.append(f"ferramentas de arquivo sem caminho: {perm}")
fontes = "".join((RAIZ / f).read_text() for f in ("canal.py", "animacao.py", "maestro.py", "legenda_post.py",
                                                  "fontes.py", "pauta.py", "radar.py", "animador_novo.py", "agente.py", "capa.py",
                                                  "publicador/comentarios_whatsapp.py"))
if '"claude", "-p"' in fontes:
    falhas.append("ainda há chamada direta ao claude fora do ia.py")

if falhas:
    print("FALHOU · " + "; ".join(falhas))
    sys.exit(1)
print("passou · texto e blocos, gasto e uso da conta anotados, erro do claude dito, prazo de verdade, resposta vazia é erro, "
      "ferramentas com caminho, nenhuma chamada direta fora do ia.py")
