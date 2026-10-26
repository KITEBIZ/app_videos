"""Testes que tentam enganar o chat da v2 (16/10/2026, "aprovo o plano v2-parte1"). Rodam contra o servidor local.

  python3 testes/chat.py            cria o vídeo de teste #900, faz os 5 testes e diz passou/falhou em cada um

1. repetida: o celular manda a mesma mensagem duas vezes (sem resposta na 1ª) -> gravada uma vez só
2. conexão cai: o celular desiste antes da resposta e reenvia -> gravada uma vez, e a 2ª diz "repetida"
3. longa: mensagem de 4.000 letras com acento e quebra de linha -> gravada igual, letra por letra
4. em fila: duas mensagens seguidas -> as duas respondidas, na ordem
5. servidor reiniciado: mensagem gravada e servidor derrubado antes de responder -> ao subir, ele responde
"""
import json, os, shutil, signal, socket, subprocess, sys, time, urllib.request, uuid
from pathlib import Path

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ))
import estudio as E

URL = "http://127.0.0.1:4400"
N = 900
res = []


def post(caminho, corpo, tempo=15):
    req = urllib.request.Request(URL + caminho, data=json.dumps(corpo).encode(), headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=tempo))


def dele(id_):
    return [m for m in E.chat(N) if m["quem"] == "ele" and m["id"] == id_]


def respondida(id_, limite=240):
    t0 = time.time()
    while time.time() - t0 < limite:
        if any(m.get("responde") == id_ for m in E.chat(N)):
            return True
        time.sleep(3)
    return False


def preparar():
    p = E.pasta(N)
    if p.exists():
        shutil.rmtree(p)
    p.mkdir(parents=True)
    f = {"num": N, "titulo": "teste do chat", "tipo": "ideia", "link": "", "texto_dele": "", "etapa": "Pauta",
         "passo": "roteiro pronto", "passo_desde": E.agora(), "erro": "", "esperando": "Aprovar o roteiro", "nota": None,
         "id_pauta": None, "criado": E.agora(), "atualizado": E.agora(), "mudou": []}
    (p / "ficha.json").write_text(json.dumps(f, ensure_ascii=False))
    (p / "chat.jsonl").write_text("")
    (p / "ROTEIRO.md").write_text("# Roteiro de teste\n\n| # | Bloco | Quem | Fala | Tela |\n|---|---|---|---|---|\n"
                                  "| 1 | Abertura | nós | Este é um vídeo de teste do chat. | TESTE |\n"
                                  "| 2 | Fecho | nós | Compartilha com quem precisa ver. | COMPARTILHE |\n")


def ok(nome, passou, detalhe=""):
    res.append((nome, passou, detalhe))
    print(("PASSOU " if passou else "FALHOU ") + nome + (f" · {detalhe}" if detalhe else ""), flush=True)


def servidor_pid():
    out = subprocess.run(["lsof", "-ti", "tcp:4400", "-sTCP:LISTEN"], capture_output=True, text=True).stdout.split()
    return int(out[0]) if out else None


def main():
    preparar()
    # 1. repetida
    i1 = str(uuid.uuid4())
    a = post(f"/api/item/{N}/mensagem", {"id": i1, "texto": "teste 1: responda só 'ok 1'"})
    b = post(f"/api/item/{N}/mensagem", {"id": i1, "texto": "teste 1: responda só 'ok 1'"})
    ok("1 repetida", len(dele(i1)) == 1 and b.get("repetida") is True and a.get("recebida"), f"{len(dele(i1))} gravada(s)")
    # 2. conexão cai: manda e fecha o socket sem ler a resposta
    i2 = str(uuid.uuid4())
    corpo = json.dumps({"id": i2, "texto": "teste 2: responda só 'ok 2'"}).encode()
    s = socket.create_connection(("127.0.0.1", 4400))
    s.sendall(f"POST /api/item/{N}/mensagem HTTP/1.1\r\nHost: x\r\nContent-Type: application/json\r\nContent-Length: {len(corpo)}\r\n\r\n".encode() + corpo)
    s.close()
    time.sleep(1)
    r = post(f"/api/item/{N}/mensagem", {"id": i2, "texto": "teste 2: responda só 'ok 2'"})
    ok("2 conexão cai e reenvia", len(dele(i2)) == 1 and r.get("repetida") is True, f"{len(dele(i2))} gravada(s), repetida={r.get('repetida')}")
    # 3. longa
    i3 = str(uuid.uuid4())
    longa = ("Ação, coração e informação: teste três.\n" * 110)[:4000]
    post(f"/api/item/{N}/mensagem", {"id": i3, "texto": longa + " Responda só 'ok 3'."})
    g = dele(i3)
    ok("3 longa", len(g) == 1 and g[0]["texto"] == (longa + " Responda só 'ok 3'.").strip(), f"{len(g[0]['texto']) if g else 0} letras gravadas")
    # 4. em fila: as três de cima mais uma, todas respondidas, na ordem
    i4 = str(uuid.uuid4())
    post(f"/api/item/{N}/mensagem", {"id": i4, "texto": "teste 4: responda só 'ok 4'"})
    todas = all(respondida(i) for i in (i1, i2, i3, i4))
    ordem = [m.get("responde") for m in E.chat(N) if m["quem"] == "agente"]
    ok("4 em fila e na ordem", todas and ordem[:4] == [i1, i2, i3, i4], f"respostas na ordem: {ordem[:4] == [i1, i2, i3, i4]}")
    # 5. servidor derrubado antes de responder
    pid = servidor_pid()
    i5 = str(uuid.uuid4())
    post(f"/api/item/{N}/mensagem", {"id": i5, "texto": "teste 5: responda só 'ok 5'"})
    if pid:
        os.kill(pid, signal.SIGKILL)
    for q in subprocess.run(["pgrep", "-f", "claude -p --model opus --permission-mode acceptEdits"], capture_output=True, text=True).stdout.split():
        os.kill(int(q), signal.SIGKILL)       # o agente que estava respondendo morre junto, como numa queda
    time.sleep(1)
    gravada = len(dele(i5)) == 1
    subprocess.Popen([sys.executable, "servidor.py"], cwd=RAIZ, stdout=open(RAIZ / "servidor.log", "a"), stderr=subprocess.STDOUT,
                     start_new_session=True)
    time.sleep(3)
    ok("5 servidor reiniciado", gravada and respondida(i5), f"gravada antes da queda={gravada}")
    print(f"\n{sum(p for _, p, _ in res)} de {len(res)} passaram")


if __name__ == "__main__":
    main()
