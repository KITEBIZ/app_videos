"""Tipo A (sem IA): a tela Regras (26/10/2026, ele: "talvez eu tenha que poder ver esse caderno de regras caso queira mudar
algo" e "pode fazer"). Numa cópia temporária da pasta regras/, com a IA fingida: listar; propor não muda o caderno; gravar
aplica só o trecho e guarda a versão de antes; desfazer volta; caderno gerado por programa é só leitura; trecho que não
existe no caderno é recusado; nome fora do padrão não abre arquivo.

  .venv/bin/python testes/regras_tela.py
"""
import shutil, sys, tempfile
from pathlib import Path
sys.path[:0] = [str(Path(sys.argv[0]).resolve().parent.parent)]
import regras_tela as R, ia

falhas = []
tmp = Path(tempfile.mkdtemp()) / "regras"
tmp.mkdir()
(tmp / "ROTEIRISTA.md").write_text("# Roteirista\n\n- Até 60 s.\n- Sem travessão.\n")
(tmp / "PUBLICO.md").write_text("# O que o público gosta (gerado por ferramentas/publico.py; não editar à mão)\n\nx\n")
R.PASTA, R.VERSOES, R.PROPOSTAS, R.HISTORICO = tmp, tmp / "versoes", tmp / ".propostas", tmp / "historico.jsonl"

resposta = {"v": '{"resumo": "vídeo pode ter até 90 s", "trocas": [{"antes": "- Até 60 s.", "depois": "- Até 90 s."}]}'}
ia.chamar = lambda *a, **k: (resposta["v"], {})

lista = {c["nome"]: c for c in R.listar()}
if set(lista) != {"ROTEIRISTA", "PUBLICO"} or not lista["PUBLICO"]["so_leitura"] or lista["ROTEIRISTA"]["so_leitura"]:
    falhas.append(f"listar: {lista}")
antes = (tmp / "ROTEIRISTA.md").read_text()
p = R.propor("ROTEIRISTA", "quero vídeos de até 90 segundos")
if (tmp / "ROTEIRISTA.md").read_text() != antes or not R.ler("ROTEIRISTA")["proposta"]:
    falhas.append("propor mudou o caderno ou não guardou a proposta")
R.aplicar("ROTEIRISTA")
depois = (tmp / "ROTEIRISTA.md").read_text()
if depois != antes.replace("Até 60 s.", "Até 90 s.") or R.ler("ROTEIRISTA")["versoes"] != 1 or R.ler("ROTEIRISTA")["proposta"]:
    falhas.append(f"aplicar: {depois!r}")
R.desfazer("ROTEIRISTA")
if (tmp / "ROTEIRISTA.md").read_text() != antes or R.ler("ROTEIRISTA")["versoes"] != 0:
    falhas.append("desfazer não voltou")
for nome, pedido, quer in (("PUBLICO", "x", "só leitura"), ("../etc", "x", "nome"), ("ROTEIRISTA", "", "vazio")):
    try:
        R.propor(nome, pedido); falhas.append(f"aceitou {quer}")
    except ValueError:
        pass
resposta["v"] = '{"resumo": "r", "trocas": [{"antes": "uma regra que não existe", "depois": "y"}]}'
try:
    R.propor("ROTEIRISTA", "muda"); falhas.append("aceitou trecho que não existe")
except RuntimeError:
    pass
# o caderno mudou entre a proposta e o ok: não grava por cima
resposta["v"] = '{"resumo": "r", "trocas": [{"antes": "- Sem travessão.", "depois": "- Sem travessão nem ponto e vírgula."}]}'
R.propor("ROTEIRISTA", "muda")
(tmp / "ROTEIRISTA.md").write_text(antes + "- Nova.\n")
try:
    R.aplicar("ROTEIRISTA"); falhas.append("gravou por cima de um caderno que mudou")
except RuntimeError:
    pass
shutil.rmtree(tmp.parent)
if falhas:
    print("FALHOU · " + "; ".join(falhas)); sys.exit(1)
print("passou · lista os cadernos; propor não muda nada; gravar troca só o trecho e guarda a versão; desfazer volta; "
      "só leitura, nome estranho, pedido vazio, trecho inexistente e caderno mudado são recusados")
