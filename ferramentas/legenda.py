#!/usr/bin/env python3
"""Legenda dos vídeos da máquina de conteúdo (30/09/2026, plano "legenda" aprovado pelo Alexandre).

Corta a fala em pedaços que se leem de uma vez. Regras trazidas do video-reels-test (smart-karaoke.cjs e
text-prep.cjs), mais três nossas: rótulo "Um:" nunca fica sozinho, número vira algarismo ANTES do corte
(senão "dez | mil linhas" se parte) e cada pedaço cabe numa linha (LIMITE letras).

  pedacos(palavras, numeros=True, limite=LIMITE, nomes=())  ->  [[{p, ini, fim}, ...], ...]

palavras: [{p, ini, fim}] como sai do alinhamento (narracao/*.json). Os tempos são preservados; um número falado
em várias palavras vira uma só ("dez mil" -> "10 mil"), do início da primeira ao fim da última.
numeros=False em relato histórico ("Dez anos depois" fica escrito, decisão de 08/09 no Farrapos).
Cor e letra não moram aqui: são da ficha de cada marca."""
import re

LIMITE = 30

# nunca terminar pedaço nestas (do text-prep.cjs do video-reels-test, mais as que pedem o substantivo seguinte:
# "qual", "cada", "qualquer", possessivos; 30/09: "Ele revisa cada | contrato" saía assim)
LIGACAO = set("""e a o as os de do da dos das no na nos nas em um uma uns umas que se por com sem para pra pro ao à
ou nem mais pelo pela até já não seu sua seus suas esse essa este esta isso isto só mas como foi ser ter
qual quais cada qualquer quaisquer meu minha meus minhas nosso nossa nossos nossas""".split())
# 22/10/2026 ("aprovo o plano idioma-do-video"): as mesmas, em espanhol e inglês (no #334 o pedaço "Tres estaciones del"
# terminava em "del"). Palavras que não existem em português: a legenda em português não muda
LIGACAO |= set("""y el la los las del al un unos unas en con sin para por su sus lo le les mi mis tu tus este esta estos
estas ese esa esos esas cual cuales cada cualquier muy ya ni pero como fue ser es son
the a an of to in on at for with by from and or but is are was were be its their his her our my your this that these
those which each any very not""".split())
# bom lugar para começar pedaço: início de oração ou de expressão (o corte antes delas ganha preferência)
ABRE = set("e ou mas que qual quais quem onde quando como porque se em com de para por sem".split())
# nomes compostos que não se partem, além de duas palavras seguidas com maiúscula no meio da frase
NOMES = [("inteligência", "artificial"), ("porto", "alegre"), ("são", "paulo"), ("rio", "grande", "do", "sul"),
         ("rio", "de", "janeiro"), ("santa", "maria"), ("vale", "do", "silício"), ("machine", "learning")]

NUM = {"zero": 0, "um": 1, "uma": 1, "dois": 2, "duas": 2, "três": 3, "tres": 3, "quatro": 4, "cinco": 5, "seis": 6,
       "sete": 7, "oito": 8, "nove": 9, "dez": 10, "onze": 11, "doze": 12, "treze": 13, "quatorze": 14,
       "catorze": 14, "quinze": 15, "dezesseis": 16, "dezessete": 17, "dezoito": 18, "dezenove": 19, "vinte": 20,
       "trinta": 30, "quarenta": 40, "cinquenta": 50, "sessenta": 60, "setenta": 70, "oitenta": 80,
       "noventa": 90, "cem": 100, "cento": 100, "duzentos": 200, "duzentas": 200, "trezentos": 300,
       "trezentas": 300, "quatrocentos": 400, "quinhentos": 500, "seiscentos": 600, "setecentos": 700,
       "oitocentos": 800, "novecentos": 900}
MULT = {"mil": 1000, "milhão": 10**6, "milhões": 10**6, "bilhão": 10**9, "bilhões": 10**9}


def limpa(p):
    return re.sub(r"[^\wà-úç%-]", "", p.lower())


def pont(p):
    m = re.search(r"[.,!?;:]+$", p)
    return m.group(0) if m else ""


def milhar(n):
    return f"{n:,}".replace(",", ".")


def algarismos(ws):
    """Número falado por extenso vira algarismo. Fica por extenso: 'um/uma' artigo, 'dois/duas/três' antes de
    substantivo ("Duas coisas"), número de rótulo ("Quatro:") e qualquer número sozinho seguido de dois-pontos."""
    saida, i = [], 0
    eh_num = lambda k: k < len(ws) and (limpa(ws[k]["p"]) in NUM or limpa(ws[k]["p"]) in MULT)
    while i < len(ws):
        c = limpa(ws[i]["p"])
        rotulo = ws[i]["p"].endswith(":")
        segue_num = eh_num(i + 1) or (i + 2 < len(ws) and limpa(ws[i + 1]["p"]) == "e" and eh_num(i + 2)) \
            or (i + 2 < len(ws) and limpa(ws[i + 1]["p"]) == "por" and limpa(ws[i + 2]["p"]).startswith("cento"))
        if rotulo or c not in NUM and c not in MULT or (c in ("um", "uma", "dois", "duas", "três", "tres") and not segue_num):
            saida.append(dict(ws[i])); i += 1; continue
        j, total, atual, ult_mult, sufixo = i, 0, 0, None, ""
        while j < len(ws):
            cj = limpa(ws[j]["p"])
            if cj in NUM:
                atual += NUM[cj]; ult_mult = None
            elif cj in MULT:
                total += (atual or 1) * MULT[cj]; ult_mult = cj; atual = 0
            elif cj == "e" and eh_num(j + 1):
                j += 1; continue
            elif cj == "por" and j + 1 < len(ws) and limpa(ws[j + 1]["p"]).startswith("cento"):
                sufixo = "%"; j += 2; break
            else:
                break
            if pont(ws[j]["p"]):          # "mil," termina o número
                j += 1; break
            j += 1
        total += atual
        fim = ws[j - 1]
        if sufixo:
            txt = f"{total}%"
        elif ult_mult:                     # "17 milhões", "10 mil": coeficiente + palavra
            txt = f"{milhar(total // MULT[ult_mult])} {ult_mult}"
        else:
            txt = str(total) if 2000 <= total <= 2099 else milhar(total)
        saida.append({"p": txt + pont(fim["p"]), "ini": ws[i]["ini"], "fim": fim["fim"]})
        i = j
    return saida


def nomes(ws, extras=()):
    """Posições k tais que cortar entre ws[k-1] e ws[k] partiria um nome."""
    presos = set()
    lista = [tuple(n) for n in NOMES] + [tuple(limpa(x) for x in n.split()) for n in extras]
    for n in lista:
        for i in range(len(ws) - len(n) + 1):
            if tuple(limpa(w["p"]) for w in ws[i:i + len(n)]) == n:
                presos.update(range(i + 1, i + len(n)))
    maiusc = lambda p: re.match(r"[A-ZÀ-Ý]", p) is not None
    for k in range(1, len(ws)):
        a, b = ws[k - 1]["p"], ws[k]["p"]
        inicio = k - 1 == 0 or re.search(r"[.!?:]$", ws[k - 2]["p"])
        if maiusc(a) and maiusc(b) and not pont(a) and not inicio and limpa(a) not in LIGACAO:
            presos.add(k)
    return presos


def largura(ws):
    return len(" ".join(w["p"] for w in ws))


def pode_cortar(ws, k, presos):
    """Corte antes de ws[k]: nenhum lado com uma palavra só (é o que prende "Um:" ao que vem depois), não termina em
    ligação, não parte nome. Rótulo de duas palavras pode fechar pedaço: "Etapa número dois: | revisa tudo." lê bem."""
    if k <= 1 or k >= len(ws) - 1 or k in presos:
        return False
    return limpa(ws[k - 1]["p"]) not in LIGACAO


def dividir(ws, limite, presos):
    """Divide em dois no corte mais equilibrado (preferindo antes de início de oração ou depois de vírgula), até caber.
    presos: posições relativas a ws (ver nomes())."""
    if largura(ws) <= limite:
        return [ws]
    melhor = None
    for k in range(1, len(ws)):
        if not pode_cortar(ws, k, presos):
            continue
        custo = max(largura(ws[:k]), largura(ws[k:]))
        if limpa(ws[k]["p"]) in ABRE or pont(ws[k - 1]["p"]):
            custo -= 6
        if melhor is None or custo < melhor[0]:
            melhor = (custo, k)
    if melhor is None:                      # nenhum corte limpo: fica inteiro (passa do limite, mas legível)
        return [ws]
    k = melhor[1]
    return dividir(ws[:k], limite, {p for p in presos if p < k}) + dividir(ws[k:], limite, {p - k for p in presos if p > k})


def pedacos(palavras, numeros=True, limite=LIMITE, nomes_extras=()):
    ws = algarismos(palavras) if numeros else [dict(w) for w in palavras]
    presos = nomes(ws, nomes_extras)
    saida, i = [], 0
    while i < len(ws):                      # 1) frase a frase: ponto, interrogação e exclamação sempre fecham
        j = i
        while j < len(ws) and not re.search(r"[.!?]$", ws[j]["p"]):
            j += 1
        frase = ws[i:j + 1]
        base = i; i = j + 1
        if largura(frase) <= limite:
            saida.append(frase); continue
        # 2) vírgula fecha quando o pedaço já tem 3+ palavras e sobram 2+ depois
        partes, ini = [], 0
        for k, w in enumerate(frase):
            if w["p"].endswith(",") and k + 1 - ini >= 3 and len(frase) - (k + 1) >= 2 and (base + k + 1) not in presos:
                partes.append((ini, frase[ini:k + 1])); ini = k + 1
        partes.append((ini, frase[ini:]))
        for ini, parte in partes:           # 3) o que ainda não cabe se divide pelo melhor corte
            saida += dividir(parte, limite, {p - base - ini for p in presos if p - base - ini > 0})
    for p in saida:                         # vírgula e ponto-e-vírgula no fim do pedaço somem
        p[-1] = dict(p[-1], p=re.sub(r"[,;]$", "", p[-1]["p"]))
    return saida
