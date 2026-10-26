"""Teste tipo A do conserto dos Olhos (17/10/2026, "aprovo o plano olhos-na-animacao"): a leitura da resposta do animador.

  python3 testes/olhos_conserta.py

Casos (entrada → esperado → proibido → origem):
  1. "CUSTO: 12,5 s · gerar foto do plenário, ~US$ 0,04" → vai para custo, não conta como conserto → contar como FEITO
     → plano: "acho que so isso tem que pedir [custo]"
  2. "FALA: 1.5 s · a voz só começa em 3 s" → vai para fala → mexer na fala → "o que é dito [...] tem que vir do roteiro"
  3. "NAO_E: 67.5 s · é a assinatura" → não era defeito → reenviar ao animador → #299, 18:32 (resposta real)
  4. "FEITO: 26.0 s · plenário fica até o capítulo 2" → conserto → perder → #299, 18:32 (resposta real)
  5. texto solto sem formato → nada → inventar item → resposta do animador com comentário
"""
import sys
from pathlib import Path

sys.path[:0] = [str(Path(__file__).resolve().parent.parent), str(Path(__file__).resolve().parent.parent / "ferramentas")]
import animacao as A

texto = """Olhei os quadros.
- FEITO: 26.0 s · plenário fica até o capítulo 2
NAO_E: 67.5 s · é a assinatura
FALA: 1.5 s · a voz só começa em 3 s
CUSTO: 12,5 s · gerar foto do plenário, ~US$ 0,04
o resto ficou como estava"""
r = A.respostas_do_animador(texto)
casos = [
    ("custo vai para custo", r["CUSTO"] == [{"t": 12.5, "msg": "gerar foto do plenário, ~US$ 0,04"}]),
    ("custo não conta como conserto", all(x["t"] != 12.5 for x in r["FEITO"])),
    ("fala vai para fala", [x["t"] for x in r["FALA"]] == [1.5]),
    ("não era defeito", [x["t"] for x in r["NAO_E"]] == [67.5]),
    ("conserto", [x["t"] for x in r["FEITO"]] == [26.0]),
    ("texto solto não vira item", sum(len(v) for v in r.values()) == 4),
    ("NÃO_É com acento", A.respostas_do_animador("NÃO_É: 3 s · ok")["NAO_E"][0]["t"] == 3.0),
]
for nome, ok in casos:
    print(("passou" if ok else "FALHOU") + " · " + nome)
sys.exit(0 if all(ok for _, ok in casos) else 1)
