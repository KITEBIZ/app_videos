#!/usr/bin/env python3
"""Narrador da @newsbr360 (08/10/2026): o gerador de narração que cada vídeo copiava (jev-v2 → janja → miriam →
pimenta, 155 linhas por vídeo), agora num lugar só. As frases vêm da ficha do vídeo (checagem.yaml: `frases` e `fala`),
não mais digitadas no src/narrar.py. Alexandre: "pode fazer" (newsbr360/ANALISE-GERADOR.md, item 1).
Regras da narração: conteudo/CLAUDE.md ("Regra da narração"). Prova: as frases do pimenta pela ficha batem com as
aprovadas (guardadas, mesmo texto) e o fator de ritmo calculado é o mesmo do áudio publicado.

  python3 ../ferramentas/checagem.py narrar [--refazer 3 7] [--seco]
"""
import argparse, json, re, subprocess, sys, tempfile, time, unicodedata
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "voz"))
import voz_alexandre as v
import conferir_voz as cv
import narrar as n_deliverit

FRASES, FALA = [], {}      # preenchidos por rodar() a partir da ficha
# ritmo (briefing de 03/10: "Ritmo mais rápido nos primeiros 10 a 15 segundos. Depois estabilizar."): o bloco de
# abertura (frases 1 a INICIO) vai a RITMO_INICIO, o resto ao RITMO_ALVO. Desde 06/10 (regra do CLAUDE.md do conteudo,
# "pode gravar as regras"): os alvos reproduzem o jev-v2 publicado. Na régua do alinhamento ele tem 6,26 e 5,86
# sílabas/s; na régua do gerador (sílabas / duração do arquivo de cada frase) isso dá 6,04 e 5,70. Calibrado: com estes
# alvos, as frases do jev-v2 saem com os fatores 1,266 e 1,031 que foram publicados.
RITMO_ALVO = 6.58          # sílabas por segundo (régua do gerador), frases depois da abertura
RITMO_INICIO = 6.58        # sílabas por segundo (régua do gerador), abertura
# 06/10: "pode fazer com +10% e sem respiros" (referência @denderson.ai: nenhum silêncio entre frases)
# 06/10, v2: ritmo e pausas do vídeo de referência (medido: 6,82 sílabas/s falando = 6,58 na régua do gerador;
# 0,3-0,8 s entre frases). Alexandre: "o audio nào ficou bom compara com o audio original"
PAUSA = 0.40
# "Criar pequenas pausas antes das frases principais": respiro maior DEPOIS destas frases (índice 1-based)
# 06/10: menores (eram 0,55-0,60), o Gemini achou o ritmo arrastado; as frases-chave mudaram de número com a saída do agente
PAUSA_LONGA = {}
INICIO = 1
# fatores da narração aprovada em 03/10 ("aprovo"): mantidos para as frases que ficaram soarem iguais e os takes do avatar
# (feitos sobre esse áudio) continuarem casando com a boca
# VÍDEO NOVO: FATOR_APROVADO = None e ACELERA = 1 (o gerador mede a voz e calcula o fator até os alvos acima).
FATOR_APROVADO = None
ACELERA = 1
DIR = FR = NOME = None


def falado(t):
    for a, b in FALA.items():
        t = t.replace(a, b)
    return v.falado(t)


def ouvir(wav, modelo, idioma="pt"):
    """O que a voz disse. 08/10/2026 ("vê se tem como deixar mais rápido"): na VPS o Whisper local levava 8 s (pequeno) e
    43 s (grande) por frase; a Groq roda o mesmo large-v3 em ~1 s. Sem chave da Groq ou se ela falhar, volta ao local."""
    if modelo == "groq":
        import os
        if not os.environ.get("GROQ_API_KEY"):
            return None
        try:
            sys.path.insert(0, str(Path(__file__).resolve().parent))
            from transcrever import palavras
            return palavras(wav, idioma)[1].strip()
        except BaseException:
            return None
    return cv.transcrever(wav, modelo, idioma)


def conferir(wav, texto, idioma="pt"):
    """idioma (22/10/2026, "aprovo o plano idioma-do-video"): a transcrição ouve no idioma do vídeo. Ouvindo como português,
    o Whisper devolvia o espanhol do #334 meio traduzido ("El Metrô presentó" -> "O metrô apresentou") e as 3 tentativas
    reprovavam uma voz que falou certo."""
    alvo = falado(texto)
    for modelo in ("groq", "small", "large"):
        ouvido = ouvir(wav, modelo, idioma)
        if ouvido is None:
            continue
        if idioma == "pt":
            norm = re.sub(r"\b([Tt])á\b", lambda m: "Está" if m.group(1) == "T" else "está", ouvido)
            norm = re.sub(r"\b[Ee]mail\b", "e-mail", norm)
            norm = norm.replace("6x1", "seis por um")    # o Whisper escreve a escala em algarismos
            norm = re.sub(r"\b7,5\s*%", "sete e meio por cento", norm)   # 08/10: o Whisper escreve 32% e 7,5%
            # revisão de 08/10: qualquer decimal ("3,2%") reprovava; o roteiro escreve "três vírgula dois"
            norm = re.sub(r"\b(\d+),(\d+)", r"\1 vírgula \2", norm).replace("%", " por cento")
        else:                                        # o mesmo, falado no idioma do vídeo (idioma-do-video)
            virgula, cento = {"es": (" coma ", " por ciento"), "en": (" point ", " percent")}[idioma]
            norm = re.sub(r"\b(\d+)[,.](\d+)", lambda m: m.group(1) + virgula + m.group(2), ouvido).replace("%", cento)
        # regra 4 da narração: a conferência aceita a sigla escrita pelo Whisper (09/10: "PGR" reprovava "pê gê érre")
        for sig, dita in FALA.items():
            if sig.isupper() and sig.isalpha():
                norm = re.sub(rf"\b{sig}\b", dita, norm)
        ds = cv.diferencas(alvo, norm, idioma)
        if not ds:
            return True, [], ouvido, modelo
        if modelo == "groq":       # a Groq já é o large-v3: reprovação dela vale, sem refazer no local
            return False, ds, ouvido, modelo
    return False, ds, ouvido, modelo


def frase(i, texto, refazer):
    wav, meta = FR / f"f{i:02d}.wav", FR / f"f{i:02d}.json"
    if wav.exists() and meta.exists() and not refazer:
        m = json.loads(meta.read_text())
        # revisão de 08/10: mudar o `fala` (pronúncia) também refaz a frase
        if m.get("texto") == texto and m.get("ok") and m.get("falado", falado(texto)) == falado(texto):
            return i, True, "guardada"
    for t in range(1, 4):
        with tempfile.TemporaryDirectory() as d:
            b = Path(d) / "b.wav"; b.write_bytes(v.tts(falado(texto))); v.limpar(b, wav)
        ok, ds, ouvido, modelo = conferir(wav, texto)
        meta.write_text(json.dumps({"texto": texto, "falado": falado(texto), "ok": ok, "ouvido": ouvido, "diferencas": ds, "modelo": modelo,
                                    "tentativa": t, "quando": time.strftime("%Y-%m-%d %H:%M")}, ensure_ascii=False, indent=1))
        if ok:
            return i, True, f"tentativa {t} ({modelo})"
    return i, False, f"ouvido: {ouvido} | " + "; ".join(ds)


def silabas(t):
    t = "".join(c for c in unicodedata.normalize("NFD", t.lower()) if unicodedata.category(c) != "Mn")
    return len(re.findall(r"[aeiouy]+", t))


def duracao(p):
    return float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(p)]))


def fatores():
    """Um fator por bloco (abertura e resto). Em 03/10 foi medido na soma do bloco até RITMO_INICIO e RITMO_ALVO; desde
    06/10 fica o da narração aprovada (FATOR_APROVADO). Fator por frase não serve (03/10): frase curta com pausa dentro
    saiu x1,55 e frase falada rápido saiu x0,65."""
    if FATOR_APROVADO is None:
        def fator(ids, alvo):
            s = sum(silabas(falado(FRASES[i - 1])) for i in ids)
            d = sum(duracao(FR / f"f{i:02d}.wav") for i in ids)
            return round(alvo / (s / d), 3)
        base = (fator(range(1, INICIO + 1), RITMO_INICIO), fator(range(INICIO + 1, len(FRASES) + 1), RITMO_ALVO))
    else:
        base = FATOR_APROVADO
    ini, resto = (round(f * ACELERA, 3) for f in base)
    return [ini if i <= INICIO else resto for i in range(1, len(FRASES) + 1)]


def rodar(aqui, nome, frases, fala=None, refazer=(), seco=False, inicio=1):
    """Gera (ou reaproveita) cada frase, confere pelo Whisper, emenda, nivela e alinha. seco=True para depois da
    conferência e devolve os fatores de ritmo (sem emendar nem chamar o alinhamento pago)."""
    global DIR, FR, NOME, FRASES, FALA, INICIO
    DIR = Path(aqui) / "narracao"; FR = DIR / "frases"; NOME = nome
    FRASES[:] = frases; FALA.clear(); FALA.update(fala or {}); INICIO = inicio
    if not 1 <= INICIO < len(FRASES):
        sys.exit(f"inicio = {INICIO}: precisa ser de 1 a {len(FRASES) - 1} (frases da abertura)")
    class A: pass
    a = A(); a.refazer = list(refazer)
    FR.mkdir(parents=True, exist_ok=True); t0 = time.time()
    with ThreadPoolExecutor(2) as ex:
        res = list(ex.map(lambda p: frase(p[0], p[1], p[0] in a.refazer), enumerate(FRASES, 1)))
    for i, ok, nota in res:
        print(f"  {i:2d} {'ok ' if ok else 'RUIM'} {nota}", flush=True)
    if not all(ok for _, ok, _ in res):
        sys.exit("há frase reprovada; nada emendado")
    F = fatores(); print("  aceleração por frase", F)
    if seco:
        return F
    mp3 = DIR / f"{NOME}.mp3"
    with tempfile.TemporaryDirectory() as d:
        d = Path(d); linhas = []
        for i, fa in enumerate(F, 1):
            r = d / f"r{i:02d}.wav"; p = d / f"p{i:02d}.wav"
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(FR / f"f{i:02d}.wav"), "-af", f"atempo={fa}",
                            "-ar", "24000", "-ac", "1", str(r)], check=True)
            subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "lavfi", "-i", "anullsrc=r=24000:cl=mono", "-t",
                            str(PAUSA_LONGA.get(i, PAUSA)), str(p)], check=True)
            linhas += [f"file '{r}'\n", f"file '{p}'\n"]
        (d / "l.txt").write_text("".join(linhas))
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", str(d / "l.txt"), "-c", "copy",
                        str(d / "j.wav")], check=True)
        subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(d / "j.wav"), "-af", "loudnorm=I=-16:TP=-1.5",
                        "-ar", "44100", "-ac", "1", "-b:a", "160k", str(mp3)], check=True)
    ditas = [falado(f) for f in FRASES]
    texto = " ".join(ditas)
    al = n_deliverit.alinhar(mp3, texto)
    ch = al["characters"]; assert "".join(c["text"] for c in ch) == texto
    frases, pos = [], 0
    for f, dita in zip(FRASES, ditas):
        i = texto.index(dita, pos); j = i + len(dita) - 1
        palavras, k = [], i
        for w in dita.split(" "):
            palavras.append({"p": w, "ini": ch[k]["start"], "fim": ch[k + len(w) - 1]["end"]}); k += len(w) + 1
        frases.append({"frase": f, "dita": dita, "ini": ch[i]["start"], "fim": ch[j]["end"], "palavras": palavras}); pos = j + 1
    dur = float(subprocess.check_output(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(mp3)]))
    json.dump({"voz": v.VOZ, "velocidade": F, "duracao": dur, "perda_alinhamento": al.get("loss"), "frases": frases},
              open(DIR / f"{NOME}.json", "w"), ensure_ascii=False, indent=1)
    print(f"{NOME}.mp3 {dur:.1f} s · alinhamento perda {al.get('loss', 0):.2f} · {time.time() - t0:.0f} s")
    for f in frases:
        print(f"  {f['ini']:6.2f} {f['fim']:6.2f}  {f['frase'][:60]}")

