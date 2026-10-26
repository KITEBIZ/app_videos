"""Testes tipo A do formato "Fomos conferir" (18/10/2026, "aprovo o plano formato-fomos-conferir").

  python3 testes/fomos_conferir.py

1. A frase do chat (servidor.molde_pedido): entrada → esperado → proibido → origem
   "usa o fomos conferir" → conferir → nada · plano aprovado
   "usa o formato Fomos Conferir neste vídeo" → conferir → nada · plano aprovado
   "volta ao molde normal" → desliga → manter ligado · plano (desliga como o molde curso)
   "tira o fomos conferir" → desliga → ligar · plano
   "usa o molde curso" → curso → conferir · molde-curso (17/10)
   "a abertura com fomos conferir ficou boa" → nada → ligar · frase normal sobre o roteiro (não pede formato)
(A parte 2, a cor das partes da segunda opinião, saiu com ela em 26/10/2026.)
"""
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(RAIZ), str(RAIZ / "ferramentas")]
from servidor import molde_pedido

casos = [
    ("frase: usa o fomos conferir", molde_pedido("usa o fomos conferir") == "conferir"),
    ("frase: usa o formato Fomos Conferir neste vídeo", molde_pedido("usa o formato Fomos Conferir neste vídeo") == "conferir"),
    ("frase: volta ao molde normal", molde_pedido("volta ao molde normal") == ""),
    ("frase: tira o fomos conferir", molde_pedido("tira o fomos conferir") == ""),
    ("frase: usa o molde curso", molde_pedido("usa o molde curso") == "curso"),
    ("frase: comentário sobre a abertura não liga", molde_pedido("a abertura com fomos conferir ficou boa") is None),
    ("frase: 'refaz as capas no formato Fomos conferir' não religa (caso real, 18/10 10:22)",
     molde_pedido("refaz as duas capas no\n  formato Fomos conferir") is None),
    ("frase: 'aplica a proposta Fomos conferir' não religa", molde_pedido("aplica a proposta Fomos conferir") is None),
]

for nome, ok in casos:
    print(("passou" if ok else "FALHOU") + " · " + nome)
sys.exit(0 if all(ok for _, ok in casos) else 1)
