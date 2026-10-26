"""A voz do vídeo (estúdio v2, 16/10/2026, "aprovo o plano v2-parte2-voz").

  python3 voz.py <número>        grava (ou regrava só o que mudou) e monta o áudio do roteiro

1. Cada fala nossa é gravada com a voz dele (ferramentas/narrador.py da v1: Gemini, a voz replicada) e conferida pela
   transcrição; até 3 tentativas. O arquivo tem o nome do texto falado: fala que não mudou não é regravada, então
   mudar o bloco 3 regrava só o bloco 3.
2. O trecho da outra pessoa é cortado do áudio da pauta pelo corte do bloco ("(início-fim)", que saiu das palavras).
3. O áudio final é montado DIRETO das peças, na ordem dos blocos, com a mesma pausa entre elas. Ninguém recorta uma
   trilha já emendada (era assim na v1, e foi daí que saiu o "Lula, Lula" do #126).
4. Conferência: o começo e o fim de cada trecho da pessoa são as palavras do roteiro; o volume das peças não destoa.
Grava narracao/completo.mp3 e narracao/completo.json (onde cada bloco começa e termina) e a situação na ficha.
"""
import hashlib, json, re, subprocess, sys, tempfile, time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import estudio as E

sys.path.insert(0, str(E.RAIZ / "ferramentas"))
import narrador as N

FALA_PADRAO = {"Instituto BR360": "Instituto BR trezentos e sessenta", "NewsBR360": "News BR trezentos e sessenta"}
# a mesma marca dita no idioma do vídeo (22/10/2026, "aprovo o plano idioma-do-video")
FALA_IDIOMA = {"pt": FALA_PADRAO,
               "es": {"Instituto BR360": "Instituto BR trescientos sesenta", "NewsBR360": "News BR trescientos sesenta"},
               "en": {"Instituto BR360": "Instituto BR three sixty", "NewsBR360": "News BR three sixty"}}
# 22/10/2026 (ele: "o video em espanhol ficou parte em espanhol e parte em pt br"; medido no #334: com a instrução de
# estilo em português, o Whisper ouviu português em 7 de 8 trechos, a voz lia o espanhol com pronúncia de português;
# com a instrução escrita em espanhol, 2 de 2 tomadas ouvidas como espanhol). O português continua com a de sempre
ESTILO_IDIOMA = {"es": "narración natural en español latinoamericano neutro, con pronunciación española, en el tono de la voz "
                       "de referencia, sin exagerar",
                 "en": "natural narration in neutral American English, with English pronunciation, in the tone of the reference "
                       "voice, without exaggeration"}
WHISPER_IDIOMA = {"es": "spanish", "en": "english"}
PAUSA = 0.40             # entre um bloco e outro (a da v1)
RITMO = N.RITMO_ALVO     # sílabas por segundo na régua do gerador (a da v1)
CORTE = E.CORTE          # o mesmo do estudio.py (aceita a origem: material/<código>)


def _norm(p):
    import unicodedata
    p = "".join(c for c in unicodedata.normalize("NFD", str(p).lower()) if unicodedata.category(c) != "Mn")
    return re.sub(r"[^\w]", "", p)


def dur(arq):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(arq)]))


def gravar_fala(fr, texto, idioma="pt"):
    """(ok, wav, nota): grava e confere uma fala; a já gravada com o mesmo texto falado é reaproveitada. idioma: o da
    conferência (a transcrição ouve nele)."""
    falado = N.falado(texto)
    estilo = ESTILO_IDIOMA.get(idioma)
    # fora do português a chave leva o idioma e o estilo: a fala gravada com a instrução de antes não é reaproveitada
    chave = hashlib.md5((falado if not estilo else f"{idioma}|{estilo}|{falado}").encode()).hexdigest()[:12]
    wav, meta = fr / f"{chave}.wav", fr / f"{chave}.json"
    if wav.exists() and meta.exists() and json.loads(meta.read_text()).get("ok"):
        return True, wav, "guardada"
    ouvido, ds = "", []
    for t in range(1, 4):
        with tempfile.TemporaryDirectory() as d:
            b = Path(d) / "b.wav"; b.write_bytes(N.v.tts(falado, estilo)); N.v.limpar(b, wav)
        ok, ds, ouvido, modelo = N.conferir(wav, texto, idioma)
        if ok and idioma in WHISPER_IDIOMA:
            # e soa no idioma do vídeo: o Whisper, sem saber o idioma, tem que ouvir esse (no #334 a frase passava na
            # conferência em espanhol e o ouvido dele ouvia português)
            try:
                from transcrever import idioma_ouvido
                ouviu = idioma_ouvido(wav)
            except Exception:
                ouviu = ""
            if ouviu and ouviu != WHISPER_IDIOMA[idioma]:
                ok, ds = False, [f"sotaque: a voz soou como {ouviu} (o vídeo é em {E.IDIOMAS[idioma]})"]
        leve = not ok and leve_demais(texto, ouvido, ds)
        meta.write_text(json.dumps({"texto": texto, "falado": falado, "ok": ok, "ouvido": ouvido, "diferencas": ds,
                                    "tentativa": t, "quando": E.agora()}, ensure_ascii=False, indent=1))
        if ok:
            return True, wav, f"gravada (tentativa {t})"
        if leve and t == 3:
            # 16/10/2026 (#201: "diz" por "disse", "tava" por "estava"; regra 3 da narração na v1: contração falada não é
            # erro): diferença de até 2 palavras passa, e o aviso fica na tela com o que a voz disse
            m = json.loads(meta.read_text()); m["ok"] = True; m["leve"] = True; meta.write_text(json.dumps(m, ensure_ascii=False, indent=1))
            return True, wav, f"aviso: a voz disse \"{ouvido}\""
    return False, wav, f"a voz disse \"{ouvido}\" ({'; '.join(ds)[:160]})"


def leve_demais(texto, ouvido, ds=None):
    """Diferença pequena entre o roteiro e o que a voz disse: até 2 palavras, contando nas diferenças que a conferência
    da v1 já calcula depois de igualar números e siglas ("8%" e "oito por cento"). Contração falada não conta."""
    troca = {"ta": "esta", "tava": "estava", "pra": "para", "pro": "para", "to": "estou"}
    total = 0
    for d in ds or []:
        m = re.match(r"\w+: '(.*)' -> '(.*)'$", d)
        if not m:
            return False
        a, b = ([troca.get(_norm(x), _norm(x)) for x in s.split() if _norm(x)] for s in m.groups())
        if a == b:
            continue
        total += max(len(a), len(b))
    return 0 < total <= 2 or (ds is not None and total == 0)


def gravar(num):
    p = E.pasta(num)
    nar = p / "narracao"; fr = nar / "frases"; fr.mkdir(parents=True, exist_ok=True)
    bs = E.blocos(num)
    if not bs:
        raise RuntimeError("o vídeo não tem roteiro")
    marca = hashlib.md5((p / "ROTEIRO.md").read_bytes()).hexdigest()
    lingua = E.idioma(num)
    N.FALA.clear(); N.FALA.update(FALA_IDIOMA[lingua])
    nossos = [b for b in bs if b["nosso"]]
    t0 = time.time()
    with ThreadPoolExecutor(2) as ex:
        res = dict(zip([b["n"] for b in nossos], ex.map(lambda b: gravar_fala(fr, b["fala"], lingua), nossos)))
    ruins = [f"bloco {n}: {nota}" for n, (ok, _, nota) in res.items() if not ok]
    if ruins:
        raise RuntimeError("a voz não conseguiu falar certo depois de 3 tentativas: " + " · ".join(ruins)
                           + ". Peça ao agente para reescrever esse bloco com outras palavras; a voz regrava sozinha.")
    novas = [n for n, (_, _, nota) in res.items() if nota != "guardada"]
    avisos = [f"bloco {n}: {nota[7:]}" for n, (_, _, nota) in res.items() if nota.startswith("aviso:")]
    # ritmo: um fator só para todas as nossas falas, até o ritmo da v1
    sil = sum(N.silabas(N.falado(b["fala"])) for b in nossos)
    seg = sum(dur(res[b["n"]][1]) for b in nossos)
    fator = round(min(1.45, max(0.9, RITMO / (sil / seg))), 3)
    pecas, blocos_t, problemas, t = [], [], [], 0.0
    with tempfile.TemporaryDirectory() as d:
        d = Path(d)
        for b in bs:
            pc = d / f"b{b['n']:02d}.wav"
            if b["nosso"]:
                subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(res[b["n"]][1]), "-af", f"atempo={fator},loudnorm=I=-16:TP=-1.5",
                                "-ar", "44100", "-ac", "1", str(pc)], check=True)
            else:
                c = E.corte(b["fala"])
                audio = p / (c[2] if c else "referencia") / "audio.m4a"
                if not c or not audio.exists():
                    raise RuntimeError(f"bloco {b['n']}: trecho sem corte ou sem o áudio de {c[2] if c else 'origem'}")
                a, z = c[0], c[1]
                subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", f"{a:.3f}", "-to", f"{z:.3f}", "-i", str(audio),
                                "-af", "afade=t=in:d=0.03,areverse,afade=t=in:d=0.06,areverse,loudnorm=I=-16:TP=-1.5",
                                "-ar", "44100", "-ac", "1", str(pc)], check=True)
                problemas += confere_trecho(b, pc, p, c)
            dd = dur(pc)
            blocos_t.append({"n": b["n"], "nosso": b["nosso"], "ini": round(t, 2), "fim": round(t + dd, 2)})
            pecas.append(pc); t += dd
            if b is not bs[-1]:
                pa = d / f"p{b['n']:02d}.wav"
                subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=44100:cl=mono", "-t", str(PAUSA), str(pa)], check=True)
                pecas.append(pa); t += PAUSA
        (d / "l.txt").write_text("".join(f"file '{x}'\n" for x in pecas))
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(d / "l.txt"), "-af",
                        "loudnorm=I=-16:TP=-1.5", "-ar", "44100", "-ac", "1", "-b:a", "160k", str(nar / "completo.mp3")], check=True)
    total = dur(nar / "completo.mp3")
    # 22/10/2026 ("aprovo o plano fluxo-viral-util"; o curso Fluxo Viral, G4: o gancho falado termina até 3 s, medido na voz
    # pronta): o fim da 1ª frase do bloco 1, pela parte das sílabas dela no tempo do bloco. Só aviso, não trava
    g = gancho(bs, blocos_t)
    if g and g["fim"] > GANCHO_S:
        avisos.insert(0, f"gancho: a primeira frase termina aos {g['fim']:.1f} s (o curso pede até {GANCHO_S:.0f} s): \"{g['frase'][:90]}\"")
    # 25/10/2026 (plano de melhorias): gravação atômica (a tela lia o completo.json pela metade e dava erro)
    E._grava(nar / "completo.json", json.dumps({"duracao": round(total, 2), "fator": fator, "roteiro": marca, "blocos": blocos_t,
                                                "problemas": problemas, "avisos": avisos, "gancho": g, "quando": E.agora()},
                                               ensure_ascii=False, indent=1))
    E.evento(num, f"voz montada: {total:.1f} s, {len(novas)} fala(s) gravada(s) agora {novas}, {len(problemas)} problema(s), em {time.time() - t0:.0f} s")
    return {"duracao": total, "novas": novas, "problemas": problemas}


GANCHO_S = 3.0
GANCHO_AJUSTE = 0.3


def gancho(bs, blocos_t):
    """{"frase", "fim"}: a primeira frase do vídeo e em que segundo da voz ela termina. Bloco 1 nosso: a parte das sílabas
    da 1ª frase no tempo do bloco; bloco 1 de outra pessoa (o trecho abre o vídeo): o fim do trecho."""
    if not bs or not blocos_t:
        return None
    b, t = bs[0], blocos_t[0]
    if not b["nosso"]:
        return {"frase": E.CORTE.sub("", b["fala"]).strip(), "fim": round(t["fim"], 2)}
    frase = re.split(r"(?<=[.!?])\s+", b["fala"].strip(), maxsplit=1)[0]
    total = N.silabas(N.falado(b["fala"])) or 1
    # +0,3 s: calibrado em 22/10/2026 contra o tempo de cada palavra (7 vozes, #301-#330): a conta por sílabas termina
    # em média 0,3 s antes do real (erro de +0,07 a -0,5 s; com a correção, até 0,4 s)
    fim = t["ini"] + (t["fim"] - t["ini"]) * min(1, N.silabas(N.falado(frase)) / total) + GANCHO_AJUSTE
    return {"frase": frase, "fim": round(min(fim, t["fim"]), 2)}


def corte_confirmado(esperado, p, c):
    """19/10/2026 (achado voz.1; ele: "pode fazer as duas"): a transcrição da pauta, com o tempo de cada palavra, já diz
    se o corte cai nas palavras certas. Se a primeira palavra dentro do corte é a primeira da fala, a última é a última
    e o corte não começa no meio da palavra anterior nem termina antes do fim da última, o corte está certo, e a
    transcrição do pedacinho (que erra em trecho curto: "matatalareu" no #301) não precisa ser feita."""
    if not c or len(esperado) < 2:
        return False
    try:
        ws = json.loads((p / (c[2] or "referencia") / "palavras.json").read_text())
    except (OSError, ValueError):
        return False
    a, z = c[0], c[1]
    dentro = [w for w in ws if a - .12 <= w[0] < z - .05]           # palavras que começam dentro do corte
    if not dentro:
        return False
    antes = [w for w in ws if w[0] < a - .12]
    corta_anterior = bool(antes) and antes[-1][1] > a + .05          # o corte começa no meio da palavra anterior
    return (_norm(dentro[0][2]) == esperado[0] and _norm(dentro[-1][2]) == esperado[-1]
            and not corta_anterior and dentro[-1][1] <= z + .25)


def confere_trecho(b, pc, p=None, c=None):
    """O trecho cortado começa e termina nas palavras do roteiro (palavra comida = o corte pegou errado)."""
    sys.path.insert(0, str(E.RAIZ / "ferramentas"))
    from transcrever import palavras
    esperado = [_norm(x) for x in CORTE.sub("", b["fala"]).split() if _norm(x)]
    if p is not None and corte_confirmado(esperado, p, c):
        return []
    try:
        ouvido = [_norm(w[2]) for w in palavras(pc)[0] if _norm(w[2])]
    except BaseException:
        return []
    if len(esperado) < 2 or len(ouvido) < 2:
        return []
    erros = []
    if esperado[0] not in ouvido[:2]:
        erros.append(f"bloco {b['n']}: o trecho devia começar em \"{esperado[0]}\" e começa em \"{ouvido[0]}\"")
    if esperado[-1] not in ouvido[-2:]:
        erros.append(f"bloco {b['n']}: o trecho devia terminar em \"{esperado[-1]}\" e termina em \"{ouvido[-1]}\"")
    return erros


if __name__ == "__main__":
    print(json.dumps(gravar(int(sys.argv[1])), ensure_ascii=False, indent=1))
