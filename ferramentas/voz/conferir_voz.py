#!/usr/bin/env python3
"""Conferência de narração: o áudio diz exatamente o texto? (29/09/2026)

Substitui a nota média do voz_alexandre.py v1, que deixou passar "colocar A inteligência artificial" com 0,96 e
reprovou frases certas porque o Whisper escreve "12" e "2.244" em algarismos e grafa marcas do jeito dele.
Agora: transcreve (Whisper small; se reprovar, confirma com o large-v3), normaliza números para extenso e marcas
conhecidas, e compara PALAVRA POR PALAVRA. Qualquer palavra a mais, a menos ou trocada reprova, e o relato diz qual.
Calibrado em testes/calibracao-voz/ (python3 testes/test_conferir_voz.py)."""
import difflib, re, subprocess, tempfile, unicodedata
from pathlib import Path

MODELOS = {"small": Path.home() / ".cache/whisper-cpp/ggml-small.bin",
           "large": Path.home() / ".cache/hyperframes/whisper/models/ggml-large-v3.bin"}
# marcas e nomes que o Whisper grafa de outro jeito: a forma escrita no roteiro -> tokens como são falados
MARCAS = {"kitebiz": ["kitebiz"], "vta": ["vta"], "erp": ["erp"], "morini": ["morini"]}
UNI = ["zero", "um", "dois", "três", "quatro", "cinco", "seis", "sete", "oito", "nove", "dez", "onze", "doze", "treze",
       "quatorze", "quinze", "dezesseis", "dezessete", "dezoito", "dezenove"]
DEZ = ["", "", "vinte", "trinta", "quarenta", "cinquenta", "sessenta", "setenta", "oitenta", "noventa"]
CEM = ["", "cento", "duzentos", "trezentos", "quatrocentos", "quinhentos", "seiscentos", "setecentos", "oitocentos", "novecentos"]


def extenso(n):
    """0 a 999.999 em português do Brasil."""
    if n < 20: return UNI[n]
    if n < 100: d, u = divmod(n, 10); return DEZ[d] + ("" if u == 0 else " e " + UNI[u])
    if n == 100: return "cem"
    if n < 1000: c, r = divmod(n, 100); return CEM[c] + ("" if r == 0 else " e " + extenso(r))
    m, r = divmod(n, 1000)
    mil = "mil" if m == 1 else extenso(m) + " mil"
    if r == 0: return mil
    return mil + (" e " if r < 100 or r % 100 == 0 else " ") + extenso(r)


# 22/10/2026 ("aprovo o plano idioma-do-video"): os números por extenso em espanhol e inglês (o Whisper escreve "11" e
# "2026"; o roteiro escreve "once" e "dos mil veintiséis"). Conferido nos casos de tests do plano (0 a 999.999)
UNI_ES = ["cero", "uno", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho", "nueve", "diez", "once", "doce", "trece",
          "catorce", "quince", "dieciseis", "diecisiete", "dieciocho", "diecinueve", "veinte", "veintiuno", "veintidos",
          "veintitres", "veinticuatro", "veinticinco", "veintiseis", "veintisiete", "veintiocho", "veintinueve"]
DEZ_ES = ["", "", "", "treinta", "cuarenta", "cincuenta", "sesenta", "setenta", "ochenta", "noventa"]
CEM_ES = ["", "ciento", "doscientos", "trescientos", "cuatrocientos", "quinientos", "seiscientos", "setecientos",
          "ochocientos", "novecientos"]
UNI_EN = ["zero", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve",
          "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen"]
DEZ_EN = ["", "", "twenty", "thirty", "forty", "fifty", "sixty", "seventy", "eighty", "ninety"]


def extenso_es(n):
    if n < 30: return UNI_ES[n]
    if n < 100: d, u = divmod(n, 10); return DEZ_ES[d] + ("" if u == 0 else " y " + UNI_ES[u])
    if n == 100: return "cien"
    if n < 1000: c, r = divmod(n, 100); return CEM_ES[c] + ("" if r == 0 else " " + extenso_es(r))
    m, r = divmod(n, 1000)
    mil = "mil" if m == 1 else extenso_es(m) + " mil"
    return mil + ("" if r == 0 else " " + extenso_es(r))


def extenso_en(n):
    if n < 20: return UNI_EN[n]
    if n < 100: d, u = divmod(n, 10); return DEZ_EN[d] + ("" if u == 0 else " " + UNI_EN[u])
    if n < 1000: c, r = divmod(n, 100); return UNI_EN[c] + " hundred" + ("" if r == 0 else " " + extenso_en(r))
    m, r = divmod(n, 1000)
    return extenso_en(m) + " thousand" + ("" if r == 0 else " " + extenso_en(r))


EXTENSO = {"pt": extenso, "es": extenso_es, "en": extenso_en}


def sem_acento(t):
    return "".join(c for c in unicodedata.normalize("NFD", t) if unicodedata.category(c) != "Mn")


def normalizar(t, idioma="pt"):
    t = t.lower()
    t = re.sub(r"\b([a-z0-9-]+)\.com\.br\b", r"\1 ponto com ponto b r", t)
    t = re.sub(r"(\d)\.(\d{3})\b", r"\1\2", t)                     # 2.244 -> 2244
    t = re.sub(r"\d+", lambda m: " " + EXTENSO[idioma](int(m.group())) + " ", t)
    ps = re.findall(r"[\wà-ú]+", sem_acento(t))
    out = []
    for p in ps:                                                      # grafias parecidas de marca contam como a marca
        alvo = "kitebiz" if p in ("kaitibiz", "kaitbiz", "kaiti", "caetbis", "kitbis") else next((m for m in MARCAS if difflib.SequenceMatcher(None, p, m).ratio() >= 0.6 and len(p) >= 3), None)
        out.append(alvo or p)
    # equivalências de fala (29/09): contração falada e grafias do Whisper que não são erro de voz
    # 17/10/2026 (ele: "mantém como era antes e tira isso do detector de erros"; o #298 travou com "pro arquivo
    # morto"): também pro/pros/pras/tá/tô; o roteiro e a legenda continuam escritos por extenso
    FALADA = {"pra": ["para"], "pro": ["para", "o"], "pros": ["para", "os"], "pras": ["para", "as"],
              "ta": ["esta"], "to": ["estou"]}
    out = [w for p in out for w in FALADA.get(p, [p])]
    j = []
    for p in out:
        if j and j[-1] == "chat" and p == "gpt":
            j[-1] = "chatgpt"
        elif j and j[-1] == "news" and p == "br":      # 15/10: "NewsBR360" na tela, "News BR trezentos e sessenta" na voz
            j[-1] = "newsbr"
        else:
            j.append(p)
    return j


def transcrever(wav, modelo="small", idioma="pt"):
    with tempfile.TemporaryDirectory() as d:
        w16 = Path(d) / "a.wav"
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(wav), "-ar", "16000", "-ac", "1", str(w16)], check=True)
        out = subprocess.run(["whisper-cli", "-m", str(MODELOS[modelo]), "-l", idioma, "-nt", "-f", str(w16)],
                             capture_output=True, text=True).stdout
    return " ".join(l.strip() for l in out.splitlines() if l.strip())


# 15/10/2026 ("aprovo o plano esteira"): a voz fala português natural e a conferência reprovava a MESMA palavra em outra
# forma ("compartilha" -> "compartilhe", "este" -> "esse", "está" -> "tá"): 4 vezes no dia (#111, #126, #130, #134), e cada
# uma parava a voz à espera de alguém. Regra da narração (CLAUDE.md, item 3): isso não é erro. A tela continua com o texto
# do roteiro.
_PARES = {("este", "esse"), ("esta", "essa"), ("isto", "isso"), ("estes", "esses"), ("estas", "essas"), ("esta", "ta"), ("estao", "tao")}


def equivalentes(x, y):
    if x == y or (x, y) in _PARES or (y, x) in _PARES:
        return True
    # a mesma palavra terminada em a/e (imperativo x indicativo: compartilha/compartilhe, segue/siga, manda/mande)
    return len(x) >= 5 and len(x) == len(y) and x[:-1] == y[:-1] and {x[-1], y[-1]} == {"a", "e"}


def nomes_proprios(texto, idioma="pt"):
    """As palavras com maiúscula no meio da frase do roteiro (nome de pessoa, instituto, lugar), já normalizadas. Sigla
    (duas maiúsculas ou mais: "MEIs", "PGR") fica de fora: "MEIs" ouvido "meios" pode ser a voz errando."""
    out, inicio = set(), True
    for w in re.findall(r"[\wÀ-ú]+|[.!?:]", texto):
        if w in ".!?:":
            inicio = True; continue
        if not inicio and w[0].isupper() and sum(c.isupper() for c in w) < 2:
            out.update(normalizar(w, idioma))
        inicio = False
    return out


def diferencas(texto, ouvido, idioma="pt"):
    a, b = normalizar(texto, idioma), normalizar(ouvido, idioma)
    nomes = nomes_proprios(texto, idioma)
    ds = []
    for op, i1, i2, j1, j2 in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if op == "equal": continue
        # 22/10/2026 ("aprovo o plano voz-nomes"; o #344 travou com a voz certa): o nome junto ou separado é a mesma
        # palavra ("AtlasIntel" x "Atlas Intel", "PoderData" x "Poder Data", e o Whisper partindo "Lula" em "Lu lá")
        if op == "replace" and "".join(a[i1:i2]) == "".join(b[j1:j2]):
            continue
        # e o nome próprio do roteiro grafado parecido pela transcrição ("Quaest" -> "Quest"): só nome com maiúscula no
        # meio da frase; palavra comum trocada continua reprovando
        if (op == "replace" and i2 - i1 == j2 - j1
                and all(x == y or (x in nomes and difflib.SequenceMatcher(None, x, y).ratio() >= .75) for x, y in zip(a[i1:i2], b[j1:j2]))):
            continue
        if op == "replace" and i2 - i1 == j2 - j1 and all(equivalentes(x, y) for x, y in zip(a[i1:i2], b[j1:j2])):
            continue
        # vídeo em outro idioma (22/10/2026, idioma-do-video; #334): o nome em português dito certo o Whisper grafa no
        # idioma dele ("Consolação" -> "Consolación", "Linha Verde" -> "línea verde", "Brigadeiro" -> "Brigadero",
        # "Prefeitura" -> "prefectura"); grafia parecida (75%) palavra por palavra não é erro de voz
        if (idioma != "pt" and op == "replace" and i2 - i1 == j2 - j1
                and all(difflib.SequenceMatcher(None, x, y).ratio() >= .75 for x, y in zip(a[i1:i2], b[j1:j2]))):
            continue
        if op == "delete" and a[i1:i2] in (["a"], ["o"]) and i1 > 0 and a[i1 - 1] == "para":   # "para a próxima" dito "pra próxima"
            continue
        ds.append(f"{op}: '{' '.join(a[i1:i2])}' -> '{' '.join(b[j1:j2])}'")
    return ds


def conferir(wav, texto):
    """(ok, diferenças, transcrição, modelo usado). Small primeiro; o large só confirma uma reprovação."""
    ouvido = transcrever(wav, "small"); ds = diferencas(texto, ouvido)
    if not ds:
        return True, [], ouvido, "small"
    ouvido = transcrever(wav, "large"); ds = diferencas(texto, ouvido)
    return (not ds), ds, ouvido, "large"
