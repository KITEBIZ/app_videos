"""roteiro-com-direcao, parte B: a fala de outra pessoa só se corta (sem IA: o agente é trocado por quem edita o arquivo)."""
import json, sys
import estudio as E, agente
N = 306
p = E.pasta(N)
E.mexe_ficha(N, etapa="Pauta", passo="roteiro pronto")
original = (p / "ROTEIRO.md").read_text()
alheio = next(b for b in E.blocos(N) if not b["nosso"] and E.corte(b["fala"]) and E.corte(b["fala"])[2] == "referencia")
c = E.corte(alheio["fala"])
ws = [w for w in json.loads((p / "referencia/palavras.json").read_text()) if c[0] - .3 <= w[0] and w[1] <= c[1] + .3]
linha = next(l for l in original.splitlines() if l.startswith(f"| {alheio['n']} |"))
fala_txt = alheio["fala"]
ok = []

def caso(nome, nova_fala, deve_voltar):
    (p / "ROTEIRO.md").write_text(original)
    nova_linha = linha.replace(fala_txt, nova_fala)
    assert nova_linha != linha or nova_fala == fala_txt, "a troca não casou"
    agente.trabalhar = lambda *a, **k: ((p / "ROTEIRO.md").write_text(original.replace(linha, nova_linha)), ("Feito.", 0))[1]
    msg, _ = E.chat_add(N, "ele", f"teste: {nome}")
    agente.responder(N, msg, modelo="opus")
    voltou = (p / "ROTEIRO.md").read_text() == original
    resp = [m for m in E.chat(N) if m.get("responde") == msg["id"]][-1]["texto"]
    passou = voltou == deve_voltar
    ok.append(passou)
    print("PASSOU" if passou else "FALHOU", "·", nome, "· voltou" if voltou else "· ficou", "·", resp[:150])

def fala(ini, fim, palavras):
    return f"{' '.join(w[2] for w in palavras)} ({ini:.2f}-{fim:.2f})".replace(".", ",", 0)

fmt = lambda x: f"{x:.2f}".replace(".", ",")
print("trecho:", alheio["n"], alheio["quem"], c, "·", len(ws), "palavras")
# 1. trocar uma palavra do meio
troca = [w[2] for w in ws]; troca[len(troca) // 2] = "jamais"
caso("trocar uma palavra da fala dela", f"{' '.join(troca)} ({fmt(c[0])}-{fmt(c[1])})", True)
# 2. juntar pedaço de outro lugar (palavras de 20 s depois) no fim
todas = json.loads((p / "referencia/palavras.json").read_text())
longe = [w[2] for w in todas if w[1] < c[0] - 30][-4:]
assert len(longe) == 4, "o pedaço de outro momento saiu vazio"
caso("juntar pedaço de outro momento", f"{' '.join([w[2] for w in ws] + longe)} ({fmt(c[0])}-{fmt(c[1])})", True)
# 3. cortar: tirar as 3 primeiras palavras e mudar o início do corte
caso("cortar o começo do trecho (pode)", f"{' '.join(w[2] for w in ws[3:])} ({fmt(ws[3][0])}-{fmt(c[1])})", False)
# 4. cortar o fim
caso("cortar o fim do trecho (pode)", f"{' '.join(w[2] for w in ws[:-3])} ({fmt(c[0])}-{fmt(ws[-4][1])})", False)
# 5. mudar uma fala NOSSA (pode): troca a linha de um bloco nosso
nosso = next(b for b in E.blocos(N) if b["nosso"])
linha, fala_txt = next(l for l in original.splitlines() if l.startswith(f"| {nosso['n']} |")), nosso["fala"]
caso("mudar a nossa fala (pode)", nosso["fala"] + " Confere.", False)
(p / "ROTEIRO.md").write_text(original)
print(f"{sum(ok)} de {len(ok)} passaram")
