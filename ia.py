"""Chamar a IA (claude -p) de um lugar só (25/10/2026, ele: "pode fazer" o "chamar IA" único; eram 12 lugares, cada um
com o seu jeito de prazo, gasto e erro: em vários o prazo não valia, o erro sumia calado e o gasto não era anotado).

  texto, uso = chamar(entrada, quem, modelo="sonnet", num=None, limite=600, ferramentas="", ...)

entrada: o texto do pedido, ou a lista de blocos (texto e imagens, como o animador manda). Devolve o texto da resposta
("" = falhou) e uso = {"segundos", "usd", "erro", "tentativas", "s" (o resultado inteiro do claude)}. Sempre:
  - prazo de verdade (o processo e os filhos param em `limite` s, mesmo com quem chamou esperando a saída);
  - o uso da conta guardado (a tela mostra) e, com `num`, a linha no gasto do vídeo;
  - registro opcional da conversa inteira (`registro`: o arquivo .jsonl);
  - ferramentas de arquivo sempre com caminho (Read/Edit/Write/Glob/Grep só na pasta do trabalho e nas pastas de leitura
    do estúdio; regras/ só leitura). Provado em 25/10 com o claude -p: sem caminho, ele lia um segredo fora da pasta.
  json_de(texto) tira o primeiro objeto (ou lista, com "[") JSON do texto, ou None.
"""
import json, re, subprocess, tempfile, threading, time
from pathlib import Path

import estudio as E

LEITURA_DO_ESTUDIO = ("regras", "web", "referencias")


def com_caminho(permitidas):
    """As permissões com caminho: "Read" vira "Read(./**)" e as pastas de LEITURA_DO_ESTUDIO; "Edit"/"Write" só "./**"."""
    raiz, out = str(E.RAIZ), []
    for item in permitidas:
        for nome in ([item] if "(" in item else item.split(",")):
            nome = nome.strip()
            if nome in ("Read", "Glob", "Grep"):
                out += [f"{nome}(./**)"] + [f"{nome}(/{raiz}/{d}/**)" for d in LEITURA_DO_ESTUDIO]
            elif nome in ("Edit", "Write"):
                out.append(f"{nome}(./**)")
            elif nome:
                out.append(nome)
    return out


def negadas():
    raiz = str(E.RAIZ)
    return [f"{f}(/{raiz}/regras/**)" for f in ("Edit", "Write")]


def comando(modelo, ferramentas="", permitidas=None, modo=None, dirs=(), blocos=False):
    cmd = ["claude", "-p", "--model", modelo, "--setting-sources", "", "--strict-mcp-config", "--tools", ferramentas,
           "--no-session-persistence", "--output-format", "stream-json", "--verbose"]
    if ferramentas:
        cmd += ["--allowedTools", *com_caminho(permitidas or [ferramentas]), "--disallowedTools", *negadas(),
                "--permission-mode", modo or "dontAsk"]
    for d in dirs:
        cmd += ["--add-dir", str(d)]
    if blocos:
        cmd += ["--input-format", "stream-json"]
    return cmd


def chamar(entrada, quem, modelo="sonnet", num=None, limite=600, ferramentas="", permitidas=None, modo=None, cwd=None,
           registro=None, dirs=(), ao_evento=None):
    """ao_evento(ev): chamado a cada evento enquanto a resposta chega (o agente do chat mostra cada passo na tela)."""
    t0 = time.time()
    blocos = isinstance(entrada, list)
    dados = json.dumps({"type": "user", "message": {"role": "user", "content": entrada}}) + "\n" if blocos else entrada
    with tempfile.TemporaryFile("w+") as erros:
        proc = subprocess.Popen(comando(modelo, ferramentas, permitidas, modo, dirs, blocos), stdin=subprocess.PIPE,
                                stdout=subprocess.PIPE, stderr=erros, text=True, cwd=cwd, start_new_session=True)
        prazo = E.prazo(proc, limite)

        def escreve():                       # à parte: pedido grande não trava enquanto a resposta já sai
            try:
                proc.stdin.write(dados); proc.stdin.close()
            except (BrokenPipeError, OSError, ValueError):
                pass
        threading.Thread(target=escreve, daemon=True).start()
        linhas = []
        try:
            for l in proc.stdout:                # linha a linha: o prazo para o processo e o laço acaba
                linhas.append(l)
                if ao_evento and l.startswith("{"):
                    try:
                        ao_evento(json.loads(l))
                    except Exception:            # o aviso de quem chamou nunca derruba a chamada
                        pass
            try:
                proc.wait(timeout=60)
            except subprocess.TimeoutExpired:
                E.mata(proc)
        finally:
            prazo.cancel()
        erros.seek(0); err = erros.read()
    saida = "".join(linhas)
    falha = f"passou de {limite} s" if prazo.estourou else ((err or "").strip()[-300:] or f"saiu com o código {proc.returncode}"
                                                           if proc.returncode else "")
    if registro:
        registro = Path(registro)
        registro.parent.mkdir(parents=True, exist_ok=True)
        registro.write_text((saida or "") + (json.dumps({"type": "estudio", "falha": falha}) + "\n" if falha else ""))
    eventos = []
    for l in (saida or "").splitlines():
        try:
            eventos.append(json.loads(l))
        except ValueError:
            pass
    for ev in eventos:
        if ev.get("type") == "rate_limit_event":
            E.guarda_limite(ev.get("rate_limit_info") or {})
    res = [ev for ev in eventos if ev.get("type") == "result"]
    s = res[-1] if res else {}
    if s and num is not None:
        E.anota_gasto(num, quem, modelo, s)
    if not s and not falha:
        falha = "o claude não devolveu resultado"
    texto = "" if falha or s.get("is_error") else (s.get("result") or "").strip()
    return texto, {"segundos": round(time.time() - t0, 1), "usd": s.get("total_cost_usd"),
                   "erro": falha or (s.get("result") if s.get("is_error") else ""), "s": s,
                   "tentativas": sum(1 for ev in eventos if ev.get("type") == "system" and ev.get("subtype") == "api_retry")}


def json_de(texto, abre="{"):
    """O primeiro objeto ("{") ou lista ("[") JSON do texto (do primeiro abre ao último fecha), ou None."""
    fecha = "}" if abre == "{" else "]"
    m = re.search(re.escape(abre) + r".*" + re.escape(fecha), texto or "", re.S)
    if not m:
        return None
    try:
        # strict=False: quebra de linha crua dentro de um texto (a tabela da CHECAGEM no campo do roteiro) é aceita; no
        # #405 (26/10/2026) o roteiro inteiro veio certo e foi jogado fora por isso, 4 minutos e US$ 0,73 perdidos
        return json.loads(m.group(0), strict=False)
    except ValueError:
        return None
