"""roteiro-com-direcao, parte C (Opus de verdade, na cópia): reescrever | propor | novo."""
import json, sys, time
import estudio as E, pauta
modo, N = sys.argv[1], int(sys.argv[2])
E.mexe_ficha(N, etapa="Pauta", passo="roteiro pronto")
t = time.time()
if modo == "reescrever":
    print(pauta.reescrever(N, "analise", "acho que esse vídeo fica melhor explicando do que checando frase por frase"))
elif modo == "propor":
    print(pauta.propor(N, "que outros caminhos dá pra fazer com esse material?"))
else:
    p = E.pasta(N)
    meta = json.loads((p / "referencia/meta.json").read_text())
    pauta.guardar_versao(N, "antes do teste de roteiro novo")
    pauta.escrever(N, E.ler_ficha(N), meta, (p / "referencia/transcricao.txt").read_text())
    bs = E.blocos(N); print(f"novo: {len(bs)} blocos, uns {E.segundos(bs)} s")
print("segundos:", round(time.time() - t))
