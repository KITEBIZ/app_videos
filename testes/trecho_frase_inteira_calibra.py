"""Calibra o fim_de_frase: o caso conhecido do #327 e todos os trechos (do vídeo da pauta) dos roteiros publicados."""
import json, sys
sys.path.insert(0, "/tmp/ca/frase"); sys.path.insert(1, "/srv/kitebiz/projetos/conteudo/estudio-v2")
import pauta, estudio as E
def j_do_fim(ws, fim):
    return max(i for i, w in enumerate(ws) if w[0] < fim - .05)      # a última palavra que começa dentro do corte
ws = [w for w in json.loads((E.pasta(327) / "referencia/palavras.json").read_text()) if pauta._norm(w[2])]
print("#327 corte 7,29-10,34 ('…a meta,'):", "fim de frase" if pauta.fim_de_frase(ws, j_do_fim(ws, 10.34)) else "MEIO da frase (esperado)")
print("#327 corte 7,29-19,60 ('…Flávio Bolsonaro.'):", "fim de frase (esperado)" if pauta.fim_de_frase(ws, j_do_fim(ws, 19.60)) else "MEIO da frase")
tot = meio = 0
for n in [300, 301, 302, 304, 305, 306, 307, 312, 318]:
    arq = E.pasta(n) / "referencia/palavras.json"
    ws = [w for w in json.loads(arq.read_text()) if pauta._norm(w[2])]
    for b in E.blocos(n):
        c = E.corte(b["fala"])
        if b["nosso"] or not c or c[2] != "referencia": continue
        tot += 1
        ult = pauta._norm(E.CORTE.sub('', b['fala']).split()[-1])
        js = [i for i, w in enumerate(ws) if c[0] - .3 <= w[0] < c[1] + .3 and pauta._norm(w[2]) == ult]
        j = js[-1] if js else j_do_fim(ws, c[1])
        if not pauta.fim_de_frase(ws, j):
            meio += 1; print(f"  #{n} b{b['n']} termina em '{' '.join(w[2] for w in ws[max(0,j-3):j+1])}' | pausa {ws[j+1][0]-ws[j][1]:.2f} s | depois: '{' '.join(w[2] for w in ws[j+1:j+4])}'")
print(f"publicados: {meio} de {tot} trechos terminam no meio da frase")
